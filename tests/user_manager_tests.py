import unittest
import datetime
from models.user_manager import create_user, is_near_birthday


class TestUserManager(unittest.TestCase):
    def test_is_near_birthday(self):
        today = datetime.date.today().strftime('%d.%m.%Y')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%d.%m.%Y')
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
        two_months_from_today = (datetime.date.today() + datetime.timedelta(days=60)).strftime('%d.%m.%Y')

        test_user = create_user({'name': 'Test User', 'tg_username': '@test_user', 'birthday': today,
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        test_user2 = create_user({'name': 'Test User2', 'tg_username': '@test_user2', 'birthday': yesterday,
                                  'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        test_user3 = create_user({'name': 'Test User3', 'tg_username': '@test_user3', 'birthday': tomorrow,
                                  'wishlist_url': 'https://example3.com', 'money_gifts': False, 'funny_gifts': False})
        test_user4 = create_user({'name': 'Test User4', 'tg_username': '@test_user4', 'birthday': two_months_from_today,
                                  'wishlist_url': 'https://example4.com', 'money_gifts': True, 'funny_gifts': True})

        self.assertTrue(is_near_birthday(test_user))
        self.assertFalse(is_near_birthday(test_user2))
        self.assertTrue(is_near_birthday(test_user3))
        self.assertFalse(is_near_birthday(test_user4))


if __name__ == '__main__':
    unittest.main()
