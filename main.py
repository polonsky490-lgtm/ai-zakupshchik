import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. Настройки
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
bot = telebot.TeleBot(TOKEN)

# Хранилище (InMemory)
user_states = {}

# 2. Мини-сервер для Render
app = Flask('')
@app.route('/')
def home(): return "Закупщик в эфире!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Обработка команд
@bot.message_handler(commands=['start'])
def welcome(message):
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, "Привет! Я твой Закупщик. Напиши, в каком ты городе?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def handle_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.send_message(message.chat.id, f"Принято: {message.text}. Теперь пришли список товаров.")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list')
def handle_list(message):
    city = user_states[message.chat.id]['city']
    goods = message.text
    bot.send_message(message.chat.id, "⏳ Секунду, ищу лучшие цены в сетевых магазинах...")

    # Промпт (твой ТЗ)
    prompt = f"Ты эксперт по ценам в Украине. Город: {city}. Список покупок: {goods}. Найди самые дешевые варианты в сетевых магазинах (АТБ, Сильпо, Варус и др.) на сегодня 16 апреля 2026 года. Выдай: 1. Магазин-победитель. 2. Общая стоимость. 3. Экономия. Обоснуй коротко."

    try:
        response = model.generate_content(prompt)
        bot.send_message(message.chat.id, response.text)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")
    
    # Сброс
    user_states[message.chat.id] = {}

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    print("Закупщик запущен!")
    # infinity_polling с параметрами против конфликтов
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
