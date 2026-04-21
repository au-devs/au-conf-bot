import unittest
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

telegram_module = types.ModuleType('telegram')
telegram_error_module = types.ModuleType('telegram.error')
telegram_ext_module = types.ModuleType('telegram.ext')
dotenv_module = types.ModuleType('dotenv')


class DummyUpdate:
    pass


class DummyKeyboardButton:
    def __init__(self, text):
        self.text = text


class DummyReplyKeyboardMarkup:
    def __init__(self, keyboard, one_time_keyboard=False, resize_keyboard=False):
        self.keyboard = keyboard
        self.one_time_keyboard = one_time_keyboard
        self.resize_keyboard = resize_keyboard


class DummyReplyKeyboardRemove:
    pass


class DummyContextTypes:
    DEFAULT_TYPE = object


telegram_module.Update = DummyUpdate
telegram_module.KeyboardButton = DummyKeyboardButton
telegram_module.ReplyKeyboardMarkup = DummyReplyKeyboardMarkup
telegram_module.ReplyKeyboardRemove = DummyReplyKeyboardRemove
telegram_module.error = telegram_error_module
telegram_error_module.BadRequest = type('BadRequest', (Exception,), {})
telegram_ext_module.ContextTypes = DummyContextTypes
dotenv_module.load_dotenv = lambda: None
sys.modules.setdefault('telegram', telegram_module)
sys.modules.setdefault('telegram.error', telegram_error_module)
sys.modules.setdefault('telegram.ext', telegram_ext_module)
sys.modules.setdefault('dotenv', dotenv_module)

from handlers.quiz import clear_edit_session, process_quiz, update_user_data


def build_update(text: str, user_id: int = 123, chat_id: int = 456):
    from_user = SimpleNamespace(id=user_id, name='Tester')
    chat = SimpleNamespace(id=chat_id)
    message = SimpleNamespace(text=text, from_user=from_user, chat=chat, reply_text=AsyncMock())
    return SimpleNamespace(message=message, effective_message=message, effective_user=from_user, effective_chat=chat)


def build_context(user_data=None):
    return SimpleNamespace(user_data=user_data or {}, chat_data={})


class TestQuizFlow(unittest.IsolatedAsyncioTestCase):
    def test_clear_edit_session_removes_stale_edit_state(self):
        context = build_context({
            'state': 'USER_INFO_EDIT',
            'quiz_chat_id': 456,
            'field_to_edit': 'money_gifts',
            'user_id': 123,
            'name': 'Tester',
        })

        clear_edit_session(context)

        self.assertNotIn('state', context.user_data)
        self.assertNotIn('quiz_chat_id', context.user_data)
        self.assertNotIn('field_to_edit', context.user_data)
        self.assertEqual(context.user_data['user_id'], 123)
        self.assertEqual(context.user_data['name'], 'Tester')

    async def test_yes_no_question_rejects_unexpected_text(self):
        update = build_update('может быть')
        context = build_context({'state': 'QUIZ_MONEY_GIFTS', 'user_id': 123})

        result = await update_user_data(update, context, 'QUIZ_FUNNY_GIFTS')

        self.assertFalse(result)
        self.assertEqual(context.user_data['state'], 'QUIZ_MONEY_GIFTS')
        update.message.reply_text.assert_awaited_once()
        self.assertIn('Да или Нет', update.message.reply_text.await_args.args[0])

    async def test_birthday_question_rejects_invalid_date(self):
        update = build_update('31/12/2000')
        context = build_context({'state': 'QUIZ_BIRTHDAY', 'user_id': 123})

        result = await update_user_data(update, context, 'QUIZ_WISHLIST_URL')

        self.assertFalse(result)
        self.assertEqual(context.user_data['state'], 'QUIZ_BIRTHDAY')
        update.message.reply_text.assert_awaited_once()
        self.assertIn('ДД.ММ.ГГГГ', update.message.reply_text.await_args.args[0])

    async def test_process_quiz_persists_user_and_clears_session(self):
        update = build_update('Нет')
        context = build_context({
            'state': 'QUIZ_FUNNY_GIFTS',
            'quiz_chat_id': 456,
            'user_id': 123,
            'tg_username': '@tester',
            'name': 'Tester',
            'birthday': '21.04.2000',
            'wishlist_url': 'https://example.com',
            'money_gifts': True,
        })

        with patch('handlers.quiz.add_user') as mock_add_user:
            await process_quiz(update, context)

        mock_add_user.assert_called_once()
        self.assertEqual(context.user_data, {})
        update.message.reply_text.assert_awaited_once()
        self.assertIn('информация сохранена', update.message.reply_text.await_args.args[0])


if __name__ == '__main__':
    unittest.main()
