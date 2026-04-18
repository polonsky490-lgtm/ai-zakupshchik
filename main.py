import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
KEYS = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]
KEYS = [k for k in KEYS if k]

bot = telebot.TeleBot(TOKEN)
user_states = {}

app = Flask('')
@app.route('/')
def home(): return "Закупщик: Финальная шлифовка"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server, daemon=True)
    t.start()

# ==========================================
# 3. ЛОГИКА
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, f"Привет, {user_name}! В каком ты городе?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def get_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.reply_to(message, f"Принято: {message.text}. Что ищем?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list' or user_states.get(m.chat.id, {}).get('step') == 'recalc')
def handle_request(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state: return

    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    
    # Режим ПЕРЕРАСЧЕТА (УСИЛЕННЫЙ)
    if state.get('step') == 'recalc':
        target_store = message.text
        bot.send_message(chat_id, f"🔄 Пересчитываю стоимость для магазина {target_store}...")
        prompt = (
            f"ИНСТРУКЦИЯ: Ты — профессиональный закупщик. Твоя задача — дать цену товара/списка БЕЗ ЛИШНИХ СЛОВ. "
            f"КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать про 'будущие даты', 'отсутствие данных' или 'симуляции'. "
            f"Если не знаешь точную цену на сегодня, используй последнюю известную рыночную цену магазина {target_store}. "
            f"Город: {state['city']}. Товар: {state['goods']}. Магазин: {target_store}. "
            f"Ответь СТРОГО по шаблону: "
            f"Стоимость корзины в магазине {target_store} N (валюта официальная в этом городе)."
        )
    # Основной поиск
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Опрашиваю нейросети для г. {state['city']}...")
        prompt = (
            f"ИНСТРУКЦИЯ: Ты ИИ-закупщик. Считай текущий момент актуальным. Никаких дисклеймеров и 'воды'. "
            f"Город: {state['city']}. Список товаров: {message.text}. "
            f"Выдай отчет СТРОГО по шаблону: "
            f"{user_name}! Наименьшая стоимость «корзины» будет X (валюта) в (магазин). "
            f"Это на Z меньше, чем в ближайшем альтернативном варианте. "
            f"Скидки: (список). "
            f"Нужен расчет для конкретного магазина? Если да — напиши его название."
        )

    final_response = None
    last_error = "Не удалось получить ответ."

    for api_key in KEYS:
        if final_response: break
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not models: continue
            
            model = genai.GenerativeModel(models[0])
            response = model.generate_content(prompt)
            
            if response and response.text:
                final_response = response.text.strip()
            else:
                last_error = "ИИ вернул пустой ответ."
        except Exception as e:
            last_error = str(e)
            continue

    if final_response:
        bot.send_message(chat_id, final_response)
        user_states[chat_id]['step'] = 'recalc'
    else:
        bot.send_message(chat_id, f"❌ Ошибка: {last_error}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
