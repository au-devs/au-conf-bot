import os
import logging
import sqlite3
from datetime import datetime
from typing import Any

import models.user as User


logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))
ALLOWED_USER_FIELDS = {'name', 'birthday', 'wishlist_url', 'money_gifts', 'funny_gifts', 'tg_username'}
PLACEHOLDER_USER_NAME = '-'
PLACEHOLDER_USER_WISHLIST = 'я не заполнял профиль'


def ensure_civil_war_cooldowns_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_cooldowns (
            user_id INTEGER NOT NULL PRIMARY KEY,
            last_used_at TEXT NOT NULL
        )
        """
    )


def ensure_civil_war_stats_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_stats (
            user_id INTEGER NOT NULL PRIMARY KEY,
            display_name VARCHAR(255) NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            successes INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cursor.execute("PRAGMA table_info(civil_war_stats)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'display_name' not in columns:
        cursor.execute("ALTER TABLE civil_war_stats ADD COLUMN display_name VARCHAR(255) NULL")


def ensure_command_cooldowns_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS command_cooldowns (
            command_name VARCHAR(255) NOT NULL PRIMARY KEY,
            last_used_at TEXT NOT NULL
        )
        """
    )


def ensure_civil_war_chance_overrides_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_chance_overrides (
            config_key VARCHAR(255) NOT NULL PRIMARY KEY,
            chance REAL NOT NULL
        )
        """
    )


def ensure_civil_war_seasons_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_seasons (
            season_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_season_entries (
            season_id INTEGER NOT NULL,
            place INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            attempts INTEGER NOT NULL,
            successes INTEGER NOT NULL,
            winrate REAL NOT NULL,
            adjusted_winrate REAL NOT NULL,
            PRIMARY KEY (season_id, place),
            FOREIGN KEY (season_id) REFERENCES civil_war_seasons (season_id) ON DELETE CASCADE
        )
        """
    )


def ensure_bot_private_chats_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_private_chats (
            user_id INTEGER NOT NULL PRIMARY KEY,
            started_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
        """
    )


def ensure_civil_war_season2_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    ensure_bot_private_chats_table(conn)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_mafia_pending (
            user_id INTEGER NOT NULL PRIMARY KEY,
            created_at TEXT NOT NULL,
            state VARCHAR(255) NOT NULL DEFAULT 'choice',
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_mafia_daily (
            event_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER NOT NULL,
            target_user_id INTEGER NULL,
            action VARCHAR(255) NOT NULL,
            created_at TEXT NOT NULL,
            processed_at TEXT NULL,
            FOREIGN KEY (actor_user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (target_user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_mafia_protection_balance (
            user_id INTEGER NOT NULL PRIMARY KEY,
            protections INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_rat_state (
            id INTEGER NOT NULL PRIMARY KEY CHECK (id = 1),
            points INTEGER NOT NULL DEFAULT 1,
            hustled_points INTEGER NOT NULL DEFAULT 0,
            generation INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute("PRAGMA table_info(civil_war_rat_state)")
    rat_state_columns = {row[1] for row in cursor.fetchall()}
    if 'hustled_points' not in rat_state_columns:
        cursor.execute("ALTER TABLE civil_war_rat_state ADD COLUMN hustled_points INTEGER NOT NULL DEFAULT 0")
    if 'generation' not in rat_state_columns:
        cursor.execute("ALTER TABLE civil_war_rat_state ADD COLUMN generation INTEGER NOT NULL DEFAULT 0")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_rat_pending (
            user_id INTEGER NOT NULL PRIMARY KEY,
            points INTEGER NOT NULL,
            bank_generation INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            source_chat_id INTEGER NULL,
            source_message_thread_id INTEGER NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_rat_steal_reports (
            event_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            taker_user_id INTEGER NOT NULL,
            taker_display_name VARCHAR(255) NOT NULL,
            bank_points INTEGER NOT NULL,
            hustled_points INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            reported_at TEXT NULL,
            FOREIGN KEY (taker_user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute("PRAGMA table_info(civil_war_rat_pending)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'source_chat_id' not in columns:
        cursor.execute("ALTER TABLE civil_war_rat_pending ADD COLUMN source_chat_id INTEGER NULL")
    if 'source_message_thread_id' not in columns:
        cursor.execute("ALTER TABLE civil_war_rat_pending ADD COLUMN source_message_thread_id INTEGER NULL")
    if 'bank_generation' not in columns:
        cursor.execute("ALTER TABLE civil_war_rat_pending ADD COLUMN bank_generation INTEGER NOT NULL DEFAULT 0")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS civil_war_rat_investors (
            user_id INTEGER NOT NULL PRIMARY KEY,
            display_name VARCHAR(255) NOT NULL,
            invested_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
        """
    )


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
            return [User.User(user_id=user[0], name=user[1], tg_username=user[2], birthday=user[3], wishlist_url=user[4],
                              money_gifts=bool(user[5]), funny_gifts=bool(user[6])) for user in users]
    except Exception as e:
        logger.error(f"Error fetching users from database at {db_path}: {str(e)}")
        return []


