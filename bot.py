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

TOKEN = "8553029498:AAFdohgB-RkT9-XZoz94PzS65BvYGri7Sa0"
ADMIN_CHAT_ID = 194614510
MAX_SLOTS = 8
DATA_FILE = "registered_users.json"

GAME_DATETIME = datetime(2026, 1, 9, 21, 0, tzinfo=timezone.utc)

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
REMINDER_4H = "Напоминание\nИгра в сквош начнётся через 4 часа."

registered_users = []


def load_users_sync():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_users_sync(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


async def load_users():
    global registered_users
    registered_users = await asyncio.to_thread(load_users_sync)


async def save_users():
    await asyncio.to_thread(save_users_sync, registered_users)


def build_participants_text():
    if not registered_users:
        return "Участников пока нет."

    text = "Участники:\n"
    for i, u in enumerate(registered_users, 1):
        status = "Основной состав" if i <= MAX_SLOTS else "Лист ожидания"
        paid = "Оплата подтверждена" if u.get("paid") else "Не оплачено"
        arrived = "Пришёл" if u.get("arrived") else "Не пришёл"
        text += f"{i}. {u['first_name']} — {status} — {paid} — {arrived}\n"
    return text


def build_info_text():
    return BASE_INFO_TEXT + "Количество игроков: " + str(len(registered_users)) + "\n\n" + build_participants_text()


def participant_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Информация по игре", callback_data="info")],
        [InlineKeyboardButton("Отменить участие", callback_data="cancel")]
    ])


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

    user_data = {
        "id": user.id,
        "first_name": user.first_name,
        "username": user.username,
        "paid": False,
        "arrived": False,
    }
    registered_users.append(user_data)
    await save_users()

    position = len(registered_users)
    is_main = position <= MAX_SLOTS

    await context.bot.send_message(
        chat_id=user.id,
        text="Ты зарегистрирован.",
        reply_markup=participant_keyboard()
    )

    if is_main:
        await context.bot.send_message(
            chat_id=user.id,
            text=PAYMENT_TEXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Я оплатил", callback_data="paid")]
            ])
        )

    await query.edit_message_text("Регистрация принята.")


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"Игрок {user.first_name} нажал кнопку «Я оплатил»."
    )

    await query.edit_message_text("Ожидается подтверждение оплаты администратором.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_data = next((u for u in registered_users if u["id"] == user.id), None)
    if not user_data:
        await query.edit_message_text("Ты не зарегистрирован.")
        return

    registered_users.remove(user_data)
    await save_users()

    await promote_from_waiting_list(context)
    await query.edit_message_text("Ты отменил участие.")


async def promote_from_waiting_list(context):
    if len(registered_users) < MAX_SLOTS:
        return

    u = registered_users[MAX_SLOTS - 1]
    if u.get("paid"):
        return

    await context.bot.send_message(
        chat_id=u["id"],
        text="Для тебя освободилось место в основном составе.\n\n" + PAYMENT_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Я оплатил", callback_data="paid")]
        ])
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    keyboard = []
    for i, u in enumerate(registered_users):
        row = [
            InlineKeyboardButton(f"Удалить {u['first_name']}", callback_data=f"del_{i}")
        ]
        if not u.get("paid"):
            row.append(
                InlineKeyboardButton(
                    f"Подтвердить оплату {u['first_name']}",
                    callback_data=f"pay_{i}"
                )
            )
        if not u.get("arrived"):
            row.append(
                InlineKeyboardButton(
                    f"Пришёл {u['first_name']}",
                    callback_data=f"arr_{i}"
                )
            )
        keyboard.append(row)

    await update.message.reply_text(
        build_participants_text(),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[1])
    registered_users.pop(idx)
    await save_users()

    await promote_from_waiting_list(context)
    await query.edit_message_text("Участник удалён.")


async def admin_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[1])
    registered_users[idx]["paid"] = True
    await save_users()

    await context.bot.send_message(
        chat_id=registered_users[idx]["id"],
        text="Оплата подтверждена администратором."
    )

    await query.edit_message_text("Оплата подтверждена.")


async def admin_arrived(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[1])
    registered_users[idx]["arrived"] = True
    await save_users()

    await query.edit_message_text("Отмечен как пришёл.")


async def reminder_24h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users:
        await context.bot.send_message(chat_id=u["id"], text=REMINDER_24H)


async def reminder_4h(context: ContextTypes.DEFAULT_TYPE):
    for u in registered_users:
        await context.bot.send_message(chat_id=u["id"], text=REMINDER_4H)


async def main():
    await load_users()
    app = Application.builder().token(TOKEN).build()

    # Напоминания
    app.job_queue.run_once(reminder_24h, GAME_DATETIME - timedelta(hours=24))

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(paid, pattern="paid"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    app.add_handler(CallbackQueryHandler(info_cb, pattern="info"))
    app.add_handler(CallbackQueryHandler(admin_delete, pattern="del_"))
    app.add_handler(CallbackQueryHandler(admin_confirm_payment, pattern="pay_"))
    app.add_handler(CallbackQueryHandler(admin_arrived, pattern="arr_"))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()  # безопасный способ без asyncio.run()
    await app.idle()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Если event loop уже запущен (например, в Replit / Jupyter)
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.get_event_loop().create_task(main())
