# user_manager.py
from models.user import User


def create_user(user_data: dict) -> 'User':
    """
    Create a new User instance from a user_data telegram dictionary.
    :param user_data:
    :return:
    """
    return User(name=user_data['name'], tg_username=user_data['tg_username'],
                birthday=user_data['birthday'], wishlist_url=user_data['wishlist_url'],
                money_gifts=user_data['money_gifts'], funny_gifts=user_data['funny_gifts'])


def update_user_fields(user: User, updated_data: dict) -> None:
    """
    Update specific fields of an existing User.

    :param user: The User instance to update.
    :param updated_data: A dictionary containing the updated data.
    """
    for field, value in updated_data.items():
        setattr(user, field, value)
