# add_user.py
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from handlers.admin_checker import is_admin
from handlers.message_handler import process_quiz

logger = logging.getLogger(__name__)


async def add_user(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /add_user <tg_username> <user_id> is issued."""
    username = update.message.from_user.name
    if not is_admin(update.message.from_user.name):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    logger.info(f"Received command to add user from {username}")
    if len(context.args) != 2:
        await update.message.reply_text("Неверное количество аргументов.\n"
                                        "Формат: /add_user tg_username user_id.\n"
                                        "Например, /add_user @User 12345")
        return
    tg_username = context.args[0]
    user_id = context.args[1]
    if not user_id.isdigit():
        await update.message.reply_text("Неверный формат ввода. user_id должен быть числом. \n"
                                        "Формат: /add_user tg_username user_id.\n"
                                        "Например, /add_user @User 12345")
        return
    context.user_data['quiz_chat_id'] = update.message.chat.id
    context.user_data['tg_username'] = tg_username
    context.user_data['state'] = 'QUIZ_START'
    context.user_data['user_id'] = user_id
    await process_quiz(update, context)
