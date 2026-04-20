import datetime
import logging
import os
import random
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_civil_war_last_used_at, upsert_civil_war_last_used_at
from handlers.admin_checker import is_admin


logger = logging.getLogger(__name__)

COOLDOWN = datetime.timedelta(hours=1)
SUCCESS_CHANCE = 0.0666
COMMAND_TEXT = "гражданская война"
ADMIN_FORCE_COMMAND_TEXT = "/civil-war"
DEFAULT_ASSETS_DIR = Path("/data/assets")


def get_assets_dir() -> Path:
    return Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR)))


def get_success_image_path() -> Path:
    return get_assets_dir() / "civilwar.jpg"


def get_fail_image_path() -> Path:
    return get_assets_dir() / "fail.jpg"


def is_civil_war_trigger(text: str | None) -> bool:
    if text is None:
        return False
    normalized_text = " ".join(text.strip().lower().split())
    if normalized_text == COMMAND_TEXT:
        return True
    if normalized_text in {ADMIN_FORCE_COMMAND_TEXT, f"{ADMIN_FORCE_COMMAND_TEXT}@au_conf_bot"}:
        return True
    if normalized_text.startswith("/civil_war"):
        command_part = normalized_text.split()[0]
        return command_part in {"/civil_war", "/civil_war@au_conf_bot"}
    return False


def should_force_success(text: str | None, user_id: int) -> bool:
    if text is None or not is_admin(user_id):
        return False
    normalized_text = " ".join(text.strip().lower().split())
    return normalized_text in {ADMIN_FORCE_COMMAND_TEXT, f"{ADMIN_FORCE_COMMAND_TEXT}@au_conf_bot"}


def _get_remaining_cooldown_message(last_used_at: datetime.datetime, now: datetime.datetime) -> str:
    remaining = COOLDOWN - (now - last_used_at)
    remaining_seconds = max(int(remaining.total_seconds()), 0)
    minutes, seconds = divmod(remaining_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"Гражданскую войну можно запускать не чаще раза в час. Осталось: {hours:02d}:{minutes:02d}:{seconds:02d}"


async def _send_image(update: Update, image_path: Path) -> None:
    if update.effective_chat is None:
        return
    if not image_path.exists():
        logger.error(f"Image file does not exist: {image_path}")
        await update.effective_chat.send_message(f"Файл не найден: {image_path.name}")
        return

    with image_path.open("rb") as image:
        await update.effective_chat.send_photo(photo=image)


async def civil_war(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    now = datetime.datetime.now()
    db_path = os.getenv("DB_PATH")
    last_used_at = get_civil_war_last_used_at(db_path, user.id)
    if last_used_at is not None and now - last_used_at < COOLDOWN:
        await message.reply_text(_get_remaining_cooldown_message(last_used_at, now))
        return

    upsert_civil_war_last_used_at(db_path, user.id, now)
    force_success = should_force_success(message.text, user.id)
    selected_image = get_success_image_path() if force_success or random.random() < SUCCESS_CHANCE else get_fail_image_path()
    await _send_image(update, selected_image)
