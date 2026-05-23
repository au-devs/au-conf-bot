-- Script for create empty users database
-- Integer: user_id
-- String: Name
-- String: tg_username
-- Date: birthday
-- String: wishlist url
-- Boolean: moneyGifts
-- Boolean: funnyGifts

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NULL,
    tg_username VARCHAR(255) NULL,
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
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS civil_war_cooldowns (
    user_id INTEGER NOT NULL PRIMARY KEY,
    last_used_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS civil_war_stats (
    user_id INTEGER NOT NULL PRIMARY KEY,
    display_name VARCHAR(255) NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS command_cooldowns (
    command_name VARCHAR(255) NOT NULL PRIMARY KEY,
    last_used_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS civil_war_chance_overrides (
    config_key VARCHAR(255) NOT NULL PRIMARY KEY,
    chance REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS civil_war_seasons (
    season_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    created_at TEXT NOT NULL
);

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
);
