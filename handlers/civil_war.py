import datetime
import html
import logging
import os
import random
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_civil_war_last_used_at, upsert_civil_war_last_used_at, update_civil_war_stats, \
    get_civil_war_stats
from handlers.civil_war_chances import get_global_rare_chance, get_global_success_chance


logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_HOURS = 1
RARE_SUCCESS_POINTS = 10
DEFAULT_RARE_CAPTION_TEMPLATE = "налудил себе +10 винов"
COMMAND_TEXT = "гражданская война"
STATS_COMMAND_TEXT = "/how-much-civil-war"
DEFAULT_ASSETS_DIR = Path("/data/assets")


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid {name}={value!r}, using default {default}")
        return default


def get_cooldown() -> datetime.timedelta:
    return datetime.timedelta(hours=get_env_float("CIVIL_WAR_COOLDOWN_HOURS", DEFAULT_COOLDOWN_HOURS))


def get_assets_dir() -> Path:
    return Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR)))


def get_success_image_path() -> Path:
    return get_assets_dir() / "civilwar.jpg"


def get_fail_image_path() -> Path:
    return get_assets_dir() / "fail.jpg"


def get_rare_image_path() -> Path:
    return get_assets_dir() / "rare.jpg"


def get_rare_caption_template() -> str:
    return os.getenv("RARE_CIVIL_WAR_CAPTION_TEMPLATE", DEFAULT_RARE_CAPTION_TEMPLATE)


def is_civil_war_trigger(text: str | None) -> bool:
    if text is None:
        return False
    normalized_text = " ".join(text.strip().lower().split())
    if normalized_text == COMMAND_TEXT:
        return True
    if normalized_text.startswith("/civil_war"):
        command_part = normalized_text.split()[0]
        return command_part in {"/civil_war", "/civil_war@au_conf_bot"}
    return False


def is_civil_war_stats_trigger(text: str | None) -> bool:
    if text is None:
        return False
    normalized_text = " ".join(text.strip().lower().split())
    if normalized_text in {STATS_COMMAND_TEXT, f"{STATS_COMMAND_TEXT}@au_conf_bot"}:
        return True
    if normalized_text.startswith("/how_much_civil_war"):
        command_part = normalized_text.split()[0]
        return command_part in {"/how_much_civil_war", "/how_much_civil_war@au_conf_bot"}
    return False


