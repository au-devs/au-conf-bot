import os
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from db.database import add_mafia_daily_action, adjust_civil_war_successes, create_mafia_pending, create_rat_pending, \
    delete_mafia_pending, delete_rat_pending, find_verified_civil_war_user, get_civil_war_leaderboard, \
    get_mafia_pending_state, get_rat_pending, get_rat_points, set_mafia_pending_state, set_rat_points
from handlers.assets import resolve_asset_path, send_asset


DEFAULT_RAT_CAPTION_TEMPLATE = "забрал крысиный банк: +{points} винов"
DEFAULT_ASSETS_DIR = Path("/data/assets")


def get_rat_caption_template() -> str:
    return os.getenv("RAT_CIVIL_WAR_CAPTION_TEMPLATE", DEFAULT_RAT_CAPTION_TEMPLATE)


def get_rat_image_path() -> Path:
    return resolve_asset_path(Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))), "rat")


def get_mafia_image_path() -> Path:
    return resolve_asset_path(Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))), "mafia")


def get_rat_choice_image_path() -> Path:
    return resolve_asset_path(Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))), "rat_choice")


async def send_private_choice(bot, user_id: int, image_path: Path, text: str) -> None:
    await send_asset(bot, image_path, fallback_name=image_path.name, chat_id=user_id, caption=text)


def get_source_chat_kwargs(update: Update) -> tuple[int | None, int | None]:
    chat = update.effective_chat
    message = update.effective_message
    if chat is None:
        return None, None
    return chat.id, getattr(message, "message_thread_id", None)


def format_private_leaderboard(db_path: str, actor_user_id: int) -> str:
    leaderboard = get_civil_war_leaderboard(db_path)
    lines = ["Кого минусуем? Отправь номер из списка:"]
    targets = [row for row in leaderboard if row[0] != actor_user_id]
    for place, (user_id, display_name, attempts, successes, _, _) in enumerate(targets, start=1):
        lines.append(f"{place}. {display_name} ({user_id}) | {successes}/{attempts}")
    return "\n".join(lines)


def find_mafia_target(db_path: str, actor_user_id: int, text: str) -> tuple[int, str] | None:
    normalized = text.strip()
    if normalized.isdigit():
        target_index = int(normalized) - 1
        leaderboard = get_civil_war_leaderboard(db_path)
        targets = [row for row in leaderboard if row[0] != actor_user_id]
        if 0 <= target_index < len(targets):
            user_id, display_name, *_ = targets[target_index]
            return user_id, display_name
    return find_verified_civil_war_user(db_path, normalized)


async def start_mafia_event(update: Update, context: ContextTypes.DEFAULT_TYPE, db_path: str) -> bool:
    user = update.effective_user
    if user is None:
        return False
    create_mafia_pending(db_path, user.id)
    try:
        await send_private_choice(
            context.bot,
            user.id,
            get_mafia_image_path(),
            (
                "Тебе выпал мафиозный выбор. Ответь цифрой:\n"
                "1. -1 вин другому\n"
                "2. Защита от одного -1"
            ),
        )
        return True
    except Exception:
        delete_mafia_pending(db_path, user.id)
        return False


async def start_rat_event(update: Update, context: ContextTypes.DEFAULT_TYPE, db_path: str) -> bool:
    user = update.effective_user
    if user is None:
        return False
    points = get_rat_points(db_path)
    source_chat_id, source_message_thread_id = get_source_chat_kwargs(update)
    create_rat_pending(
        db_path,
        user.id,
        points,
        source_chat_id=source_chat_id,
        source_message_thread_id=source_message_thread_id,
    )
    try:
        await send_private_choice(
            context.bot,
            user.id,
            get_rat_choice_image_path(),
            (
                f"Тебе выпала крыса. В банке {points} винов. Ответь цифрой:\n"
                f"1. Забрать +{points} сейчас\n"
                f"2. Передать дальше, банк станет {points + 2}"
            ),
        )
        return True
    except Exception:
        delete_rat_pending(db_path, user.id)
        return False


async def process_season2_private_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if chat is None or user is None or message is None or getattr(chat, "type", None) != "private":
        return False

    text = (message.text or "").strip()
    db_path = os.getenv("DB_PATH")

    rat_pending = get_rat_pending(db_path, user.id)
    if rat_pending is not None:
        rat_points, source_chat_id, source_message_thread_id = rat_pending
        if text == "1":
            adjust_civil_war_successes(db_path, user.id, rat_points)
            set_rat_points(db_path, 1)
            delete_rat_pending(db_path, user.id)
            image_path = get_rat_image_path()
            caption = get_rat_caption_template().format(points=rat_points)
            if source_chat_id is None:
                await send_asset(context.bot, image_path, fallback_name=image_path.name, chat_id=user.id, caption=caption)
            else:
                chat_kwargs = {"chat_id": source_chat_id}
                if source_message_thread_id is not None:
                    chat_kwargs["message_thread_id"] = source_message_thread_id
                await send_asset(context.bot, image_path, fallback_name=image_path.name, caption=caption, **chat_kwargs)
            return True
        if text == "2":
            set_rat_points(db_path, rat_points + 2)
            delete_rat_pending(db_path, user.id)
            await message.reply_text(f"Передал дальше. Новый крысиный банк: {rat_points + 2}")
            return True
        await message.reply_text("Ответь 1 или 2.")
        return True

    mafia_state = get_mafia_pending_state(db_path, user.id)
    if mafia_state is None:
        return False

    if mafia_state == "choice":
        if text == "1":
            set_mafia_pending_state(db_path, user.id, "target")
            await message.reply_text(format_private_leaderboard(db_path, user.id))
            return True
        if text == "2":
            add_mafia_daily_action(db_path, user.id, "protect")
            delete_mafia_pending(db_path, user.id)
            await message.reply_text("Защита принята. До статы это останется в тайне.")
            return True
        await message.reply_text("Ответь 1 или 2.")
        return True

    if mafia_state == "target":
        target = find_mafia_target(db_path, user.id, text)
        if target is None:
            await message.reply_text("Не нашел такого пользователя. Отправь номер из списка.")
            return True
        target_user_id, target_display_name = target
        if target_user_id == user.id:
            await message.reply_text("Себя минусовать нельзя. Выбери другого.")
            return True
        add_mafia_daily_action(db_path, user.id, "attack", target_user_id)
        delete_mafia_pending(db_path, user.id)
        await message.reply_text(f"Принято: {target_display_name} получит -1 вин на дневной стате, если не защитится.")
        return True

    return False
