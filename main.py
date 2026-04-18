import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime

# ==========================================
# 1. НАСТРОЙКИ И СПИСОК РАБОЧИХ МОДЕЛЕЙ
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

# Список моделей из твоего лога, которые ГАРАНТИРОВАННО существуют
MODELS_PRIORITY = [
    'gemini-2.5-flash',       # Твой основной "движок"
    'gemini-2.0-flash',       # Быстрый запасной вариант
    'gemini-pro-latest',      # Стабильный ветеран
    'gemini-1.5-flash-latest' # Резерв (если flash-latest сработает)
]

bot = telebot.TeleBot(TOKEN)
user_states = {}

# ==========================================
# 2. СЕРВЕР ДЛЯ RENDER
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Закупщик в эфире!"

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
    bot.reply_to(message, f"Принято: {message.text}. Теперь пришли список товаров через запятую (это могут быть продукты или техника).")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list' or user_states.get(m.chat.id, {}).get('step') == 'recalc')
def handle_request(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state: return

    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Режим перерасчета для конкретного магазина
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = (
            f"Город: {state['city']}. Список: {state['goods']}. Дата: {current_date}. "
            f"Рассчитай итоговую стоимость корзины ТОЛЬКО для магазина {target_store}. "
            f"Никакой 'воды' и дисклеймеров. Ответь строго: "
            f"Стоимость корзины в магазине {target_store} N грн."
        )
    else:
        # Основной отчет по твоему промпту
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Ищу лучшие предложения в г. {state['city']} на {current_date}...")

        prompt = (
            f"Ты — профессиональный ИИ-закупщик. Никакой самодеятельности и 'воды'. "
            f"Город: {state['city']}. Список товаров: {message.text}. Дата: {current_date}. "
            f"Если это продукты — ищи в АТБ, Сильпо, Варус. Если техника/промтовары — ищи в крупнейших сетях (Розетка, Comfy и т.д.). "
            f"Сформируй отчет СТРОГО по структуре: "
            f"{user_name}! Наименьшая стоимость «корзины» составленной из твоего списка будет X грн. "
            f"(вместо X подставь сумму, вместо грн. - валюту города). "
            f"Эта стоимость рассчитана при условии покупки всего перечня в ____ (название магазина). "
            f"Эта стоимость на Z грн. меньше, чем в ближайшем альтернативном (название) варианте. "
            f"Обрати внимание на товары с максимальной скидкой: (перечень товаров). "
            f"Хочешь ли ты чтобы я рассчитал стоимость корзины для конкретного магазина? Если да напиши его название?"
        )

    # УМНЫЙ ПЕРЕБОР МОДЕЛЕЙ (БЕЗ ВЫВОДА ОШИБОК 404 ПОЛЬЗОВАТЕЛЮ)
    final_response = None
    for model_name in MODELS_PRIORITY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                final_response = response.text.strip()
                break # Успешно получили ответ, выходим из цикла
        except Exception:
            continue # Если 404 или 429, просто пробуем следующую модель

    if final_response:
        bot.send_message(chat_id, final_response)
        user_states[chat_id]['step'] = 'recalc'
    else:
        bot.send_message(chat_id, "⚠️ Все мои каналы связи сейчас перегружены. Пожалуйста, попробуй повторить запрос через 1-2 минуты.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
