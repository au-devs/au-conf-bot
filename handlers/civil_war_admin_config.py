import os

from telegram import Update
from telegram.ext import ContextTypes

from db.database import delete_civil_war_chance_overrides, get_civil_war_chance_overrides, upsert_civil_war_chance_override
from handlers.admin_checker import is_admin
from handlers.civil_war_chances import GLOBAL_RARE_KEY, GLOBAL_SUCCESS_KEY, format_chance, get_global_rare_chance, \
    get_global_success_chance, parse_chance


ADMIN_CONFIG_STATE = "CIVIL_WAR_ADMIN_CONFIG"
HELP_TEXT = """Скрытые админские команды гражданки:
/civil_war_config - показать текущие override
/set_civil_war_chance <chance> - общий шанс победы
/set_rare_civil_war_chance <chance> - общий шанс rare
/reset_civil_war_chances - сбросить runtime override до env/default

chance можно писать как 0.0666, 6.66 или 6.66%."""


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


async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _reply_private_admin_only(update):
        return
    await update.effective_message.reply_text(HELP_TEXT)


async def civil_war_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _reply_private_admin_only(update):
        return
    db_path = os.getenv("DB_PATH")
    overrides = get_civil_war_chance_overrides(db_path)
    await update.effective_message.reply_text(
        f"Текущий общий шанс победы: {format_chance(get_global_success_chance(db_path))}\n"
        f"Текущий общий шанс rare: {format_chance(get_global_rare_chance(db_path))}\n\n"
        f"{_format_overrides(overrides)}"
    )


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
