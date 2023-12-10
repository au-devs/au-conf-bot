import sqlite3
import unittest
import os
from db.database import create_database, add_user, get_db_users, clear_database
from models.user_manager import create_user


class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Создаем тестовую базу перед каждым тестом
        self.db_path = 'users_test.sqlite'
        create_database(self.db_path)

    def tearDown(self):
        self.db_path = 'users_test.sqlite'
        clear_database(self.db_path)

    def test_check_birthday(self):
        test_user = create_user({'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        test_user2 = create_user({'name': 'Test User2', 'tg_username': '@test_user2', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        test_user3 = create_user({'name': 'Test User3', 'tg_username': '@test_user3', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example3.com', 'money_gifts': False, 'funny_gifts': False})
        add_user(self.db_path, test_user)
        add_user(self.db_path, test_user2)
        add_user(self.db_path, test_user3)
        users = get_db_users(self.db_path)
        self.assertEqual(len(users), 3)


if __name__ == '__main__':
    unittest.main()
