from telegram import Update
from telegram.ext import ContextTypes

from handlers.admin_checker import is_admin
from handlers.assets import send_asset
from handlers.civil_war import get_fail_image_path, get_rare_fail_image_path, get_rare_image_path, get_success_image_path
from handlers.civil_war_season2 import get_mafia_image_path, get_rat_choice_image_path, get_rat_image_path


def _is_admin_update(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    try:
        return is_admin(user.id)
    except Exception:
        return False


def _get_chat_kwargs(update: Update) -> dict:
    chat = update.effective_chat
    message = update.effective_message
    if chat is None:
        return {}
    chat_kwargs = {"chat_id": chat.id}
    message_thread_id = getattr(message, "message_thread_id", None)
    if message_thread_id is not None:
        chat_kwargs["message_thread_id"] = message_thread_id
    return chat_kwargs


async def _send_admin_asset(update: Update, context: ContextTypes.DEFAULT_TYPE, asset_path, caption: str) -> None:
    message = update.effective_message
    if not _is_admin_update(update):
        if message is not None:
            await message.reply_text("Команда доступна только админу.")
        return

    await send_asset(
        context.bot,
        asset_path,
        fallback_name=asset_path.name,
        caption=caption,
        **_get_chat_kwargs(update),
    )


async def test_civil_war_win(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_admin_asset(update, context, get_success_image_path(), "Тест: обычная победа")


async def test_civil_war_fail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_admin_asset(update, context, get_fail_image_path(), "Тест: обычное поражение")


async def test_civil_war_rare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_admin_asset(update, context, get_rare_image_path(), "Тест: редкая победа")


async def test_civil_war_rare_fail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_admin_asset(update, context, get_rare_fail_image_path(), "Тест: редкое поражение")


async def test_civil_war_mafia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_admin_asset(update, context, get_mafia_image_path(), "Тест: мафиозный выбор")


async def test_civil_war_rat_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_admin_asset(update, context, get_rat_choice_image_path(), "Тест: крысиный выбор")


async def test_civil_war_rat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_admin_asset(update, context, get_rat_image_path(), "Тест: крысиный банк")
