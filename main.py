import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# ==========================================
# 1. НАСТРОЙКИ (ПОДДЕРЖКА ДВУХ КЛЮЧЕЙ)
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
# Берем два ключа из переменных окружения
KEYS = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]
# Оставляем только те ключи, которые реально добавлены
KEYS = [k for k in KEYS if k]

MODELS_PRIORITY = ['gemini-1.5-flash', 'gemini-1.5-pro']

bot = telebot.TeleBot(TOKEN)
user_states = {}

app = Flask('')
@app.route('/')
def home(): return "Закупщик на двух ключах!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==========================================
# 3. ЛОГИКА
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, f"Привет, {user_name}! Я готов. В каком ты городе?")

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
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
    
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = f"Цена на {yesterday} для {state['city']}, список {state['goods']} в {target_store}. Шаблон: Стоимость корзины в магазине {target_store} N (валюта)."
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Анализирую рынок г. {state['city']}...")
        prompt = (
            f"ИНСТРУКЦИЯ: Ты ИИ-закупщик. Текущая дата — {yesterday}. Никаких дисклеймеров о будущем. "
            f"Город: {state['city']}. Список товаров: {message.text}. "
            f"Выдай отчет СТРОГО по шаблону: "
            f"{user_name}! Наименьшая стоимость «корзины» составленной из твоего списка будет X (валюта). "
            f"Эта стоимость рассчитана при условии покупки всего перечня в ____. "
            f"Эта стоимость на Z меньше, чем в ближайшем альтернативном варианте. "
            f"Обрати внимание на товары с максимальной скидкой: (список). "
            f"Хочешь ли ты чтобы я рассчитал стоимость корзины для конкретного магазина? Если да напиши его название?"
        )

    # ЛОГИКА ПЕРЕБОРА КЛЮЧЕЙ И МОДЕЛЕЙ
    final_response = None
    for api_key in KEYS:
        if final_response: break
        genai.configure(api_key=api_key) # Переключаем ключ
        
        for model_name in MODELS_PRIORITY:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    final_response = response.text.strip()
                    break
            except Exception as e:
                print(f"Ключ {api_key[:5]}... Модель {model_name} ошибка: {e}")
                continue

    if final_response:
        bot.send_message(chat_id, final_response)
        user_states[chat_id]['step'] = 'recalc'
    else:
        bot.send_message(chat_id, "⚠️ Все ресурсы (ключи 1 и 2) временно исчерпаны. Попробуй через 2-3 минуты.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
