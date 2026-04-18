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
def home(): return "Закупщик: Контроль качества"

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
    
    # РЕЖИМ ПЕРЕРАСЧЕТА (С ВЕРИФИКАЦИЕЙ МОДЕЛИ)
    if state.get('step') == 'recalc':
        target_store = message.text
        bot.send_message(chat_id, f"🔄 Проверяю наличие и цену {state['goods']} в {target_store}...")
        prompt = (
            f"ИНСТРУКЦИЯ: Найди цену ТОЛЬКО на модель {state['goods']} в {target_store} (г. {state['city']}). "
            f"ВНИМАНИЕ: Сначала проверь, является ли найденная цена реальной именно для ЭТОЙ модели. "
            f"Если ты видишь цену 799 € для модели, которая стоит 1200 €+, это ошибка — не пиши её! "
            f"Если в {target_store} нет именно {state['goods']}, напиши: 'В {target_store} этой модели нет, но есть [Название] за [Цена]'. "
            f"Если модель ЕСТЬ, ответь СТРОГО: Стоимость корзины в магазине {target_store} N (валюта)."
        )
    # ОСНОВНОЙ ПОИСК
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Глубокий поиск для г. {state['city']}...")
        prompt = (
            f"ИНСТРУКЦИЯ: Найди лучшую цену на {message.text} в г. {state['city']}. "
            f"Сравни MediaMarkt, Saturn, Amazon, Otto. "
            f"ВАЖНО: Проверь соответствие букв и цифр в названии модели. Не путай Bravia 8 (XR80) с Bravia 3 или 7. "
            f"Выдай отчет СТРОГО по шаблону: "
            f"{user_name}! Наименьшая стоимость «корзины» будет X (валюта) в (магазин). "
            f"Это на Z меньше, чем в ближайшем альтернативном варианте. "
            f"Скидки: (коротко). "
            f"Хочешь расчет для конкретного магазина?"
        )

    final_response = None
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
                break
        except Exception:
            continue

    if final_response:
        bot.send_message(chat_id, final_response)
        user_states[chat_id]['step'] = 'recalc'
    else:
        bot.send_message(chat_id, "❌ Ошибка. Повтори запрос.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
