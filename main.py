import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from handlers.start_handler import start
from handlers.new_database import new_database
from handlers.message_handler import message_handler, username_updater
from handlers.get_users import get_users
from handlers.add_user import add_user
from handlers.civil_war import civil_war, civil_war_stats, get_assets_dir
from handlers.remove_user import remove_user_handler
from handlers.user_info import user_info
from handlers.edit_user_info import edit_info
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, PicklePersistence, filters

load_dotenv()  # Load environment variables from .env file
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Get bot token from environment variable
BOT_PERSISTENCE_PATH = get_assets_dir() / 'bot_persistence.pkl'
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
         BotCommand("civil_war", "Гражданская война"),
         BotCommand("how_much_civil_war", "Статистика гражданской войны"),
         BotCommand("new_database", "[ADMIN] Создание новой базы данных пользователей"),
         BotCommand("add_user", "[ADMIN] Добавление нового пользователя"),
         BotCommand("get_users", "[ADMIN] Список всех пользователей"),
         BotCommand("remove_user", "[ADMIN]  Удаление пользователя")]
    )


def main() -> None:
    # Create the Application
    try:
        Path(BOT_PERSISTENCE_PATH).parent.mkdir(parents=True, exist_ok=True)
        persistence = PicklePersistence(filepath=str(BOT_PERSISTENCE_PATH))
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).persistence(persistence).post_init(post_init).build()
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
    application.add_handler(CommandHandler("civil_war", civil_war))
    application.add_handler(CommandHandler("how_much_civil_war", civil_war_stats))
    # Add message handlers. We explicitly exclude command updates from the generic
    # message_handler, otherwise the command message itself (e.g. "/start") would be
    # consumed by the quiz state machine and stored as an answer to the next question.
    non_command_filter = filters.ALL & ~filters.COMMAND
    application.add_handler(
        MessageHandler(filters.ChatType.GROUP & ~filters.COMMAND, username_updater),
        group=1,
    )
    application.add_handler(MessageHandler(non_command_filter, message_handler), group=2)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
