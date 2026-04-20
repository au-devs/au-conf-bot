# message_handler.py
import os
import logging
import datetime

import telegram.error
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from db.database import add_user, get_db_users, update_user, update_reminder, get_reminder_status, \
    reset_birthday_today_reminders, update_username
from models.user_manager import create_user, get_closest_birthday
from util.util import markdown_escape


load_dotenv()

logger = logging.getLogger(__name__)

y_n_keyboard = [
    [KeyboardButton('Да'), KeyboardButton('Нет')]
]
info_keyboard = [
    [KeyboardButton('Имя'), KeyboardButton('Дата рождения')],
    [KeyboardButton('Ссылка на wishlist'), KeyboardButton('Денежный подарок')],
    [KeyboardButton('Смешной подарок')],
]

STATE_RESPONSE_MAP = {
    'QUIZ_START': "Давай заполним твои данные",
    'QUIZ_NAME': "Как тебя называть?",
    'QUIZ_BIRTHDAY': "Введи дату рождения в формате ДД.ММ.ГГГГ",
    'QUIZ_WISHLIST_URL': "Введи что хочешь на праздники (или ссылку на wishlist)",
    'QUIZ_MONEY_GIFTS': "Хочешь ли ты денежный подарок? (да/нет)",
    'QUIZ_FUNNY_GIFTS': "Хочешь ли ты смешной подарок? (да/нет)",
    'QUIZ_FINISHED': "Спасибо за ответы, информация сохранена!",
    'USER_INFO_EDIT': "Что хочешь изменить?",
}
QUIZ_STATE_TO_FIELD = {
    'QUIZ_START': 'user_id',
    'QUIZ_NAME': 'name',
    'QUIZ_BIRTHDAY': 'birthday',
    'QUIZ_WISHLIST_URL': 'wishlist_url',
    'QUIZ_MONEY_GIFTS': 'money_gifts',
    'QUIZ_FUNNY_GIFTS': 'funny_gifts',
    'QUIZ_FINISHED': '',
}
KEYBOARD_TO_FIELD = {
    'Имя': 'name',
    'Дата рождения': 'birthday',
    'Ссылка на wishlist': 'wishlist_url',
    'Денежный подарок': 'money_gifts',
    'Смешной подарок': 'funny_gifts',
}

async def update_user_data(update: Update, context: ContextTypes, next_state: str) -> None:
    user_id = update.message.from_user.id
    user_input = update.message.text
    current_state = context.user_data.get('state')
    reply_markup = ReplyKeyboardMarkup(y_n_keyboard, one_time_keyboard=True, resize_keyboard=True)

    if context.user_data.get('user_id') is None:
        context.user_data['user_id'] = user_id
    else:
        if current_state == 'QUIZ_START':
            user_input = context.user_data.get('user_id')
        context.user_data[QUIZ_STATE_TO_FIELD.get(current_state)] = user_input
    context.user_data['state'] = next_state

    if next_state == 'QUIZ_MONEY_GIFTS' or next_state == 'QUIZ_FUNNY_GIFTS':
        await update.message.reply_text(STATE_RESPONSE_MAP.get(next_state), reply_markup=reply_markup)
        return

    elif next_state == 'QUIZ_FINISHED':
        await update.message.reply_text(STATE_RESPONSE_MAP.get(next_state), reply_markup=ReplyKeyboardRemove())
        return
    await update.message.reply_text(STATE_RESPONSE_MAP.get(next_state))

