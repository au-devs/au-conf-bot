# Season 2: Mafia Civil War

## Eligibility

Only verified users participate in Season 2 leaderboard and private seasonal events.

A verified user must satisfy both conditions:

- The user exists in the `users` table.
- The user has sent `/start` to the bot in private chat.

If a seasonal private event drops for a non-verified user, the event is burned and the bot explicitly says that the user has not sent `/start` to the bot in private chat or has not filled the profile.

## Standard Events

Each civil war roll has a cooldown controlled by `CIVIL_WAR_COOLDOWN_HOURS`.

Roll priority:

1. Rare win
2. Rare loss
3. Mafia event
4. Rat event
5. Normal win
6. Loss

Events:

- Normal win: `+1` win.
- Rare win: `+10` wins.
- Loss: `0` wins.
- Rare loss: `-1` win, clamped at zero total wins.

Default chances:

- `CIVIL_WAR_SUCCESS_CHANCE=0.0666`
- `CIVIL_WAR_RARE_SUCCESS_CHANCE=0.00666`
- `CIVIL_WAR_RARE_LOSS_CHANCE=0.0133`
- `CIVIL_WAR_MAFIA_EVENT_CHANCE=0.0888`
- `CIVIL_WAR_RAT_EVENT_CHANCE=0.015`
- `RARE_FAIL_CIVIL_WAR_CAPTION_TEMPLATE=словил редкое поражение: -1 вин`

All chances can be overridden at runtime by the admin via `/civil_war_config` in private chat.

Rare loss sends `rare_fail.jpg` from `ASSETS_DIR`.

## Mafia Event

When the mafia event drops for a verified user, the bot sends a private message to that user.

The user chooses one action:

- Attack another verified leaderboard participant: target receives pending `-1` win.
- Protect themselves: protection blocks one pending `-1` win against that user.

Attack target selection is private. The bot sends the current verified leaderboard to the user, and the user replies with target username or user id.

Mafia attacks and protections are not applied immediately. They are stored until the next `/stats` run or scheduled daily stats run.

At stats time:

- If nobody receives damage, append: `Город просыпается, сегодня никто не умер`
- If users receive damage, append: `Город просыпается, но [список пользователей] нежданули на -N вин`
- If protection reduces or blocks damage, the stats message explicitly mentions the protected user and the reduced or blocked damage.

Damage is clamped at zero total wins.

## Rat Event

When the rat event drops for a verified user, the bot sends a private message to that user.

The user chooses one action:

- Take the current rat bank immediately.
- Pass the rat bank forward, increasing it by `+2`.

The rat bank starts at `1`.

If the user takes the bank:

- The user receives the current rat bank as wins.
- The bot sends `rat.jpg` from `ASSETS_DIR`.
- Caption is controlled by `RAT_CIVIL_WAR_CAPTION_TEMPLATE`.
- The rat bank resets to `1`.

If the user passes the bank:

- The rat bank increases by `2`.
- The next normal win receives the accumulated rat bank bonus.
- After a normal win takes the rat bank, it resets to `1`.

## Stats

`/stats` can be called only by an admin or by the scheduled job.

Regular users cannot call `/stats`, because mafia attacks and protections must stay hidden until the stats moment.

Stats apply pending mafia results before rendering the leaderboard.

Daily stats schedule:

- `11:00 Asia/Yekaterinburg`
- `06:00 UTC`

Only users from the `users` table are included in the active leaderboard.
