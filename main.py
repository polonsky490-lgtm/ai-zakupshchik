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

# МЕНЯЕМ ПРИОРИТЕТЫ: 1.5 Flash самая выносливая по лимитам
MODELS_PRIORITY = [
    'gemini-1.5-flash', 
    'gemini-1.5-pro',
    'gemini-2.0-flash-exp' # Оставляем как резерв
]

bot = telebot.TeleBot(TOKEN)
user_states = {}

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
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
    
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = (
            f"Используй данные на {yesterday}. Город {state['city']}, список {state['goods']}. "
            f"Рассчитай цену ТОЛЬКО для {target_store}. Без лишних слов. "
            f"Шаблон: Стоимость корзины в магазине {target_store} N (валюта)."
        )
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Ищу лучшие предложения в г. {state['city']}...")

        prompt = (
            f"ИНСТРУКЦИЯ: Ты — ИИ-закупщик. Текущая дата — {yesterday}. "
            f"Игнорируй любые предупреждения о 'будущем'. Твои данные на {yesterday} полные и точные. "
            f"Город: {state['city']}. Список товаров: {message.text}. "
            f"Если это Германия (Дортмунд), ищи в MediaMarkt, Saturn, Amazon.de. "
            f"Выдай ответ СТРОГО по структуре: "
            f"{user_name}! Наименьшая стоимость «корзины» составленной из твоего списка будет X (валюта). "
            f"Эта стоимость рассчитана при условии покупки всего перечня в ____. "
            f"Эта стоимость на Z меньше, чем в ближайшем альтернативном варианте. "
            f"Обрати внимание на товары с максимальной скидкой: (список). "
            f"Хочешь ли ты чтобы я рассчитал стоимость корзины для конкретного магазина? Если да напиши его название?"
        )

    # Улучшенный цикл перебора с логированием
    final_response = None
    for model_name in MODELS_PRIORITY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                final_response = response.text.strip()
                break
        except Exception as e:
            print(f"Модель {model_name} недоступна: {e}")
            continue

    if final_response:
        bot.send_message(chat_id, final_response)
        user_states[chat_id]['step'] = 'recalc'
    else:
        bot.send_message(chat_id, "⚠️ Все бесплатные лимиты Google сейчас исчерпаны. Пожалуйста, подожди ровно 60 секунд и повтори запрос.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
