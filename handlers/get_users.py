# get_users.py
import logging
import os

from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_checker import is_admin
from db.database import get_db_users

logger = logging.getLogger(__name__)


async def get_users(update: Update, context: ContextTypes):
    db_path = os.getenv('DB_PATH')
    """ Get all users from the database. """
    logger.info(f"Received command to get users from {update.effective_user.name}")
    if not is_admin(update.message.from_user.name):
        logger.info(f"{update.message.from_user.name} is not admin, not getting users")
        return
    users = get_db_users(db_path)
    logger.info(f"Got {len(users)} users from database")
    await update.message.reply_text(f"Users: {users}")
