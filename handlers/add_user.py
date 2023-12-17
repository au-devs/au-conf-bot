# add_user.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from handlers.message_handler import process_quiz

logger = logging.getLogger(__name__)


async def add_user(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /add_user <tg_username> is issued."""
    username = update.message.from_user.name
    if not is_admin(update.message.from_user.name):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    logger.info(f"Received command to add user from {username}")
    if len(context.args) != 1:
        await update.message.reply_text("Неверное количество аргументов")
        return
    tg_username = context.args[0]
    context.user_data['quiz_chat_id'] = update.message.chat.id
    context.user_data['tg_username'] = tg_username
    context.user_data['state'] = 'QUIZ_START'
    await process_quiz(update, context)
