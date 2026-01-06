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

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Новый игрок: {user.first_name}\nID: {user.id}\nПозиция: {position}"
    )

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

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Оплата: {user['first_name']} ({user['id']})"
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

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Пришёл: {user['first_name']} ({user['id']})"
    )


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

    main = registered_users[:MAX_SLOTS]
    wait = registered_users[MAX_SLOTS:]

    text = "Админка\n\nОсновной состав:\n"
    for i, u in enumerate(main, 1):
        text += (
            f"{i}. {u['first_name']} | "
            f"{'опл' if u['paid'] else 'не опл'} | "
            f"{'пришёл' if u['arrived'] else 'не пришёл'}\n"
        )

    text += "\nЛист ожидания:\n"
    for i, u in enumerate(wait, 1):
        text += f"{i}. {u['first_name']}\n"

    keyboard = [
        [InlineKeyboardButton("Удалить игрока", callback_data="admin_remove")]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(
            f"{u['first_name']} ({u['id']})",
            callback_data=f"remove_{u['id']}"
        )] for u in registered_users
    ]

    await query.message.reply_text(
        "Кого удалить:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[1])

    user = get_user(user_id)
    if not user:
        return

    registered_users.remove(user)
    save_users(registered_users)

    await query.message.reply_text("Игрок удалён.")

    if len(registered_users) >= MAX_SLOTS:
        promoted = registered_users[MAX_SLOTS - 1]
        keyboard = [
            [InlineKeyboardButton("Я оплатил", callback_data="paid")],
            [InlineKeyboardButton("Отменить участие", callback_data="cancel")]
        ]
        await context.bot.send_message(
            promoted["id"],
            "Ты в основном составе.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


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

    app.add_handler(CallbackQueryHandler(admin_remove, pattern="admin_remove"))
    app.add_handler(CallbackQueryHandler(remove_user, pattern="remove_"))

    app.run_polling()


if __name__ == "__main__":
    main()