def _get_remaining_cooldown_message(last_used_at: datetime.datetime, now: datetime.datetime) -> str:
    cooldown = get_cooldown()
    remaining = cooldown - (now - last_used_at)
    remaining_seconds = max(int(remaining.total_seconds()), 0)
    minutes, seconds = divmod(remaining_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    cooldown_hours = get_env_float("CIVIL_WAR_COOLDOWN_HOURS", DEFAULT_COOLDOWN_HOURS)
    return (
        f"Гражданскую войну можно запускать не чаще раза в {cooldown_hours:g} часов. "
        f"Осталось: {hours:02d}:{minutes:02d}:{seconds:02d}"
    )


def _get_thread_kwargs(update: Update) -> dict:
    message = update.effective_message
    message_thread_id = getattr(message, "message_thread_id", None)
    if message_thread_id is None:
        return {}
    return {"message_thread_id": message_thread_id}


def _get_success_caption(user) -> tuple[str, str | None]:
    username = getattr(user, "username", None)
    if username:
        return f"@{username} устроил гражданскую войну", None

    display_name = getattr(user, "full_name", None) or getattr(user, "name", None) or "пользователь"
    user_id = getattr(user, "id", None)
    if user_id is None:
        return f"@{display_name} устроил гражданскую войну", None

    escaped_name = html.escape(display_name)
    return f'<a href="tg://user?id={user_id}">@{escaped_name}</a> устроил гражданскую войну', "HTML"


def _get_user_caption_mention(user) -> tuple[str, str | None]:
    username = getattr(user, "username", None)
    if username:
        return f"@{username}", None

    display_name = getattr(user, "full_name", None) or getattr(user, "name", None) or "пользователь"
    user_id = getattr(user, "id", None)
    if user_id is None:
        return f"@{display_name}", None

    escaped_name = html.escape(display_name)
    return f'<a href="tg://user?id={user_id}">@{escaped_name}</a>', "HTML"


def _get_rare_success_caption(user) -> tuple[str, str | None]:
    mention, parse_mode = _get_user_caption_mention(user)
    template = get_rare_caption_template()
    if parse_mode == "HTML":
        template = html.escape(template)
    return f"{mention} {template}", parse_mode


def _get_user_display_name(user) -> str | None:
    username = getattr(user, "username", None)
    if username:
        return f"@{username}"
    return getattr(user, "full_name", None) or getattr(user, "name", None)


def _get_chat_kwargs(update: Update, send_to_general: bool = False) -> dict:
    chat = update.effective_chat
    if chat is None:
        return {}
    chat_kwargs = {"chat_id": chat.id}
    if not send_to_general:
        chat_kwargs.update(_get_thread_kwargs(update))
    return chat_kwargs


async def _send_text(bot, update: Update, text: str) -> None:
    chat_kwargs = _get_chat_kwargs(update)
    if not chat_kwargs:
        return
    await bot.send_message(text=text, **chat_kwargs)


async def _send_image(
    bot,
    update: Update,
    image_path: Path,
    send_to_general: bool = False,
    caption: str | None = None,
    parse_mode: str | None = None,
) -> None:
    chat_kwargs = _get_chat_kwargs(update, send_to_general=send_to_general)
    if not chat_kwargs:
        return
    if not image_path.exists():
        logger.error(f"Image file does not exist: {image_path}")
        await bot.send_message(text=f"Файл не найден: {image_path.name}", **chat_kwargs)
        return

    photo_kwargs = dict(chat_kwargs)
    if caption is not None:
        photo_kwargs["caption"] = caption
    if parse_mode is not None:
        photo_kwargs["parse_mode"] = parse_mode

    with image_path.open("rb") as image:
        await bot.send_photo(photo=image, **photo_kwargs)


async def civil_war(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    now = datetime.datetime.now()
    db_path = os.getenv("DB_PATH")
    last_used_at = get_civil_war_last_used_at(db_path, user.id)
    cooldown = get_cooldown()
    if last_used_at is not None and now - last_used_at < cooldown:
        await _send_text(context.bot, update, _get_remaining_cooldown_message(last_used_at, now))
        return

    upsert_civil_war_last_used_at(db_path, user.id, now)
    roll = random.random()
    rare_success_chance = get_global_rare_chance(db_path)
    success_chance = get_global_success_chance(db_path)
    is_rare_success = roll < rare_success_chance
    is_success = is_rare_success or roll < success_chance
    successes_delta = RARE_SUCCESS_POINTS if is_rare_success else int(is_success)
    update_civil_war_stats(db_path, user.id, successes_delta, _get_user_display_name(user))
    if is_rare_success:
        selected_image = get_rare_image_path()
        caption, parse_mode = _get_rare_success_caption(user)
    else:
        selected_image = get_success_image_path() if is_success else get_fail_image_path()
        caption, parse_mode = _get_success_caption(user) if is_success else (None, None)
    await _send_image(
        context.bot,
        update,
        selected_image,
        send_to_general=is_success,
        caption=caption,
        parse_mode=parse_mode,
    )


async def civil_war_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    db_path = os.getenv("DB_PATH")
    attempts, successes = get_civil_war_stats(db_path, user.id)
    failures = max(attempts - successes, 0)
    winrate = 0 if attempts == 0 else (successes / attempts) * 100

    await _send_text(
        context.bot,
        update,
        f"Пытался устроить войну = {attempts}\n"
        f"Спровоцировал гражданскую войну = {successes}\n"
        f"Мастурбировал = {failures}\n"
        f"Винрейт = {winrate:.2f}%"
    )
