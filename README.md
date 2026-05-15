# au-conf-bot

Environment variables (from .env file)
```bash
TELEGRAM_BOT_TOKEN=<YOUR TOKEN>
ADMINS_IDS=<ADMIN1_TG_ID>,<ADMIN2_TG_ID>
DB_PATH=users.sqlite
ASSETS_DIR=/data/assets
CIVIL_WAR_COOLDOWN_HOURS=1
STATS_COOLDOWN_HOURS=3
```

How to run:
```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Available commands:
```
/start - start bot
/new_database - create new database (if you are admin)
```
