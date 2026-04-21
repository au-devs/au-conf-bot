# user_manager.py
import datetime
from models.user import User


def parse_bool_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value in {'да', 'true', '1', 'yes'}:
            return True
        if normalized_value in {'нет', 'false', '0', 'no'}:
            return False
    return bool(value)


def create_user(user_data: dict) -> User:
    """
    Create a new User instance from a user_data telegram dictionary.
    :param user_data:
    :return:
    """
    return User(user_id=user_data['user_id'], name=user_data['name'], tg_username=user_data['tg_username'],
                birthday=user_data['birthday'], wishlist_url=user_data['wishlist_url'],
                money_gifts=parse_bool_value(user_data['money_gifts']),
                funny_gifts=parse_bool_value(user_data['funny_gifts']))


def update_user_fields(user: User, updated_data: dict) -> None:
    """
    Update specific fields of an existing User.

    :param user: The User instance to update.
    :param updated_data: A dictionary containing the updated data.
    """
    for field, value in updated_data.items():
        setattr(user, field, value)


def get_closest_birthday(user: User) -> datetime.date:
    """
    Get the closest birthday of the user in the future

    :param user: The User instance to check
    :return: The closest birthday of the user in the future
    """
    birthday = user.birthday
    today = datetime.date.today()
    birthday_day = birthday.split('.')[0]
    birthday_month = birthday.split('.')[1]
    birthday_date = datetime.date(today.year, int(birthday_month), int(birthday_day))

    if birthday_date < today:
        birthday_date = datetime.date(today.year + 1, int(birthday_month), int(birthday_day))

    return birthday_date


def is_near_birthday(user: User) -> bool:
    """
    Check if the user's birthday is within 14 days from now

    :param user: The User instance to check
    :return: True if the user's birthday is within 14 days from now, False otherwise
    """
    today = datetime.date.today()

    return 14 >= (get_closest_birthday(user) - today).days >= 0
