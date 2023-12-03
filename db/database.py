    # database.py
import os
import logging
import sqlite3


logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))


def create_database() -> None:
    db_path = os.getenv('DB_PATH')
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


def get_db_users() -> list:
    db_path = os.getenv('DB_PATH')
    logger.info(f"Fetching users from database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    logger.info(f"Fetched {len(users)} users from database at {db_path}")
    return users