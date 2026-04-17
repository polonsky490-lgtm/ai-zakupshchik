import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. Настройки
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
# Используем самую актуальную модель
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TOKEN)
user_states = {}

# 2. Flask сервер
app = Flask('')
@app.route('/')
def home(): return "Закупщик активен!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Логика бота
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_states[message.chat.id] = {'step': 'city'}
    bot.reply_to(message, "Привет! Я готов. В каком ты городе?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def get_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.reply_to(message, f"Город {message.text} принят. Что покупаем?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list')
def get_list(message):
    chat_id = message.chat.id
    city = user_states[chat_id]['city']
    goods = message.text
    
    bot.send_message(chat_id, f"🔎 Ищу товары в г. {city}...")

    # Детальный промпт по твоему ТЗ
    prompt = (
        f"Ты — профессиональный закупщик. Город: {city}. Список: {goods}. "
        f"Найди актуальные цены в сетях АТБ, Сильпо, Варус на 17 апреля 2026 года. "
        f"Выдай: 1. Магазин с самой дешевой корзиной. 2. Итоговую сумму. 3. Экономию."
    )

    try:
        # Пытаемся получить ответ
        response = model.generate_content(prompt)
        
        if response and response.text:
            bot.send_message(chat_id, response.text)
        else:
            # Если ИИ заблокировал ответ по соображениям безопасности
            bot.send_message(chat_id, "⚠️ ИИ вернул пустой ответ или заблокировал запрос.")
            
    except Exception as e:
        # Выводим конкретную техническую ошибку прямо в чат
        bot.send_message(chat_id, f"❌ Ошибка при вызове ИИ: {str(e)}")
    
    # Сброс состояния
    user_states[chat_id] = {}

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
