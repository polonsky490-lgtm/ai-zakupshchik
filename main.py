import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. Настройки
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Google AI
genai.configure(api_key=GEMINI_KEY)

# Пытаемся подключить модель 'gemini-pro' - она самая стабильная
# и гарантированно есть во всех версиях библиотеки
try:
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"Критическая ошибка модели: {e}")

bot = telebot.TeleBot(TOKEN)
user_states = {}

# 2. Flask сервер (для Render)
app = Flask('')
@app.route('/')
def home(): return "Бот Закупщик в сети!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Логика бота
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_states[message.chat.id] = {'step': 'city'}
    bot.reply_to(message, "Привет, Григорий! Я твой Закупщик. Напиши, в каком ты городе?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def get_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.reply_to(message, f"Город {message.text} принят. Теперь пришли список продуктов через запятую.")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list')
def get_list(message):
    chat_id = message.chat.id
    city = user_states[chat_id]['city']
    goods = message.text
    
    bot.send_message(chat_id, "⏳ Ищу лучшие цены в сетевых магазинах Днепра...")

    # Твой промпт (упростил для надежности)
    prompt = f"Ты помощник по покупкам. Город: {city}. Список товаров: {goods}. Найди актуальные цены в супермаркетах АТБ, Варус, Сильпо на сегодня (16 апреля 2026). Напиши: какой магазин самый дешевый для всей корзины, общую сумму и сколько сэкономим."

    try:
        # Генерируем ответ
        response = model.generate_content(prompt)
        if response.text:
            bot.send_message(chat_id, response.text)
        else:
            bot.send_message(chat_id, "ИИ вернул пустой ответ. Попробуй еще раз.")
    except Exception as e:
        # Выводим ошибку, чтобы понять, в чем дело
        bot.send_message(chat_id, f"Ошибка ИИ: {str(e)}")
    
    # Сброс состояния для нового круга
    user_states[chat_id] = {}

if __name__ == "__main__":
    Thread(target=run, daemon=True).start()
    print("Запуск бота...")
    bot.infinity_polling(skip_pending=True)
