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
def home(): return "Закупщик в режиме отладки!"

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
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
    
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = f"Цена на {yesterday} для {state['city']} в магазине {target_store} для {state['goods']}. Ответь строго: Стоимость корзины в {target_store} N грн."
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Проверяю базу данных по г. {state['city']}...")
        prompt = (
            f"ИНСТРУКЦИЯ: Ты ИИ-закупщик. Текущая дата — {yesterday}. "
            f"Город: {state['city']}. Список товаров: {message.text}. "
            f"Выдай отчет СТРОГО по шаблону: "
            f"{user_name}! Наименьшая стоимость «корзины» будет X (валюта) в (магазин). "
            f"Это на Z меньше, чем в ближайшем альтернативном варианте. "
            f"Скидки: (список). "
            f"Нужен расчет для конкретного магазина?"
        )

    last_error = ""
    final_response = None

    # Пробуем только ОДНУ самую стабильную модель, но по разным ключам
    for api_key in KEYS:
        if final_response: break
        try:
            genai.configure(api_key=api_key)
            # Отключаем фильтры безопасности, чтобы они не блокировали поиск цен
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
            response = model.generate_content(prompt)
            
            if response and response.text:
                final_response = response.text.strip()
            else:
                last_error = "ИИ вернул пустой ответ (возможно, сработал внутренний фильтр)."
        except Exception as e:
            last_error = str(e)
            continue

    if final_response:
        bot.send_message(chat_id, final_response)
        user_states[chat_id]['step'] = 'recalc'
    else:
        # Выводим реальную причину ошибки Григорию
        bot.send_message(chat_id, f"❌ Техническая ошибка: {last_error}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
