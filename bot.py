# --- coding: utf-8 ---
import os
import json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = "8553029498:AAFPIjBNIPQjjlfbLUk6xdWw7xThkLUUDsU"
ADMIN_CHAT_ID = 194614510
MAX_SLOTS = 8
DATA_FILE = "registered_users.json"

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
    text = (
        "*Играем на площадке:*\n"
        "Сквош-клуб «Москва»\n"
        "улица Лужники, 24, стр. 21, метро «Воробьёвы горы»\n\n"
        "*Пятница 19 Декабря*\n"
        "*Сбор:* 20:30\n"
        "*Начало игры:* 21:00\n\n"
        "Ты присоединился к игре в сквош *Spivak Run* \n\n"
        "*Пожалуйста, ознакомься с условиями участия:*\n"
        "— Участник самостоятельно несёт ответственность за свою жизнь и здоровье.\n"
        "— Участник несёт ответственность за сохранность личных вещей.\n"
        "— Согласие на обработку персональных данных.\n"
        "— Согласие на фото- и видеосъёмку во время мероприятия.\n\n"
        "*Условия оплаты и отмены участия:*\n"
        "— При отмене участия менее чем за 24 часа до начала игры оплата не возвращается.\n"
        "— При отмене не позднее чем за 24 часа до игры средства возвращаются.\n"
        "— Допускается передача оплаченного места другому игроку при самостоятельном поиске замены.\n\n"
        "Если согласен с условиями — нажми кнопку ниже."
    )

    keyboard = [[
        InlineKeyboardButton("Принимаю, играю", callback_data="register"),
        InlineKeyboardButton("Отменить", callback_data="cancel")
    ]]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id

    if user_id in registered_users:
        pos = registered_users.index(user_id) + 1
        await query.edit_message_text(f"Ты уже зарегистрирован. Позиция: {pos}")
        return

    registered_users.append(user_id)
    save_users(registered_users)

    position = len(registered_users)
    is_main = position <= MAX_SLOTS

    username = f"@{user.username}" if user.username else "—"

    admin_text = (
        " Новый игрок\n\n"
        f"Имя: {user.first_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}\n"
        f"Статус: {'Основной состав' if is_main else 'Лист ожидания'}\n"
        f"Позиция: {position}"
    )

    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

    keyboard = [[InlineKeyboardButton("Отменить участие", callback_data="cancel")]]
    await context.bot.send_message(
        chat_id=user_id,
        text="Ты зарегистрирован!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await query.edit_message_text("Ты зарегистрирован!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id

    if user_id in registered_users:
        position = registered_users.index(user_id) + 1
        was_main = position <= MAX_SLOTS

        registered_users.remove(user_id)
        save_users(registered_users)

        await query.edit_message_text("Ты отменил участие в игре.")

        username = f"@{user.username}" if user.username else "—"

        admin_text = (
            "Отмена участия\n\n"
            f"Имя: {user.first_name}\n"
            f"Username: {username}\n"
            f"ID: {user.id}\n"
            f"Был в составе: {'Основной' if was_main else 'Лист ожидания'}\n"
            f"Позиция на момент отмены: {position}"
        )

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text
        )
    else:
        await query.edit_message_text("Ты не был зарегистрирован.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(register, pattern="register"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    app.run_polling()

if __name__ == "__main__":
    main()
