import datetime
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import db.database as db
from models.user_manager import create_user

telegram_module = types.ModuleType('telegram')
telegram_ext_module = types.ModuleType('telegram.ext')
telegram_error_module = types.ModuleType('telegram.error')


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
sys.modules.setdefault('telegram', telegram_module)
sys.modules.setdefault('telegram.error', telegram_error_module)
sys.modules.setdefault('telegram.ext', telegram_ext_module)

from handlers.birthday_reminders import process_birthday_reminders


def build_update():
    from_user = SimpleNamespace(id=123, name='Tester')
    chat = SimpleNamespace(id=456, type='supergroup', send_message=AsyncMock())
    message = SimpleNamespace(reply_text=AsyncMock(), from_user=from_user, chat=chat, message_thread_id=42)
    return SimpleNamespace(message=message, effective_message=message, effective_user=from_user, effective_chat=chat)


def build_context():
    return SimpleNamespace(user_data={}, chat_data={})


class TestBirthdayReminders(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_path = 'users_test.sqlite'
        db.create_database(self.db_path)
        self.old_db_path = None

    def tearDown(self):
        db.clear_database(self.db_path)

    def _patch_today(self, fake_today: datetime.date):
        class FakeDate(datetime.date):
            @classmethod
            def today(cls):
                return fake_today

        return patch('handlers.birthday_reminders.datetime.date', FakeDate)

    async def test_process_resets_advance_flags_outside_window(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        db.update_reminder(self.db_path, 1, '@test_user', 'reminder_14_days')

        fake_today = datetime.date(2026, 1, 20)
        update = build_update()
        context = build_context()

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(fake_today):
            await process_birthday_reminders(update, context)

        self.assertFalse(db.get_reminder_status(self.db_path, 1, '@test_user', 'reminder_14_days'))

    async def test_process_does_not_reset_advance_flags_inside_window_across_new_year(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '14.01.2000',
                                 'wishlist_url': 'https://example.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        db.update_reminder(self.db_path, 1, '@test_user', 'reminder_14_days')

        fake_today = datetime.date(2026, 1, 1)
        update = build_update()
        context = build_context()

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(fake_today):
            await process_birthday_reminders(update, context)

        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'reminder_14_days'))

    async def test_process_keeps_birthday_today_flag_on_birthday(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '21.04.2000',
                                 'wishlist_url': 'https://example.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)

        fake_today = datetime.date(2026, 4, 21)
        update = build_update()
        context = build_context()

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(fake_today):
            await process_birthday_reminders(update, context)

        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))
        update.effective_chat.send_message.assert_awaited_once()
        self.assertNotIn('message_thread_id', update.effective_chat.send_message.await_args.kwargs)


if __name__ == '__main__':
    unittest.main()
