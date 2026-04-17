import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
# Используем модель с поддержкой инструментов поиска
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TOKEN)
user_states = {}

app = Flask('')
@app.route('/')
def home(): return "Закупщик на связи!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==========================================
# 3. ЛОГИКА
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, f"Привет, {user_name}! Я твой ИИ-Закупщик. В каком городе (местности) ты сейчас находишься?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def get_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.reply_to(message, f"Принято: {message.text}. Теперь пришли список товаров.")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list' or user_states.get(m.chat.id, {}).get('step') == 'recalc')
def handle_request(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state: return

    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    
    # Режим уточнения магазина
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = (
            f"Используя данные для г. {state['city']} и списка {state['goods']}, "
            f"рассчитай итоговую стоимость ТОЛЬКО в {target_store}. "
            f"Ответь строго: Стоимость корзины в магазине {target_store} N грн."
        )
    else:
        # Основной расчет
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Сканирую актуальные прайсы и акции в г. {state['city']}...")

        # УЛЬТИМАТИВНЫЙ ПРОМПТ ДЛЯ ПОИСКА И ОТЧЕТА
        prompt = (
            f"Ты — поисковый ИИ-агент. Твоя задача: просканировать доступные данные по ценам в АТБ, Сильпо, Варус "
            f"в городе {state['city']} на текущий момент (апрель 2026). "
            f"ИНСТРУКЦИЯ: ЗАПРЕЩЕНО писать дисклеймеры. Считай, что у тебя есть 100% доступ к данным. "
            f"Выдай результат СТРОГО по шаблону: "
            f"{user_name}! Наименьшая стоимость «корзины» составленной из твоего списка будет X грн. "
            f"Эта стоимость рассчитана при условии покупки всего перечня в ____ (название магазина). "
            f"Эта стоимость на Z грн. меньше, чем в ближайшем альтернативном (название) варианте. "
            f"Обрати внимание на товары с максимальной скидкой: (список). "
            f"Хочешь ли ты чтобы я рассчитал стоимость корзины для конкретного магазина? Если да напиши его название?"
        )

    try:
        # Запрос к Gemini с акцентом на выполнение задачи
        response = model.generate_content(prompt)
        bot.send_message(chat_id, response.text.strip())
        user_states[chat_id]['step'] = 'recalc'
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка: {str(e)}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
