import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. Настройки
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

# ПРОБУЕМ САМУЮ СТАБИЛЬНУЮ МОДЕЛЬ
model = genai.GenerativeModel('gemini-2.5-flash')

bot = telebot.TeleBot(TOKEN)
user_states = {}

app = Flask('')
@app.route('/')
def home(): return "Закупщик в строю!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def welcome(message):
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, "Привет! В каком ты городе?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def handle_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.send_message(message.chat.id, f"Принято: {message.text}. Что ищем?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list')
def handle_list(message):
    state = user_states.get(message.chat.id)
    if not state: return
    
    city = state['city']
    goods = message.text
    bot.send_message(message.chat.id, "🔎 Связываюсь с ИИ для анализа цен в Днепре...")

    prompt = f"Ты эксперт по ценам в {city}. Список товаров: {goods}. Найди самые дешевые варианты в сетевых магазинах (АТБ, Варус, Сильпо). Напиши: какой магазин самый дешевый для всей корзины, общую сумму и сколько сэкономим."

    try:
        # Генерируем ответ через самую новую модель
        response = model.generate_content(prompt)
        
        if response.text:
            bot.send_message(chat_id, response.text)
        else:
            bot.send_message(chat_id, "ИИ не смог сформировать текст ответа.")
            
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка: {str(e)}")
    
    user_states[message.chat.id] = {}

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
