# get_users.py
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from db.database import get_user
from models.user import User

logger = logging.getLogger(__name__)


async def user_info(update: Update, context: ContextTypes):
    db_path = os.getenv('DB_PATH')
    tg_username = update.message.from_user.name
    logger.info(f"Received command to get users from {update.effective_user.name}")
    user_db = get_user(db_path, tg_username)
    user = User(tg_username=user_db[0], name=user_db[1], birthday=user_db[2], wishlist_url=user_db[3],
                money_gifts=bool(user_db[4]), funny_gifts=bool(user_db[5]))
    logger.info(f"Got {user} from database")
    money_gifts = 'Нет'
    funny_gifts = 'Нет'
    if user.money_gifts:
        money_gifts = 'Да'
    if user.funny_gifts:
        funny_gifts = 'Да'

    await update.message.reply_text(
        f"*Имя:* {user.name.replace('.', '\\.')}\n"
        f"*Юзернейм*: {user.tg_username.replace('.', '\\.')}\n"
        f"*Дата рождения:* {user.birthday.replace('.', '\\.')}\n"
        f"*Вишлист:* {user.wishlist_url.replace('.', '\\.')}\n"
        f"*Подарок деньгами:* {money_gifts}\n"
        f"*Рофляный подарок:* {funny_gifts}",
        parse_mode='MarkdownV2'
    )
