import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime
import time

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

# Список моделей для авто-переключения в случае лимитов
MODELS_PRIORITY = ['gemini-2.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']

bot = telebot.TeleBot(TOKEN)
user_states = {}

# ==========================================
# 2. СЕРВЕР ДЛЯ RENDER
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Закупщик активен!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==========================================
# 3. ЛОГИКА БОТА
# ==========================================

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text.lower() == 'привет')
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
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = f"Стоимость корзины для {state['city']} в магазине {target_store} для списка {state['goods']}. Ответь по шаблону: Стоимость корзины в магазине {target_store} N грн."
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Ищу лучшие цены в г. {state['city']}...")
        prompt = (
            f"Ты ИИ-закупщик. Город: {state['city']}. Список: {state['goods']}. Дата: {current_date}. "
            f"Сформируй отчет СТРОГО по структуре: "
            f"{user_name}! Наименьшая стоимость «корзины» составленной из твоего списка будет X грн. "
            f"Эта стоимость рассчитана при условии покупки всего перечня в ____. "
            f"Эта стоимость на Z грн. меньше, чем в ближайшем альтернативном варианте. "
            f"Обрати внимание на товары с максимальной скидкой: (список). "
            f"Хочешь ли ты чтобы я рассчитал стоимость корзины для конкретного магазина? Если да напиши его название?"
        )

    # ПОПЫТКА ВЫЗОВА ИИ С ПЕРЕБОРОМ МОДЕЛЕЙ
    success = False
    for model_name in MODELS_PRIORITY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            bot.send_message(chat_id, response.text.strip())
            user_states[chat_id]['step'] = 'recalc'
            success = True
            break # Выход из цикла, если успешно
        except Exception as e:
            if "429" in str(e):
                continue # Пробуем следующую модель, если у этой кончился лимит
            else:
                bot.send_message(chat_id, f"❌ Ошибка ИИ: {str(e)}")
                break

    if not success:
        bot.send_message(chat_id, "⚠️ Все мои 'мозги' сейчас заняты (лимит запросов). Пожалуйста, повтори запрос через 60 секунд.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
