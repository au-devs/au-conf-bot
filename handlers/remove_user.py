# remove_user.py
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from db.database import remove_user, get_user

logger = logging.getLogger(__name__)


async def remove_user_handler(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /remove_user <user_id> is issued."""
    db_path = os.getenv('DB_PATH')
    username = update.message.from_user.name
    if not is_admin(update.message.from_user.name):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    logger.info(f"Received command to remove_user from {username}")
    if len(context.args) != 1:
        await update.message.reply_text("Неверное количество аргументов")
        return
    target_user_id = context.args[0]
    logger.info(f"Removing user {target_user_id}")
    remove_user(db_path, target_user_id)
    if len(get_user(db_path, target_user_id)) == 0:
        await update.message.reply_text(f"Пользователь с id {target_user_id} удален из списка 🥲")