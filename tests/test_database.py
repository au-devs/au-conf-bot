import unittest
import db.database as db
from models.user_manager import create_user


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.db_path = 'users_test.sqlite'
        db.create_database(self.db_path)

    def tearDown(self):
        self.db_path = 'users_test.sqlite'
        db.clear_database(self.db_path)

    def test_add_user(self):
        test_user = create_user({'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        test_user2 = create_user({'name': 'Test User2', 'tg_username': '@test_user2', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        test_user3 = create_user({'name': 'Test User3', 'tg_username': '@test_user3', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example3.com', 'money_gifts': False, 'funny_gifts': False})
        db.add_user(self.db_path, test_user)
        db.add_user(self.db_path, test_user2)
        db.add_user(self.db_path, test_user3)
        users = db.get_db_users(self.db_path)
        self.assertEqual(len(users), 3)
        self.assertIn(test_user, users)
        self.assertIn(test_user2, users)
        self.assertIn(test_user3, users)

    def test_update_user(self):
        test_user = create_user({'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        users = db.get_db_users(self.db_path)
        self.assertEqual(len(users), 1)
        self.assertIn(test_user, users)
        updated_user = create_user({'name': 'Updated User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                    'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        db.update_user(self.db_path, updated_user)
        users = db.get_db_users(self.db_path)
        self.assertEqual(len(users), 1)
        self.assertIn(updated_user, users)
        self.assertNotIn(test_user, users)


if __name__ == '__main__':
    unittest.main()
