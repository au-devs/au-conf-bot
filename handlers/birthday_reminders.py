import datetime
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_db_users, get_reminder_status, reset_user_reminders, update_reminder
from models.user_manager import get_closest_birthday
from util.util import markdown_escape


logger = logging.getLogger(__name__)
ADVANCE_REMINDER_TYPES = ['reminder_14_days', 'reminder_7_days', 'reminder_1_days']


async def process_birthday_reminders(update: Update, context: ContextTypes) -> None:
    chat = update.effective_chat
    if chat is None or getattr(chat, 'type', None) not in {'group', 'supergroup'}:
        return

    last_birthday_check = context.chat_data.get('last_birthday_check')
    if last_birthday_check is not None and (datetime.datetime.now() - last_birthday_check).days < 1:
        return

    context.chat_data['last_birthday_check'] = datetime.datetime.now()
    logger.info("Birthdays are not checked, checking birthdays")
    db_path = os.getenv('DB_PATH')
    users = get_db_users(db_path)
    for user in users:
        if user.birthday is None:
            continue
        birthday_date = get_closest_birthday(user)
        days_until_birthday = (birthday_date - datetime.date.today()).days
        if days_until_birthday > 14:
            reset_user_reminders(db_path, user.user_id, ADVANCE_REMINDER_TYPES)
        if days_until_birthday != 0:
            reset_user_reminders(db_path, user.user_id, ['birthday_today'])
        if days_until_birthday in [14, 7, 1]:
            reminder_type = f"reminder_{days_until_birthday}_days"
            if get_reminder_status(db_path, user.user_id, user.tg_username, reminder_type):
                continue
            await chat.send_message(
                f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО НЕ УЧЕБНАЯ ТРЕВОГА ❗❗❗\n"
                f"Скоро день рождения у {markdown_escape(user.tg_username)}\n"
                f"*Дата:* {markdown_escape(user.birthday)}\n"
                f"*Желаемые подарки:* {markdown_escape(user.wishlist_url)}\n",
                parse_mode='MarkdownV2'
            )
            update_reminder(db_path, user.user_id, user.tg_username, reminder_type)
        elif days_until_birthday == 0:
            if get_reminder_status(db_path, user.user_id, user.tg_username, 'birthday_today'):
                continue
            await chat.send_message(
                f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО АВТОМАТИЧЕСКОЕ ПОЗДРАВЛЕНИЕ ❗❗❗\n"
                f"🎉 🎉 🎉  С ДНЕМ РОЖДЕНИЯ {markdown_escape(user.tg_username)}  🎉 🎉 🎉\n",
                parse_mode='MarkdownV2'
            )
            update_reminder(db_path, user.user_id, user.tg_username, 'birthday_today')
