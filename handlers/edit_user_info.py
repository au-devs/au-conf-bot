# edit_user_info.py
import logging
from telegram import Update, KeyboardButton
from telegram.ext import ContextTypes
from handlers.message_handler import edit_user_data

logger = logging.getLogger(__name__)
y_n_keyboard = [
    [KeyboardButton('Да'), KeyboardButton('Нет')]
]


async def edit_info(update: Update, context: ContextTypes):
    chat_type = update.message.chat.type
    if chat_type == 'private':
        context.user_data['state'] = 'USER_INFO_EDIT'
        context.user_data['quiz_chat_id'] = update.message.chat.id
        logger.info(f"Received command to edit user info from {update.effective_user.name}")
        await edit_user_data(update, context)
