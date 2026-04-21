# add_user.py
import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.admin_checker import is_admin
from handlers.quiz import clear_quiz_session, process_quiz

logger = logging.getLogger(__name__)


async def add_user(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /add_user <tg_username> <user_id> is issued."""
    username = update.message.from_user.name
    if not is_admin(update.message.from_user.id):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    logger.info(f"Received command to add user from {username}")
    if update.message.chat.type != 'private':
        await update.message.reply_text("Запусти /add_user в личке с ботом. Анкета заполняется в том же чате.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Неверное количество аргументов.\n"
                                        "Формат: /add_user tg_username user_id.\n"
                                        "Например, /add_user @User 12345")
        return
    tg_username = context.args[0]
    user_id_str = context.args[1]
    if not user_id_str.isdigit():
        await update.message.reply_text("Неверный формат ввода. user_id должен быть числом. \n"
                                        "Формат: /add_user tg_username user_id.\n"
                                        "Например, /add_user @User 12345")
        return
    clear_quiz_session(context)
    context.user_data['quiz_chat_id'] = update.message.chat.id
    context.user_data['tg_username'] = tg_username
    context.user_data['state'] = 'QUIZ_START'
    context.user_data['user_id'] = int(user_id_str)
    await update.message.reply_text(
        f"Заполняем анкету для {tg_username}. Ответы будут сохранены на user_id {user_id_str}."
    )
    await process_quiz(update, context)
