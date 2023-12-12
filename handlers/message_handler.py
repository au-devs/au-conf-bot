# message_handler.py
import os
import logging
import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from db.database import add_user, get_db_users
from models.user_manager import create_user, is_near_birthday
from handlers.user_info import user_info

logger = logging.getLogger(__name__)

y_n_keyboard = [
    [KeyboardButton('Да'), KeyboardButton('Нет')]
]

STATE_RESPONSE_MAP = {
    'QUIZ_START': "Давай заполним твои данные",
    'QUIZ_NAME': "Как тебя называть?",
    'QUIZ_BIRTHDAY': "Введи дату рождения в формате ДД.ММ.ГГГГ",
    'QUIZ_WISHLIST_URL': "Введи что хочешь на праздники (или ссылку на wishlist)",
    'QUIZ_MONEY_GIFTS': "Хочешь ли ты денежный подарок? (да/нет)",
    'QUIZ_FUNNY_GIFTS': "Хочешь ли ты смешной подарок? (да/нет)",
    'QUIZ_FINISHED': "Спасибо за ответы, информация сохранена!",
}
QUIZ_STATE_TO_FIELD = {
    'QUIZ_START': 'tg_username',
    'QUIZ_NAME': 'name',
    'QUIZ_BIRTHDAY': 'birthday',
    'QUIZ_WISHLIST_URL': 'wishlist_url',
    'QUIZ_MONEY_GIFTS': 'money_gifts',
    'QUIZ_FUNNY_GIFTS': 'funny_gifts',
    'QUIZ_FINISHED': '',
}


async def update_user_data(update: Update, context: ContextTypes, next_state: str) -> None:
    username = update.message.from_user.name
    user_input = update.message.text
    current_state = context.user_data.get('state')
    reply_markup = ReplyKeyboardMarkup(y_n_keyboard, one_time_keyboard=True, resize_keyboard=True)
    logger.info(f"User {username} input: {user_input}, current state: {current_state}")

    if context.user_data.get('tg_username') is None:
        context.user_data['tg_username'] = username
    else:
        if current_state == 'QUIZ_START':
            user_input = username
        context.user_data[QUIZ_STATE_TO_FIELD.get(current_state)] = user_input
    context.user_data['state'] = next_state

    if next_state == 'QUIZ_MONEY_GIFTS' or next_state == 'QUIZ_FUNNY_GIFTS':
        await update.message.reply_text(STATE_RESPONSE_MAP.get(next_state), reply_markup=reply_markup)
        return
    await update.message.reply_text(STATE_RESPONSE_MAP.get(next_state))


async def message_handler(update: Update, context: ContextTypes) -> None:
    if context.user_data.get('state') in QUIZ_STATE_TO_FIELD.keys():
        # ignore chat if it's not same as quiz_chat_id
        if update.message.chat.id != context.user_data.get('quiz_chat_id'):
            return
        await process_quiz(update, context)
    else:
        last_birthday_check = context.chat_data.get('last_birthday_check')
        if last_birthday_check is None or (datetime.datetime.now() - last_birthday_check).days >= 1:
            # Set last_birthday_check to now
            context.chat_data['last_birthday_check'] = datetime.datetime.now()
            logger.info(f"Birthdays is not checked, checking birthdays")
            users = get_db_users(os.getenv('DB_PATH'))
            for user in users:
                if is_near_birthday(user):
                    logging.info(f"User {user.tg_username} is near birthday")
                    await update.message.reply_text(
                        f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО НЕ УЧЕБНАЯ ТРЕВОГА ❗❗❗\n"
                        f"Скоро день рождения у {user.tg_username}\n"
                        f"Дата: {user.birthday}\n"
                        f"Желаемые подарки:{user.wishlist_url}\n"
                        f"Возможно пора собирать секретную конфу 🤔🤔🤔")
            logger.info(f"Checked birthdays for {len(users)} users")
            return


async def process_quiz(update: Update, context: ContextTypes) -> None:
    current_state = context.user_data.get('state')
    logger.info(f"Processing quiz, current state: {current_state}")
    if current_state == 'QUIZ_START':
        await update_user_data(update, context, 'QUIZ_NAME')
    elif current_state == 'QUIZ_NAME':
        await update_user_data(update, context, 'QUIZ_BIRTHDAY')
    elif current_state == 'QUIZ_BIRTHDAY':
        await update_user_data(update, context, 'QUIZ_WISHLIST_URL')
    elif current_state == 'QUIZ_WISHLIST_URL':
        await update_user_data(update, context, 'QUIZ_MONEY_GIFTS')
    elif current_state == 'QUIZ_MONEY_GIFTS':
        await update_user_data(update, context, 'QUIZ_FUNNY_GIFTS')
    elif current_state == 'QUIZ_FUNNY_GIFTS':
        await update_user_data(update, context, 'QUIZ_FINISHED')
        user = create_user(context.user_data)
        add_user(os.getenv('DB_PATH'), user)
        logger.info(f"User {user.tg_username} added to database")
