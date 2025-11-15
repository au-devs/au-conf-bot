# util.py

def markdown_escape(text: str) -> str:
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_users_list(users: list) -> str:
    """Format users list into readable Markdown text"""
    if not users:
        return "Список пользователей пуст"
        
    result = "*Список пользователей:*\n\n"
    for user in users:
        money_gifts = 'Да' if user.money_gifts else 'Нет'
        funny_gifts = 'Да' if user.funny_gifts else 'Нет'
        result += (
            f"*Telegram ID:* {markdown_escape(str(user.user_id))}\n"
            f"*Имя:* {markdown_escape(user.name)}\n"
            f"*Юзернейм:* {markdown_escape(user.tg_username)}\n"
            f"*Дата рождения:* {markdown_escape(user.birthday)}\n"
            f"*Вишлист:* {markdown_escape(user.wishlist_url)}\n"
            f"*Подарок деньгами:* {markdown_escape(money_gifts)}\n"
            f"*Рофляный подарок:* {markdown_escape(funny_gifts)}\n\n"
        )
    return result
