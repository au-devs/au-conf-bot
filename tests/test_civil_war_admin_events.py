import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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

from handlers.civil_war_admin_events import test_civil_war_rat


class TestCivilWarAdminEvents(unittest.IsolatedAsyncioTestCase):
    def build_update(self):
        return SimpleNamespace(
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(id=-100),
            effective_message=SimpleNamespace(message_thread_id=77, reply_text=AsyncMock()),
        )

    async def test_admin_event_sends_asset_to_current_chat_thread(self):
        update = self.build_update()
        context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock(), send_animation=AsyncMock(), send_message=AsyncMock()))

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test')
            temp_path = Path(temp_file.name)

        try:
            with patch('handlers.civil_war_admin_events.is_admin', return_value=True), \
                    patch('handlers.civil_war_admin_events.get_rat_image_path', return_value=temp_path):
                await test_civil_war_rat(update, context)
        finally:
            temp_path.unlink()

        context.bot.send_photo.assert_awaited_once()
        self.assertEqual(context.bot.send_photo.await_args.kwargs['chat_id'], -100)
        self.assertEqual(context.bot.send_photo.await_args.kwargs['message_thread_id'], 77)
        self.assertEqual(context.bot.send_photo.await_args.kwargs['caption'], 'Тест: крысиный банк')

    async def test_non_admin_event_is_rejected(self):
        update = self.build_update()
        context = SimpleNamespace(bot=SimpleNamespace(send_photo=AsyncMock(), send_animation=AsyncMock(), send_message=AsyncMock()))

        with patch('handlers.civil_war_admin_events.is_admin', return_value=False):
            await test_civil_war_rat(update, context)

        update.effective_message.reply_text.assert_awaited_once_with("Команда доступна только админу.")
        context.bot.send_photo.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
