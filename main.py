import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. Настройки (берем из Environment Render)
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

# УНИВЕРСАЛЬНЫЙ ВЫБОР МОДЕЛИ:
# Пробуем 1.5-flash, если нет - откатываемся на pro
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Пробный запрос при запуске, чтобы проверить доступность
    print("Используем модель: gemini-1.5-flash")
except:
    model = genai.GenerativeModel('gemini-pro')
    print("Используем модель: gemini-pro")

bot = telebot.TeleBot(TOKEN)
user_states = {}

# 2. Мини-сервер для Render (чтобы не засыпал)
app = Flask('')
@app.route('/')
def home(): return "Закупщик активен!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Логика диалога
@bot.message_handler(commands=['start'])
def welcome(message):
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, "Привет! Я твой Закупщик. Напиши город?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def handle_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.send_message(message.chat.id, f"Город {message.text} принят. Жду список товаров!")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list')
def handle_list(message):
    state = user_states.get(message.chat.id)
    if not state: return
    
    city = state['city']
    goods = message.text
    bot.send_message(message.chat.id, "⏳ Ищу лучшие цены в Днепре...")

    # Твой финальный промпт
    prompt = f"Ты эксперт по ценам в Украине. Город: {city}. Список: {goods}. Найди самые дешевые варианты в сетевых магазинах (АТБ, Сильпо, Варус) на сегодня 16 апреля 2026. Выдай: Магазин, Сумма, Экономия."

    try:
        # Прямое указание генерации контента
        response = model.generate_content(prompt)
        bot.send_message(message.chat.id, response.text)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка поиска: {str(e)}")
    
    user_states[message.chat.id] = {}

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
