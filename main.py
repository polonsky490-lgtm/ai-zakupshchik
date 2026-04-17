import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# ==========================================
# 1. НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Google AI
genai.configure(api_key=GEMINI_KEY)
# Используем модель из твоего списка доступных
model = genai.GenerativeModel('gemini-2.5-flash')

bot = telebot.TeleBot(TOKEN)
user_states = {}

# ==========================================
# 2. ФЕЙКОВЫЙ СЕРВЕР ДЛЯ RENDER (ЧТОБЫ НЕ ЗАСЫПАЛ)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Закупщик в эфире и готов к работе!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==========================================
# 3. ЛОГИКА ТЕЛЕГРАМ-БОТА
# ==========================================

# Команда /start или Привет
@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text.lower() == 'привет')
def send_welcome(message):
    user_states[message.chat.id] = {'step': 'city'}
    bot.reply_to(message, "Привет, Григорий! Я твой ИИ-Закупщик. В каком городе (местности) ты сейчас находишься?")

# Шаг 1: Получаем город
@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def get_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.reply_to(message, f"Принято: {message.text}. Теперь пришли список товаров через запятую. Я проанализирую цены в сетевых магазинах.")

# Шаг 2: Получаем список и вызываем Gemini
@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list')
def get_list(message):
    chat_id = message.chat.id
    city = user_states[chat_id]['city']
    goods = message.text
    
    bot.send_message(chat_id, f"🔎 Начинаю поиск в г. {city}. Это займет около 10-15 секунд...")

    # Формируем промпт по твоему ТЗ
    prompt = (
        f"Ты профессиональный ИИ-закупщик. Твоя задача — проанализировать цены в городе {city} на товары: {goods}. "
        f"Рассматривай только сетевые магазины (АТБ, Сильпо, Варус). Игнорируй рынки и мелкие лавки. "
        f"Выдай результат строго в формате: "
        f"Название магазина – "
        f"Стоимость закупки – "
        f"Экономия – "
        f"В конце добавь краткое обоснование выбора."
    )

    try:
        # Прямой вызов модели
        response = model.generate_content(prompt)
        
        if response.text:
            bot.send_message(chat_id, response.text)
        else:
            bot.send_message(chat_id, "⚠️ ИИ не смог сформировать текст. Попробуй изменить список товаров.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Произошла ошибка: {str(e)}")
    
    # Сброс состояния, чтобы можно было начать заново
    user_states[chat_id] = {}

# ==========================================
# 4. ЗАПУСК
# ==========================================
if __name__ == "__main__":
    # Запускаем "сердцебиение" для Render
    keep_alive()
    print("Бот Закупщик запущен...")
    # Запускаем прослушивание Телеграм с защитой от конфликтов
    bot.infinity_polling(skip_pending=True)
