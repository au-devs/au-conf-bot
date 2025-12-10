# migration database 

Environment variables:
```bash
MIGRATION=true
DB_BACKUP_PATH=users_backup.sqlite
DB_PATH=users.sqlite
ADMINS=<tg_id>
```

How to run:
```bash
python3 migration.py
```
After successful migration admins will be notified, bot will begin collecting telegram IDs and updating them in DB
