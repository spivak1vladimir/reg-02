import os
import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8553029498:AAFdohgB-RkT9-XZoz94PzS65BvYGri7Sa0"
ADMIN_CHAT_ID = 194614510
MAX_SLOTS = 8
DATA_FILE = "registered_users.json"

GAME_DATETIME = datetime(2026, 1, 9, 21, 0, tzinfo=timezone.utc)

logging.basicConfig(level=logging.INFO)

# -------------------- TEXT --------------------

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
    "09 Января 2026\n"
    "Сбор: 20:30\n"
    "Начало игры: 21:00\n\n"
    "Ты присоединился к игре в Сквош Spivak Run\n\n"
    + TERMS_TEXT +
    "Если согласен с условиями — нажми кнопку ниже."
)

BASE_INFO_TEXT = (
    "Игра в сквош — Spivak Run\n\n"
    "09 Января 2026\n"
    "Сбор: 20:30\n"
    "Начало игры: 21:00\n\n"
    "Адрес:\n"
    "Сквош Москва\n"
    "ул. Лужники, 24, стр. 21, Москва\n"
    "этаж 4\n"
    "https://yandex.ru/maps/-/CLDvEIoP\n\n"
)

PAYMENT_TEXT = (
    "Стоимость участия — 1500 ₽\n\n"
    "Оплата по номеру 8 925 826-57-45\n"
    "Сбербанк / Т-Банк\n\n"
    "Ссылка для оплаты:\n"
    "https://messenger.online.sberbank.ru/sl/vLgV7vtHhUxKx2dQt\n\n"
    "После оплаты нажми кнопку ниже."
)

REMINDER_24H = "Напоминание\nИгра в сквош состоится завтра в 21:00."
REMINDER_2H = "Напоминание\nИгра в сквош скоро начнётся."

# -------------------- STORAGE --------------------

users_lock = asyncio.Lock()
registered_users: list[dict] = []


async def load_users():
    if not os.path.exists(DATA_FILE):
        return []
    return await asyncio.to_thread(
        lambda: json.load(open(DATA_FILE, "r", encoding="utf-8"))
    )


async def save_users():
    await asyncio.to_thread(
        lambda: json.dump(
            registered_users,
            open(DATA_FILE, "w", encoding="utf-8"),
            ensure_ascii=False,
            indent=2
        )
    )

# -------------------- HELPERS --------------------

def build_participants_text():
    if not registered_users:
        return "Участников пока нет."

    lines = ["Участники:"]
    for i, u in enumerate(registered_users, 1):
        status = "Основной состав" if i <= MAX_SLOTS else "Лист ожидания"
        paid = "Оплата подтверждена" if u.get("paid") else "Не оплачено"
        lines.append(f"{i}. {u['first_name']} — {status} — {paid}")
    return "\n".join(lines)


def build_info_text():
    return BASE_INFO_TEXT + build_participants_text()


def participant_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Информация по игре", callback_data="info")],
        [InlineKeyboardButton("Отменить участие", callback_data="cancel")]
    ])

# -------------------- HANDLERS --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Принимаю, играю", callback_data="register")],
        [InlineKeyboardButton("Информация по игре", callback_data="info")]
    ]
    await update.message.reply_text(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def info_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(build_info_text())


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    async with users_lock:
        if any(u["id"] == user.id for u in registered_users):
            await query.edit_message_text("Ты уже зарегистрирован.")
            return

        registered_users.append({
            "id": user.id,
            "first_name": user.first_name,
            "username": user.username,
            "paid": False
        })
        await save_users()

        position = len(registered_users)
        is_main = position <= MAX_SLOTS

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Новый участник\n\n"
        f"Имя: {user.first_name}\n"
        f"Username: @{user.username}" if user.username else "—"
    )

    await context.bot.send_message(
        user.id,
        "Ты зарегистрирован.",
        reply_markup=participant_keyboard()
    )

    if is_main:
        await context.bot.send_message(
            user.id,
            PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Я оплатил", callback_data="paid")]]
            )
        )

    await query.edit_message_text("Регистрация принята.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with users_lock:
        for i, u in enumerate(registered_users):
            if u["id"] == user_id:
                registered_users.pop(i)
                await save_users()
                break
        else:
            await query.edit_message_text("Ты не зарегистрирован.")
            return

    await context.bot.send_message(ADMIN_CHAT_ID, "Участник отменил участие.")
    await query.edit_message_text("Ты отменил участие.")


# -------------------- MAIN --------------------

async def post_init(app: Application):
    global registered_users
    registered_users = await load_users()

    app.job_queue.run_once(reminder_24h, GAME_DATETIME - timedelta(hours=24))
    app.job_queue.run_once(reminder_2H, GAME_DATETIME - timedelta(hours=2))


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(info_cb, pattern="info"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))

    app.run_polling()


if __name__ == "__main__":
    main()
