# message_handler.py
import datetime
import logging
import os

import telegram.error
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from db.database import get_db_users, update_username
from handlers.birthday_reminders import process_birthday_reminders
from handlers.civil_war import civil_war, civil_war_stats, is_civil_war_trigger, is_civil_war_stats_trigger
from handlers.quiz import QUIZ_TRANSITIONS, edit_user_data, process_quiz


load_dotenv()

logger = logging.getLogger(__name__)


async def message_handler(update: Update, context: ContextTypes) -> None:
    if is_civil_war_stats_trigger(update.effective_message.text if update.effective_message else None):
        await civil_war_stats(update, context)
        return

    if is_civil_war_trigger(update.effective_message.text if update.effective_message else None):
        await civil_war(update, context)
        return

    if (context.user_data.get('state') in QUIZ_TRANSITIONS and update.message.chat.id ==
            context.user_data.get('quiz_chat_id')):
        await process_quiz(update, context)
    elif (context.user_data.get('state') == 'USER_INFO_EDIT' and update.message.chat.id ==
          context.user_data.get('quiz_chat_id')):
        await edit_user_data(update, context)

    await process_birthday_reminders(update, context)


async def username_updater(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    last_username_check = context.chat_data.get('last_username_check')
    if last_username_check is not None and (datetime.datetime.now() - last_username_check).days < 1:
        return

    logger.info("Usernames have not been checked today, refreshing...")
    context.chat_data['last_username_check'] = datetime.datetime.now()
    db_path = os.getenv('DB_PATH')
    users = get_db_users(db_path)
    for user in users:
        if user.user_id is None:
            continue
        try:
            chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user.user_id)
        except telegram.error.BadRequest:
            logger.warning(f"Member {user.user_id} doesn't exist in chat {chat.id}. Skipping...")
            continue
        except Exception as e:
            logger.warning(f"Failed to fetch member {user.user_id} in chat {chat.id}: {e}")
            continue

        actual_name = chat_member.user.name
        if actual_name and user.tg_username != actual_name:
            logger.info(
                f"Updating username for user_id={user.user_id}: "
                f"{user.tg_username!r} -> {actual_name!r}"
            )
            update_username(db_path, actual_name, user.user_id)
