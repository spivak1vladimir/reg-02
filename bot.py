import os
import json
import logging
from datetime import datetime, timedelta, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8553029498:AAFdohgB-RkT9-XZoz94PzS65BvYGri7Sa0"
ADMIN_CHAT_ID = 194614510
MAX_SLOTS = 8
DATA_FILE = "registered_users.json"

GAME_DATETIME = datetime(2026, 1, 6, 21, 0, tzinfo=timezone.utc)

logging.basicConfig(level=logging.INFO)

TERMS_TEXT = (
    "Пожалуйста, ознакомься с условиями участия:\n"
    "— Участник самостоятельно несёт ответственность за свою жизнь и здоровье.\n"
    "— Участник несёт ответственность за сохранность личных вещей.\n"
    "— Согласие на обработку персональных данных.\n"
    "— Согласие на фото- и видеосъёмку во время мероприятия.\n\n"
    "Условия оплаты и отмены участия:\n"
    "— При отмене участия менее чем за 24 часа до начала игры оплата не возвращается.\n"
    "— При отмене не позднее чем за 24 часа до игры средства возвращаются.\n"
    "— Допускается передача оплаченного места другому игроку при самостоятельном поиске замены.\n\n"
)

START_TEXT = (
    "Играем на площадке:\n"
    "Сквош Москва\n"
    "ул. Лужники, 24, стр. 21, Москва\n"
    "этаж 4\n\n"
    "06 Января 2026\n"
    "Сбор: 20:30\n"
    "Начало игры: 21:00\n\n"
    "Ты присоединился к игре в Сквош Spivak Run\n\n"
    + TERMS_TEXT +
    "Если согласен с условиями — нажми кнопку ниже."
)

BASE_INFO_TEXT = (
    "Игра в сквош — Spivak Run\n\n"
    "06 Января 2026\n"
    "Сбор: 20:30\n"
    "Начало игры: 21:00\n\n"
    "Адрес:\n"
    "Сквош Москва\n"
    "ул. Лужники, 24, стр. 21, Москва\n"
    "этаж 4\n"
    "https://yandex.ru/maps/-/CLDvEIoP\n\n"
)

PAYMENT_TEXT = (
    "Ты зарегистрирован на игру в сквош 06 Января\n\n"
    "Стоимость участия — 1500 ₽\n\n"
    "Оплата по номеру 8 925 826-57-45\n"
    "Сбербанк / Т-Банк\n\n"
    "После оплаты нажми кнопку ниже."
)

REMINDER_24H = "Напоминание\nИгра в сквош состоится завтра в 21:00."
REMINDER_2H = "Напоминание\nИгра в сквош начнётся через 2 часа."

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

registered_users = load_users()

def build_participants_text():
    if not registered_users:
        return "Участников пока нет."
    return "Участники:\n" + "\n".join(
        f"{i}. {u['first_name']}" for i, u in enumerate(registered_users, 1)
    )

def build_info_text():
    return BASE_INFO_TEXT + build_participants_text()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Принимаю, играю", callback_data="register")],
        [InlineKeyboardButton("Информация по игре", callback_data="info")],
        [InlineKeyboardButton("Отменить", callback_data="cancel")]
    ]
    await update.message.reply_text(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def info_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(build_info_text())

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if any(u["id"] == user.id for u in registered_users):
        await query.edit_message_text("Ты уже зарегистрирован.")
        return

    registered_users.append({
        "id": user.id,
        "first_name": user.first_name
    })
    save_users(registered_users)

    if len(registered_users) <= MAX_SLOTS:
        await context.bot.send_message(
            chat_id=user.id,
            text=PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Я оплатил", callback_data="paid")]]
            )
        )

    await query.edit_message_text("Регистрация принята.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    registered_users[:] = [u for u in registered_users if u["id"] != query.from_user.id]
    save_users(registered_users)
    await query.edit_message_text("Участие отменено.")

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"Оплата отмечена: {update.callback_query.from_user.first_name}"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    keyboard = [
        [InlineKeyboardButton(f" {u['first_name']}", callback_data=f"del_{i}")]
        for i, u in enumerate(registered_users)
    ]
    await update.message.reply_text(
        build_participants_text(),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    idx = int(query.data.split("_")[1])
    removed = registered_users.pop(idx)
    save_users(registered_users)
    await query.answer(f"{removed['first_name']} удалён")

async def reminder_24h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users:
        await context.bot.send_message(chat_id=u["id"], text=REMINDER_24H)

async def reminder_2h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users:
        await context.bot.send_message(chat_id=u["id"], text=REMINDER_2H)

def main():
    app = Application.builder().token(TOKEN).build()

    app.job_queue.run_once(reminder_24h, GAME_DATETIME - timedelta(hours=24))
    app.job_queue.run_once(reminder_2h, GAME_DATETIME - timedelta(hours=2))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(info_cb, pattern="info"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    app.add_handler(CallbackQueryHandler(paid, pattern="paid"))
    app.add_handler(CallbackQueryHandler(admin_delete, pattern="del_"))

    app.run_polling()

if __name__ == "__main__":
    main()
