# remove_user.py
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from db.database import remove_user, get_user, get_id_by_username, get_username_by_id

logger = logging.getLogger(__name__)

USAGE = (
    "Неверное количество аргументов\n"
    "Формат: /remove_user <user_id> или /remove_user <tg_username>\n"
    "Пример: /remove_user 12345 или /remove_user @User"
)


async def remove_user_handler(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /remove_user <user_id> or /remove_user <tg_username> is issued."""
    db_path = os.getenv('DB_PATH')
    if not is_admin(update.message.from_user.id):
        logger.info(f"{update.message.from_user.name} is not admin, not removing users")
        return
    logger.info(f"Received command to remove_user from {update.message.from_user.name}")
    if len(context.args) != 1:
        await update.message.reply_text(USAGE)
        return

    arg = context.args[0]
    try:
        if arg.isdigit():
            user_id = int(arg)
            username = get_username_by_id(db_path, user_id)
        else:
            username = arg
            user_id = get_id_by_username(db_path, arg)

        if user_id is None or username is None:
            await update.message.reply_text(
                f"Пользователь {arg} не найден в базе данных."
            )
            return

        remove_user(db_path, user_id)
        if not get_user(db_path, user_id):
            await update.message.reply_text(
                f"Пользователь {username} с id {user_id} удален из списка 🥲"
            )
        else:
            await update.message.reply_text(
                f"Не удалось удалить пользователя {username} с id {user_id}."
            )
    except Exception as e:
        logger.error(f"Error removing user {arg}: {str(e)}")
        await update.message.reply_text(
            f"Произошла ошибка при удалении пользователя {arg}."
        )