def get_user(db_path: str, user_id: int) -> tuple | None | Any:
    logger.info(f"Fetching user with id {user_id} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            if user is None:
                logger.info(f"User not found in database at {db_path}")
                return tuple()
            logger.info(f"Fetched user {user} from database at {db_path}")
            return user
    except Exception as e:
        logger.error(f"Error fetching user {user_id} from database at {db_path}: {str(e)}")

def get_user_by_username(db_path: str, username: str) -> tuple | None | Any:
    logger.info(f"Fetching user {username} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE tg_username = ?", (username,))
            user = cursor.fetchone()
            if user is None:
                logger.info(f"User not found in database at {db_path}")
                return tuple()
            logger.info(f"Fetched user {user} from database at {db_path}")
            return user
    except Exception as e:
        logger.error(f"Error fetching user {username} from database at {db_path}: {str(e)}")

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
    user_id = user.user_id
    tg_username = user.tg_username
    birthday = user.birthday
    wishlist_url = user.wishlist_url
    money_gifts = user.money_gifts
    funny_gifts = user.funny_gifts

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone() is not None:
                logger.info(f"User {tg_username} with id {user_id} already exists in database at {db_path}, not adding")
                return

            cursor.execute("INSERT INTO users (user_id, name, tg_username, birthday, wishlist_url, money_gifts, funny_gifts) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, name, tg_username, birthday, wishlist_url, money_gifts,
                                                         funny_gifts))
            cursor.execute("INSERT INTO reminders (user_id, reminder_14_days, reminder_7_days, reminder_1_days) "
                           "VALUES (?, 0, 0, 0)", (user_id,))
        logger.info(f"Added user {tg_username} with id {user_id} to database at {db_path}")

    except Exception as e:
        logger.error(f"Error adding user {tg_username} with id {user_id} to database: {str(e)}")

def update_username(db_path: str, username: str, user_id: int) -> None:
    logger.info(f"Updating user's username with id {user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET tg_username = ? WHERE user_id = ?", (username, user_id))
            conn.commit()

    except Exception as e:
        logger.info(f"Error updating user's username with id {user_id}: {str(e)}")

def update_user(db_path: str, user_id: int, field_to_update: str, updated_data: str) -> None:
    user = get_user(db_path, user_id)
    logger.info(f"Updating user {user} in database at {db_path}")
    if user is None:
        logger.info(f"User with id {user_id} not found in database at {db_path}")
        return
    if field_to_update not in ALLOWED_USER_FIELDS:
        logger.error(f"Attempted to update unsupported field {field_to_update!r}")
        return
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {field_to_update} = ? WHERE user_id = ?",
                           (updated_data, user_id))
            conn.commit()
        logger.info(f"Updated user {user} in database at {db_path}")

    except Exception as e:
        logger.error(f"Error updating user {user} in database at {db_path}: {str(e)}")


