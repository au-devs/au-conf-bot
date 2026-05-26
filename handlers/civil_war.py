import datetime
import html
import logging
import os
import random
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_civil_war_last_used_at, upsert_civil_war_last_used_at, update_civil_war_stats, \
    get_civil_war_stats, get_rat_points, has_verified_private_chat, set_rat_points
from handlers.assets import resolve_asset_path, send_asset
from handlers.civil_war_chances import get_global_mafia_event_chance, get_global_rare_chance, \
    get_global_rare_loss_chance, get_global_rat_event_chance, get_global_success_chance
from handlers.civil_war_season2 import get_rat_image_path, start_mafia_event, start_rat_event


logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_HOURS = 1
RARE_SUCCESS_POINTS = 10
RARE_LOSS_POINTS = -1
DEFAULT_RARE_CAPTION_TEMPLATE = "налудил себе +10 винов"
DEFAULT_RARE_FAIL_CAPTION_TEMPLATE = "словил редкое поражение: -1 вин"
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
    return resolve_asset_path(get_assets_dir(), "civilwar")


def get_fail_image_path() -> Path:
    return resolve_asset_path(get_assets_dir(), "fail")


def get_rare_image_path() -> Path:
    return resolve_asset_path(get_assets_dir(), "rare")


def get_rare_fail_image_path() -> Path:
    return resolve_asset_path(get_assets_dir(), "rare_fail")


def get_season2_unverified_message() -> str:
    return (
        "Сезонный ивент сгорел: ты не написал /start боту в личку "
        "или не заполнил профиль."
    )


def get_rare_caption_template() -> str:
    return os.getenv("RARE_CIVIL_WAR_CAPTION_TEMPLATE", DEFAULT_RARE_CAPTION_TEMPLATE)


def get_rare_fail_caption_template() -> str:
    return os.getenv("RARE_FAIL_CIVIL_WAR_CAPTION_TEMPLATE", DEFAULT_RARE_FAIL_CAPTION_TEMPLATE)


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
    cooldown_label = "один час" if cooldown_hours == 1 else f"{cooldown_hours:g} часов"
    return (
        f"Гражданскую войну можно запускать не чаще раза в {cooldown_label}. "
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


def _append_rat_bonus_caption(caption: str, parse_mode: str | None, rat_bonus: int) -> tuple[str, str | None]:
    bonus_text = f" и забрал крысиный банк +{rat_bonus} винов"
    if parse_mode == "HTML":
        bonus_text = html.escape(bonus_text)
    return f"{caption}{bonus_text}", parse_mode


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


def _get_rare_fail_caption(user) -> tuple[str, str | None]:
    mention, parse_mode = _get_user_caption_mention(user)
    template = get_rare_fail_caption_template()
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
    await send_asset(bot, image_path, caption=caption, parse_mode=parse_mode, **chat_kwargs)


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
    rare_loss_chance = get_global_rare_loss_chance(db_path)
    mafia_event_chance = get_global_mafia_event_chance(db_path)
    rat_event_chance = get_global_rat_event_chance(db_path)
    success_chance = get_global_success_chance(db_path)

    threshold = rare_success_chance
    is_rare_success = roll < threshold
    threshold += rare_loss_chance
    is_rare_loss = not is_rare_success and roll < threshold
    threshold += mafia_event_chance
    is_mafia_event = not is_rare_success and not is_rare_loss and roll < threshold
    threshold += rat_event_chance
    is_rat_event = not is_rare_success and not is_rare_loss and not is_mafia_event and roll < threshold
    threshold += success_chance
    is_success = not any([is_rare_success, is_rare_loss, is_mafia_event, is_rat_event]) and roll < threshold

    rat_bonus = 0
    if is_success:
        rat_points = get_rat_points(db_path)
        if rat_points > 1:
            rat_bonus = rat_points
            set_rat_points(db_path, 1)

    if is_rare_success:
        successes_delta = RARE_SUCCESS_POINTS
    elif is_rare_loss:
        successes_delta = RARE_LOSS_POINTS
    else:
        successes_delta = int(is_success) + rat_bonus
    update_civil_war_stats(db_path, user.id, successes_delta, _get_user_display_name(user))

    if is_mafia_event or is_rat_event:
        if has_verified_private_chat(db_path, user.id):
            if is_mafia_event:
                event_started = await start_mafia_event(update, context, db_path)
            else:
                event_started = await start_rat_event(update, context, db_path)
            if not event_started:
                await _send_text(context.bot, update, get_season2_unverified_message())
        else:
            await _send_text(context.bot, update, get_season2_unverified_message())
        selected_image = get_fail_image_path()
        caption, parse_mode = (None, None)
    elif is_rare_success:
        selected_image = get_rare_image_path()
        caption, parse_mode = _get_rare_success_caption(user)
    elif is_rare_loss:
        selected_image = get_rare_fail_image_path()
        caption, parse_mode = _get_rare_fail_caption(user)
    else:
        selected_image = get_rat_image_path() if rat_bonus > 0 else get_success_image_path() if is_success else get_fail_image_path()
        caption, parse_mode = _get_success_caption(user) if is_success else (None, None)
        if is_success and rat_bonus > 0 and caption is not None:
            caption, parse_mode = _append_rat_bonus_caption(caption, parse_mode, rat_bonus)
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
