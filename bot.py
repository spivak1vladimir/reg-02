import os
import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================== CONFIG ==================

TOKEN = "8553029498:AAFdohgB-RkT9-XZoz94PzS65BvYGri7Sa0"
ADMIN_CHAT_ID = 194614510
MAX_SLOTS = 8
DATA_FILE = "registered_users.json"

GAME_DATETIME = datetime(2026, 1, 9, 21, 0, tzinfo=timezone.utc)

logging.basicConfig(level=logging.INFO)

# ================== TEXTS ==================

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
    + TERMS_TEXT
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
REMINDER_4H = "Напоминание\nИгра в сквош начнётся через 4 часа."

# ================== STORAGE ==================

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
            indent=2,
        )
    )

# ================== HELPERS ==================

def build_participants_text():
    if not registered_users:
        return "Участников пока нет."

    lines = ["Участники:\n"]
    for i, u in enumerate(registered_users, 1):
        status = "Основной состав" if i <= MAX_SLOTS else "Лист ожидания"
        paid = "подтверждена" if u.get("paid") else "не оплачено"
        arrived = "Пришёл" if u.get("arrived") else "Не пришёл"

        lines.append(
            f"{i}. {u['first_name']} — {status}\n"
            f"   Оплата: {paid}\n"
            f"   Статус: {arrived}\n"
        )

    return "\n".join(lines)


def build_info_text():
    return BASE_INFO_TEXT + build_participants_text()


def participant_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Информация по игре", callback_data="info")],
            [InlineKeyboardButton("Отменить участие", callback_data="cancel")],
        ]
    )

# ================== REMINDERS ==================

async def reminder_24h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users:
        await context.bot.send_message(u["id"], REMINDER_24H)


async def reminder_4h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users:
        await context.bot.send_message(u["id"], REMINDER_4H)

# ================== USER HANDLERS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Принимаю, играю", callback_data="register")],
        [InlineKeyboardButton("Информация по игре", callback_data="info")],
    ]

    await update.message.reply_text(START_TEXT)
    await update.message.reply_text(
        "Если согласен с условиями — нажми кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(keyboard),
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

        registered_users.append(
            {
                "id": user.id,
                "first_name": user.first_name,
                "username": user.username,
                "paid": False,
                "arrived": False,
            }
        )
        await save_users()

        is_main = len(registered_users) <= MAX_SLOTS

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Новый участник: {user.first_name}",
    )

    await context.bot.send_message(
        user.id,
        "Ты зарегистрирован.",
        reply_markup=participant_keyboard(),
    )

    if is_main:
        await context.bot.send_message(
            user.id,
            PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Я оплатил", callback_data="paid")]]
            ),
        )

    await query.edit_message_text("Регистрация принята.")


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Игрок {update.callback_query.from_user.first_name} нажал кнопку «Я оплатил».",
    )
    await update.callback_query.edit_message_text(
        "Ожидается подтверждение оплаты администратором."
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    async with users_lock:
        for i, u in enumerate(registered_users):
            if u["id"] == uid:
                registered_users.pop(i)
                await save_users()
                break
        else:
            await query.edit_message_text("Ты не зарегистрирован.")
            return

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        "Участник отменил участие.",
    )
    await query.edit_message_text("Ты отменил участие.")

# ================== ADMIN ==================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    keyboard = []
    for i, u in enumerate(registered_users):
        row = [
            InlineKeyboardButton(
                f"Удалить {u['first_name']}", callback_data=f"del_{i}"
            )
        ]
        if not u.get("paid"):
            row.append(
                InlineKeyboardButton(
                    f"Подтвердить оплату {u['first_name']}",
                    callback_data=f"pay_{i}",
                )
            )
        if u.get("paid") and not u.get("arrived"):
            row.append(
                InlineKeyboardButton(
                    f"Пришёл {u['first_name']}",
                    callback_data=f"arr_{i}",
                )
            )
        keyboard.append(row)

    await update.message.reply_text(
        build_participants_text(),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    idx = int(update.callback_query.data.split("_")[1])

    removed = registered_users.pop(idx)
    await save_users()

    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"Удалён участник {removed['first_name']}.",
    )
    await update.callback_query.edit_message_text("Участник удалён.")


async def admin_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    idx = int(update.callback_query.data.split("_")[1])

    registered_users[idx]["paid"] = True
    await save_users()

    await context.bot.send_message(
        registered_users[idx]["id"],
        "Оплата подтверждена администратором.",
    )
    await update.callback_query.edit_message_text("Оплата подтверждена.")


async def admin_arrived(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    idx = int(update.callback_query.data.split("_")[1])

    registered_users[idx]["arrived"] = True
    await save_users()

    await update.callback_query.edit_message_text("Отмечен как пришёл.")

# ================== INIT ==================

async def post_init(app: Application):
    global registered_users
    registered_users = await load_users()

    app.job_queue.run_once(reminder_24h, GAME_DATETIME - timedelta(hours=24))
    app.job_queue.run_once(reminder_4h, GAME_DATETIME - timedelta(hours=4))

# ================== MAIN ==================

def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(info_cb, pattern="info"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    app.add_handler(CallbackQueryHandler(paid, pattern="paid"))

    app.add_handler(CallbackQueryHandler(admin_delete, pattern="del_"))
    app.add_handler(CallbackQueryHandler(admin_confirm_payment, pattern="pay_"))
    app.add_handler(CallbackQueryHandler(admin_arrived, pattern="arr_"))

    app.run_polling()


if __name__ == "__main__":
    main()
