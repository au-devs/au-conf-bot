# handlers.py
import os
import logging

from telegram import Update
from telegram.ext import ContextTypes
from db.database import get_user
from message_handler import process_quiz

logger = logging.getLogger(__name__)
# States


async def start(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /start is issued."""
    db_path = os.getenv('DB_PATH')
    username = update.message.from_user.name
    logger.info(f"User: {username} with ID {update.message.from_user.id} started bot")
    # Check if user exists in database
    if get_user(db_path, username):
        logger.info(f"User {username} exists in database")
        await update.message.reply_text(f"Привет, {username}!")
    else:
        await update.message.reply_text(f"Привет, {username}. Ты новенький, давай заполним твои данные")
        # Устанавливаем состояние в первый шаг
        context.user_data['state'] = 'QUIZ_START'
        await process_quiz(update, context)
