--- SQL script for migration old DB with username primary key to apply new logic with user_id primary key

BEGIN TRANSACTION;

ALTER TABLE users RENAME TO users_old;
ALTER TABLE reminders RENAME TO reminders_old;

CREATE TABLE users (
    user_id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NULL,
    tg_username VARCHAR(255) NULL,
    birthday DATE NULL,
    wishlist_url VARCHAR(255) NULL,
    money_gifts BOOLEAN NULL,
    funny_gifts BOOLEAN NULL
);

CREATE TABLE reminders (
    user_id INTEGER NOT NULL PRIMARY KEY,
    reminder_14_days BOOLEAN NOT NULL DEFAULT 0,
    reminder_7_days BOOLEAN NOT NULL DEFAULT 0,
    reminder_1_days BOOLEAN NOT NULL DEFAULT 0,
    birthday_today BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON UPDATE CASCADE
);

INSERT INTO users (name, tg_username, birthday, wishlist_url, money_gifts, funny_gifts)
SELECT name, tg_username, birthday, wishlist_url, money_gifts, funny_gifts
FROM users_old
ORDER BY tg_username;

INSERT INTO reminders (reminder_14_days, reminder_7_days, reminder_1_days, birthday_today)
SELECT reminder_14_days, reminder_7_days, reminder_1_days, birthday_today
FROM reminders_old;

DROP TABLE users_old;
DROP TABLE reminders_old;

COMMIT;