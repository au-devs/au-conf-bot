import os
import logging

from dotenv import load_dotenv
from handlers.start_handler import start
from handlers.new_database import new_database
from handlers.message_handler import message_handler
from handlers.get_users import get_users
from handlers.add_user import add_user
from handlers.remove_user import remove_user_handler
from handlers.user_info import user_info
from handlers.edit_user_info import edit_info
from telegram import Update, BotCommand, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()  # Load environment variables from .env file
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Get bot token from environment variable

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [BotCommand("start", "Начало квиза"),
         BotCommand("info", "Вывод информации о себе"),
         BotCommand('edit_info', "Изменение информации о себе"),
         BotCommand("new_database", "[ADMIN] Создание новой базы данных пользователей"),
         BotCommand("add_user", "[ADMIN] Добавление нового пользователя"),
         BotCommand("get_users", "[ADMIN] Список всех пользователей"),
         BotCommand("remove_user", "[ADMIN]  Удаление пользователя")]
    )


def main() -> None:
    # Create the Application
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    except ValueError:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        exit(1)

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new_database", new_database))
    application.add_handler(CommandHandler("get_users", get_users))
    application.add_handler(CommandHandler("add_user", add_user))
    application.add_handler(CommandHandler("info", user_info))
    application.add_handler(CommandHandler("remove_user", remove_user_handler))
    application.add_handler(CommandHandler("edit_info", edit_info))
    # Add message handlers
    application.add_handler(MessageHandler(filters.ALL, message_handler))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
