# get_users.py
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from db.database import get_db_users
from util.util import format_users_list

logger = logging.getLogger(__name__)


async def get_users(update: Update, context: ContextTypes):
    db_path = os.getenv('DB_PATH')
    """ Get all users from the database. """
    logger.info(f"Received command to get users from {update.effective_user.name}")
    if not is_admin(update.message.from_user.id):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    users = get_db_users(db_path)
    logger.info(f"Got {len(users)} users from database")
    formatted_users = format_users_list(users)
    await update.message.reply_text(formatted_users, parse_mode='MarkdownV2')
