# migration database

Environment variables:
```bash
MIGRATION=true
DB_BACKUP_PATH=users_backup.sqlite
DB_PATH=users.sqlite
ADMINS_IDS=<tg_id>[,<tg_id>...]
TELEGRAM_BOT_TOKEN=<bot_token>
```

How to run:
```bash
python3 -m db.migration
```
After a successful migration admins will be notified, `COLLECT_IDS=true` is appended
to the `.env` file, and the bot will begin collecting real Telegram IDs and updating
them in the DB. When every row has a real (positive) `user_id`, `COLLECT_IDS=false`
is written back to `.env` automatically.
