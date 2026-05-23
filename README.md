# au-conf-bot

Environment variables (from .env file)
```bash
TELEGRAM_BOT_TOKEN=<YOUR TOKEN>
ADMINS_IDS=<ADMIN1_TG_ID>,<ADMIN2_TG_ID>
DB_PATH=users.sqlite
ASSETS_DIR=/data/assets
CIVIL_WAR_COOLDOWN_HOURS=1
STATS_COOLDOWN_HOURS=3
CIVIL_WAR_SUCCESS_CHANCE=0.0666
CIVIL_WAR_RARE_SUCCESS_CHANCE=0.00666
CIVIL_WAR_RARE_LOSS_CHANCE=0.0133
CIVIL_WAR_MAFIA_EVENT_CHANCE=0.0888
CIVIL_WAR_RAT_EVENT_CHANCE=0.015
RARE_CIVIL_WAR_CAPTION_TEMPLATE=съел сладкий пирог, +10 винов
RARE_FAIL_CIVIL_WAR_CAPTION_TEMPLATE=словил редкое поражение: -1 вин
RAT_CIVIL_WAR_CAPTION_TEMPLATE=забрал крысиный банк: +{points} винов
```

Assets in ASSETS_DIR:
```bash
civilwar.jpg
fail.jpg
rare.jpg
rare_fail.jpg
rat.jpg
mafia.jpg
rat_choice.jpg
```

Asset formats:
```bash
.jpg
.jpeg
.png
.webp
.gif
```

The bot resolves assets by basename. For example, `rare.gif` can be used instead of `rare.jpg`.

Daily stats schedule:
```bash
06:00 UTC
11:00 Asia/Yekaterinburg
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
/civil_war - civil war roll
/how_much_civil_war - personal civil war stats
/stats - global civil war stats, admin only in season 2
/help-admin - hidden admin help in private chat
/civil_war_config - hidden admin chance config menu in private chat
/save_civil_war_season <name> - save current leaderboard as season
/start_civil_war_season <name> - save current leaderboard and reset active stats
/civil_war_seasons - list saved seasons
/civil_war_season_stats <season_id|name> - show saved season stats
```
