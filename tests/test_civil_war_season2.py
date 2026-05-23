import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import db.database as db
from models.user_manager import create_user

telegram_module = types.ModuleType('telegram')
telegram_ext_module = types.ModuleType('telegram.ext')


class DummyUpdate:
    pass


class DummyContextTypes:
    DEFAULT_TYPE = object


telegram_module.Update = DummyUpdate
telegram_ext_module.ContextTypes = DummyContextTypes
sys.modules.setdefault('telegram', telegram_module)
sys.modules.setdefault('telegram.ext', telegram_ext_module)

from handlers.civil_war_season2 import find_mafia_target, format_private_leaderboard, process_season2_private_response, \
    send_private_choice, start_mafia_event, start_rat_event


class TestCivilWarSeason2(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_path = 'users_test.sqlite'
        db.create_database(self.db_path)
        self.add_user(1, '@actor')
        self.add_user(2, '@target_a')
        self.add_user(3, '@target_b')
        db.update_civil_war_stats(self.db_path, 1, True)
        db.update_civil_war_stats(self.db_path, 2, True)
        db.update_civil_war_stats(self.db_path, 3, False)

    def tearDown(self):
        db.clear_database(self.db_path)

    def add_user(self, user_id: int, username: str):
        db.add_user(self.db_path, create_user({
            'user_id': user_id,
            'name': username.lstrip('@'),
            'tg_username': username,
            'birthday': '01.01.2000',
            'wishlist_url': 'https://example.com',
            'money_gifts': True,
            'funny_gifts': True,
        }))

    def build_update(self, text: str):
        message = SimpleNamespace(text=text, reply_text=AsyncMock())
        return SimpleNamespace(
            effective_chat=SimpleNamespace(id=456, type='private'),
            effective_user=SimpleNamespace(id=1),
            effective_message=message,
        )

    def test_private_leaderboard_uses_compact_target_numbers(self):
        message = format_private_leaderboard(self.db_path, 1)

        self.assertIn('1. @target_a', message)
        self.assertIn('2. @target_b', message)
        self.assertNotIn('@actor', message)

    def test_find_mafia_target_by_visible_number(self):
        target = find_mafia_target(self.db_path, 1, '1')

        self.assertEqual(target, (2, '@target_a'))

    async def test_private_response_accepts_target_number(self):
        db.create_mafia_pending(self.db_path, 1)
        db.set_mafia_pending_state(self.db_path, 1, 'target')
        update = self.build_update('1')
        context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock(), send_animation=AsyncMock(), send_message=AsyncMock()))

        with patch('handlers.civil_war_season2.os.getenv', return_value=self.db_path):
            handled = await process_season2_private_response(update, context)

        self.assertTrue(handled)
        damaged, defended = db.process_mafia_daily_actions(self.db_path)
        self.assertEqual(damaged, [('@target_a', 1, 1, 0)])
        self.assertEqual(defended, [])

    async def test_send_private_choice_uses_photo_when_asset_exists(self):
        bot = SimpleNamespace(send_photo=AsyncMock(), send_message=AsyncMock(), send_animation=AsyncMock())
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            await send_private_choice(bot, 1, temp_path, 'choice text')
        finally:
            temp_path.unlink()

        bot.send_photo.assert_awaited_once()
        self.assertEqual(bot.send_photo.await_args.kwargs['caption'], 'choice text')
        bot.send_message.assert_not_awaited()

    async def test_start_mafia_event_sends_choice_photo(self):
        update = self.build_update('/start')
        context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock(), send_message=AsyncMock(), send_animation=AsyncMock()))

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            with patch('handlers.civil_war_season2.get_mafia_image_path', return_value=temp_path):
                started = await start_mafia_event(update, context, self.db_path)
        finally:
            temp_path.unlink()

        self.assertTrue(started)
        context.bot.send_photo.assert_awaited_once()
        self.assertIn('мафиозный выбор', context.bot.send_photo.await_args.kwargs['caption'])

    async def test_start_rat_event_stores_source_chat(self):
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=-100, type='supergroup'),
            effective_user=SimpleNamespace(id=1),
            effective_message=SimpleNamespace(message_thread_id=77),
        )
        context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock(), send_message=AsyncMock(), send_animation=AsyncMock()))

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            with patch('handlers.civil_war_season2.get_rat_choice_image_path', return_value=temp_path):
                started = await start_rat_event(update, context, self.db_path)
        finally:
            temp_path.unlink()

        self.assertTrue(started)
        self.assertEqual(db.get_rat_pending(self.db_path, 1), (1, -100, 77))

    async def test_rat_take_sends_rat_asset_to_source_chat(self):
        db.create_rat_pending(self.db_path, 1, 4, source_chat_id=-100, source_message_thread_id=77)
        update = self.build_update('1')
        context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock(), send_message=AsyncMock(), send_animation=AsyncMock()))

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            with patch('handlers.civil_war_season2.os.getenv', side_effect=lambda name, default=None: self.db_path if name == 'DB_PATH' else default), \
                    patch('handlers.civil_war_season2.get_rat_image_path', return_value=temp_path):
                handled = await process_season2_private_response(update, context)
        finally:
            temp_path.unlink()

        self.assertTrue(handled)
        context.bot.send_photo.assert_awaited_once()
        self.assertEqual(context.bot.send_photo.await_args.kwargs['chat_id'], -100)
        self.assertEqual(context.bot.send_photo.await_args.kwargs['message_thread_id'], 77)
        self.assertIn('+4', context.bot.send_photo.await_args.kwargs['caption'])


if __name__ == '__main__':
    unittest.main()
