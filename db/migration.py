import asyncio
import os
import logging
import sqlite3
import shutil

from telegram import Bot
from dotenv import load_dotenv


load_dotenv()

DB_PATH = os.getenv('DB_PATH')
DB_BACKUP_PATH = os.getenv('DB_BACKUP_PATH')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")
MIGRATION = (os.getenv('MIGRATION') or '').lower() == "true"

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
logger = logging.getLogger(__name__)


def backup_db(db_path: str, backup: str) -> None:
    """Backup using copy from shutil lib"""
    logger.info(f"Backup DB in path {backup}")
    shutil.copy(db_path, backup)


def run_migration(db_path: str) -> None:
    """Run SQL migration"""
    logger.info("Running migration...")
    if not MIGRATION:
        logger.info("MIGRATION=false, skipping migration")
        return
    logger.info("MIGRATION=true, executing migration")
    backup_db(DB_PATH, DB_BACKUP_PATH)
    with open(os.path.join(SCRIPT_DIR, "migration.sql"), "r", encoding="utf-8") as f:
        migration_sql_script = f.read()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.executescript(migration_sql_script)
            conn.commit()
        with open(ENV_FILE_PATH, "a", encoding="utf-8") as f:
            f.write("\nCOLLECT_IDS=true\n")
        logger.info("Migration has been finished. COLLECT_IDS mode is set to true. Notifying admins...")
        notify_admins(text="Migration has been finished. "
                           "COLLECT_IDS mode is set to true. "
                           "Collecting telegram IDs from users...")

    except Exception as e:
        logger.error(f"Error running migration of database at {db_path}: {str(e)}")


def all_users_have_ids() -> bool | None:
    """Check whether all users have actual (positive) Telegram IDs in the database.

    Users that still hold a placeholder id assigned by the migration are stored
    with a negative user_id, so we simply count those."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE user_id <= 0")
            remaining = cursor.fetchone()[0]
        return remaining == 0
    except Exception as e:
        logger.error(f"Something went wrong while checking user IDs: {str(e)}")
        return None


def notify_admins(text: str) -> None | Exception:
    admins_ids_env = os.getenv('ADMINS_IDS')
    if not admins_ids_env:
        logger.warning("ADMINS_IDS is not set, cannot notify admins")
        return
    admins_ids = [int(x) for x in admins_ids_env.split(',') if x.strip()]

    async def send_msg():
        for admin_id in admins_ids:
            try:
                await bot.send_message(chat_id=admin_id, text=text)
                logger.info(f"Message is sent to admin with id {admin_id}")
            except Exception as e:
                logger.warning(f"Failed to send message to admin with id {admin_id}: {str(e)}")
    asyncio.run(send_msg())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_migration(DB_PATH)
