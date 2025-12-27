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

GAME_DATETIME = datetime(2025, 12, 30, 21, 0)

PAYMENT_TEXT = (
    "Ты зарегистрирован на игру в сквош 30 декабря\n\n"
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
    "30 декабря\n"
    "Сбор: 20:30\n"
    "Начало игры: 21:00\n\n"
    "Ты присоединился к игре в Сквош Spivak Run\n\n"
    "Если согласен с условиями — нажми кнопку ниже."
)

BASE_INFO_TEXT = (
    "Игра в сквош — Spivak Run\n\n"
    "30 декабря\n"
    "Сбор: 20:30\n"
    "Начало игры: 21:00\n\n"
    "Адрес:\n"
    "Сквош Москва\n"
    "ул. Лужники, 24, стр. 21, Москва\n"
    "этаж 4\n"
    "https://yandex.ru/maps/-/CLDvEIoP\n\n"
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
pinned_message_id = None


def build_participants_text():
    if not registered_users:
        return "Участников пока нет."
    text = "Участники:\n"
    for i, u in enumerate(registered_users, start=1):
        text += f"{i}. Имя: {u['first_name']}\n"
    return text


def build_info_text():
    return BASE_INFO_TEXT + build_participants_text()


async def update_pinned_message(context: ContextTypes.DEFAULT_TYPE):
    global pinned_message_id
    text = build_info_text()

    if pinned_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=ADMIN_CHAT_ID,
                message_id=pinned_message_id,
                text=text
            )
            return
        except:
            pinned_message_id = None

    msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
    await context.bot.pin_chat_message(chat_id=ADMIN_CHAT_ID, message_id=msg.message_id)
    pinned_message_id = msg.message_id


async def notify_all_users(context: ContextTypes.DEFAULT_TYPE):
    text = build_participants_text()
    for u in registered_users:
        try:
            await context.bot.send_message(chat_id=u["id"], text=text)
        except:
            pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Принимаю, играю", callback_data="register")],
        [InlineKeyboardButton("Показать участников", callback_data="participants")],
        [InlineKeyboardButton("Отменить", callback_data="cancel")]
    ]
    await update.message.reply_text(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_info_text())


async def participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(build_participants_text())


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if any(u["id"] == user.id for u in registered_users):
        await query.edit_message_text("Ты уже зарегистрирован.")
        return

    user_data = {
        "id": user.id,
        "first_name": user.first_name,
        "username": user.username
    }

    registered_users.append(user_data)
    save_users(registered_users)

    position = len(registered_users)
    is_main = position <= MAX_SLOTS
    username = f"@{user.username}" if user.username else "—"

    admin_text = (
        "Новый игрок!\n\n"
        f"Имя: {user.first_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Статус: {'Основной состав' if is_main else 'Лист ожидания'}\n"
        f"Позиция: {position}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

    await context.bot.send_message(chat_id=user.id, text=build_info_text())

    if is_main:
        keyboard = [[InlineKeyboardButton("Я оплатил", callback_data="paid")]]
        await context.bot.send_message(
            chat_id=user.id,
            text=PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=user.id,
            text="Ты в листе ожидания. Я напишу, если появится место."
        )

    await notify_all_users(context)
    await update_pinned_message(context)

    await query.edit_message_text("Регистрация принята.")


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"Игрок {user.first_name} (ID {user.id}) нажал 'Я оплатил'."
    )

    await query.edit_message_text("Спасибо. Оплата отмечена.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    user_data = next((u for u in registered_users if u["id"] == user.id), None)
    if not user_data:
        await query.edit_message_text("Ты не был зарегистрирован.")
        return

    position = registered_users.index(user_data) + 1
    status = "Основной состав" if position <= MAX_SLOTS else "Лист ожидания"

    registered_users.remove(user_data)
    save_users(registered_users)

    username = f"@{user.username}" if user.username else "—"

    admin_text = (
        "Игрок отменил участие\n\n"
        f"Имя: {user.first_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Статус: {status}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

    if len(registered_users) >= MAX_SLOTS:
        new_main = registered_users[MAX_SLOTS - 1]
        keyboard = [[InlineKeyboardButton("Я оплатил", callback_data="paid")]]
        await context.bot.send_message(
            chat_id=new_main["id"],
            text=PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    await notify_all_users(context)
    await update_pinned_message(context)

    await query.edit_message_text("Ты отменил участие.")


async def reminder_24h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users[:MAX_SLOTS]:
        await context.bot.send_message(chat_id=u["id"], text=REMINDER_TEXT)


async def reminder_2h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users[:MAX_SLOTS]:
        await context.bot.send_message(
            chat_id=u["id"],
            text="Напоминание\nИгра в сквош начнётся через 2 часа."
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.job_queue.run_once(reminder_24h, GAME_DATETIME - timedelta(hours=24))
    app.job_queue.run_once(reminder_2h, GAME_DATETIME - timedelta(hours=2))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    app.add_handler(CallbackQueryHandler(paid, pattern="paid"))
    app.add_handler(CallbackQueryHandler(participants, pattern="participants"))

    app.run_polling()


if __name__ == "__main__":
    main()
