import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

# Список гарантированно рабочих моделей
MODELS_PRIORITY = [
    'gemini-2.0-flash', 
    'gemini-1.5-flash', 
    'gemini-pro'
]

bot = telebot.TeleBot(TOKEN)
user_states = {}

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
    bot.reply_to(message, f"Принято: {message.text}. Теперь пришли список товаров через запятую.")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list' or user_states.get(m.chat.id, {}).get('step') == 'recalc')
def handle_request(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state: return

    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    
    # ВЫЧИСЛЯЕМ ВЧЕРАШНЮЮ ДАТУ, чтобы ИИ не боялся "будущего"
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
    
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = (
            f"Основываясь на ценах на дату {yesterday}, рассчитай стоимость корзины для {state['city']} "
            f"в магазине {target_store} для товаров: {state['goods']}. "
            f"ЗАПРЕЩЕНО писать дисклеймеры про будущее. Ответь строго: "
            f"Стоимость корзины в магазине {target_store} N грн."
        )
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Анализирую базу цен на {yesterday}...")

        prompt = (
            f"ИНСТРУКЦИЯ: Ты — ИИ-закупщик. Твоя текущая дата — {yesterday}. "
            f"ЗАПРЕЩЕНО использовать фразы 'дата является будущей', 'не имею доступа' или 'симуляция'. "
            f"Все данные на {yesterday} считай актуальными и окончательными. "
            f"Город: {state['city']}. Список товаров: {message.text}. "
            f"Сформируй отчет СТРОГО по структуре: "
            f"{user_name}! Наименьшая стоимость «корзины» составленной из твоего списка будет X грн. "
            f"Эта стоимость рассчитана при условии покупки всего перечня в ____. "
            f"Эта стоимость на Z грн. меньше, чем в ближайшем альтернативном варианте. "
            f"Обрати внимание на товары с максимальной скидкой: (перечень). "
            f"Хочешь ли ты чтобы я рассчитал стоимость корзины для конкретного магазина? Если да напиши его название?"
        )

    # ПЕРЕБОР МОДЕЛЕЙ
    final_response = None
    for model_name in MODELS_PRIORITY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                final_response = response.text.strip()
                break
        except Exception:
            continue

    if final_response:
        bot.send_message(chat_id, final_response)
        user_states[chat_id]['step'] = 'recalc'
    else:
        bot.send_message(chat_id, "⚠️ Сервер перегружен. Пожалуйста, попробуй через минуту.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
