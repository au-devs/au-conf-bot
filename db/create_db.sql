-- Script for create empty users database
-- String: Name
-- String: tg_username
-- Date: birthday
-- String: wishlist url
-- Boolean: moneyGifts
-- Boolean: funnyGifts

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER NOT NULL PRIMARY KEY,
    tg_username VARCHAR(255) NULL,
    name VARCHAR(255) NULL,
    birthday DATE NULL,
    wishlist_url VARCHAR(255) NULL,
    money_gifts BOOLEAN NULL,
    funny_gifts BOOLEAN NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    user_id INTEGER NOT NULL PRIMARY KEY,
    reminder_14_days BOOLEAN NOT NULL DEFAULT 0,
    reminder_7_days BOOLEAN NOT NULL DEFAULT 0,
    reminder_1_days BOOLEAN NOT NULL DEFAULT 0,
    birthday_today BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);
