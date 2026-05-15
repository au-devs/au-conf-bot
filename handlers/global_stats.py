import datetime
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_civil_war_leaderboard, get_command_last_used_at, upsert_command_last_used_at


logger = logging.getLogger(__name__)

STATS_COMMAND = "stats"
STATS_COOLDOWN = datetime.timedelta(hours=6)
STATS_CHAT_IDS_KEY = "stats_chat_ids"
PLACE_MARKERS = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
}


def register_stats_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int | None) -> None:
    if chat_id is None:
        return
    chat_ids = context.bot_data.setdefault(STATS_CHAT_IDS_KEY, set())
    chat_ids.add(chat_id)


def format_global_stats_message(db_path: str) -> str:
    leaderboard = get_civil_war_leaderboard(db_path, limit=10)
    if not leaderboard:
        return "📉 Статистики гражданской войны пока нет."

    total_attempts = sum(row[2] for row in leaderboard)
    total_successes = sum(row[3] for row in leaderboard)
    total_winrate = 0 if total_attempts == 0 else (total_successes / total_attempts) * 100
    lines = [
        "🏆 Топ-10 гражданской войны",
        f"📊 Общий винрейт топа: {total_winrate:.2f}% ({total_successes}/{total_attempts})",
        "",
    ]
    for place, (_, display_name, attempts, successes, winrate) in enumerate(leaderboard, start=1):
        failures = attempts - successes
        place_marker = PLACE_MARKERS.get(place, f"{place}.")
        lines.append(
            f"{place_marker} {display_name}: {winrate * 100:.2f}% | "
            f"🔥 {successes} / 🎲 {attempts} / 💀 {failures}"
        )
    return "\n".join(lines)


def get_remaining_cooldown_message(last_used_at: datetime.datetime, now: datetime.datetime) -> str:
    remaining = STATS_COOLDOWN - (now - last_used_at)
    remaining_seconds = max(int(remaining.total_seconds()), 0)
    minutes, seconds = divmod(remaining_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"/stats можно запускать не чаще раза в 6 часов. Осталось: {hours:02d}:{minutes:02d}:{seconds:02d}"


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None:
        return

    register_stats_chat(context, chat.id if chat is not None else None)
    db_path = os.getenv("DB_PATH")
    now = datetime.datetime.now()
    last_used_at = get_command_last_used_at(db_path, STATS_COMMAND)
    if last_used_at is not None and now - last_used_at < STATS_COOLDOWN:
        await message.reply_text(get_remaining_cooldown_message(last_used_at, now))
        return

    upsert_command_last_used_at(db_path, STATS_COMMAND, now)
    await message.reply_text(format_global_stats_message(db_path))


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
