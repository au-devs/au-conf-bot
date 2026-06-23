import math
import os
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from db.database import add_mafia_daily_action, add_rat_investor, adjust_civil_war_successes, clear_rat_investors, \
    consume_rat_pending, create_mafia_pending, create_rat_pending, create_rat_steal_report, delete_mafia_pending, delete_rat_pending, \
    find_verified_civil_war_user, get_civil_war_leaderboard, get_mafia_pending_state, get_rat_hustled_points, \
    get_rat_pending, get_rat_state, keep_latest_season2_pending, reset_rat_hustled_points, \
    set_mafia_pending_state, set_rat_points
from handlers.assets import resolve_asset_path, send_asset


DEFAULT_RAT_CAPTION_TEMPLATE = "забрал крысиный банк: +{points} винов"
DEFAULT_RAT_INVESTOR_CAPTION_TEMPLATE = "{username} инвестировал в крысиный банк. Деньги должны работать, аутяги должны инвестировать. Банк: +{points} винов"
DEFAULT_RAT_DIVIDEND_CAPTION_TEMPLATE = "Деньги должны работать, аутяги должны получать дивиденды: {investors} получили по +{dividend} винов"
DEFAULT_RAT_STEAL_STATS_CAPTION_TEMPLATE = "{taker} скрысил банк на +{points} винов. Аутяги нахастлили {hustled}, но крыса все испортила"
DEFAULT_RAT_BANK_PASS_INCREMENT = 2
DEFAULT_RAT_INVESTOR_DIVIDEND_RATE = 0.25
DEFAULT_RAT_INVESTOR_DIVIDEND_MIN = 1
DEFAULT_RAT_INVESTOR_DIVIDEND_MAX = 3
DEFAULT_ASSETS_DIR = Path("/data/assets")


def get_rat_caption_template() -> str:
    return os.getenv("RAT_CIVIL_WAR_CAPTION_TEMPLATE", DEFAULT_RAT_CAPTION_TEMPLATE)


def get_rat_investor_caption_template() -> str:
    return os.getenv("RAT_INVESTOR_CAPTION_TEMPLATE", DEFAULT_RAT_INVESTOR_CAPTION_TEMPLATE)


def get_rat_dividend_caption_template() -> str:
    return os.getenv("RAT_DIVIDEND_CAPTION_TEMPLATE", DEFAULT_RAT_DIVIDEND_CAPTION_TEMPLATE)


def get_rat_steal_stats_caption_template() -> str:
    return os.getenv("RAT_STEAL_STATS_CAPTION_TEMPLATE", DEFAULT_RAT_STEAL_STATS_CAPTION_TEMPLATE)


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_rat_bank_pass_increment() -> int:
    return max(get_env_int("RAT_BANK_PASS_INCREMENT", DEFAULT_RAT_BANK_PASS_INCREMENT), 1)


def calculate_rat_dividend(points: int) -> int:
    rate = max(get_env_float("RAT_INVESTOR_DIVIDEND_RATE", DEFAULT_RAT_INVESTOR_DIVIDEND_RATE), 0)
    min_dividend = max(get_env_int("RAT_INVESTOR_DIVIDEND_MIN", DEFAULT_RAT_INVESTOR_DIVIDEND_MIN), 0)
    max_dividend = max(get_env_int("RAT_INVESTOR_DIVIDEND_MAX", DEFAULT_RAT_INVESTOR_DIVIDEND_MAX), min_dividend)
    return min(max(math.ceil(points * rate), min_dividend), max_dividend)


def format_rat_invest_reward_text(points: int) -> str:
    future_points = points + get_rat_bank_pass_increment()
    dividend = calculate_rat_dividend(future_points)
    return f"инвесторы будут получать по +{dividend} винов на каждой стате, пока банк работает"


def get_user_display_name(user) -> str:
    username = getattr(user, "username", None)
    if username:
        return f"@{username}"
    return getattr(user, "full_name", None) or getattr(user, "name", None) or "пользователь"


def get_rat_image_path() -> Path:
    return resolve_asset_path(Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))), "rat")


def get_mafia_image_path() -> Path:
    return resolve_asset_path(Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))), "mafia")


def get_rat_choice_image_path() -> Path:
    return resolve_asset_path(Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))), "rat_choice")


def get_rat_investor_image_path() -> Path:
    return resolve_asset_path(Path(os.getenv("ASSETS_DIR", str(DEFAULT_ASSETS_DIR))), "rat_investor")


async def send_private_choice(bot, user_id: int, image_path: Path, text: str) -> None:
    await send_asset(bot, image_path, fallback_name=image_path.name, chat_id=user_id, caption=text)


async def send_to_source_chat(bot, image_path: Path, source_chat_id: int | None, caption: str, fallback_user_id: int) -> None:
    if source_chat_id is None:
        await send_asset(bot, image_path, fallback_name=image_path.name, chat_id=fallback_user_id, caption=caption)
        return
    await send_asset(bot, image_path, fallback_name=image_path.name, chat_id=source_chat_id, caption=caption)


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
    delete_rat_pending(db_path, user.id)
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
    delete_mafia_pending(db_path, user.id)
    points, bank_generation = get_rat_state(db_path)
    source_chat_id, source_message_thread_id = get_source_chat_kwargs(update)
    create_rat_pending(
        db_path,
        user.id,
        points,
        bank_generation=bank_generation,
        source_chat_id=source_chat_id,
        source_message_thread_id=source_message_thread_id,
    )
    try:
        next_points = points + get_rat_bank_pass_increment()
        await send_private_choice(
            context.bot,
            user.id,
            get_rat_choice_image_path(),
            (
                f"Тебе выпала крыса. В банке {points} винов. Ответь цифрой:\n"
                f"1. Забрать +{points} сейчас\n"
                f"2. Инвестировать, банк станет {next_points}; {format_rat_invest_reward_text(points)}"
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
    keep_latest_season2_pending(db_path, user.id)

    rat_pending = get_rat_pending(db_path, user.id)
    if rat_pending is not None:
        if text == "1":
            consumed_pending = consume_rat_pending(db_path, user.id)
            if consumed_pending is None:
                await message.reply_text("Это предложение уже устарело: крысиный банк изменился.")
                return True
            rat_points, source_chat_id, source_message_thread_id = consumed_pending
            display_name = get_user_display_name(user)
            adjust_civil_war_successes(db_path, user.id, rat_points)
            create_rat_steal_report(db_path, user.id, display_name, rat_points, get_rat_hustled_points(db_path))
            set_rat_points(db_path, 1)
            reset_rat_hustled_points(db_path)
            clear_rat_investors(db_path)
            image_path = get_rat_image_path()
            caption = f"{display_name} {get_rat_caption_template().format(points=rat_points)}"
            await send_to_source_chat(context.bot, image_path, source_chat_id, caption, user.id)
            return True
        if text == "2":
            consumed_pending = consume_rat_pending(db_path, user.id)
            if consumed_pending is None:
                await message.reply_text("Это предложение уже устарело: крысиный банк изменился.")
                return True
            rat_points, source_chat_id, source_message_thread_id = consumed_pending
            new_points = rat_points + get_rat_bank_pass_increment()
            set_rat_points(db_path, new_points)
            display_name = get_user_display_name(user)
            add_rat_investor(db_path, user.id, display_name)
            caption = get_rat_investor_caption_template().format(username=display_name, points=new_points)
            await send_to_source_chat(context.bot, get_rat_investor_image_path(), source_chat_id, caption, user.id)
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
