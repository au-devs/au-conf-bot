import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import db.database as db

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

from handlers.civil_war_admin_config import ADMIN_CONFIG_STATE, civil_war_config, process_admin_config_response, \
    set_rare_civil_war_chance


class TestCivilWarAdminConfig(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_path = 'users_test.sqlite'
        db.create_database(self.db_path)

    def tearDown(self):
        db.clear_database(self.db_path)

    def build_update(self, text: str):
        return SimpleNamespace(
            effective_chat=SimpleNamespace(type='private'),
            effective_user=SimpleNamespace(id=123),
            effective_message=SimpleNamespace(text=text, reply_text=AsyncMock()),
        )

    async def test_set_rare_chance_with_args(self):
        update = self.build_update('/set_rare_civil_war_chance 7%')
        context = SimpleNamespace(args=['7%'], user_data={})

        with patch('handlers.civil_war_admin_config.is_admin', return_value=True), \
                patch('handlers.civil_war_admin_config.os.getenv', return_value=self.db_path):
            await set_rare_civil_war_chance(update, context)

        self.assertEqual(db.get_civil_war_chance_override(self.db_path, 'global_rare'), 0.07)
        update.effective_message.reply_text.assert_awaited_once()

    async def test_dialog_sets_rare_chance(self):
        update = self.build_update('/set_rare_civil_war_chance')
        context = SimpleNamespace(args=[], user_data={})

        with patch('handlers.civil_war_admin_config.is_admin', return_value=True):
            await set_rare_civil_war_chance(update, context)

        self.assertEqual(context.user_data[ADMIN_CONFIG_STATE]['action'], 'set_global')

        response = self.build_update('8%')
        with patch('handlers.civil_war_admin_config.is_admin', return_value=True), \
                patch('handlers.civil_war_admin_config.os.getenv', return_value=self.db_path):
            handled = await process_admin_config_response(response, context)

        self.assertTrue(handled)
        self.assertEqual(db.get_civil_war_chance_override(self.db_path, 'global_rare'), 0.08)
        self.assertNotIn(ADMIN_CONFIG_STATE, context.user_data)

    async def test_config_outputs_global_chances(self):
        db.upsert_civil_war_chance_override(self.db_path, 'global_success', 0.1)
        db.upsert_civil_war_chance_override(self.db_path, 'global_rare', 0.02)
        update = self.build_update('/civil_war_config')
        context = SimpleNamespace(args=[], user_data={})

        with patch('handlers.civil_war_admin_config.is_admin', return_value=True), \
                patch('handlers.civil_war_admin_config.os.getenv', side_effect=lambda name, default=None: self.db_path if name == 'DB_PATH' else default):
            await civil_war_config(update, context)

        message = update.effective_message.reply_text.await_args.args[0]
        self.assertIn('Текущий общий шанс победы: 10.000%', message)
        self.assertIn('Текущий общий шанс rare: 2.000%', message)
        self.assertIn('global_success = 10.000%', message)
        self.assertIn('global_rare = 2.000%', message)


if __name__ == '__main__':
    unittest.main()
