# message_handler.py
import os
import logging

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from db.database import add_user
from models.user_manager import create_user

QUIZ_START, QUIZ_NAME, QUIZ_BIRTHDAY, QUIZ_WISHLIST_URL, QUIZ_MONEY_GIFTS, QUIZ_FUNNY_GIFTS, QUIZ_FINISHED = range(7)
logger = logging.getLogger(__name__)

y_n_keyboard = [
    [KeyboardButton('Да'), KeyboardButton('Нет')]
]


async def process_quiz(update: Update, context: ContextTypes) -> None:
    db_path = os.getenv('DB_PATH')
    reply_markup = ReplyKeyboardMarkup(y_n_keyboard, one_time_keyboard=True, resize_keyboard=True)

    username = update.message.from_user.name
    user_input = update.message.text
    current_state = context.user_data.get('state')
    logger.info(f"User {username} input: {user_input}, current state: {current_state}")
    logger.info(f"User data: {context.user_data}")

    if current_state == 'QUIZ_START':
        await update.message.reply_text("1. Как тебя называть?")
        context.user_data['tg_username'] = update.message.from_user.name
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
        await update.message.reply_text("4. Хочешь ли ты денежный подарок? (да/нет)", reply_markup=reply_markup)

    elif current_state == QUIZ_MONEY_GIFTS:
        selected_option = update.message.text
        context.user_data['money_gifts'] = False
        if selected_option.lower() == 'да':
            context.user_data['money_gifts'] = True
        logger.info(f"User {username} entered money gifts")
        context.user_data['state'] = QUIZ_FUNNY_GIFTS
        await update.message.reply_text("5. Хочешь ли ты смешной подарок? (да/нет)", reply_markup=reply_markup)

    elif current_state == QUIZ_FUNNY_GIFTS:
        selected_option = update.message.text
        context.user_data['funny_gifts'] = False
        if selected_option.lower() == 'да':
            context.user_data['funny_gifts'] = True
        logger.info(f"User {username} entered funny gifts")
        context.user_data['state'] = QUIZ_FINISHED

        # Add user to database
        add_user(db_path, create_user(context.user_data))
        await update.message.reply_text("Спасибо за ответы! Теперь ты в списке!")
        await update.message.reply_text(f"{context.user_data}")
