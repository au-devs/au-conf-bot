import os

from telegram import Update
from telegram.ext import ContextTypes

from db.database import clear_civil_war_stats, create_civil_war_season, get_civil_war_leaderboard, \
    get_civil_war_season_entries, get_civil_war_seasons
from handlers.admin_checker import is_admin
from handlers.global_stats import BAYES_PRIOR_ATTEMPTS, BAYES_PRIOR_SUCCESS_RATE, PLACE_MARKERS


SEASON_STATE = "CIVIL_WAR_SEASON"


def _is_private_admin(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None or getattr(chat, "type", None) != "private":
        return False
    try:
        return is_admin(user.id)
    except Exception:
        return False


async def _reply_private_admin_only(update: Update) -> bool:
    if _is_private_admin(update):
        return True
    message = update.effective_message
    if message is not None and getattr(update.effective_chat, "type", None) == "private":
        await message.reply_text("Команда доступна только админу.")
    return False


def _format_season_entries(name: str, entries: list[tuple[int, int, str, int, int, float, float]]) -> str:
    if not entries:
        return f"📉 В сезоне {name} нет статистики."

    total_attempts = sum(row[3] for row in entries)
    total_successes = sum(row[4] for row in entries)
    total_winrate = 0 if total_attempts == 0 else (total_successes / total_attempts) * 100
    lines = [
        f"🏆 Сезон: {name}",
        f"📊 Общий винрейт сезона: {total_winrate:.2f}% ({total_successes}/{total_attempts})",
        "",
    ]
    for place, _, display_name, attempts, successes, winrate, adjusted_winrate in entries:
        failures = max(attempts - successes, 0)
        place_marker = PLACE_MARKERS.get(place, f"{place}.")
        lines.append(
            f"{place_marker} {display_name}: {winrate * 100:.2f}% "
            f"(рейтинг {adjusted_winrate * 100:.2f}%) | "
            f"🔥 {successes} / 🎲 {attempts} / 💀 {failures}"
        )
    return "\n".join(lines)


async def save_civil_war_season(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _reply_private_admin_only(update):
        return
    if not context.args:
        context.user_data[SEASON_STATE] = {"action": "save"}
        await update.effective_message.reply_text("Введи название сезона.")
        return

    await _save_season(update, " ".join(context.args))


async def _save_season(update: Update, name: str, reset_stats: bool = False) -> None:
    db_path = os.getenv("DB_PATH")
    leaderboard = get_civil_war_leaderboard(
        db_path,
        prior_attempts=BAYES_PRIOR_ATTEMPTS,
        prior_success_rate=BAYES_PRIOR_SUCCESS_RATE,
    )
    if not leaderboard:
        await update.effective_message.reply_text("Статистики гражданской войны пока нет, сезон не создан.")
        return

    season_id = create_civil_war_season(db_path, name, leaderboard)
    if season_id is None:
        await update.effective_message.reply_text("Не удалось сохранить сезон.")
        return
    if reset_stats:
        clear_civil_war_stats(db_path)
        await update.effective_message.reply_text(f"Сезон сохранен: #{season_id} {name}. Новый сезон начат, текущая статистика сброшена.")
        return
    await update.effective_message.reply_text(f"Сезон сохранен: #{season_id} {name}")


async def start_civil_war_season(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _reply_private_admin_only(update):
        return
    if not context.args:
        context.user_data[SEASON_STATE] = {"action": "start"}
        await update.effective_message.reply_text("Введи название завершаемого сезона.")
        return

    await _save_season(update, " ".join(context.args), reset_stats=True)


async def civil_war_seasons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    seasons = get_civil_war_seasons(os.getenv("DB_PATH"))
    if not seasons:
        await update.effective_message.reply_text("Сезонов пока нет.")
        return
    lines = ["Сезоны гражданской войны:"]
    for season_id, name, created_at in seasons:
        lines.append(f"{season_id}. {name} ({created_at.strftime('%Y-%m-%d %H:%M')})")
    await update.effective_message.reply_text("\n".join(lines))


async def civil_war_season_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Формат: /civil_war_season_stats <season_id|name>")
        return

    season_ref = " ".join(context.args)
    season = get_civil_war_season_entries(os.getenv("DB_PATH"), season_ref)
    if season is None:
        await update.effective_message.reply_text(f"Сезон не найден: {season_ref}")
        return

    season_id, name, _, entries = season
    await update.effective_message.reply_text(_format_season_entries(f"#{season_id} {name}", entries))


async def process_season_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    state = context.user_data.get(SEASON_STATE)
    if not state:
        return False
    if not await _reply_private_admin_only(update):
        return True

    name = (update.effective_message.text or "").strip()
    if not name:
        await update.effective_message.reply_text("Название сезона не должно быть пустым.")
        return True
    await _save_season(update, name, reset_stats=state.get("action") == "start")
    context.user_data.pop(SEASON_STATE, None)
    return True
