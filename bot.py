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

TOKEN = "8278233482:AAEFV2yTlktZ1LmLitEaWZ81iFysewE4Idk"
ADMIN_CHAT_ID = 194614510
MAX_SLOTS = 10
DATA_FILE = "registered_users.json"

GAME_DATETIME = datetime(2026, 1, 8, 18, 0)

logging.basicConfig(level=logging.INFO)

PAYMENT_TEXT = (
    "Ты зарегистрирован на игру в волейбол 02 января\n\n"
    "Как добраться:\n"
    "просп. Маршала Жукова, 4, стр. 2, Москва\n"
    "https://yandex.ru/maps/-/CLD0vNom\n\n"
    "Стоимость участия — 1400 ₽\n\n"
    "Оплата по номеру 8 925 826-57-45\n"
    "Сбербанк / Т-Банк\n\n"
    "Ссылка для оплаты:\n"
    "https://messenger.online.sberbank.ru/sl/7yOSdYz0k38b6kC9G\n\n"
    "После оплаты нажми кнопку ниже."
)

REMINDER_TEXT = (
    "Напоминание\n"
    "Игра в волейбол состоится завтра в 18:00.\n"
    "После прихода нажми кнопку подтверждения."
)

START_TEXT = (
    "Играем на площадке:\n"
    "Пляжный центр «Лето»\n"
    "просп. Маршала Жукова, 4, стр. 2, Москва\n"
    "08 января\n"
    "Сбор: 17:30\n"
    "Начало игры: 18:00\n"
    "Продолжительность игры: 2 часа\n\n"
    "Ты присоединился к игре в Волейбол Spivak Run\n\n"
    "Пожалуйста, ознакомься с условиями участия:\n\n"
    "Участник самостоятельно несёт ответственность за свою жизнь и здоровье.\n"
    "Участник несёт ответственность за сохранность личных вещей.\n"
    "Согласие на обработку персональных данных.\n"
    "Согласие на фото- и видеосъёмку во время мероприятия.\n"
    "При отмене участия менее чем за 24 часа до начала игры оплата не возвращается.\n"
    "Допускается передача оплаченного места другому игроку при самостоятельном поиске замены.\n"
    "Если согласен с условиями — нажми кнопку ниже."
)

BASE_INFO_TEXT = (
    "Игра в волейбол — Spivak Run\n\n"
    "08 января\n"
    "Сбор: 17:30\n"
    "Начало игры: 18:00\n"
    "Продолжительность игры: 2 часа\n\n"
    "Адрес:\n"
    "Пляжный центр «Лето»\n"
    "просп. Маршала Жукова, 4, стр. 2, Москва\n\n"
)


def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


registered_users = load_users()


def get_user(user_id):
    return next((u for u in registered_users if u["id"] == user_id), None)


def build_participants_text():
    if not registered_users:
        return "Участников пока нет."
    text = "Участники:\n"
    for i, u in enumerate(registered_users, 1):
        text += f"{i}. {u['first_name']}\n"
    text += f"\nВсего участников: {len(registered_users)}"
    return text


def build_info_text():
    return BASE_INFO_TEXT + build_participants_text()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Принимаю, играю", callback_data="register")]]
    await update.message.reply_text(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if get_user(user.id):
        await query.edit_message_text("Ты уже зарегистрирован.")
        return

    registered_users.append({
        "id": user.id,
        "first_name": user.first_name,
        "username": user.username,
        "paid": False,
        "arrived": False
    })
    save_users(registered_users)

    position = len(registered_users)
    is_main = position <= MAX_SLOTS
    status = "Основной состав" if is_main else "Лист ожидания"
    username = f"@{user.username}" if user.username else "—"

    admin_text = (
        "Новый игрок!\n\n"
        f"Имя: {user.first_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Статус: {status}\n"
        f"Позиция: {position}"
    )

    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

    await context.bot.send_message(chat_id=user.id, text=build_info_text())

    if is_main:
        keyboard = [
            [InlineKeyboardButton("Я оплатил", callback_data="paid")],
            [InlineKeyboardButton("Отменить участие", callback_data="cancel")]
        ]
        await context.bot.send_message(
            user.id,
            PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            user.id,
            "Ты в листе ожидания.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Отменить участие", callback_data="cancel")]
            ])
        )

    await query.edit_message_text("Регистрация принята.")


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if not user:
        return

    user["paid"] = True
    save_users(registered_users)

    keyboard = [
        [InlineKeyboardButton("Я пришёл", callback_data="arrived")],
        [InlineKeyboardButton("Отменить участие", callback_data="cancel")]
    ]

    await query.edit_message_text(
        "Оплата отмечена. После прихода нажми кнопку подтверждения.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def arrived(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if not user:
        return

    user["arrived"] = True
    save_users(registered_users)

    await query.edit_message_text("Приход подтверждён.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if not user:
        return

    registered_users.remove(user)
    save_users(registered_users)

    await query.edit_message_text("Участие отменено.")

    if len(registered_users) >= MAX_SLOTS:
        promoted = registered_users[MAX_SLOTS - 1]
        keyboard = [
            [InlineKeyboardButton("Я оплатил", callback_data="paid")],
            [InlineKeyboardButton("Отменить участие", callback_data="cancel")]
        ]
        await context.bot.send_message(
            promoted["id"],
            "Освободилось место. Ты в основном составе.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    await update.message.reply_text(build_info_text())


async def reminder_24h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users[:MAX_SLOTS]:
        keyboard = [[InlineKeyboardButton("Я пришёл", callback_data="arrived")]]
        await context.bot.send_message(
            u["id"],
            REMINDER_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.job_queue.run_once(reminder_24h, GAME_DATETIME - timedelta(hours=24))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(paid, pattern="paid"))
    app.add_handler(CallbackQueryHandler(arrived, pattern="arrived"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))

    app.run_polling()


if __name__ == "__main__":
    main()
