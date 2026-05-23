import sys
import types
import unittest
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

from handlers.civil_war_season2 import find_mafia_target, format_private_leaderboard, process_season2_private_response


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
            effective_chat=SimpleNamespace(type='private'),
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
        context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock()))

        with patch('handlers.civil_war_season2.os.getenv', return_value=self.db_path):
            handled = await process_season2_private_response(update, context)

        self.assertTrue(handled)
        damaged, defended = db.process_mafia_daily_actions(self.db_path)
        self.assertEqual(damaged, [('@target_a', 1, 1, 0)])
        self.assertEqual(defended, [])


if __name__ == '__main__':
    unittest.main()
