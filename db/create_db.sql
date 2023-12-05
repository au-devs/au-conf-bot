-- Script for create empty users database
-- String: Name
-- String: tg_username
-- Date: birthday
-- String: wishlist url
-- Boolean: moneyGifts
-- Boolean: funnyGifts

CREATE TABLE users (
    tg_username VARCHAR(255) NOT NULL PRIMARY KEY,
    name VARCHAR(255) NULL,
    birthday DATE NULL,
    wishlist_url VARCHAR(255) NULL,
    money_gifts BOOLEAN NULL,
    funny_gifts BOOLEAN NULL
);