# remove_user.py
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from db.database import remove_user, get_user, get_id_by_username, get_username_by_id

logger = logging.getLogger(__name__)


async def remove_user_handler(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /remove_user <user_id> or /remove_user <tg_username> is issued."""
    db_path = os.getenv('DB_PATH')
    if not is_admin(update.message.from_user.name):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    logger.info(f"Received command to remove_user from {update.message.from_user.name}")
    if len(context.args) != 1:
        await update.message.reply_text("Неверное количество аргументов\n"
                                        "Формат: /remove_user <user_id> или /remove_user <tg_username>\n"
                                        "Пример: /remove_user 12345 или remove_user @User")
        return
    try:
        user_id = context.args[0]
        if not context.args[0].isdigit():
            user_id = get_id_by_username(db_path, context.args[0])
            username = context.args[0]
        else:
            username = get_username_by_id(db_path, user_id)
        remove_user(db_path, user_id)
        if len(get_user(db_path, user_id)) == 0:
            await update.message.reply_text(f"Пользователь {username} с id {user_id} удален из списка 🥲")
    except Exception as e:
        logger.info(f"Error removing user: {str(e)}")