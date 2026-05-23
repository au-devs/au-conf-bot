# Season 1: гражданская война

Правила первого сезона зафиксированы по текущей реализации бота.

## Триггеры

- `гражданская война`
- `/civil_war`
- `/civil_war@au_conf_bot`

Команда `/civil-war` не является триггером.

## Cooldown

- Каждый пользователь может запускать гражданку не чаще одного раза в `CIVIL_WAR_COOLDOWN_HOURS`.
- Дефолт: `1` час.
- Cooldown хранится по `user_id` в `civil_war_cooldowns`.

## Шансы

- Обычная победа: `CIVIL_WAR_SUCCESS_CHANCE`.
- Дефолт: `0.0666` (`6.66%`).
- Редкая победа: `CIVIL_WAR_RARE_SUCCESS_CHANCE`.
- Дефолт: `0.00666` (`0.666%`).
- Runtime override задается админом через скрытые команды:
  `/set_civil_war_chance`, `/set_rare_civil_war_chance`, `/reset_civil_war_chances`.
- Персональных шансов для отдельных игроков в первом сезоне нет.

Rare входит в общий win-roll: если выпал rare, это также считается победой.

## Scoring

- Любой запуск после cooldown дает `+1` attempt.
- Fail дает `+0` successes.
- Обычная победа дает `+1` success.
- Rare victory дает `+10` successes.
- В отображении failures считается как `max(attempts - successes, 0)`.

## Картинки

Все картинки берутся из `ASSETS_DIR`.

- Fail: `fail.jpg`
- Обычная победа: `civilwar.jpg`
- Rare victory: `rare.jpg`

Дефолтный `ASSETS_DIR`: `/data/assets`.

## Сообщения

- Fail отправляется в текущий топик.
- Обычная победа отправляется в general topic.
- Rare victory отправляется в general topic.
- Подпись обычной победы: `<username> устроил гражданскую войну`.
- Подпись rare victory: `<username> <RARE_CIVIL_WAR_CAPTION_TEMPLATE>`.
- Дефолт `RARE_CIVIL_WAR_CAPTION_TEMPLATE`: `налудил себе +10 винов`.

Если у пользователя нет username, используется HTML mention по `tg://user?id=<user_id>`.

## Личная статистика

Команда:

- `/how_much_civil_war`
- `/how-much-civil-war`

Формат:

```text
Пытался устроить войну = attempts
Спровоцировал гражданскую войну = successes
Мастурбировал = max(attempts - successes, 0)
Винрейт = successes / attempts * 100
```

## Leaderboard

Команда `/stats` показывает текущий активный сезон, то есть текущую таблицу `civil_war_stats`.

Перед выводом `/stats` бот:

- пытается дозаполнить missing display names через Telegram `get_chat_member`;
- создает placeholder-профили в `users` для участников, которых нет в `users`.

Сортировка leaderboard:

```text
adjusted_winrate DESC,
winrate DESC,
successes DESC,
attempts DESC
```

Формула рейтинга:

```text
adjusted_winrate = (successes + 100 * 0.0666) / (attempts + 100)
```

Также выводится отдельная строка худшего рейтинга по `adjusted_winrate ASC`.

## Seasons

Сезон сохраняется как snapshot leaderboard в:

- `civil_war_seasons`
- `civil_war_season_entries`

`/save_civil_war_season <name>` сохраняет snapshot без сброса текущей статистики.

`/start_civil_war_season <name>`:

- сохраняет текущий leaderboard как завершенный сезон;
- очищает `civil_war_stats`;
- новый `/stats` начинает считаться с нуля.
