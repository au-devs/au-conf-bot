import datetime
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_civil_war_leaderboard, get_civil_war_lowest_winrate, get_command_last_used_at, \
    upsert_command_last_used_at
from handlers.admin_checker import is_admin


logger = logging.getLogger(__name__)

STATS_COMMAND = "stats"
DEFAULT_STATS_COOLDOWN_HOURS = 3
STATS_CHAT_IDS_KEY = "stats_chat_ids"
BAYES_PRIOR_ATTEMPTS = 100
BAYES_PRIOR_SUCCESS_RATE = 0.0666
PLACE_MARKERS = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
}


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid {name}={value!r}, using default {default}")
        return default


def get_stats_cooldown() -> datetime.timedelta:
    return datetime.timedelta(hours=get_env_float("STATS_COOLDOWN_HOURS", DEFAULT_STATS_COOLDOWN_HOURS))


def register_stats_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int | None) -> None:
    if chat_id is None:
        return
    chat_ids = context.bot_data.setdefault(STATS_CHAT_IDS_KEY, set())
    chat_ids.add(chat_id)


def format_global_stats_message(db_path: str) -> str:
    leaderboard = get_civil_war_leaderboard(
        db_path,
        prior_attempts=BAYES_PRIOR_ATTEMPTS,
        prior_success_rate=BAYES_PRIOR_SUCCESS_RATE,
    )
    if not leaderboard:
        return "📉 Статистики гражданской войны пока нет."

    total_attempts = sum(row[2] for row in leaderboard)
    total_successes = sum(row[3] for row in leaderboard)
    total_winrate = 0 if total_attempts == 0 else (total_successes / total_attempts) * 100
    lines = [
        "🏆 Рейтинг гражданской войны",
        f"📊 Общий винрейт: {total_winrate:.2f}% ({total_successes}/{total_attempts})",
        "",
    ]
    for place, (_, display_name, attempts, successes, winrate, adjusted_winrate) in enumerate(leaderboard, start=1):
        failures = attempts - successes
        place_marker = PLACE_MARKERS.get(place, f"{place}.")
        lines.append(
            f"{place_marker} {display_name}: {winrate * 100:.2f}% "
            f"(рейтинг {adjusted_winrate * 100:.2f}%) | "
            f"🔥 {successes} / 🎲 {attempts} / 💀 {failures}"
        )
    lowest_winrate = get_civil_war_lowest_winrate(
        db_path,
        prior_attempts=BAYES_PRIOR_ATTEMPTS,
        prior_success_rate=BAYES_PRIOR_SUCCESS_RATE,
    )
    if lowest_winrate is not None:
        _, display_name, attempts, successes, winrate, adjusted_winrate = lowest_winrate
        lines.extend([
            "",
            f"🫡 {display_name}: худший рейтинг {adjusted_winrate * 100:.2f}% "
            f"при винрейте {winrate * 100:.2f}% ({successes}/{attempts}). "
            "Бро, тебе надо тренироваться",
        ])
    return "\n".join(lines)


def get_remaining_cooldown_message(last_used_at: datetime.datetime, now: datetime.datetime) -> str:
    cooldown = get_stats_cooldown()
    remaining = cooldown - (now - last_used_at)
    remaining_seconds = max(int(remaining.total_seconds()), 0)
    minutes, seconds = divmod(remaining_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    cooldown_hours = get_env_float("STATS_COOLDOWN_HOURS", DEFAULT_STATS_COOLDOWN_HOURS)
    return f"/stats можно запускать не чаще раза в {cooldown_hours:g} часов. Осталось: {hours:02d}:{minutes:02d}:{seconds:02d}"


def is_bot_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    try:
        return is_admin(user_id)
    except Exception as e:
        logger.warning(f"Failed to check bot admin status for user_id={user_id}: {e}")
        return False


async def can_bypass_stats_cooldown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    return is_bot_admin(getattr(user, "id", None))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None:
        return

    register_stats_chat(context, chat.id if chat is not None else None)
    db_path = os.getenv("DB_PATH")
    now = datetime.datetime.now()
    last_used_at = get_command_last_used_at(db_path, STATS_COMMAND)
    bypass_cooldown = await can_bypass_stats_cooldown(update, context)
    stats_cooldown = get_stats_cooldown()
    if not bypass_cooldown and last_used_at is not None and now - last_used_at < stats_cooldown:
        await message.reply_text(get_remaining_cooldown_message(last_used_at, now))
        return

    if not bypass_cooldown:
        upsert_command_last_used_at(db_path, STATS_COMMAND, now)
    await message.reply_text(format_global_stats_message(db_path))


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None:
        return
    if not is_bot_admin(getattr(user, "id", None)):
        logger.info(f"Non-admin user_id={getattr(user, 'id', None)} tried to run /admin_stats")
        return

    register_stats_chat(context, chat.id if chat is not None else None)
    await message.reply_text(format_global_stats_message(os.getenv("DB_PATH")))


async def send_daily_stats(context: ContextTypes.DEFAULT_TYPE) -> None:
    db_path = os.getenv("DB_PATH")
    message = format_global_stats_message(db_path)
    chat_ids = sorted(context.bot_data.get(STATS_CHAT_IDS_KEY, set()))
    if not chat_ids:
        logger.info("No chats registered for daily stats")
        return

    for chat_id in chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.warning(f"Failed to send daily stats to chat_id={chat_id}: {e}")
