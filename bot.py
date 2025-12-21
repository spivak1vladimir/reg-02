# --- coding: utf-8 ---
import os
import json
import logging
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = "8553029498:AAFdohgB-RkT9-XZoz94PzS65BvYGri7Sa0"
ADMIN_CHAT_ID = 194614510
MAX_SLOTS = 8
DATA_FILE = "registered_users.json"

GAME_DATETIME = datetime(2025, 12, 23, 21, 0)

PAYMENT_TEXT = (
    "Ты зарегистрирован на игру в сквош 23 декабря\n\n"
    "Как добраться:\n"
    "ул. Лужники, 24, стр. 21, Москва\n"
    "Этаж 4\n"
    "https://yandex.ru/maps/-/CLDvEIoP\n\n"
    "Стоимость участия — 1500 ₽\n\n"
    "Оплата по номеру 8 925 826-57-45\n"
    "Сбербанк / Т-Банк\n\n"
    "Ссылка для оплаты:\n"
    "https://www.tbank.ru/cf/5TWRup86c3a\n\n"
    "После оплаты нажми кнопку ниже."
)

REMINDER_TEXT = (
    "Напоминание\n"
    "Игра в сквош состоится завтра в 21:00.\n"
    "Адрес: ул. Лужники, 24, стр. 21, этаж 4."
)

START_TEXT = (
    "Играем на площадке:\n"
    "Сквош Москва\n"
    "ул. Лужники, 24, стр. 21, Москва\n"
    "этаж 4\n\n"
    "23 декабря\n"
    "Сбор: 20:30\n"
    "Начало игры: 21:00\n\n"
    "Ты присоединился к игре в Сквош Spivak Run\n\n"
    "Пожалуйста, ознакомься с условиями участия:\n"
    "— Участник самостоятельно несёт ответственность за свою жизнь и здоровье.\n"
    "— Участник несёт ответственность за сохранность личных вещей.\n"
    "— Согласие на обработку персональных данных.\n"
    "— Согласие на фото- и видеосъёмку во время мероприятия.\n\n"
    "Условия оплаты и отмены участия:\n"
    "— При отмене участия менее чем за 24 часа до начала игры оплата не возвращается.\n"
    "— При отмене не позднее чем за 24 часа до игры средства возвращаются.\n"
    "— Допускается передача оплаченного места другому игроку при самостоятельном поиске замены.\n\n"
    "Если согласен с условиями — нажми кнопку ниже."
)

logging.basicConfig(level=logging.INFO)


def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False)


registered_users = load_users()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Принимаю, играю", callback_data="register"),
        InlineKeyboardButton("Отменить", callback_data="cancel")
    ]]

    await update.message.reply_text(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = query.from_user

    if user_id in registered_users:
        await query.edit_message_text("Ты уже зарегистрирован.")
        return

    registered_users.append(user_id)
    save_users(registered_users)

    position = len(registered_users)
    is_main = position <= MAX_SLOTS
    username = f"@{user.username}" if user.username else "—"

    # Сообщение админу
    admin_text = (
        "Новый игрок!\n\n"
        f"Имя: {user.first_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Статус: {'Основной состав' if is_main else 'Лист ожидания'}\n"
        f"Позиция: {position}\n\n"
        f"Всего игроков: {len(registered_users)}\n"
        f"Основной состав: {min(len(registered_users), MAX_SLOTS)} / {MAX_SLOTS}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

    # Сообщение пользователю
    if is_main:
        keyboard = [[InlineKeyboardButton("Я оплатил", callback_data="paid")]]
        await context.bot.send_message(
            chat_id=user_id,
            text=PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="Ты в листе ожидания. Я напишу, если появится место."
        )

    await query.edit_message_text("Регистрация принята.")


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"Игрок {user.first_name} (ID {user.id}) нажал 'Я оплатил'. Проверь чек."
    )

    await query.edit_message_text("Спасибо. Оплата отмечена.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in registered_users:
        await query.edit_message_text("Ты не был зарегистрирован.")
        return

    registered_users.remove(user_id)
    save_users(registered_users)

    # Продвигаем из листа ожидания
    if len(registered_users) >= MAX_SLOTS:
        new_main_id = registered_users[MAX_SLOTS - 1]
        keyboard = [[InlineKeyboardButton("Я оплатил", callback_data="paid")]]
        await context.bot.send_message(
            chat_id=new_main_id,
            text=PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    await query.edit_message_text("Ты отменил участие.")


async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    for user_id in registered_users[:MAX_SLOTS]:
        try:
            await context.bot.send_message(chat_id=user_id, text=REMINDER_TEXT)
        except:
            pass


def main():
    app = Application.builder().token(TOKEN).build()

    # Напоминание за 24 часа (JobQueue)
    reminder_time = GAME_DATETIME - timedelta(hours=24)
    app.job_queue.run_once(reminder_job, reminder_time)

    # Хэндлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    app.add_handler(CallbackQueryHandler(paid, pattern="paid"))

    app.run_polling()


if __name__ == "__main__":
    main()
