import datetime
import logging
import os

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from db.database import add_user, update_user
from models.user_manager import create_user


logger = logging.getLogger(__name__)

y_n_keyboard = [
    [KeyboardButton('Да'), KeyboardButton('Нет')]
]
info_keyboard = [
    [KeyboardButton('Имя'), KeyboardButton('Дата рождения')],
    [KeyboardButton('Ссылка на wishlist'), KeyboardButton('Денежный подарок')],
    [KeyboardButton('Смешной подарок')],
]
QUIZ_FLOW = {
    'QUIZ_START': {'next_state': 'QUIZ_NAME', 'field': 'user_id', 'prompt': "Давай заполним твои данные"},
    'QUIZ_NAME': {'next_state': 'QUIZ_BIRTHDAY', 'field': 'name', 'prompt': "Как тебя называть?"},
    'QUIZ_BIRTHDAY': {'next_state': 'QUIZ_WISHLIST_URL', 'field': 'birthday', 'prompt': "Введи дату рождения в формате ДД.ММ.ГГГГ"},
    'QUIZ_WISHLIST_URL': {'next_state': 'QUIZ_MONEY_GIFTS', 'field': 'wishlist_url', 'prompt': "Введи что хочешь на праздники (или ссылку на wishlist)"},
    'QUIZ_MONEY_GIFTS': {'next_state': 'QUIZ_FUNNY_GIFTS', 'field': 'money_gifts', 'prompt': "Хочешь ли ты денежный подарок? (да/нет)"},
    'QUIZ_FUNNY_GIFTS': {'next_state': 'QUIZ_FINISHED', 'field': 'funny_gifts', 'prompt': "Хочешь ли ты смешной подарок? (да/нет)"},
}
STATE_RESPONSE_MAP = {
    **{state: config['prompt'] for state, config in QUIZ_FLOW.items()},
    'QUIZ_FINISHED': "Спасибо за ответы, информация сохранена!",
    'USER_INFO_EDIT': "Что хочешь изменить?",
}
QUIZ_TRANSITIONS = {state: config['next_state'] for state, config in QUIZ_FLOW.items()}
QUIZ_STATE_TO_FIELD = {state: config['field'] for state, config in QUIZ_FLOW.items()}
KEYBOARD_TO_FIELD = {
    'Имя': 'name',
    'Дата рождения': 'birthday',
    'Ссылка на wishlist': 'wishlist_url',
    'Денежный подарок': 'money_gifts',
    'Смешной подарок': 'funny_gifts',
}
FIELD_TO_PROMPT = {
    config['field']: config['prompt']
    for config in QUIZ_FLOW.values()
    if config['field'] != 'user_id'
}
QUIZ_SESSION_KEYS = {
    'state',
    'quiz_chat_id',
    'field_to_edit',
    'user_id',
    'tg_username',
    'name',
    'birthday',
    'wishlist_url',
    'money_gifts',
    'funny_gifts',
}
YES_NO_FIELDS = {'money_gifts', 'funny_gifts'}


def clear_quiz_session(context: ContextTypes) -> None:
    for key in QUIZ_SESSION_KEYS:
        context.user_data.pop(key, None)


def clear_edit_session(context: ContextTypes) -> None:
    context.user_data.pop('field_to_edit', None)
    context.user_data.pop('quiz_chat_id', None)
    context.user_data.pop('state', None)


def normalize_yes_no_value(value):
    if not isinstance(value, str):
        return None
    normalized_value = value.strip().lower()
    if normalized_value == 'да':
        return True
    if normalized_value == 'нет':
        return False
    return None


def normalize_birthday_value(value):
    if not isinstance(value, str):
        return None
    try:
        parsed_date = datetime.datetime.strptime(value.strip(), '%d.%m.%Y')
    except ValueError:
        return None
    return parsed_date.strftime('%d.%m.%Y')


def normalize_text_value(value):
    if not isinstance(value, str):
        return None
    stripped_value = value.strip()
    return stripped_value or None


def normalize_field_value(field: str, value):
    if field == 'birthday':
        return normalize_birthday_value(value)
    if field in YES_NO_FIELDS:
        return normalize_yes_no_value(value)
    return normalize_text_value(value)


def get_validation_error(field: str) -> str:
    if field == 'birthday':
        return "Дата должна быть в формате ДД.ММ.ГГГГ."
    if field in YES_NO_FIELDS:
        return "Пожалуйста, выбери один из вариантов: Да или Нет."
    return "Ответ не должен быть пустым."


