import unittest
from datetime import datetime
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
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        test_user2 = create_user({'user_id': 2, 'name': 'Test User2', 'tg_username': '@test_user2', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        test_user3 = create_user({'user_id': 3, 'name': 'Test User3', 'tg_username': '@test_user3', 'birthday': '01.01.2000',
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
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        users = db.get_db_users(self.db_path)
        self.assertEqual(len(users), 1)
        self.assertIn(test_user, users)
        updated_user = create_user({'user_id': 1, 'name': 'Updated User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                    'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        db.update_user(self.db_path, 1, 'name', 'Updated User')
        users = db.get_db_users(self.db_path)
        self.assertEqual(len(users), 1)
        self.assertIn(updated_user, users)
        self.assertNotIn(test_user, users)

    def test_civil_war_cooldown_persistence(self):
        last_used_at = datetime(2026, 4, 21, 12, 0, 0)
        db.upsert_civil_war_last_used_at(self.db_path, 12345, last_used_at)

        saved_last_used_at = db.get_civil_war_last_used_at(self.db_path, 12345)

        self.assertEqual(saved_last_used_at, last_used_at)

    def test_civil_war_stats_persistence(self):
        db.update_civil_war_stats(self.db_path, 12345, False)
        db.update_civil_war_stats(self.db_path, 12345, True)
        db.update_civil_war_stats(self.db_path, 12345, False)

        attempts, successes = db.get_civil_war_stats(self.db_path, 12345)

        self.assertEqual(attempts, 3)
        self.assertEqual(successes, 1)

    def test_civil_war_leaderboard(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        test_user2 = create_user({'user_id': 2, 'name': 'Test User2', 'tg_username': '@test_user2', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        db.add_user(self.db_path, test_user2)
        db.update_civil_war_stats(self.db_path, 1, True)
        db.update_civil_war_stats(self.db_path, 1, False)
        db.update_civil_war_stats(self.db_path, 2, True)

        leaderboard = db.get_civil_war_leaderboard(self.db_path)

        self.assertEqual(leaderboard[0][0], 2)
        self.assertEqual(leaderboard[0][1], '@test_user2')
        self.assertEqual(leaderboard[0][2], 1)
        self.assertEqual(leaderboard[0][3], 1)
        self.assertEqual(leaderboard[1][0], 1)

    def test_civil_war_leaderboard_includes_low_sample_users(self):
        leader = create_user({'user_id': 1, 'name': 'Leader', 'tg_username': '@leader', 'birthday': '01.01.2000',
                              'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        contender = create_user({'user_id': 2, 'name': 'Contender', 'tg_username': '@contender', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        outlier = create_user({'user_id': 3, 'name': 'Outlier', 'tg_username': '@outlier', 'birthday': '01.01.2000',
                               'wishlist_url': 'https://example3.com', 'money_gifts': False, 'funny_gifts': False})
        db.add_user(self.db_path, leader)
        db.add_user(self.db_path, contender)
        db.add_user(self.db_path, outlier)
        for _ in range(150):
            db.update_civil_war_stats(self.db_path, 1, True)
        for _ in range(50):
            db.update_civil_war_stats(self.db_path, 1, False)
        for _ in range(75):
            db.update_civil_war_stats(self.db_path, 2, True)
            db.update_civil_war_stats(self.db_path, 2, False)
        for _ in range(2):
            db.update_civil_war_stats(self.db_path, 3, True)

        leaderboard = db.get_civil_war_leaderboard(self.db_path)

        self.assertEqual([row[0] for row in leaderboard], [1, 2, 3])

    def test_civil_war_lowest_winrate(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        test_user2 = create_user({'user_id': 2, 'name': 'Test User2', 'tg_username': '@test_user2', 'birthday': '01.01.2000',
                                  'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        db.add_user(self.db_path, test_user2)
        db.update_civil_war_stats(self.db_path, 1, True)
        db.update_civil_war_stats(self.db_path, 2, False)

        lowest_winrate = db.get_civil_war_lowest_winrate(self.db_path)

        self.assertEqual(lowest_winrate[0], 2)
        self.assertEqual(lowest_winrate[1], '@test_user2')
        self.assertEqual(lowest_winrate[2], 1)
        self.assertEqual(lowest_winrate[3], 0)

    def test_civil_war_lowest_winrate_includes_low_sample_users(self):
        leader = create_user({'user_id': 1, 'name': 'Leader', 'tg_username': '@leader', 'birthday': '01.01.2000',
                              'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        contender = create_user({'user_id': 2, 'name': 'Contender', 'tg_username': '@contender', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        outlier = create_user({'user_id': 3, 'name': 'Outlier', 'tg_username': '@outlier', 'birthday': '01.01.2000',
                               'wishlist_url': 'https://example3.com', 'money_gifts': False, 'funny_gifts': False})
        db.add_user(self.db_path, leader)
        db.add_user(self.db_path, contender)
        db.add_user(self.db_path, outlier)
        for _ in range(200):
            db.update_civil_war_stats(self.db_path, 1, True)
        db.update_civil_war_stats(self.db_path, 2, True)
        for _ in range(100):
            db.update_civil_war_stats(self.db_path, 2, False)
        for _ in range(2):
            db.update_civil_war_stats(self.db_path, 3, False)

        lowest_winrate = db.get_civil_war_lowest_winrate(self.db_path)

        self.assertEqual(lowest_winrate[0], 2)

    def test_command_cooldown_persistence(self):
        last_used_at = datetime(2026, 5, 15, 12, 0, 0)
        db.upsert_command_last_used_at(self.db_path, 'stats', last_used_at)

        saved_last_used_at = db.get_command_last_used_at(self.db_path, 'stats')

        self.assertEqual(saved_last_used_at, last_used_at)

    def test_reset_user_reminders(self):
        test_user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                                 'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, test_user)
        db.update_reminder(self.db_path, 1, '@test_user', 'reminder_14_days')
        db.update_reminder(self.db_path, 1, '@test_user', 'birthday_today')

        db.reset_user_reminders(self.db_path, 1, ['reminder_14_days'])

        self.assertFalse(db.get_reminder_status(self.db_path, 1, '@test_user', 'reminder_14_days'))
        self.assertTrue(db.get_reminder_status(self.db_path, 1, '@test_user', 'birthday_today'))


if __name__ == '__main__':
    unittest.main()
