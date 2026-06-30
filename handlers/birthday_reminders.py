import datetime
import logging
import os

from telegram.ext import ContextTypes

from db.database import get_db_users, get_reminder_status, reset_user_reminders, update_reminder
from handlers.global_stats import STATS_CHAT_IDS_KEY
from models.user_manager import get_closest_birthday
from util.util import markdown_escape


logger = logging.getLogger(__name__)
ADVANCE_REMINDER_TYPES = ['reminder_14_days', 'reminder_7_days', 'reminder_1_days']

# Birthday reminders broadcast to every group chat the bot is active in. We reuse the
# chat registry that already powers /stats (handlers/global_stats.py) instead of
# keeping a second, redundant list of "known" chats in sync with it.
KNOWN_GROUP_CHAT_IDS_KEY = STATS_CHAT_IDS_KEY


async def _broadcast(bot, chat_ids: list[int], text: str) -> None:
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')
        except Exception as e:
            logger.warning(f"Failed to send birthday reminder to chat_id={chat_id}: {e}")


async def send_daily_birthday_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily job_queue task: checks every user's birthday once a day and broadcasts
    reminders/congratulations to every group chat the bot is registered in.

    Replaces the old behaviour where reminders only fired as a side effect of someone
    sending a message in the group (see issue #7): on a quiet day, the actual
    "happy birthday" message on the day itself could be silently skipped, because
    get_closest_birthday() rolls over to next year as soon as the date is in the past.
    """
    db_path = os.getenv('DB_PATH')
    chat_ids = sorted(chat_id for chat_id in context.bot_data.get(KNOWN_GROUP_CHAT_IDS_KEY, set()) if chat_id < 0)
    if not chat_ids:
        logger.info("No chats registered for birthday reminders")
        return

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

        if days_until_birthday in (14, 7, 1):
            reminder_type = f"reminder_{days_until_birthday}_days"
            if get_reminder_status(db_path, user.user_id, user.tg_username, reminder_type):
                continue
            await _broadcast(
                context.bot,
                chat_ids,
                f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО НЕ УЧЕБНАЯ ТРЕВОГА ❗❗❗\n"
                f"Скоро день рождения у {markdown_escape(user.tg_username)}\n"
                f"*Дата:* {markdown_escape(user.birthday)}\n"
                f"*Желаемые подарки:* {markdown_escape(user.wishlist_url)}\n",
            )
            update_reminder(db_path, user.user_id, user.tg_username, reminder_type)
        elif days_until_birthday == 0:
            if get_reminder_status(db_path, user.user_id, user.tg_username, 'birthday_today'):
                continue
            await _broadcast(
                context.bot,
                chat_ids,
                f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО АВТОМАТИЧЕСКОЕ ПОЗДРАВЛЕНИЕ ❗❗❗\n"
                f"🎉 🎉 🎉  С ДНЕМ РОЖДЕНИЯ {markdown_escape(user.tg_username)}  🎉 🎉 🎉\n",
            )
            update_reminder(db_path, user.user_id, user.tg_username, 'birthday_today')
