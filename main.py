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

genai.configure(api_key=GEMINI_KEY)
# Используем flash модель для быстроты и обхода жестких фильтров безопасности
model = genai.GenerativeModel('gemini-1.5-flash')

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
# 3. ЛОГИКА ТЕЛЕГРАМ-БОТА
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
def handle_goods_or_recalc(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state: return

    user_name = message.from_user.first_name if message.from_user.first_name else "Друг"
    
    if state.get('step') == 'recalc':
        target_store = message.text
        prompt = (
            f"Используй данные по городу {state['city']} и списку товаров: {state['goods']}. "
            f"Рассчитай актуальную стоимость корзины ТОЛЬКО для магазина {target_store}. "
            f"Никаких дисклеймеров и извинений. Ответь строго по шаблону: "
            f"Стоимость корзины в магазине {target_store} N грн."
        )
    else:
        user_states[chat_id]['goods'] = message.text
        goods = message.text
        city = state['city']
        bot.send_message(chat_id, f"🔎 Анализирую текущие цены в г. {city}...")

        # ЖЕСТКИЙ СИСТЕМНЫЙ ПРОМПТ ДЛЯ УДАЛЕНИЯ "ВОДЫ"
        prompt = (
            f"ИНСТРУКЦИЯ: Ты действующий эксперт по мониторингу цен в Украине (АТБ, Сильпо, Варус). "
            f"Твоя задача — выдать расчет на текущий момент БЕЗ любых вводных фраз, извинений и упоминаний о 'симуляции' или 'отсутствии доступа'. "
            f"Если ты видишь в запросе 2026 год — воспринимай его как текущее время. "
            f"Город: {city}. Список товаров: {goods}. "
            f"СТРОГАЯ СТРУКТУРА ОТВЕТА (НИКАКОГО ДРУГОГО ТЕКСТА ДО И ПОСЛЕ): "
            f"{user_name}! Наименьшая стоимость «корзины» составленной из твоего списка будет X грн. "
            f"Эта стоимость рассчитана при условии покупки всего перечня в ____ (название магазина). "
            f"Эта стоимость на Z грн. меньше, чем в ближайшем альтернативном (название) варианте. "
            f"Обрати внимание на товары с максимальной скидкой: (перечень товаров). "
            f"Хочешь ли ты чтобы я рассчитал стоимость корзины для конкретного магазина? Если да напиши его название?"
        )

    try:
        response = model.generate_content(prompt)
        # Убираем возможные лишние пробелы и пустые строки в начале
        final_text = response.text.strip()
        bot.send_message(chat_id, final_text)
        user_states[chat_id]['step'] = 'recalc'
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
