# get_users.py
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes
from db.database import get_user
from models.user import User
from util.util import markdown_escape
from handlers.admin_checker import is_admin

logger = logging.getLogger(__name__)


async def user_info(update: Update, context: ContextTypes):
    db_path = os.getenv('DB_PATH')
    tg_username = update.message.from_user.username
    user_id = update.message.from_user.id
    if len(context.args) != 0 and is_admin(user_id):
        tg_username = context.args[0]
    logger.info(f"Received command to get user info from {update.effective_user.name}")
    user_db = get_user(db_path, user_id)
    user = User(user_id=user_db[0], name=user_db[1], tg_username=user_db[2], birthday=user_db[3], wishlist_url=user_db[4],
                money_gifts=bool(user_db[5]), funny_gifts=bool(user_db[6]))
    logger.info(f"Got {user} from database")
    money_gifts = 'Нет'
    funny_gifts = 'Нет'
    if user.money_gifts:
        money_gifts = 'Да'
    if user.funny_gifts:
        funny_gifts = 'Да'

    await update.message.reply_text(
        f"*Telegram ID:* {markdown_escape(str(user.user_id))}\n"
        f"*Имя:* {markdown_escape(user.name)}\n"
        f"*Юзернейм*: {markdown_escape(user.tg_username)}\n"
        f"*Дата рождения:* {markdown_escape(user.birthday)}\n"
        f"*Вишлист:* {markdown_escape(user.wishlist_url)}\n"
        f"*Подарок деньгами:* {markdown_escape(money_gifts)}\n"
        f"*Рофляный подарок:* {markdown_escape(funny_gifts)}",
        parse_mode='MarkdownV2'
    )
