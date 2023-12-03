# au-conf-bot

Environment variables (from .env file)
```bash
TELEGRAM_BOT_TOKEN=<YOUR TOKEN>
ADMINS=<ADMIN1_TG_NAME>,<ADMIN2_TG_NAME>
DB_PATH=users.sqlite
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