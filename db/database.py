# database.py
import os
import logging
import sqlite3

logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))


def get_db_tables(db_path: str) -> list:
    logger.info(f"Fetching tables from database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    conn.close()
    logger.info(f"Fetched {len(tables)} tables from database at {db_path}")
    return tables


def get_db_users(db_path: str) -> list:
    logger.info(f"Fetching users from database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    logger.info(f"Fetched {len(users)} users from database at {db_path}")
    return users


def get_user(db_path: str, user: str) -> list:
    logger.info(f"Fetching user {user} from database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE tg_username = ?", (user,))
    user = cursor.fetchone()
    conn.close()
    logger.info(f"Fetched user {user} from database at {db_path}")
    return user


def create_database(db_path: str) -> None:
    logger.info(f"Check if database exists at {db_path}")
    if os.path.exists(db_path):
        logger.info(f"Database exists at {db_path}, not creating a new one")
        return
    logger.info(f"Database does not exist at {db_path}, creating a new one")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_db_script = os.path.join(script_dir, 'create_db.sql')
    logger.info(f"Reading SQL script from {create_db_script}")
    with open(create_db_script, 'r') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()
    logger.info(f"Database created at {db_path}")


def add_user(db_path: str, user: str) -> None:
    logger.info(f"Adding user {user} to database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Add user only if it does not exist
    cursor.execute("SELECT * FROM users WHERE tg_username = ?", (user,))
    if cursor.fetchone() is not None:
        logger.info(f"User {user} already exists in database at {db_path}, not adding")
        return
    cursor.execute("INSERT INTO users (tg_username) VALUES (?)", (user,))
    conn.commit()
    conn.close()
    logger.info(f"Added user {user} to database at {db_path}")
