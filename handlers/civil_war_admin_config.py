import os

from telegram import Update
from telegram.ext import ContextTypes

from db.database import delete_civil_war_chance_overrides, get_civil_war_chance_overrides, upsert_civil_war_chance_override
from handlers.admin_checker import is_admin
from handlers.civil_war_chances import GLOBAL_MAFIA_EVENT_KEY, GLOBAL_RARE_KEY, GLOBAL_RARE_LOSS_KEY, \
    GLOBAL_RAT_EVENT_KEY, GLOBAL_SUCCESS_KEY, format_chance, get_global_mafia_event_chance, get_global_rare_chance, \
    get_global_rare_loss_chance, get_global_rat_event_chance, get_global_success_chance, parse_chance


ADMIN_CONFIG_STATE = "CIVIL_WAR_ADMIN_CONFIG"
HELP_TEXT = """Скрытые админские команды гражданки:
/civil_war_config - меню настройки шансов гражданки
/save_civil_war_season <name> - сохранить текущий лидерборд как сезон
/start_civil_war_season <name> - сохранить текущий сезон и начать новый
/civil_war_seasons - список сезонов
/civil_war_season_stats <season_id|name> - статистика сезона

chance можно писать как 0.0666, 6.66 или 6.66%."""

CHANCE_CONFIGS = [
    ("1", GLOBAL_SUCCESS_KEY, "обычная победа", get_global_success_chance),
    ("2", GLOBAL_RARE_KEY, "редкая победа", get_global_rare_chance),
    ("3", GLOBAL_RARE_LOSS_KEY, "редкое поражение", get_global_rare_loss_chance),
    ("4", GLOBAL_MAFIA_EVENT_KEY, "мафиозный ивент", get_global_mafia_event_chance),
    ("5", GLOBAL_RAT_EVENT_KEY, "крысиный ивент", get_global_rat_event_chance),
]


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


def _format_overrides(overrides: dict[str, float]) -> str:
    if not overrides:
        return "Runtime override: нет"
    lines = ["Runtime override:"]
    for key, chance in overrides.items():
        lines.append(f"{key} = {format_chance(chance)}")
    return "\n".join(lines)


def _format_config_menu(db_path: str) -> str:
    lines = ["Выбери шанс для изменения:"]
    for number, _, label, getter in CHANCE_CONFIGS:
        lines.append(f"{number}. {label}: {format_chance(getter(db_path))}")
    lines.extend([
        "6. Сбросить runtime override до env/default",
        "",
        _format_overrides(get_civil_war_chance_overrides(db_path)),
    ])
    return "\n".join(lines)


async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _reply_private_admin_only(update):
        return
    await update.effective_message.reply_text(HELP_TEXT)


async def civil_war_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _reply_private_admin_only(update):
        return
    db_path = os.getenv("DB_PATH")
    context.user_data[ADMIN_CONFIG_STATE] = {"action": "select_key"}
    await update.effective_message.reply_text(_format_config_menu(db_path))


async def _set_global_chance(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, label: str) -> None:
    if not await _reply_private_admin_only(update):
        return
    if not context.args:
        context.user_data[ADMIN_CONFIG_STATE] = {"action": "set_global", "key": key, "label": label}
        await update.effective_message.reply_text(f"Введи {label}, например 6.66% или 0.0666.")
        return

    try:
        chance = parse_chance(context.args[0])
    except ValueError as e:
        await update.effective_message.reply_text(f"Не смог разобрать шанс: {e}")
        return
    upsert_civil_war_chance_override(os.getenv("DB_PATH"), key, chance)
    await update.effective_message.reply_text(f"{label} установлен: {format_chance(chance)}")


async def set_civil_war_chance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_global_chance(update, context, GLOBAL_SUCCESS_KEY, "общий шанс победы")


async def set_rare_civil_war_chance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_global_chance(update, context, GLOBAL_RARE_KEY, "общий шанс rare")


async def reset_civil_war_chances(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _reply_private_admin_only(update):
        return
    delete_civil_war_chance_overrides(os.getenv("DB_PATH"))
    context.user_data.pop(ADMIN_CONFIG_STATE, None)
    await update.effective_message.reply_text("Runtime override сброшены. Теперь используются env/default.")


async def process_admin_config_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    state = context.user_data.get(ADMIN_CONFIG_STATE)
    if not state:
        return False
    if not await _reply_private_admin_only(update):
        return True

    message = update.effective_message
    text = (message.text or "").strip()
    db_path = os.getenv("DB_PATH")
    try:
        if state["action"] == "select_key":
            if text == "6" or text.lower() == "reset":
                delete_civil_war_chance_overrides(db_path)
                await message.reply_text("Runtime override сброшены. Теперь используются env/default.")
                context.user_data.pop(ADMIN_CONFIG_STATE, None)
                return True
            selected = next((item for item in CHANCE_CONFIGS if item[0] == text or item[1] == text), None)
            if selected is None:
                await message.reply_text("Выбери номер 1-6.")
                return True
            _, key, label, _ = selected
            context.user_data[ADMIN_CONFIG_STATE] = {"action": "set_global", "key": key, "label": label}
            await message.reply_text(f"Введи шанс для '{label}', например 6.66% или 0.0666.")
            return True
        if state["action"] == "set_global":
            chance = parse_chance(text)
            upsert_civil_war_chance_override(db_path, state["key"], chance)
            await message.reply_text(f"{state['label']} установлен: {format_chance(chance)}")
        else:
            await message.reply_text("Неизвестное состояние настройки.")
    except ValueError as e:
        await message.reply_text(f"Не смог разобрать ввод: {e}")
        return True

    context.user_data.pop(ADMIN_CONFIG_STATE, None)
    return True
