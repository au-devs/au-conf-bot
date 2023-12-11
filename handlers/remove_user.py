# remove_user.py
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from db.database import remove_user, get_user

logger = logging.getLogger(__name__)


async def remove_user_handler(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /remove_user <tg_username> is issued."""
    db_path = os.getenv('DB_PATH')
    username = update.message.from_user.name
    if not is_admin(update.message.from_user.name):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    logger.info(f"Received command to remove_user from {username}")
    if len(context.args) != 1:
        await update.message.reply_text("Неверное количество аргументов")
        return
    tg_username = context.args[0]
    logger.info(f"Removing user {tg_username}")
    remove_user(db_path, tg_username)
    if len(get_user(db_path, tg_username)) == 0:
        await update.message.reply_text(f"Пользователь {tg_username} удален из списка 🥲")
