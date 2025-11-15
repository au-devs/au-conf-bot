# new_database.py
import os
import logging

from telegram import Update
from telegram.ext import ContextTypes
from db.database import create_database
from handlers.admin_checker import is_admin

logger = logging.getLogger(__name__)


async def new_database(update: Update, context: ContextTypes) -> None:
    logger.info(f"Received command to create a new database from {update.effective_user.name}")
    db_path = os.getenv('DB_PATH')
    if not is_admin(update.message.from_user.id):
        logger.info(f"{update.message.from_user.name} is not admin, not creating a new database")
        return
    create_database(db_path)
