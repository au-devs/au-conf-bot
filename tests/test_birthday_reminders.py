import datetime
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import db.database as db
from models.user_manager import create_user

# ---------------------------------------------------------------------------
# Telegram stub (must be the first module that touches sys.modules so that
# later test modules importing us as the first file don't get a stripped stub)
# ---------------------------------------------------------------------------
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

from handlers.birthday_reminders import (  # noqa: E402
    BIRTHDAY_CHAT_IDS_KEY,
    get_last_birthday_run,
    mark_birthday_run,
    register_birthday_chat,
    send_daily_birthday_reminders,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_test_user(db_path, birthday):
    user = create_user({
        'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user',
        'birthday': birthday, 'wishlist_url': 'https://example.com',
        'money_gifts': True, 'funny_gifts': True,
    })
    db.add_user(db_path, user)


def build_context(chat_ids=(-456,)):
    return SimpleNamespace(
        bot_data={BIRTHDAY_CHAT_IDS_KEY: set(chat_ids)},
        bot=SimpleNamespace(send_message=AsyncMock()),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBirthdayReminders(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_path = 'users_test.sqlite'
        db.create_database(self.db_path)

    def tearDown(self):
        db.clear_database(self.db_path)

    def _patch_today(self, fake_today: datetime.date):
        class FakeDate(datetime.date):
            @classmethod
            def today(cls):
                return fake_today
        return patch('handlers.birthday_reminders.datetime.date', FakeDate)

    # ------------------------------------------------------------------
    # Existing happy-path tests (updated for BIRTHDAY_CHAT_IDS_KEY)
    # ------------------------------------------------------------------

    async def test_does_nothing_without_registered_chats(self):
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=())

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        context.bot.send_message.assert_not_called()
        self.assertFalse(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))

    async def test_resets_advance_flags_outside_window(self):
        add_test_user(self.db_path, '01.01.2000')
        db.update_reminder(self.db_path, 1, '@test_user', 'reminder_14_days')
        context = build_context()

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 1, 20)):
            await send_daily_birthday_reminders(context)

        self.assertFalse(db.get_reminder_status(self.db_path, 1, '@test_user', 'reminder_14_days'))

    async def test_does_not_reset_advance_flags_inside_window_across_new_year(self):
        add_test_user(self.db_path, '14.01.2000')
        db.update_reminder(self.db_path, 1, '@test_user', 'reminder_14_days')
        context = build_context()

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 1, 1)):
            await send_daily_birthday_reminders(context)

        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'reminder_14_days'))

    async def test_sends_advance_reminder_with_expected_payload(self):
        add_test_user(self.db_path, '05.05.2000')
        context = build_context(chat_ids=(-456,))

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'reminder_14_days'))
        context.bot.send_message.assert_awaited_once()
        kwargs = context.bot.send_message.await_args.kwargs
        self.assertEqual(kwargs['chat_id'], -456)
        self.assertIn('Скоро день рождения', kwargs['text'])
        self.assertEqual(kwargs['parse_mode'], 'MarkdownV2')

    async def test_sends_birthday_greeting_and_sets_flag(self):
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-456,))

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))
        context.bot.send_message.assert_awaited_once()
        kwargs = context.bot.send_message.await_args.kwargs
        self.assertEqual(kwargs['chat_id'], -456)
        self.assertIn('С ДНЕМ РОЖДЕНИЯ', kwargs['text'])
        self.assertEqual(kwargs['parse_mode'], 'MarkdownV2')

    async def test_broadcasts_to_every_registered_chat_exactly_once(self):
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-100, -200, -300))

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        self.assertEqual(context.bot.send_message.await_count, 3)
        sent_chat_ids = {call.kwargs['chat_id'] for call in context.bot.send_message.await_args_list}
        self.assertEqual(sent_chat_ids, {-100, -200, -300})
        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))

    async def test_does_not_resend_already_delivered_reminder(self):
        add_test_user(self.db_path, '21.04.2000')
        db.update_reminder(self.db_path, 1, '@test_user', 'birthday_today')
        context = build_context()

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        context.bot.send_message.assert_not_called()

    async def test_ignores_chat_ids_above_zero(self):
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(123,))

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        context.bot.send_message.assert_not_called()

    # ------------------------------------------------------------------
    # Fix 1: _broadcast() return value gates reminder flag
    # ------------------------------------------------------------------

    async def test_full_broadcast_failure_does_not_set_flag(self):
        """If every send raises, the per-user reminder flag must NOT be set."""
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-456,))
        context.bot.send_message = AsyncMock(side_effect=Exception("Telegram unavailable"))

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        context.bot.send_message.assert_awaited_once()
        self.assertFalse(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))

    async def test_partial_broadcast_failure_does_not_set_flag(self):
        """If even one chat fails, the flag must NOT be set (at-least-once semantics)."""
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-100, -200))

        async def selective_fail(**kwargs):
            if kwargs.get('chat_id') == -200:
                raise Exception("Chat unavailable")

        context.bot.send_message = AsyncMock(side_effect=selective_fail)

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        self.assertEqual(context.bot.send_message.await_count, 2)  # both attempted
        self.assertFalse(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))

    async def test_full_broadcast_success_sets_flag(self):
        """All sends succeed → flag IS set."""
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-100, -200))

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(datetime.date(2026, 4, 21)):
            await send_daily_birthday_reminders(context)

        self.assertEqual(context.bot.send_message.await_count, 2)
        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))

    # ------------------------------------------------------------------
    # Fix 2: durable daily-run guard + catch-up
    # ------------------------------------------------------------------

    def test_mark_and_get_last_birthday_run_roundtrip(self):
        """mark_birthday_run / get_last_birthday_run roundtrip through SQLite."""
        self.assertIsNone(get_last_birthday_run(self.db_path))
        target = datetime.date(2026, 4, 21)
        mark_birthday_run(self.db_path, target)
        self.assertEqual(get_last_birthday_run(self.db_path), target)

    async def test_duplicate_run_guard_skips_second_call_same_day(self):
        """A second call on the same calendar day must be a no-op."""
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-456,))
        fake_today = datetime.date(2026, 4, 21)

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(fake_today):
            await send_daily_birthday_reminders(context)
            first_count = context.bot.send_message.await_count
            self.assertGreater(first_count, 0)  # first run actually sent

            await send_daily_birthday_reminders(context)  # same patched day

        # Second call must have added zero new sends
        self.assertEqual(context.bot.send_message.await_count, first_count)

    async def test_catchup_runs_when_last_run_was_yesterday(self):
        """If last_run < today the guard lets the job through (catch-up scenario)."""
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-456,))
        fake_today = datetime.date(2026, 4, 21)

        # Simulate last run was the day before
        mark_birthday_run(self.db_path, datetime.date(2026, 4, 20))

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(fake_today):
            await send_daily_birthday_reminders(context)

        context.bot.send_message.assert_awaited_once()
        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))

    async def test_no_catchup_needed_when_already_ran_today(self):
        """If last_run == today, the job is skipped entirely."""
        add_test_user(self.db_path, '21.04.2000')
        context = build_context(chat_ids=(-456,))
        fake_today = datetime.date(2026, 4, 21)

        mark_birthday_run(self.db_path, fake_today)

        with patch('handlers.birthday_reminders.os.getenv', return_value=self.db_path), \
                self._patch_today(fake_today):
            await send_daily_birthday_reminders(context)

        context.bot.send_message.assert_not_called()

    # ------------------------------------------------------------------
    # Fix 3: register_birthday_chat
    # ------------------------------------------------------------------

    def test_register_birthday_chat_adds_group_and_supergroup(self):
        context = SimpleNamespace(bot_data={})
        register_birthday_chat(context, -456, "supergroup")
        register_birthday_chat(context, -789, "group")
        register_birthday_chat(context, 123, "private")   # must not be added
        register_birthday_chat(context, None, "group")    # must not be added
        self.assertEqual(context.bot_data.get(BIRTHDAY_CHAT_IDS_KEY), {-456, -789})

    def test_register_birthday_chat_is_idempotent(self):
        context = SimpleNamespace(bot_data={})
        register_birthday_chat(context, -456, "group")
        register_birthday_chat(context, -456, "group")
        self.assertEqual(len(context.bot_data[BIRTHDAY_CHAT_IDS_KEY]), 1)


if __name__ == '__main__':
    unittest.main()
