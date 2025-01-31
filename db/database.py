import os
import logging
import sqlite3
from typing import Any

import models.user as User

logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))


def get_db_tables(db_path: str) -> list:
    logger.info(f"Fetching tables from database at {db_path}")
    tables = []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            logger.info(f"Fetched {len(tables)} tables from database at {db_path}")
    except Exception as e:
        logger.error(f"Error fetching tables from database at {db_path}: {str(e)}")
    return tables


def get_db_users(db_path: str) -> list:
    logger.info(f"Fetching users from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            logger.info(f"Fetched {len(users)} users from database at {db_path}")
            return [User.User(tg_username=user[0], name=user[1], birthday=user[2], wishlist_url=user[3],
                              money_gifts=bool(user[4]), funny_gifts=bool(user[5])) for user in users]
    except Exception as e:
        logger.error(f"Error fetching users from database at {db_path}: {str(e)}")
        return []


def get_user(db_path: str, user: str) -> tuple:
    logger.info(f"Fetching user {user} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE tg_username = ?", (user,))
            user = cursor.fetchone()
            if user is None:
                logger.info(f"User not found in database at {db_path}")
                return tuple()
            logger.info(f"Fetched user {user} from database at {db_path}")
            return user
    except Exception as e:
        logger.error(f"Error fetching user {user} from database at {db_path}: {str(e)}")


def create_database(db_path: str) -> None:
    logger.info(f"Check if database exists at {db_path}")
    if os.path.exists(db_path):
        logger.info(f"Database exists at {db_path}, not creating a new one")
        return

    logger.info(f"Database does not exist at {db_path}, creating a new one")

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            create_db_script = os.path.join(script_dir, 'create_db.sql')
            logger.info(f"Reading SQL script from {create_db_script}")

            with open(create_db_script, 'r') as f:
                sql_script = f.read()

            cursor.executescript(sql_script)
            conn.commit()

        logger.info(f"Database created at {db_path}")

    except Exception as e:
        logger.error(f"Error creating database at {db_path}: {str(e)}")


def clear_database(db_path: str) -> None:
    logger.info(f"Clearing database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for table_name in tables:
                cursor.execute(f"DELETE FROM {table_name[0]}")

            conn.commit()

        logger.info(f"Database at {db_path} cleared")

    except Exception as e:
        logger.error(f"Error clearing database at {db_path}: {str(e)}")


def add_user(db_path: str, user: User) -> None:
    """
    :rtype: object
    """
    logger.info(f"Adding user {user} to database at {db_path}")
    name = user.name
    tg_username = user.tg_username
    birthday = user.birthday
    wishlist_url = user.wishlist_url
    money_gifts = user.money_gifts
    funny_gifts = user.funny_gifts

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE tg_username = ?", (tg_username,))
            if cursor.fetchone() is not None:
                logger.info(f"User {tg_username} already exists in database at {db_path}, not adding")
                return

            cursor.execute("INSERT INTO users (name, tg_username, birthday, wishlist_url, money_gifts, funny_gifts) "
                           "VALUES (?, ?, ?, ?, ?, ?)", (name, tg_username, birthday, wishlist_url, money_gifts,
                                                         funny_gifts))
            cursor.execute("INSERT INTO reminders (tg_username, reminder_14_days, reminder_7_days, reminder_1_days) "
                           "VALUES (?, 0, 0, 0)", (tg_username,))
        logger.info(f"Added user {tg_username} to database at {db_path}")

    except Exception as e:
        logger.error(f"Error adding user {tg_username} to database: {str(e)}")


def update_user(db_path: str, tg_username: str, field_to_update: str, updated_data: str) -> None:
    user = get_user(db_path, tg_username)
    logger.info(f"Updating user {user} in database at {db_path}")
    if user is None:
        logger.info(f"User {user} not found in database at {db_path}")
        return
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(f"UPDATE users SET {field_to_update} = ? WHERE tg_username = ?",
                           (updated_data, tg_username))
            conn.commit()

        logger.info(f"Updated user {user} in database at {db_path}")

    except Exception as e:
        logger.error(f"Error updating user {user} in database at {db_path}: {str(e)}")


def remove_user(db_path: str, user: str) -> None:
    logger.info(f"Removing user {user} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM users WHERE tg_username = ?", (user,))
            cursor.execute("DELETE FROM reminders WHERE tg_username = ?", (user,))
            conn.commit()

        logger.info(f"Removed user {user} from database at {db_path}")

    except Exception as e:
        logger.error(f"Error removing user {user} from database at {db_path}: {str(e)}")


def update_reminder(db_path: str, tg_username: str, reminder_type: str) -> None:
    logger.info(f"Updating reminder {reminder_type} for user {tg_username} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE reminders SET {reminder_type} = 1 WHERE tg_username = ?", (tg_username,))
            conn.commit()
        logger.info(f"Updated reminder {reminder_type} for user {tg_username} in database at {db_path}")
    except Exception as e:
        logger.error(f"Error updating reminder {reminder_type} for user {tg_username} in database at {db_path}: {str(e)}")


def get_reminder_status(db_path: str, tg_username: str, reminder_type: str) -> bool:
    logger.info(f"Fetching reminder status {reminder_type} for user {tg_username} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {reminder_type} FROM reminders WHERE tg_username = ?", (tg_username,))
            result = cursor.fetchone()
            return result[0] == 1 if result else False
    except Exception as e:
        logger.error(f"Error fetching reminder status {reminder_type} for user {tg_username} from database at {db_path}: {str(e)}")
        return False


def reset_reminders(db_path: str) -> None:
    logger.info(f"Resetting all reminders in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET reminder_14_days = 0, reminder_7_days = 0, reminder_1_days = 0, birthday_today = 0")
            conn.commit()
        logger.info(f"All reminders reset in database at {db_path}")
    except Exception as e:
        logger.error(f"Error resetting reminders in database at {db_path}: {str(e)}")

def reset_birthday_today_reminders(db_path: str) -> None:
    logger.info(f"Resetting birthday_today reminders in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET birthday_today = 0")
            conn.commit()
        logger.info(f"birthday_today reminders reset in database at {db_path}")
    except Exception as e:
        logger.error(f"Error resetting birthday_today reminders in database at {db_path}: {str(e)}")
