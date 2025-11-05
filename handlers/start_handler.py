# handlers.py
import os
import logging

from telegram import Update
from telegram.ext import ContextTypes
from db.database import get_user
from handlers.message_handler import process_quiz

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /start is issued."""
    db_path = os.getenv('DB_PATH')
    username = update.message.from_user.name
    user_id = update.message.from_user.id
    logger.info(f"User: {username} with ID {update.message.from_user.id} started bot")
    # Check if user exists in database
    if get_user(db_path, user_id):
        logger.info(f"User {username} exists in database")
        await update.message.reply_text(f"Привет, {username}!")
    else:
        chat_type = update.message.chat.type
        if chat_type == 'private':
            await update.message.reply_text(f"Привет, {username}. Ты новенький, давай заполним твои данные")
            # Set state to QUIZ_START
            context.user_data['user_id'] = user_id
            context.user_data['state'] = 'QUIZ_START'
            context.user_data['quiz_chat_id'] = update.message.chat.id
            context.user_data['tg_username'] = username
            await process_quiz(update, context)
        else:
            await update.message.reply_text(f"Привет, {username}. Если хочешь пройти опрос, напиши /start в личные "
                                            f"сообщения боту (мне)")
