import sys
import types
import unittest
from types import SimpleNamespace

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

from handlers.global_stats import format_global_stats_message, register_stats_chat


class TestGlobalStats(unittest.TestCase):
    def setUp(self):
        self.db_path = 'users_test.sqlite'
        db.create_database(self.db_path)

    def tearDown(self):
        db.clear_database(self.db_path)

    def test_register_stats_chat(self):
        context = SimpleNamespace(bot_data={})

        register_stats_chat(context, 123)
        register_stats_chat(context, 123)

        self.assertEqual(context.bot_data['stats_chat_ids'], {123})

    def test_format_global_stats_message(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        test_user2 = create_user({'user_id': 2, 'name': 'Test User2', 'tg_username': '@test_user2', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        db.add_user(self.db_path, test_user2)
        db.update_civil_war_stats(self.db_path, 1, True)
        db.update_civil_war_stats(self.db_path, 1, False)
        db.update_civil_war_stats(self.db_path, 2, False)

        message = format_global_stats_message(self.db_path)

        self.assertIn('🏆 Рейтинг гражданской войны', message)
        self.assertIn('🥇', message)
        self.assertIn('@test_user', message)
        self.assertIn('50.00%', message)
        self.assertIn('рейтинг', message)
        self.assertIn('@test_user2', message)
        self.assertIn('Бро, тебе надо тренироваться', message)

    def test_format_global_stats_message_includes_low_sample_users(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        outlier = create_user({'user_id': 2, 'name': 'Outlier', 'tg_username': '@outlier', 'birthday': '01.01.2000',
                               'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        db.add_user(self.db_path, outlier)
        for _ in range(200):
            db.update_civil_war_stats(self.db_path, 1, True)
        for _ in range(2):
            db.update_civil_war_stats(self.db_path, 2, True)

        message = format_global_stats_message(self.db_path)

        self.assertIn('@test_user', message)
        self.assertIn('@outlier', message)
        self.assertLess(message.index('@test_user'), message.index('@outlier'))


if __name__ == '__main__':
    unittest.main()
