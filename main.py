import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# 1. Инициализация (Бот + ИИ)
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Самый быстрый для закупок
bot = telebot.TeleBot(TOKEN)

# Хранилище состояний (в рамках одной сессии)
user_states = {}

# 2. Фейковый сервер для Render
app = Flask('')
@app.route('/')
def home(): return "Закупщик активен!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. ЛОГИКА БОТА

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text.lower() == 'привет')
def start_cmd(message):
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, "Привет, Григорий! Я твой Закупщик. Напиши, в каком ты городе?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def handle_city(message):
    city = message.text
    user_states[message.chat.id] = {'step': 'list', 'city': city}
    bot.send_message(message.chat.id, f"Принято: {city}. Теперь пришли список товаров (можно просто текстом).")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list')
def handle_list(message):
    city = user_states[message.chat.id]['city']
    goods = message.text
    bot.send_message(message.chat.id, "⏳ Понял. Начинаю поиск лучших цен в сетевых магазинах... Это займет секунд 10-15.")

    # ТОТ САМЫЙ ПРОМПТ ИЗ ТВОЕГО ТЗ
    full_prompt = f"""
    Ты — профессиональный ИИ-закупщик. Твоя задача — проанализировать цены в городе {city}.
    Список товаров: {goods}
    
    ИНСТРУКЦИЯ:
    1. Найди цены на эти товары во всех сетевых магазинах города (АТБ, Сильпо, Варус и т.д.).
    2. Оцени наличие, скидки и реальную цену на сегодня (16 апреля 2026 года).
    3. Выбери ОДИН магазин, где вся корзина выйдет ДЕШЕВЛЕ всего.
    4. Рассчитай примерную экономию по сравнению с другими сетями.
    5. Если указана марка — ищи только её. Если нет — бери самый дешевый аналог.
    
    РЕЗУЛЬТАТ ВЫДАЙ СТРОГО В ФОРМАТЕ:
    Название магазина – 
    Стоимость закупки – 
    Экономия – 
    
    В конце добавь короткое пояснение, почему выбран этот магазин.
    """

    try:
        response = model.generate_content(full_prompt)
        bot.send_message(message.chat.id, response.text)
    except Exception as e:
        bot.send_message(message.chat.id, "Упс, поиск сорвался. Попробуй еще раз.")
        print(f"Ошибка Gemini: {e}")

    # Сброс состояния
    user_states[message.chat.id] = {}

if __name__ == "__main__":
    Thread(target=run).start()
    print("Бот запущен...")
    bot.infinity_polling()
