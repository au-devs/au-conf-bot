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

from handlers.civil_war import _send_image, _send_text


def build_update(thread_id: int = 42):
    chat = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
    message = SimpleNamespace(message_thread_id=thread_id)
    return SimpleNamespace(effective_chat=chat, effective_message=message)


class TestCivilWarThreading(unittest.IsolatedAsyncioTestCase):
    async def test_send_text_keeps_current_topic(self):
        update = build_update()

        await _send_text(update, 'test')

        update.effective_chat.send_message.assert_awaited_once()
        self.assertEqual(update.effective_chat.send_message.await_args.kwargs['message_thread_id'], 42)

    async def test_send_image_keeps_current_topic(self):
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


if __name__ == '__main__':
    unittest.main()
