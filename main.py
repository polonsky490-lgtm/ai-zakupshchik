import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# ==========================================
# 1. НАСТРОЙКИ (ДВА КЛЮЧА)
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
KEYS = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]
KEYS = [k for k in KEYS if k]

bot = telebot.TeleBot(TOKEN)
user_states = {}

app = Flask('')
@app.route('/')
def home(): return "Закупщик: Аналитик (Путь 2) активен"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server, daemon=True)
    t.start()

# ==========================================
# 3. ЛОГИКА БОТА (ИНТЕЛЛЕКТУАЛЬНЫЙ ПОДБОР)
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    user_states[message.chat.id] = {'step': 'city'}
    bot.send_message(message.chat.id, f"Привет, {user_name}! Я твой ИИ-Закупщик. В каком городе (местности) ты сейчас находишься?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'city')
def get_city(message):
    user_states[message.chat.id] = {'step': 'list', 'city': message.text}
    bot.reply_to(message, f"Принято: {message.text}. Что ищем?")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get('step') == 'list' or user_states.get(m.chat.id, {}).get('step') == 'recalc')
def handle_request(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state: return

    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
    
    # Режим ПЕРЕРАСЧЕТА (ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ)
    if state.get('step') == 'recalc':
        target_store = message.text
        bot.send_message(chat_id, f"🔄 Анализирую ассортимент {target_store} по параметрам...")
        prompt = (
            f"Найди {state['goods']} в {target_store} (г. {state['city']}). "
            f"ИНСТРУКЦИЯ: Если название не совпадает на 100%, но технические характеристики (бренд, диагональ, тип экрана, год) идентичны, "
            f"выдай цену и ОБЯЗАТЕЛЬНО добавь в начале: 'Это похоже на ваш запрос на 95%'. "
            f"КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать дисклеймеры про будущие даты. "
            f"Ответь строго по шаблону: "
            f"[Твое предупреждение, если нужно]. Стоимость корзины в магазине {target_store} N (валюта)."
        )
    # ОСНОВНОЙ ПОИСК
    else:
        user_states[chat_id]['goods'] = message.text
        bot.send_message(chat_id, f"🔎 Глубокий поиск «Аналитик» для г. {state['city']}...")
        prompt = (
            f"Ты — профессиональный аналитик. Твоя задача: найти лучшую цену на {message.text}. "
            f"Если в разных магазинах (Amazon, MediaMarkt, Otto и т.д.) товар называется по-разному, "
            f"используй интеллектуальный подбор по параметрам. "
            f"Если уверен в совпадении параметров, но не в буквах названия, пиши: 'Это похоже на ваш запрос на 95%'. "
            f"Выдай отчет СТРОГО по структуре: "
            f"{user_name}! Наименьшая стоимость «корзины» будет X (валюта) в (магазин). "
            f"Это на Z меньше, чем в ближайшем альтернативном варианте. "
            f"Скидки: (коротко). "
            f"Хочешь расчет для конкретного магазина?"
        )

    final_response = None
    for api_key in KEYS:
        if final_response: break
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not models: continue
            model = genai.GenerativeModel(models[0])
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
        bot.send_message(chat_id, "❌ Все ресурсы сейчас заняты. Повторите запрос позже.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
