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

from handlers.civil_war_seasons import SEASON_STATE, civil_war_season_stats, civil_war_seasons, process_season_response, \
    save_civil_war_season, start_civil_war_season


class TestCivilWarSeasons(unittest.IsolatedAsyncioTestCase):
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

    async def test_save_season_with_args(self):
        db.update_civil_war_stats(self.db_path, 1, True, '@winner')
        update = self.build_update('/save_civil_war_season First')
        context = SimpleNamespace(args=['First'], user_data={})

        with patch('handlers.civil_war_seasons.is_admin', return_value=True), \
                patch('handlers.civil_war_seasons.os.getenv', return_value=self.db_path):
            await save_civil_war_season(update, context)

        seasons = db.get_civil_war_seasons(self.db_path)
        self.assertEqual(seasons[0][1], 'First')
        update.effective_message.reply_text.assert_awaited_once()

    async def test_save_season_dialog(self):
        db.update_civil_war_stats(self.db_path, 1, True, '@winner')
        update = self.build_update('/save_civil_war_season')
        context = SimpleNamespace(args=[], user_data={})

        with patch('handlers.civil_war_seasons.is_admin', return_value=True):
            await save_civil_war_season(update, context)

        self.assertEqual(context.user_data[SEASON_STATE]['action'], 'save')

        response = self.build_update('Dialog Season')
        with patch('handlers.civil_war_seasons.is_admin', return_value=True), \
                patch('handlers.civil_war_seasons.os.getenv', return_value=self.db_path):
            handled = await process_season_response(response, context)

        self.assertTrue(handled)
        self.assertEqual(db.get_civil_war_seasons(self.db_path)[0][1], 'Dialog Season')
        self.assertNotIn(SEASON_STATE, context.user_data)

    async def test_list_and_show_season(self):
        db.update_civil_war_stats(self.db_path, 1, True, '@winner')
        leaderboard = db.get_civil_war_leaderboard(self.db_path)
        season_id = db.create_civil_war_season(self.db_path, 'First', leaderboard)

        list_update = self.build_update('/civil_war_seasons')
        stats_update = self.build_update('/civil_war_season_stats')

        with patch('handlers.civil_war_seasons.os.getenv', return_value=self.db_path):
            await civil_war_seasons(list_update, SimpleNamespace(args=[], user_data={}))
            await civil_war_season_stats(stats_update, SimpleNamespace(args=[str(season_id)], user_data={}))

        self.assertIn('First', list_update.effective_message.reply_text.await_args.args[0])
        self.assertIn('@winner', stats_update.effective_message.reply_text.await_args.args[0])

    async def test_start_season_saves_snapshot_and_resets_current_stats(self):
        db.update_civil_war_stats(self.db_path, 1, True, '@winner')
        update = self.build_update('/start_civil_war_season First')
        context = SimpleNamespace(args=['First'], user_data={})

        with patch('handlers.civil_war_seasons.is_admin', return_value=True), \
                patch('handlers.civil_war_seasons.os.getenv', return_value=self.db_path):
            await start_civil_war_season(update, context)

        seasons = db.get_civil_war_seasons(self.db_path)
        self.assertEqual(seasons[0][1], 'First')
        self.assertEqual(db.get_civil_war_leaderboard(self.db_path), [])
        self.assertIn('Новый сезон начат', update.effective_message.reply_text.await_args.args[0])

    async def test_start_season_dialog(self):
        db.update_civil_war_stats(self.db_path, 1, True, '@winner')
        update = self.build_update('/start_civil_war_season')
        context = SimpleNamespace(args=[], user_data={})

        with patch('handlers.civil_war_seasons.is_admin', return_value=True):
            await start_civil_war_season(update, context)

        self.assertEqual(context.user_data[SEASON_STATE]['action'], 'start')

        response = self.build_update('Dialog Season')
        with patch('handlers.civil_war_seasons.is_admin', return_value=True), \
                patch('handlers.civil_war_seasons.os.getenv', return_value=self.db_path):
            handled = await process_season_response(response, context)

        self.assertTrue(handled)
        self.assertEqual(db.get_civil_war_seasons(self.db_path)[0][1], 'Dialog Season')
        self.assertEqual(db.get_civil_war_leaderboard(self.db_path), [])


if __name__ == '__main__':
    unittest.main()