async def message_handler(update: Update, context: ContextTypes) -> None:
    if (context.user_data.get('state') in QUIZ_STATE_TO_FIELD.keys() and update.message.chat.id ==
            context.user_data.get('quiz_chat_id')):
        await process_quiz(update, context)
    elif (context.user_data.get('state') == 'USER_INFO_EDIT' and update.message.chat.id ==
          context.user_data.get('quiz_chat_id')):
        await edit_user_data(update, context)
    
    last_birthday_check = context.chat_data.get('last_birthday_check')
    if last_birthday_check is None or (datetime.datetime.now() - last_birthday_check).days >= 1:
        # Set last_birthday_check to now
        context.chat_data['last_birthday_check'] = datetime.datetime.now()
        logger.info(f"Birthdays are not checked, checking birthdays")
        users = get_db_users(os.getenv('DB_PATH'))
        for user in users:
            if user.birthday is None:
                continue
            birthday_date = get_closest_birthday(user)
            days_until_birthday = (birthday_date - datetime.date.today()).days
            if days_until_birthday in [14, 7, 1]:
                reminder_type = f"reminder_{days_until_birthday}_days"
                if not get_reminder_status(os.getenv('DB_PATH'), user.user_id, user.tg_username, reminder_type):
                    await update.message.reply_text(
                        f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО НЕ УЧЕБНАЯ ТРЕВОГА ❗❗❗\n"
                        f"Скоро день рождения у {markdown_escape(user.tg_username)}\n"
                        f"*Дата:* {markdown_escape(user.birthday)}\n"
                        f"*Желаемые подарки:* {markdown_escape(user.wishlist_url)}\n",
                        parse_mode='MarkdownV2'
                    )
                    update_reminder(os.getenv('DB_PATH'), user.user_id, user.tg_username, reminder_type)
            elif days_until_birthday == 0:
                if not get_reminder_status(os.getenv('DB_PATH'), user.user_id, user.tg_username, 'birthday_today'):
                    await update.message.reply_text(
                        f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО АВТОМАТИЧЕСКОЕ ПОЗДРАВЛЕНИЕ ❗❗❗\n"
                        f"🎉 🎉 🎉  С ДНЕМ РОЖДЕНИЯ {markdown_escape(user.tg_username)}  🎉 🎉 🎉\n",
                        parse_mode='MarkdownV2'
                    )
                    update_reminder(os.getenv('DB_PATH'), user.user_id, user.tg_username, 'birthday_today')
        reset_birthday_today_reminders(os.getenv('DB_PATH'))

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
        logger.info(f"User {user.tg_username} with id {user.user_id} added to database")

async def edit_user_data(update: Update, context: ContextTypes) -> None:
    user_input = update.message.text
    user_id = update.message.from_user.id
    current_state = context.user_data.get('state')
    y_n_markup = ReplyKeyboardMarkup(y_n_keyboard, one_time_keyboard=True, resize_keyboard=True)
    if context.user_data.get('user_id') is None:
        context.user_data['user_id'] = user_id
    field_to_edit = context.user_data.get('field_to_edit')
    if user_input == '/edit_info':
        reply_markup = ReplyKeyboardMarkup(info_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(STATE_RESPONSE_MAP.get(current_state), reply_markup=reply_markup)
        return
    elif current_state == 'USER_INFO_EDIT' and field_to_edit is None:
        field_to_edit = user_input
        logger.info(f"User {update.effective_user.name} is editing {field_to_edit}")
        context.user_data['field_to_edit'] = KEYBOARD_TO_FIELD.get(field_to_edit)
        if context.user_data['field_to_edit'] == 'money_gifts' or context.user_data['field_to_edit'] == 'funny_gifts':
            await update.message.reply_text(STATE_RESPONSE_MAP.get(current_state), reply_markup=y_n_markup)
        await update.message.reply_text('Введите новое значение')
    elif current_state == 'USER_INFO_EDIT' and field_to_edit is not None:
        if user_input == 'Да':
            user_input = True
        elif user_input == 'Нет':
            user_input = False
        update_user(os.getenv('DB_PATH'), user_id, field_to_edit, user_input)
        logger.info(f"User {update.effective_user.name} edited {field_to_edit} to {user_input}")
        context.user_data['field_to_edit'] = None
        context.user_data['state'] = None
        await update.message.reply_text('Изменения сохранены', reply_markup=ReplyKeyboardRemove())

async def username_updater(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    last_username_check = context.chat_data.get('last_username_check')
    if last_username_check is not None and (datetime.datetime.now() - last_username_check).days < 1:
        return

    logger.info("Usernames have not been checked today, refreshing...")
    context.chat_data['last_username_check'] = datetime.datetime.now()
    db_path = os.getenv('DB_PATH')
    users = get_db_users(db_path)
    for user in users:
        if user.user_id is None:
            continue
        try:
            chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user.user_id)
        except telegram.error.BadRequest:
            logger.warning(f"Member {user.user_id} doesn't exist in chat {chat.id}. Skipping...")
            continue
        except Exception as e:
            logger.warning(f"Failed to fetch member {user.user_id} in chat {chat.id}: {e}")
            continue

        actual_name = chat_member.user.name
        if actual_name and user.tg_username != actual_name:
            logger.info(
                f"Updating username for user_id={user.user_id}: "
                f"{user.tg_username!r} -> {actual_name!r}"
            )
            update_username(db_path, actual_name, user.user_id)

