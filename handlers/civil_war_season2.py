import os
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from db.database import add_mafia_daily_action, adjust_civil_war_successes, create_mafia_pending, create_rat_pending, \
    delete_mafia_pending, delete_rat_pending, find_verified_civil_war_user, get_civil_war_leaderboard, \
    get_mafia_pending_state, get_rat_pending_points, get_rat_points, set_mafia_pending_state, set_rat_points


DEFAULT_RAT_CAPTION_TEMPLATE = "забрал крысиный банк: +{points} винов"
DEFAULT_ASSETS_DIR = Path("/data/assets")


def get_rat_caption_template() -> str:
    return os.getenv("RAT_CIVIL_WAR_CAPTION_TEMPLATE", DEFAULT_RAT_CAPTION_TEMPLATE)


def get_rat_image_path() -> Path:
    return Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))) / "rat.jpg"


def format_private_leaderboard(db_path: str, actor_user_id: int) -> str:
    leaderboard = get_civil_war_leaderboard(db_path)
    lines = ["Кого минусуем? Отправь username или user_id из списка:"]
    for place, (user_id, display_name, attempts, successes, _, _) in enumerate(leaderboard, start=1):
        if user_id == actor_user_id:
            continue
        lines.append(f"{place}. {display_name} ({user_id}) | {successes}/{attempts}")
    return "\n".join(lines)


async def start_mafia_event(update: Update, context: ContextTypes.DEFAULT_TYPE, db_path: str) -> bool:
    user = update.effective_user
    if user is None:
        return False
    create_mafia_pending(db_path, user.id)
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
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
    create_rat_pending(db_path, user.id, points)
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
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

    rat_points = get_rat_pending_points(db_path, user.id)
    if rat_points is not None:
        if text == "1":
            adjust_civil_war_successes(db_path, user.id, rat_points)
            set_rat_points(db_path, 1)
            delete_rat_pending(db_path, user.id)
            image_path = get_rat_image_path()
            caption = get_rat_caption_template().format(points=rat_points)
            if image_path.exists():
                with image_path.open("rb") as image:
                    await context.bot.send_photo(chat_id=user.id, photo=image, caption=caption)
            else:
                await message.reply_text(f"{caption}\nФайл не найден: {image_path.name}")
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
        target = find_verified_civil_war_user(db_path, text)
        if target is None:
            await message.reply_text("Не нашел такого пользователя в верифицированном лидерборде. Отправь username или user_id из списка.")
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
