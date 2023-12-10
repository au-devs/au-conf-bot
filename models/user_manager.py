# user_manager.py
import datetime
from models.user import User


def create_user(user_data: dict) -> User:
    """
    Create a new User instance from a user_data telegram dictionary.
    :param user_data:
    :return:
    """
    return User(name=user_data['name'], tg_username=user_data['tg_username'],
                birthday=user_data['birthday'], wishlist_url=user_data['wishlist_url'],
                money_gifts=bool(user_data['money_gifts']), funny_gifts=bool(user_data['funny_gifts']))


def update_user_fields(user: User, updated_data: dict) -> None:
    """
    Update specific fields of an existing User.

    :param user: The User instance to update.
    :param updated_data: A dictionary containing the updated data.
    """
    for field, value in updated_data.items():
        setattr(user, field, value)


def is_near_birthday(user: User) -> bool:
    """
    Check if the user's birthday is within 14 days from now

    :param user: The User instance to check
    :return: True if the user's birthday is within 14 days from now, False otherwise
    """
    birthday = user.birthday
    today = datetime.date.today()
    birthday_day = birthday.split('.')[0]
    birthday_month = birthday.split('.')[1]
    birthday_date = datetime.date(today.year, int(birthday_month), int(birthday_day))

    return 14 >= (today - birthday_date).days >= 0
