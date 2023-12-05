import os
import logging

from dotenv import load_dotenv
from handlers.start_handler import start
from handlers.new_database import new_database
from handlers.message_handler import process_quiz
from handlers.get_users import get_users
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters


load_dotenv() # Load environment variables from .env file
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') # Get bot token from environment variable

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    # Create the Application
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    except ValueError:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        exit(1)

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new_database", new_database))
    application.add_handler(CommandHandler("get_users", get_users))
    # Add message handlers
    application.add_handler(MessageHandler(filters.ALL, process_quiz))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
