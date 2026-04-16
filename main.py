import os
import telebot

# Читаем токен
TOKEN = os.getenv("TELEGRAM_TOKEN")

# ПРОВЕРКА ДЛЯ ЛОГОВ (мы удалим это позже ради безопасности)
if TOKEN:
    print(f"Токен найден! Его длина: {len(TOKEN)} символов.")
    if ":" in TOKEN:
        print("Двоеточие в токене присутствует.")
    else:
        print("ОШИБКА: Двоеточие в токене НЕ найдено!")
else:
    print("ОШИБКА: Переменная TELEGRAM_TOKEN пуста или не найдена!")

# Если токен пустой, эта строчка выдаст ту самую ошибку
bot = telebot.TeleBot(TOKEN)
