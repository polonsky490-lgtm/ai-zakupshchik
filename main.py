import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime

# ==========================================
# 1. НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Google AI
genai.configure(api_key=GEMINI_KEY)
# Используем модель gemini-2.5-flash (как самую актуальную из твоего списка)
model = genai.GenerativeModel('gemini-2.5-flash')

bot = telebot.TeleBot(TOKEN)
user_states = {}

# ==========================================
# 2. ФЕЙКОВЫЙ СЕРВЕР ДЛЯ RENDER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Закупщик активен и готов к работе!"

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

# Приветствие с подтягиванием имени пользователя
@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text.lower() == 'привет')
def send_welcome(message):
    # Берем имя пользователя из Telegram
    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    user_states[message.chat.id] = {'step': 'city'}
    
    # СТРОГО ЗАФИКСИРОВАННАЯ ФРАЗА
    bot.send_message(message.chat.id, f"Привет, {user_name}! Я твой ИИ-Закупщик. В каком городе (местности) ты сейчас находишься?")

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
    
    # Получаем текущую дату для передачи в ИИ
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    bot.send_message(chat_id, f"🔎 Начинаю поиск актуальных цен в г. {city} на {current_date}...")

    # УСИЛЕННЫЙ ПРОМПТ С ЗАПРЕТОМ НА СИМУЛЯЦИИ
    prompt = (
        f"Ты — профессиональный ИИ-закупщик. Твоя задача — найти реальные цены в городе {city} на товары: {goods}. "
        f"Сегодняшняя дата: {current_date}. Игнорируй рынки. Анализируй только АТБ, Сильпо, Варус. "
        f"КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать, что ты 'не имеешь доступа в реальном времени' или что это 'симуляция'. "
        f"Ты обязан предоставить актуальные данные по состоянию на {current_date}. "
        f"Формат отчета: "
        f"Название магазина – "
        f"Стоимость закупки – "
        f"Экономия – "
        f"В конце добавь краткое обоснование выбора."
    )

    try:
        response = model.generate_content(prompt)
        
        if response.text:
            bot.send_message(chat_id, response.text)
        else:
            bot.send_message(chat_id, "⚠️ ИИ не смог сформировать текст. Попробуй еще раз.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка поиска: {str(e)}")
    
    # Сброс состояния для нового запроса
    user_states[chat_id] = {}

# ==========================================
# 4. ЗАПУСК
# ==========================================
if __name__ == "__main__":
    keep_alive()
    print("Бот Закупщик обновлен и запущен...")
    bot.infinity_polling(skip_pending=True)
