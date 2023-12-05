# user.py
from typing import Optional


class User:
    def __init__(self, name: str, tg_username: str, birthday: Optional[str], wishlist_url: Optional[str],
                 money_gifts: Optional[bool], funny_gifts: Optional[bool]):
        self.name = name
        self.tg_username = tg_username
        self.birthday = birthday
        self.wishlist_url = wishlist_url
        self.money_gifts = money_gifts
        self.funny_gifts = funny_gifts

    def __repr__(self):
        return f"User(name={self.name}, tg_username={self.tg_username}, " \
               f"birthday={self.birthday}, wishlist_url={self.wishlist_url}, " \
               f"money_gifts={self.money_gifts}, funny_gifts={self.funny_gifts})"
