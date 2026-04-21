import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

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

from handlers.civil_war import _get_success_caption, _send_image, _send_text


def build_update(thread_id: int = 42):
    chat = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
    message = SimpleNamespace(message_thread_id=thread_id)
    user = SimpleNamespace(id=123, username='ramil', full_name='Рамиль', name='Рамиль')
    return SimpleNamespace(effective_chat=chat, effective_message=message, effective_user=user)


class TestCivilWarThreading(unittest.IsolatedAsyncioTestCase):
    def test_success_caption_uses_username_when_available(self):
        update = build_update()

        caption, parse_mode = _get_success_caption(update.effective_user)

        self.assertEqual(caption, '@ramil устроил гражданскую войну')
        self.assertIsNone(parse_mode)

    async def test_send_text_keeps_current_topic(self):
        update = build_update()

        await _send_text(update, 'test')

        update.effective_chat.send_message.assert_awaited_once()
        self.assertEqual(update.effective_chat.send_message.await_args.kwargs['message_thread_id'], 42)

    async def test_send_fail_image_keeps_current_topic(self):
        update = build_update()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            await _send_image(update, temp_path)
        finally:
            os.unlink(temp_path)

        update.effective_chat.send_photo.assert_awaited_once()
        self.assertEqual(update.effective_chat.send_photo.await_args.kwargs['message_thread_id'], 42)

    async def test_send_success_image_goes_to_general(self):
        update = build_update()

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            await _send_image(
                update,
                temp_path,
                send_to_general=True,
                caption='@ramil устроил гражданскую войну',
            )
        finally:
            os.unlink(temp_path)

        update.effective_chat.send_photo.assert_awaited_once()
        self.assertNotIn('message_thread_id', update.effective_chat.send_photo.await_args.kwargs)
        self.assertEqual(
            update.effective_chat.send_photo.await_args.kwargs['caption'],
            '@ramil устроил гражданскую войну',
        )


if __name__ == '__main__':
    unittest.main()
