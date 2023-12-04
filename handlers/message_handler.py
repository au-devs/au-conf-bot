# message_handler.py
import logging

from telegram import Update
from telegram.ext import ContextTypes

QUIZ_START, QUIZ_NAME, QUIZ_BIRTHDAY, QUIZ_WISHLIST_URL, QUIZ_MONEY_GIFTS, QUIZ_FUNNY_GIFTS, QUIZ_FINISHED = range(7)
logger = logging.getLogger(__name__)


async def process_quiz(update: Update, context: ContextTypes) -> None:
    username = update.message.from_user.name
    user_input = update.message.text
    current_state = context.user_data.get('state')
    logger.info(f"User {username} input: {user_input}, current state: {current_state}")
    logger.info(f"User data: {context.user_data}")

    if current_state == 'QUIZ_START':
        await update.message.reply_text("1. Как тебя называть?")
        context.user_data['state'] = QUIZ_NAME

    elif current_state == QUIZ_NAME:
        context.user_data['name'] = user_input
        logger.info(f"User {username} entered name")
        context.user_data['state'] = QUIZ_BIRTHDAY
        await update.message.reply_text("2. Введи дату рождения в формате ДД.ММ.ГГГГ")

    elif current_state == QUIZ_BIRTHDAY:
        context.user_data['birthday'] = user_input
        logger.info(f"User {username} entered birthday")
        context.user_data['state'] = QUIZ_WISHLIST_URL
        await update.message.reply_text("3. Введи что хочешь на праздники (или ссылку на wishlist)")

    elif current_state == QUIZ_WISHLIST_URL:
        context.user_data['wishlist_url'] = user_input
        logger.info(f"User {username} entered wishlist url")
        context.user_data['state'] = QUIZ_MONEY_GIFTS
        await update.message.reply_text("4. Хочешь ли ты денежный подарок? (да/нет)")

    elif current_state == QUIZ_MONEY_GIFTS:
        context.user_data['money_gifts'] = user_input
        logger.info(f"User {username} entered money gifts")
        context.user_data['state'] = QUIZ_FUNNY_GIFTS
        await update.message.reply_text("5. Хочешь ли ты смешной подарок? (да/нет)")

    elif current_state == QUIZ_FUNNY_GIFTS:
        context.user_data['funny_gifts'] = user_input
        logger.info(f"User {username} entered funny gifts")
        context.user_data['state'] = QUIZ_FINISHED
        await update.message.reply_text("Спасибо за ответы! Теперь ты в списке!")
        await update.message.reply_text(f"{context.user_data}")
