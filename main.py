import os
import logging
from dotenv import load_dotenv

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


load_dotenv() # Load environment variables from .env file
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') # Get bot token from environment variable

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /start is issued."""
    logger.info(f"User: {update.message.from_user.name} with ID {update.message.from_user.id} started bot")
    await update.message.reply_text("Hi!")


def main() -> None:
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
