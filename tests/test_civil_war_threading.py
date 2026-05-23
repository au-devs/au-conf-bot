import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
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

from handlers.civil_war import _get_rare_success_caption, _get_success_caption, _get_user_display_name, _send_image, \
    _send_text, civil_war, get_cooldown, is_civil_war_trigger


def build_update(thread_id: int = 42):
    chat = SimpleNamespace(id=456)
    message = SimpleNamespace(message_thread_id=thread_id)
    user = SimpleNamespace(id=123, username='ramil', full_name='Рамиль', name='Рамиль')
    return SimpleNamespace(effective_chat=chat, effective_message=message, effective_user=user)


def build_context():
    return SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock()))


class TestCivilWarThreading(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_path = 'users_test.sqlite'
        db.create_database(self.db_path)

    def tearDown(self):
        db.clear_database(self.db_path)

    def test_civil_war_cooldown_uses_env_or_default(self):
        old_value = os.environ.pop('CIVIL_WAR_COOLDOWN_HOURS', None)
        try:
            self.assertEqual(get_cooldown().total_seconds(), 3600)
            os.environ['CIVIL_WAR_COOLDOWN_HOURS'] = '2.5'
            self.assertEqual(get_cooldown().total_seconds(), 9000)
        finally:
            if old_value is None:
                os.environ.pop('CIVIL_WAR_COOLDOWN_HOURS', None)
            else:
                os.environ['CIVIL_WAR_COOLDOWN_HOURS'] = old_value

    def test_success_caption_uses_username_when_available(self):
        update = build_update()

        caption, parse_mode = _get_success_caption(update.effective_user)

        self.assertEqual(caption, '@ramil устроил гражданскую войну')
        self.assertIsNone(parse_mode)

    def test_user_display_name_prefers_username(self):
        update = build_update()

        display_name = _get_user_display_name(update.effective_user)

        self.assertEqual(display_name, '@ramil')

    def test_rare_success_caption_uses_env_template(self):
        update = build_update()

        with patch('handlers.civil_war.os.getenv', return_value='съел сладкий пирог, +10 винов'):
            caption, parse_mode = _get_rare_success_caption(update.effective_user)

        self.assertEqual(caption, '@ramil съел сладкий пирог, +10 винов')
        self.assertIsNone(parse_mode)

    async def test_civil_war_stores_user_display_name(self):
        update = build_update()
        update.effective_message.text = 'гражданская война'
        context = build_context()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            with patch('handlers.civil_war.os.getenv', side_effect=lambda name, default=None: 'users_test.sqlite' if name == 'DB_PATH' else default), \
                    patch('handlers.civil_war.get_civil_war_last_used_at', return_value=None), \
                    patch('handlers.civil_war.upsert_civil_war_last_used_at'), \
                    patch('handlers.civil_war.random.random', return_value=1), \
                    patch('handlers.civil_war.get_fail_image_path', return_value=temp_path), \
                    patch('handlers.civil_war.update_civil_war_stats') as update_stats:
                await civil_war(update, context)
        finally:
            os.unlink(temp_path)

        update_stats.assert_called_once_with('users_test.sqlite', 123, 0, '@ramil')

    async def test_civil_war_rare_success_adds_ten_wins_and_uses_rare_caption(self):
        update = build_update()
        update.effective_message.text = 'гражданская война'
        context = build_context()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            with patch('handlers.civil_war.os.getenv', side_effect=lambda name, default=None: 'users_test.sqlite' if name == 'DB_PATH' else default), \
                    patch('handlers.civil_war.get_civil_war_last_used_at', return_value=None), \
                    patch('handlers.civil_war.upsert_civil_war_last_used_at'), \
                    patch('handlers.civil_war.random.random', return_value=0.001), \
                    patch('handlers.civil_war.get_rare_image_path', return_value=temp_path), \
                    patch('handlers.civil_war.update_civil_war_stats') as update_stats:
                await civil_war(update, context)
        finally:
            os.unlink(temp_path)

        update_stats.assert_called_once_with('users_test.sqlite', 123, 10, '@ramil')
        self.assertEqual(
            context.bot.send_photo.await_args.kwargs['caption'],
            '@ramil налудил себе +10 винов',
        )

    async def test_civil_war_uses_global_rare_override(self):
        db.upsert_civil_war_chance_override(self.db_path, 'global_rare', 0.5)
        update = build_update()
        update.effective_message.text = 'гражданская война'
        context = build_context()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            with patch('handlers.civil_war.os.getenv', side_effect=lambda name, default=None: self.db_path if name == 'DB_PATH' else default), \
                    patch('handlers.civil_war.get_civil_war_last_used_at', return_value=None), \
                    patch('handlers.civil_war.upsert_civil_war_last_used_at'), \
                    patch('handlers.civil_war.random.random', return_value=0.2), \
                    patch('handlers.civil_war.get_rare_image_path', return_value=temp_path), \
                    patch('handlers.civil_war.update_civil_war_stats') as update_stats:
                await civil_war(update, context)
        finally:
            os.unlink(temp_path)

        update_stats.assert_called_once_with(self.db_path, 123, 10, '@ramil')

    def test_civil_war_dash_command_is_not_trigger(self):
        self.assertFalse(is_civil_war_trigger('/civil-war'))

    async def test_send_text_keeps_current_topic(self):
        update = build_update()
        context = build_context()

        await _send_text(context.bot, update, 'test')

        context.bot.send_message.assert_awaited_once()
        self.assertEqual(context.bot.send_message.await_args.kwargs['message_thread_id'], 42)
        self.assertEqual(context.bot.send_message.await_args.kwargs['chat_id'], 456)

    async def test_send_fail_image_keeps_current_topic(self):
        update = build_update()
        context = build_context()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            await _send_image(context.bot, update, temp_path)
        finally:
            os.unlink(temp_path)

        context.bot.send_photo.assert_awaited_once()
        self.assertEqual(context.bot.send_photo.await_args.kwargs['message_thread_id'], 42)
        self.assertEqual(context.bot.send_photo.await_args.kwargs['chat_id'], 456)

    async def test_send_success_image_goes_to_general(self):
        update = build_update()
        context = build_context()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            await _send_image(
                context.bot,
                update,
                temp_path,
                send_to_general=True,
                caption='@ramil устроил гражданскую войну',
            )
        finally:
            os.unlink(temp_path)

        context.bot.send_photo.assert_awaited_once()
        self.assertNotIn('message_thread_id', context.bot.send_photo.await_args.kwargs)
        self.assertEqual(
            context.bot.send_photo.await_args.kwargs['caption'],
            '@ramil устроил гражданскую войну',
        )
        self.assertEqual(context.bot.send_photo.await_args.kwargs['chat_id'], 456)


if __name__ == '__main__':
    unittest.main()
