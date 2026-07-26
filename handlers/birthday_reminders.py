import datetime
import logging
import os

from telegram.ext import ContextTypes

from db.database import (
    get_command_last_used_at,
    get_db_users,
    get_reminder_status,
    reset_user_reminders,
    update_reminder,
    upsert_command_last_used_at,
)
from models.user_manager import get_closest_birthday
from util.util import markdown_escape


logger = logging.getLogger(__name__)

ADVANCE_REMINDER_TYPES = ['reminder_14_days', 'reminder_7_days', 'reminder_1_days']

# Separate from stats_chat_ids: populated on both regular messages AND command
# updates (via a group=0 passthrough handler in main.py), so command-only group
# chats are not missed.
BIRTHDAY_CHAT_IDS_KEY = "birthday_chat_ids"

_BIRTHDAY_JOB_DB_KEY = "birthday_daily_job"


def register_birthday_chat(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int | None,
    chat_type: str | None,
) -> None:
    """Register a group/supergroup chat for birthday reminder broadcasts."""
    if chat_id is None or chat_type not in ("group", "supergroup"):
        return
    chat_ids: set = context.bot_data.setdefault(BIRTHDAY_CHAT_IDS_KEY, set())
    chat_ids.add(chat_id)


def get_last_birthday_run(db_path: str) -> datetime.date | None:
    """Return the calendar date on which the birthday job last ran, or None."""
    dt = get_command_last_used_at(db_path, _BIRTHDAY_JOB_DB_KEY)
    return dt.date() if dt is not None else None


def mark_birthday_run(db_path: str, run_date: datetime.date | None = None) -> None:
    """Persist *run_date* (defaults to today) as the last birthday-job run date."""
    date_to_store = run_date if run_date is not None else datetime.date.today()
    # Store as midnight datetime so the ISO round-trip via command_cooldowns works
    dt = datetime.datetime.combine(date_to_store, datetime.time.min)
    upsert_command_last_used_at(db_path, _BIRTHDAY_JOB_DB_KEY, dt)


async def _broadcast(bot, chat_ids: list[int], text: str) -> bool:
    """Send *text* to every chat in *chat_ids*.

    Returns True only when every send succeeded; False if ANY delivery failed.
    Errors are logged but never re-raised so a single bad chat never blocks others.
    """
    all_ok = True
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')
        except Exception as e:
            logger.warning(f"Failed to send birthday reminder to chat_id={chat_id}: {e}")
            all_ok = False
    return all_ok


async def send_daily_birthday_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily job_queue task: send birthday reminders to every registered group chat.

    Durability contract
    -------------------
    - The run date is marked in SQLite at the START of execution to prevent
      double-runs on the same calendar day (e.g. catch-up one-shot + scheduled
      job, or two same-day restarts). The early-exit guard uses that persisted
      date so a second call on the same day is a no-op.
    - Per-user reminder flags are only set AFTER a fully-successful broadcast.
      If delivery fails for even one registered chat, the flag is left unset so
      the user will be retried on the next scheduled run.

    Known limitation: if the job marks today and then crashes mid-execution,
    the remaining users are not retried on the same calendar day (the date is
    already marked, so the catch-up on restart is also skipped). A complete fix
    requires per-chat delivery tracking; this implementation covers the primary
    failure mode — the bot being completely down at 06:01 UTC.
    """
    db_path = os.getenv('DB_PATH')
    today = datetime.date.today()

    # Prevent double-runs on the same calendar day
    if get_last_birthday_run(db_path) == today:
        logger.info("Birthday reminders already processed today, skipping duplicate run.")
        return

    # Mark immediately so a crash+restart on the same day doesn't re-run the whole check
    mark_birthday_run(db_path, today)

    chat_ids = sorted(
        chat_id
        for chat_id in context.bot_data.get(BIRTHDAY_CHAT_IDS_KEY, set())
        if chat_id < 0
    )
    if not chat_ids:
        logger.info("No chats registered for birthday reminders")
        return

    users = get_db_users(db_path)
    for user in users:
        if user.birthday is None:
            continue
        birthday_date = get_closest_birthday(user)
        days_until_birthday = (birthday_date - today).days
        if days_until_birthday > 14:
            reset_user_reminders(db_path, user.user_id, ADVANCE_REMINDER_TYPES)
        if days_until_birthday != 0:
            reset_user_reminders(db_path, user.user_id, ['birthday_today'])

        if days_until_birthday in (14, 7, 1):
            reminder_type = f"reminder_{days_until_birthday}_days"
            if get_reminder_status(db_path, user.user_id, user.tg_username, reminder_type):
                continue
            delivered = await _broadcast(
                context.bot,
                chat_ids,
                f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО НЕ УЧЕБНАЯ ТРЕВОГА ❗❗❗\n"
                f"Скоро день рождения у {markdown_escape(user.tg_username)}\n"
                f"*Дата:* {markdown_escape(user.birthday)}\n"
                f"*Желаемые подарки:* {markdown_escape(user.wishlist_url)}\n",
            )
            if delivered:
                update_reminder(db_path, user.user_id, user.tg_username, reminder_type)
        elif days_until_birthday == 0:
            if get_reminder_status(db_path, user.user_id, user.tg_username, 'birthday_today'):
                continue
            delivered = await _broadcast(
                context.bot,
                chat_ids,
                f"❗❗❗ ВСЕМ ВНИМАНИЕ ЭТО АВТОМАТИЧЕСКОЕ ПОЗДРАВЛЕНИЕ ❗❗❗\n"
                f"🎉 🎉 🎉  С ДНЕМ РОЖДЕНИЯ {markdown_escape(user.tg_username)}  🎉 🎉 🎉\n",
            )
            if delivered:
                update_reminder(db_path, user.user_id, user.tg_username, 'birthday_today')
