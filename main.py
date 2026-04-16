import telebot
import os

# Твой токен, который ты уже знаешь
TOKEN = 'ТВОЙ_ТЕЛЕГРАМ_ТОКЕН'
bot = telebot.TeleBot(TOKEN)

# База данных «в уме» (пока программа запущена)
user_data = {}

# 1. Обработка команды /start или слова "Привет"
@bot.message_handler(func=lambda message: message.text.lower() in ['привет', '/start', 'hi'])
def welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'step': 'city'} # Фиксируем, что ждем город
    bot.reply_to(message, "Привет, Григорий! Я твой персональный Закупщик. В каком городе (местности) ты сейчас находишься?")

# 2. Обработка следующего сообщения (получаем город)
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('step') == 'city')
def get_city(message):
    chat_id = message.chat.id
    user_data[chat_id]['city'] = message.text
    user_data[chat_id]['step'] = 'list' # Теперь ждем список
    bot.reply_to(message, f"Принято: {message.text}. Теперь пришли мне список покупок. Помни: где важна марка — укажи её, где нет — я найду самое дешевое!")

# 3. Обработка списка и вызов Gemini (заглушка для теста)
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('step') == 'list')
def handle_shopping_list(message):
    city = user_data[message.chat.id]['city']
    shopping_list = message.text
    
    bot.reply_to(message, f"Начинаю поиск в городе {city} для списка:\n{shopping_list}\n\nПодожди пару секунд, сканирую полки магазинов...")
    
    # СЮДА МЫ ПОТОМ ВСТАВИМ ЛОГИКУ GEMINI С ТВОИМ ПРОМПТОМ
    
    # Очищаем состояние для нового запроса
    user_data[message.chat.id]['step'] = None

# Запуск бота
print("Бот Закупщик запущен...")
bot.infinity_polling()