def get_reply_markup_for_field(field: str):
    if field in YES_NO_FIELDS:
        return ReplyKeyboardMarkup(y_n_keyboard, one_time_keyboard=True, resize_keyboard=True)
    return None


def get_reply_markup_for_state(state: str):
    if state == 'QUIZ_FINISHED':
        return ReplyKeyboardRemove()
    field = QUIZ_STATE_TO_FIELD.get(state)
    if field is None:
        return None
    return get_reply_markup_for_field(field)


async def send_state_prompt(update: Update, state: str, prefix: str | None = None) -> None:
    prompt = STATE_RESPONSE_MAP.get(state)
    if prompt is None:
        return
    message_text = f"{prefix}\n{prompt}" if prefix else prompt
    reply_markup = get_reply_markup_for_state(state)
    if reply_markup is None:
        await update.message.reply_text(message_text)
        return
    await update.message.reply_text(message_text, reply_markup=reply_markup)


async def update_user_data(update: Update, context: ContextTypes, next_state: str) -> bool:
    user_id = update.message.from_user.id
    user_input = update.message.text or ''
    current_state = context.user_data.get('state')
    current_field = QUIZ_STATE_TO_FIELD.get(current_state)

    if context.user_data.get('user_id') is None:
        context.user_data['user_id'] = user_id

    if current_state == 'QUIZ_START':
        context.user_data['user_id'] = context.user_data.get('user_id', user_id)
    elif current_field is not None:
        normalized_input = normalize_field_value(current_field, user_input)
        if normalized_input is None:
            await send_state_prompt(update, current_state, get_validation_error(current_field))
            return False
        context.user_data[current_field] = normalized_input

    context.user_data['state'] = next_state
    await send_state_prompt(update, next_state)
    return True


async def process_quiz(update: Update, context: ContextTypes) -> None:
    current_state = context.user_data.get('state')
    logger.info(f"Processing quiz, current state: {current_state}")
    next_state = QUIZ_TRANSITIONS.get(current_state)
    if next_state is None:
        return

    state_updated = await update_user_data(update, context, next_state)
    if not state_updated:
        return

    if next_state == 'QUIZ_FINISHED':
        user = create_user(context.user_data)
        add_user(os.getenv('DB_PATH'), user)
        logger.info(f"User {user.tg_username} with id {user.user_id} added to database")
        clear_quiz_session(context)


async def edit_user_data(update: Update, context: ContextTypes) -> None:
    user_input = update.message.text or ''
    user_id = update.message.from_user.id
    current_state = context.user_data.get('state')
    if context.user_data.get('user_id') is None:
        context.user_data['user_id'] = user_id
    field_to_edit = context.user_data.get('field_to_edit')
    if user_input == '/edit_info':
        reply_markup = ReplyKeyboardMarkup(info_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(STATE_RESPONSE_MAP.get(current_state), reply_markup=reply_markup)
        return
    if current_state == 'USER_INFO_EDIT' and field_to_edit is None:
        normalized_field = KEYBOARD_TO_FIELD.get(user_input)
        if normalized_field is None:
            reply_markup = ReplyKeyboardMarkup(info_keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Пожалуйста, выбери поле из клавиатуры.",
                reply_markup=reply_markup,
            )
            return
        logger.info(f"User {update.effective_user.name} is editing {normalized_field}")
        context.user_data['field_to_edit'] = normalized_field
        reply_markup = get_reply_markup_for_field(normalized_field)
        if reply_markup is not None:
            await update.message.reply_text(FIELD_TO_PROMPT[normalized_field], reply_markup=reply_markup)
            return
        await update.message.reply_text(FIELD_TO_PROMPT[normalized_field])
        return
    if current_state == 'USER_INFO_EDIT' and field_to_edit is not None:
        normalized_input = normalize_field_value(field_to_edit, user_input)
        if normalized_input is None:
            reply_markup = get_reply_markup_for_field(field_to_edit)
            await update.message.reply_text(
                get_validation_error(field_to_edit),
                reply_markup=reply_markup,
            )
            return
        update_user(os.getenv('DB_PATH'), user_id, field_to_edit, normalized_input)
        logger.info(f"User {update.effective_user.name} edited {field_to_edit} to {normalized_input}")
        clear_edit_session(context)
        await update.message.reply_text('Изменения сохранены', reply_markup=ReplyKeyboardRemove())
