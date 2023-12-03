# handlers.py
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /start is issued."""
    logger.info(f"User: {update.message.from_user.name} with ID {update.message.from_user.id} started bot")
    await update.message.reply_text(str(update))