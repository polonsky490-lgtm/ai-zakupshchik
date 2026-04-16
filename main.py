import os
import telebot
from flask import Flask
from threading import Thread

# 1. Создаем микро-сайт для Render
app = Flask('')

@app.route('/')
def home():
    return "Закупщик в сети!"

def run():
    # Render сам подставит нужный порт в переменную PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# 2. Настройка бота
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: message.text.lower() in ['привет', '/start'])
def welcome(message):
    bot.reply_to(message, "Привет, Григорий! Бот-Закупщик на связи. В каком городе ты?")

if __name__ == "__main__":
    # Сначала запускаем микро-сайт
    keep_alive()
    # Потом запускаем бота
    print("Бот запущен...")
    bot.infinity_polling()