def remove_user(db_path: str, user: int) -> None:
    logger.info(f"Removing user with id {user} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user,))
            cursor.execute("DELETE FROM reminders WHERE user_id = ?", (user,))
            conn.commit()

        logger.info(f"Removed user with id {user} from database at {db_path}")

    except Exception as e:
        logger.error(f"Error removing user with id {user} from database at {db_path}: {str(e)}")

def get_id_by_username(db_path: str, username: str) -> int | None:
    logger.info(f"Fetching user with {username} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE tg_username = ?", (username,))
            row = cursor.fetchone()
            if row is None:
                logger.info(f"User with username {username} is not found in database at {db_path}")
                return None
            logger.info(f"Fetched user {username} with id {row[0]}")
            return row[0]
    except Exception as e:
        logger.error(f"Error fetching user with username {username} in database at {db_path}: {str(e)}")
        return None


def get_username_by_id(db_path: str, user_id: int) -> str | None:
    logger.info(f"Fetching user with id {user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tg_username FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row is None:
                logger.info(f"User with id {user_id} is not found in database at {db_path}")
                return None
            logger.info(f"Fetched user {row[0]} with id {user_id} in database at {db_path}")
            return row[0]
    except Exception as e:
        logger.error(f"Error fetching user with id {user_id} in database at {db_path}: {str(e)}")
        return None

def update_reminder(db_path: str, user_id: int, tg_username: str, reminder_type: str) -> None:
    logger.info(f"Updating reminder {reminder_type} for user {tg_username} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE reminders SET {reminder_type} = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        logger.info(f"Updated reminder {reminder_type} for user {tg_username} with tg_id {user_id} in database at {db_path}")
    except Exception as e:
        logger.error(f"Error updating reminder {reminder_type} for user {tg_username} with tg_id {user_id} in database at {db_path}: {str(e)}")


def get_reminder_status(db_path: str, user_id: int, tg_username: str, reminder_type: str) -> bool:
    logger.info(f"Fetching reminder status {reminder_type} for user {tg_username} with tg_id {user_id} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {reminder_type} FROM reminders WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] == 1 if result else False
    except Exception as e:
        logger.error(f"Error fetching reminder status {reminder_type} for user {tg_username} with tg_id {user_id} from database at {db_path}: {str(e)}")
        return False


def reset_user_reminders(db_path: str, user_id: int, reminder_types: list[str]) -> None:
    if not reminder_types:
        return
    logger.info(f"Resetting reminders {reminder_types} for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            assignments = ", ".join(f"{reminder_type} = 0" for reminder_type in reminder_types)
            cursor.execute(f"UPDATE reminders SET {assignments} WHERE user_id = ?", (user_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error resetting reminders {reminder_types} for user_id={user_id} in database at {db_path}: {str(e)}")


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


def get_civil_war_last_used_at(db_path: str, user_id: int) -> datetime | None:
    logger.info(f"Fetching civil war cooldown for user_id={user_id} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_cooldowns_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT last_used_at FROM civil_war_cooldowns WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return datetime.fromisoformat(row[0])
    except Exception as e:
        logger.error(f"Error fetching civil war cooldown for user_id={user_id} from database at {db_path}: {str(e)}")
        return None


def upsert_civil_war_last_used_at(db_path: str, user_id: int, last_used_at: datetime) -> None:
    logger.info(f"Updating civil war cooldown for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_cooldowns_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_cooldowns (user_id, last_used_at)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_used_at = excluded.last_used_at
                """,
                (user_id, last_used_at.isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error updating civil war cooldown for user_id={user_id} in database at {db_path}: {str(e)}")


def update_civil_war_stats(
        db_path: str,
        user_id: int,
        successes_delta: int | bool,
        display_name: str | None = None,
) -> None:
    logger.info(f"Updating civil war stats for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_stats (user_id, display_name, attempts, successes)
                VALUES (?, ?, 1, MAX(?, 0))
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = COALESCE(excluded.display_name, display_name),
                    attempts = attempts + 1,
                    successes = MAX(successes + ?, 0)
                """,
                (user_id, display_name, int(successes_delta), int(successes_delta)),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error updating civil war stats for user_id={user_id} in database at {db_path}: {str(e)}")


def adjust_civil_war_successes(db_path: str, user_id: int, successes_delta: int) -> None:
    logger.info(f"Adjusting civil war successes for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_stats (user_id, attempts, successes)
                VALUES (?, 0, MAX(?, 0))
                ON CONFLICT(user_id) DO UPDATE SET
                    successes = MAX(successes + ?, 0)
                """,
                (user_id, int(successes_delta), int(successes_delta)),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error adjusting civil war successes for user_id={user_id} in database at {db_path}: {str(e)}")


def clear_civil_war_stats(db_path: str) -> None:
    logger.info(f"Clearing civil war stats in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM civil_war_stats")
            conn.commit()
    except Exception as e:
        logger.error(f"Error clearing civil war stats in database at {db_path}: {str(e)}")


def get_civil_war_stats_without_display_names(db_path: str) -> list[int]:
    logger.info(f"Fetching civil war stats rows without display_name from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id
                FROM civil_war_stats
                WHERE attempts > 0 AND (display_name IS NULL OR display_name = '')
                """
            )
            return [int(row[0]) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching civil war stats without display_name from database at {db_path}: {str(e)}")
        return []


def get_civil_war_stat_user_ids(db_path: str) -> list[int]:
    logger.info(f"Fetching civil war stat user ids from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM civil_war_stats WHERE attempts > 0")
            return [int(row[0]) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching civil war stat user ids from database at {db_path}: {str(e)}")
        return []


def update_civil_war_display_name(db_path: str, user_id: int, display_name: str) -> None:
    logger.info(f"Updating civil war display_name for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE civil_war_stats SET display_name = ? WHERE user_id = ?",
                (display_name, user_id),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error updating civil war display_name for user_id={user_id} in database at {db_path}: {str(e)}")


def create_missing_users_from_civil_war_stats(db_path: str) -> None:
    logger.info(f"Creating missing users from civil war stats in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (user_id, name, tg_username, birthday, wishlist_url, money_gifts, funny_gifts)
                SELECT
                    civil_war_stats.user_id,
                    ?,
                    COALESCE(civil_war_stats.display_name, ?),
                    NULL,
                    ?,
                    0,
                    0
                FROM civil_war_stats
                LEFT JOIN users ON users.user_id = civil_war_stats.user_id
                WHERE civil_war_stats.attempts > 0 AND users.user_id IS NULL
                """,
                (PLACEHOLDER_USER_NAME, PLACEHOLDER_USER_NAME, PLACEHOLDER_USER_WISHLIST),
            )
            cursor.execute(
                """
                INSERT INTO reminders (user_id, reminder_14_days, reminder_7_days, reminder_1_days, birthday_today)
                SELECT users.user_id, 0, 0, 0, 0
                FROM users
                LEFT JOIN reminders ON reminders.user_id = users.user_id
                WHERE reminders.user_id IS NULL
                """
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error creating missing users from civil war stats in database at {db_path}: {str(e)}")


def get_civil_war_stats(db_path: str, user_id: int) -> tuple[int, int]:
    logger.info(f"Fetching civil war stats for user_id={user_id} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT attempts, successes FROM civil_war_stats WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return 0, 0
            return int(row[0]), int(row[1])
    except Exception as e:
        logger.error(f"Error fetching civil war stats for user_id={user_id} from database at {db_path}: {str(e)}")
        return 0, 0


def get_civil_war_chance_override(db_path: str, config_key: str) -> float | None:
    logger.info(f"Fetching civil war chance override {config_key} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_chance_overrides_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT chance FROM civil_war_chance_overrides WHERE config_key = ?", (config_key,))
            row = cursor.fetchone()
            return None if row is None else float(row[0])
    except Exception as e:
        logger.error(f"Error fetching civil war chance override {config_key} from database at {db_path}: {str(e)}")
        return None


def upsert_civil_war_chance_override(db_path: str, config_key: str, chance: float) -> None:
    logger.info(f"Updating civil war chance override {config_key} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_chance_overrides_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_chance_overrides (config_key, chance)
                VALUES (?, ?)
                ON CONFLICT(config_key) DO UPDATE SET chance = excluded.chance
                """,
                (config_key, chance),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error updating civil war chance override {config_key} in database at {db_path}: {str(e)}")


def delete_civil_war_chance_overrides(db_path: str) -> None:
    logger.info(f"Deleting all civil war chance overrides from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_chance_overrides_table(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM civil_war_chance_overrides")
            conn.commit()
    except Exception as e:
        logger.error(f"Error deleting civil war chance overrides from database at {db_path}: {str(e)}")


def get_civil_war_chance_overrides(db_path: str) -> dict[str, float]:
    logger.info(f"Fetching civil war chance overrides from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_chance_overrides_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT config_key, chance FROM civil_war_chance_overrides ORDER BY config_key")
            return {str(row[0]): float(row[1]) for row in cursor.fetchall()}
    except Exception as e:
        logger.error(f"Error fetching civil war chance overrides from database at {db_path}: {str(e)}")
        return {}


def get_civil_war_leaderboard(
        db_path: str,
        limit: int | None = None,
        prior_attempts: int = 100,
        prior_success_rate: float = 0.0666,
) -> list[tuple[int, str, int, int, float, float]]:
    logger.info(f"Fetching civil war leaderboard from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            query = """
                SELECT
                    civil_war_stats.user_id,
                    COALESCE(users.tg_username, civil_war_stats.display_name, users.name, CAST(civil_war_stats.user_id AS TEXT)) AS display_name,
                    civil_war_stats.attempts,
                    civil_war_stats.successes,
                    CAST(civil_war_stats.successes AS REAL) / civil_war_stats.attempts AS winrate,
                    (civil_war_stats.successes + ?) / (civil_war_stats.attempts + ?) AS adjusted_winrate
                FROM civil_war_stats
                JOIN users ON users.user_id = civil_war_stats.user_id
                WHERE civil_war_stats.attempts > 0
                ORDER BY adjusted_winrate DESC, winrate DESC, civil_war_stats.successes DESC, civil_war_stats.attempts DESC
                """
            prior_successes = prior_attempts * prior_success_rate
            params = (prior_successes, prior_attempts)
            if limit is not None:
                query += " LIMIT ?"
                params = (prior_successes, prior_attempts, limit)
            cursor.execute(query, params)
            return [
                (int(row[0]), str(row[1]), int(row[2]), int(row[3]), float(row[4]), float(row[5]))
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.error(f"Error fetching civil war leaderboard from database at {db_path}: {str(e)}")
        return []


def get_civil_war_lowest_winrate(
        db_path: str,
        prior_attempts: int = 100,
        prior_success_rate: float = 0.0666,
) -> tuple[int, str, int, int, float, float] | None:
    logger.info(f"Fetching lowest civil war winrate from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    civil_war_stats.user_id,
                    COALESCE(users.tg_username, civil_war_stats.display_name, users.name, CAST(civil_war_stats.user_id AS TEXT)) AS display_name,
                    civil_war_stats.attempts,
                    civil_war_stats.successes,
                    CAST(civil_war_stats.successes AS REAL) / civil_war_stats.attempts AS winrate,
                    (civil_war_stats.successes + ?) / (civil_war_stats.attempts + ?) AS adjusted_winrate
                FROM civil_war_stats
                JOIN users ON users.user_id = civil_war_stats.user_id
                WHERE civil_war_stats.attempts > 0
                ORDER BY adjusted_winrate ASC, winrate ASC, civil_war_stats.successes ASC, civil_war_stats.attempts DESC
                LIMIT 1
                """,
                (prior_attempts * prior_success_rate, prior_attempts),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return int(row[0]), str(row[1]), int(row[2]), int(row[3]), float(row[4]), float(row[5])
    except Exception as e:
        logger.error(f"Error fetching lowest civil war winrate from database at {db_path}: {str(e)}")
        return None


def create_civil_war_season(
        db_path: str,
        name: str,
        leaderboard: list[tuple[int, str, int, int, float, float]],
        created_at: datetime | None = None,
) -> int | None:
    logger.info(f"Creating civil war season {name!r} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_seasons_tables(conn)
            cursor = conn.cursor()
            saved_at = created_at or datetime.now()
            cursor.execute(
                "INSERT INTO civil_war_seasons (name, created_at) VALUES (?, ?)",
                (name, saved_at.isoformat()),
            )
            season_id = int(cursor.lastrowid)
            cursor.executemany(
                """
                INSERT INTO civil_war_season_entries (
                    season_id, place, user_id, display_name, attempts, successes, winrate, adjusted_winrate
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (season_id, place, user_id, display_name, attempts, successes, winrate, adjusted_winrate)
                    for place, (user_id, display_name, attempts, successes, winrate, adjusted_winrate)
                    in enumerate(leaderboard, start=1)
                ],
            )
            conn.commit()
            return season_id
    except Exception as e:
        logger.error(f"Error creating civil war season {name!r} in database at {db_path}: {str(e)}")
        return None


def get_civil_war_seasons(db_path: str) -> list[tuple[int, str, datetime]]:
    logger.info(f"Fetching civil war seasons from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_seasons_tables(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT season_id, name, created_at FROM civil_war_seasons ORDER BY season_id DESC")
            return [(int(row[0]), str(row[1]), datetime.fromisoformat(row[2])) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching civil war seasons from database at {db_path}: {str(e)}")
        return []


def get_civil_war_season_entries(db_path: str, season_ref: str) -> tuple[int, str, datetime, list[tuple[int, int, str, int, int, float, float]]] | None:
    logger.info(f"Fetching civil war season {season_ref!r} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_seasons_tables(conn)
            cursor = conn.cursor()
            if season_ref.isdigit():
                cursor.execute(
                    "SELECT season_id, name, created_at FROM civil_war_seasons WHERE season_id = ?",
                    (int(season_ref),),
                )
            else:
                cursor.execute(
                    "SELECT season_id, name, created_at FROM civil_war_seasons WHERE name = ? ORDER BY season_id DESC LIMIT 1",
                    (season_ref,),
                )
            season = cursor.fetchone()
            if season is None:
                return None
            season_id = int(season[0])
            cursor.execute(
                """
                SELECT place, user_id, display_name, attempts, successes, winrate, adjusted_winrate
                FROM civil_war_season_entries
                WHERE season_id = ?
                ORDER BY place
                """,
                (season_id,),
            )
            entries = [
                (int(row[0]), int(row[1]), str(row[2]), int(row[3]), int(row[4]), float(row[5]), float(row[6]))
                for row in cursor.fetchall()
            ]
            return season_id, str(season[1]), datetime.fromisoformat(season[2]), entries
    except Exception as e:
        logger.error(f"Error fetching civil war season {season_ref!r} from database at {db_path}: {str(e)}")
        return None


def mark_bot_private_chat_started(db_path: str, user_id: int, started_at: datetime | None = None) -> None:
    logger.info(f"Marking private chat as started for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_bot_private_chats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bot_private_chats (user_id, started_at)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET started_at = excluded.started_at
                """,
                (user_id, (started_at or datetime.now()).isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error marking private chat for user_id={user_id} in database at {db_path}: {str(e)}")


def has_verified_private_chat(db_path: str, user_id: int) -> bool:
    logger.info(f"Checking verified private chat for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_bot_private_chats_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM users
                JOIN bot_private_chats ON bot_private_chats.user_id = users.user_id
                WHERE users.user_id = ?
                """,
                (user_id,),
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking verified private chat for user_id={user_id} in database at {db_path}: {str(e)}")
        return False


def create_mafia_pending(db_path: str, user_id: int, created_at: datetime | None = None) -> None:
    logger.info(f"Creating mafia pending action for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_mafia_pending (user_id, created_at, state)
                VALUES (?, ?, 'choice')
                ON CONFLICT(user_id) DO UPDATE SET created_at = excluded.created_at, state = 'choice'
                """,
                (user_id, (created_at or datetime.now()).isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error creating mafia pending action for user_id={user_id} in database at {db_path}: {str(e)}")


def get_mafia_pending_state(db_path: str, user_id: int) -> str | None:
    logger.info(f"Fetching mafia pending state for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT state FROM civil_war_mafia_pending WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return None if row is None else str(row[0])
    except Exception as e:
        logger.error(f"Error fetching mafia pending state for user_id={user_id} in database at {db_path}: {str(e)}")
        return None


def set_mafia_pending_state(db_path: str, user_id: int, state: str) -> None:
    logger.info(f"Setting mafia pending state for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("UPDATE civil_war_mafia_pending SET state = ? WHERE user_id = ?", (state, user_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Error setting mafia pending state for user_id={user_id} in database at {db_path}: {str(e)}")


def delete_mafia_pending(db_path: str, user_id: int) -> None:
    logger.info(f"Deleting mafia pending action for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM civil_war_mafia_pending WHERE user_id = ?", (user_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error deleting mafia pending action for user_id={user_id} in database at {db_path}: {str(e)}")


def keep_latest_season2_pending(db_path: str, user_id: int) -> str | None:
    logger.info(f"Resolving latest season 2 pending action for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                SELECT pending_type
                FROM (
                    SELECT 'mafia' AS pending_type, created_at FROM civil_war_mafia_pending WHERE user_id = ?
                    UNION ALL
                    SELECT 'rat' AS pending_type, created_at FROM civil_war_rat_pending WHERE user_id = ?
                )
                ORDER BY created_at DESC, pending_type
                LIMIT 1
                """,
                (user_id, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                conn.commit()
                return None
            pending_type = str(row[0])
            if pending_type == 'mafia':
                cursor.execute("DELETE FROM civil_war_rat_pending WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("DELETE FROM civil_war_mafia_pending WHERE user_id = ?", (user_id,))
            conn.commit()
            return pending_type
    except Exception as e:
        logger.error(f"Error resolving latest season 2 pending action for user_id={user_id} in database at {db_path}: {str(e)}")
        return None


def add_mafia_daily_action(
        db_path: str,
        actor_user_id: int,
        action: str,
        target_user_id: int | None = None,
        created_at: datetime | None = None,
) -> None:
    logger.info(f"Adding mafia daily action={action} for actor_user_id={actor_user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_mafia_daily (actor_user_id, target_user_id, action, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (actor_user_id, target_user_id, action, (created_at or datetime.now()).isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error adding mafia daily action for actor_user_id={actor_user_id} in database at {db_path}: {str(e)}")


def find_verified_civil_war_user(db_path: str, token: str) -> tuple[int, str] | None:
    normalized = token.strip()
    if not normalized:
        return None
    username = normalized if normalized.startswith("@") else f"@{normalized}"
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            if normalized.lstrip("@").isdigit():
                cursor.execute(
                    """
                    SELECT users.user_id, COALESCE(users.tg_username, users.name, CAST(users.user_id AS TEXT))
                    FROM users
                    JOIN civil_war_stats ON civil_war_stats.user_id = users.user_id
                    WHERE users.user_id = ? AND civil_war_stats.attempts > 0
                    """,
                    (int(normalized.lstrip("@")),),
                )
            else:
                cursor.execute(
                    """
                    SELECT users.user_id, COALESCE(users.tg_username, users.name, CAST(users.user_id AS TEXT))
                    FROM users
                    JOIN civil_war_stats ON civil_war_stats.user_id = users.user_id
                    WHERE users.tg_username = ? AND civil_war_stats.attempts > 0
                    """,
                    (username,),
                )
            row = cursor.fetchone()
            return None if row is None else (int(row[0]), str(row[1]))
    except Exception as e:
        logger.error(f"Error finding verified civil war user {token!r} in database at {db_path}: {str(e)}")
        return None


def process_mafia_daily_actions(db_path: str, processed_at: datetime | None = None) -> tuple[list[tuple[str, int, int, int]], list[tuple[str, int, int]]]:
    logger.info(f"Processing mafia daily actions in database at {db_path}")
    processed_time = processed_at or datetime.now()
    damaged: list[tuple[str, int, int, int]] = []
    defended: list[tuple[str, int, int]] = []
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            ensure_civil_war_stats_table(conn)
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                SELECT event_id, actor_user_id, target_user_id, action
                FROM civil_war_mafia_daily
                WHERE processed_at IS NULL
                ORDER BY event_id
                """
            )
            events = cursor.fetchall()
            if not events:
                conn.commit()
                return damaged, defended

            event_ids = [int(row[0]) for row in events]
            placeholders = ", ".join("?" for _ in event_ids)
            cursor.execute(
                f"UPDATE civil_war_mafia_daily SET processed_at = ? WHERE event_id IN ({placeholders})",
                (processed_time.isoformat(), *event_ids),
            )

            attacks: dict[int, int] = {}
            protections: dict[int, int] = {}
            for _, actor_user_id, target_user_id, action in events:
                if action == 'attack' and target_user_id is not None:
                    target_id = int(target_user_id)
                    attacks[target_id] = attacks.get(target_id, 0) + 1
                elif action == 'protect':
                    actor_id = int(actor_user_id)
                    protections[actor_id] = protections.get(actor_id, 0) + 1

            affected_user_ids = set(attacks) | set(protections)
            protection_balances: dict[int, int] = {}
            if affected_user_ids:
                balance_placeholders = ", ".join("?" for _ in affected_user_ids)
                cursor.execute(
                    f"""
                    SELECT user_id, protections
                    FROM civil_war_mafia_protection_balance
                    WHERE user_id IN ({balance_placeholders})
                    """,
                    tuple(affected_user_ids),
                )
                protection_balances = {
                    int(user_id): max(int(protections_count), 0)
                    for user_id, protections_count in cursor.fetchall()
                }

            for user_id, new_protections in protections.items():
                protection_balances[user_id] = protection_balances.get(user_id, 0) + new_protections

            for target_user_id, attack_count in attacks.items():
                available_protections = protection_balances.get(target_user_id, 0)
                used_protections = min(attack_count, available_protections)
                damage = max(attack_count - used_protections, 0)
                protection_balances[target_user_id] = available_protections - used_protections
                cursor.execute(
                    """
                    SELECT COALESCE(users.tg_username, users.name, CAST(users.user_id AS TEXT))
                    FROM users
                    WHERE users.user_id = ?
                    """,
                    (target_user_id,),
                )
                row = cursor.fetchone()
                display_name = str(row[0]) if row is not None else str(target_user_id)
                if damage > 0:
                    cursor.execute(
                        """
                        INSERT INTO civil_war_stats (user_id, attempts, successes)
                        VALUES (?, 0, 0)
                        ON CONFLICT(user_id) DO UPDATE SET successes = MAX(successes - ?, 0)
                        """,
                        (target_user_id, damage),
                    )
                    damaged.append((display_name, damage, attack_count, used_protections))
                elif used_protections > 0:
                    defended.append((display_name, attack_count, used_protections))

            for user_id in affected_user_ids:
                cursor.execute(
                    """
                    INSERT INTO civil_war_mafia_protection_balance (user_id, protections, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        protections = excluded.protections,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, max(protection_balances.get(user_id, 0), 0), processed_time.isoformat()),
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Error processing mafia daily actions in database at {db_path}: {str(e)}")
    return damaged, defended


def get_mafia_protection_balance(db_path: str, user_id: int) -> int:
    logger.info(f"Fetching mafia protection balance for user_id={user_id} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT protections FROM civil_war_mafia_protection_balance WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return 0 if row is None else max(int(row[0]), 0)
    except Exception as e:
        logger.error(f"Error fetching mafia protection balance for user_id={user_id} from database at {db_path}: {str(e)}")
        return 0


def get_rat_points(db_path: str) -> int:
    logger.info(f"Fetching rat points from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT points FROM civil_war_rat_state WHERE id = 1")
            row = cursor.fetchone()
            return 1 if row is None else max(int(row[0]), 1)
    except Exception as e:
        logger.error(f"Error fetching rat points from database at {db_path}: {str(e)}")
        return 1


def get_rat_state(db_path: str) -> tuple[int, int]:
    logger.info(f"Fetching rat state from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT points, generation FROM civil_war_rat_state WHERE id = 1")
            row = cursor.fetchone()
            if row is None:
                return 1, 0
            return max(int(row[0]), 1), max(int(row[1]), 0)
    except Exception as e:
        logger.error(f"Error fetching rat state from database at {db_path}: {str(e)}")
        return 1, 0


def get_rat_hustled_points(db_path: str) -> int:
    logger.info(f"Fetching rat hustled points from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT hustled_points FROM civil_war_rat_state WHERE id = 1")
            row = cursor.fetchone()
            return 0 if row is None else max(int(row[0]), 0)
    except Exception as e:
        logger.error(f"Error fetching rat hustled points from database at {db_path}: {str(e)}")
        return 0


def set_rat_points(db_path: str, points: int, updated_at: datetime | None = None) -> None:
    logger.info(f"Setting rat points={points} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_rat_state (id, points, generation, updated_at)
                VALUES (1, ?, 1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    points = excluded.points,
                    generation = generation + 1,
                    updated_at = excluded.updated_at
                """,
                (max(int(points), 1), (updated_at or datetime.now()).isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error setting rat points in database at {db_path}: {str(e)}")


def add_rat_hustled_points(db_path: str, points_delta: int, updated_at: datetime | None = None) -> None:
    logger.info(f"Adding rat hustled points_delta={points_delta} in database at {db_path}")
    if points_delta <= 0:
        return
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_rat_state (id, points, hustled_points, updated_at)
                VALUES (1, 1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    hustled_points = hustled_points + excluded.hustled_points,
                    updated_at = excluded.updated_at
                """,
                (int(points_delta), (updated_at or datetime.now()).isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error adding rat hustled points in database at {db_path}: {str(e)}")


def reset_rat_hustled_points(db_path: str, updated_at: datetime | None = None) -> None:
    logger.info(f"Resetting rat hustled points in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_rat_state (id, points, hustled_points, updated_at)
                VALUES (1, 1, 0, ?)
                ON CONFLICT(id) DO UPDATE SET
                    hustled_points = 0,
                    updated_at = excluded.updated_at
                """,
                ((updated_at or datetime.now()).isoformat(),),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error resetting rat hustled points in database at {db_path}: {str(e)}")


def create_rat_steal_report(
        db_path: str,
        taker_user_id: int,
        taker_display_name: str,
        bank_points: int,
        hustled_points: int,
        created_at: datetime | None = None,
) -> None:
    logger.info(f"Creating rat steal report for taker_user_id={taker_user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_rat_steal_reports (
                    taker_user_id, taker_display_name, bank_points, hustled_points, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    taker_user_id,
                    taker_display_name,
                    max(int(bank_points), 1),
                    max(int(hustled_points), 0),
                    (created_at or datetime.now()).isoformat(),
                ),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error creating rat steal report for taker_user_id={taker_user_id} in database at {db_path}: {str(e)}")


def process_rat_steal_reports(
        db_path: str,
        reported_at: datetime | None = None,
) -> list[tuple[str, int, int]]:
    logger.info(f"Processing rat steal reports in database at {db_path}")
    report_time = reported_at or datetime.now()
    reports: list[tuple[str, int, int]] = []
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                SELECT event_id, taker_display_name, bank_points, hustled_points
                FROM civil_war_rat_steal_reports
                WHERE reported_at IS NULL
                ORDER BY event_id
                """
            )
            rows = cursor.fetchall()
            if not rows:
                conn.commit()
                return reports

            event_ids = [int(row[0]) for row in rows]
            placeholders = ", ".join("?" for _ in event_ids)
            cursor.execute(
                f"UPDATE civil_war_rat_steal_reports SET reported_at = ? WHERE event_id IN ({placeholders})",
                (report_time.isoformat(), *event_ids),
            )
            reports = [(str(row[1]), max(int(row[2]), 1), max(int(row[3]), 0)) for row in rows]
            conn.commit()
    except Exception as e:
        logger.error(f"Error processing rat steal reports in database at {db_path}: {str(e)}")
    return reports


def create_rat_pending(
        db_path: str,
        user_id: int,
        points: int,
        bank_generation: int | None = None,
        created_at: datetime | None = None,
        source_chat_id: int | None = None,
        source_message_thread_id: int | None = None,
) -> None:
    logger.info(f"Creating rat pending action for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            if bank_generation is None:
                cursor.execute("SELECT generation FROM civil_war_rat_state WHERE id = 1")
                state_row = cursor.fetchone()
                bank_generation = 0 if state_row is None else max(int(state_row[0]), 0)
            cursor.execute(
                """
                INSERT INTO civil_war_rat_pending (
                    user_id, points, bank_generation, created_at, source_chat_id, source_message_thread_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    points = excluded.points,
                    bank_generation = excluded.bank_generation,
                    created_at = excluded.created_at,
                    source_chat_id = excluded.source_chat_id,
                    source_message_thread_id = excluded.source_message_thread_id
                """,
                (
                    user_id,
                    max(int(points), 1),
                    max(int(bank_generation), 0),
                    (created_at or datetime.now()).isoformat(),
                    source_chat_id,
                    source_message_thread_id,
                ),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error creating rat pending action for user_id={user_id} in database at {db_path}: {str(e)}")


def get_rat_pending(db_path: str, user_id: int) -> tuple[int, int | None, int | None] | None:
    logger.info(f"Fetching rat pending action for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT points, source_chat_id, source_message_thread_id
                FROM civil_war_rat_pending
                WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return (
                max(int(row[0]), 1),
                None if row[1] is None else int(row[1]),
                None if row[2] is None else int(row[2]),
            )
    except Exception as e:
        logger.error(f"Error fetching rat pending action for user_id={user_id} in database at {db_path}: {str(e)}")
        return None


def get_rat_pending_points(db_path: str, user_id: int) -> int | None:
    logger.info(f"Fetching rat pending action for user_id={user_id} in database at {db_path}")
    pending = get_rat_pending(db_path, user_id)
    return None if pending is None else pending[0]


def consume_rat_pending(db_path: str, user_id: int) -> tuple[int, int | None, int | None] | None:
    logger.info(f"Consuming rat pending action for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                SELECT points, bank_generation, source_chat_id, source_message_thread_id
                FROM civil_war_rat_pending
                WHERE user_id = ?
                """,
                (user_id,),
            )
            pending = cursor.fetchone()
            if pending is None:
                conn.commit()
                return None

            cursor.execute("SELECT points, generation FROM civil_war_rat_state WHERE id = 1")
            state = cursor.fetchone()
            current_points, current_generation = (1, 0) if state is None else (max(int(state[0]), 1), max(int(state[1]), 0))
            pending_points = max(int(pending[0]), 1)
            pending_generation = max(int(pending[1]), 0)
            is_current = pending_points == current_points and pending_generation == current_generation
            cursor.execute("DELETE FROM civil_war_rat_pending WHERE user_id = ?", (user_id,))
            if is_current:
                cursor.execute(
                    """
                    INSERT INTO civil_war_rat_state (id, points, generation, updated_at)
                    VALUES (1, ?, 1, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        generation = generation + 1,
                        updated_at = excluded.updated_at
                    """,
                    (current_points, datetime.now().isoformat()),
                )
            conn.commit()

            if not is_current:
                return None
            return (
                pending_points,
                None if pending[2] is None else int(pending[2]),
                None if pending[3] is None else int(pending[3]),
            )
    except Exception as e:
        logger.error(f"Error consuming rat pending action for user_id={user_id} in database at {db_path}: {str(e)}")
        return None


def delete_rat_pending(db_path: str, user_id: int) -> None:
    logger.info(f"Deleting rat pending action for user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM civil_war_rat_pending WHERE user_id = ?", (user_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error deleting rat pending action for user_id={user_id} in database at {db_path}: {str(e)}")


def add_rat_investor(
        db_path: str,
        user_id: int,
        display_name: str,
        invested_at: datetime | None = None,
) -> None:
    logger.info(f"Adding rat investor user_id={user_id} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO civil_war_rat_investors (user_id, display_name, invested_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    invested_at = excluded.invested_at
                """,
                (user_id, display_name, (invested_at or datetime.now()).isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error adding rat investor user_id={user_id} in database at {db_path}: {str(e)}")


def get_rat_investors(db_path: str) -> list[tuple[int, str]]:
    logger.info(f"Fetching rat investors from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, display_name
                FROM civil_war_rat_investors
                ORDER BY invested_at, user_id
                """
            )
            return [(int(row[0]), str(row[1])) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching rat investors from database at {db_path}: {str(e)}")
        return []


def clear_rat_investors(db_path: str) -> None:
    logger.info(f"Clearing rat investors in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_civil_war_season2_tables(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM civil_war_rat_investors")
            conn.commit()
    except Exception as e:
        logger.error(f"Error clearing rat investors in database at {db_path}: {str(e)}")


def get_command_last_used_at(db_path: str, command_name: str) -> datetime | None:
    logger.info(f"Fetching cooldown for command={command_name} from database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_command_cooldowns_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT last_used_at FROM command_cooldowns WHERE command_name = ?", (command_name,))
            row = cursor.fetchone()
            if row is None:
                return None
            return datetime.fromisoformat(row[0])
    except Exception as e:
        logger.error(f"Error fetching cooldown for command={command_name} from database at {db_path}: {str(e)}")
        return None


def upsert_command_last_used_at(db_path: str, command_name: str, last_used_at: datetime) -> None:
    logger.info(f"Updating cooldown for command={command_name} in database at {db_path}")
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_command_cooldowns_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO command_cooldowns (command_name, last_used_at)
                VALUES (?, ?)
                ON CONFLICT(command_name) DO UPDATE SET last_used_at = excluded.last_used_at
                """,
                (command_name, last_used_at.isoformat()),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error updating cooldown for command={command_name} in database at {db_path}: {str(e)}")

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
