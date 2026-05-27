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

    def test_clear_civil_war_stats(self):
        db.update_civil_war_stats(self.db_path, 12345, True)

        db.clear_civil_war_stats(self.db_path)

        self.assertEqual(db.get_civil_war_stats(self.db_path, 12345), (0, 0))
        self.assertEqual(db.get_civil_war_leaderboard(self.db_path), [])

    def test_civil_war_chance_override_persistence(self):
        db.upsert_civil_war_chance_override(self.db_path, 'global_rare', 0.42)

        self.assertEqual(db.get_civil_war_chance_override(self.db_path, 'global_rare'), 0.42)
        self.assertEqual(db.get_civil_war_chance_overrides(self.db_path), {'global_rare': 0.42})

        db.delete_civil_war_chance_overrides(self.db_path)

        self.assertIsNone(db.get_civil_war_chance_override(self.db_path, 'global_rare'))

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

    def test_civil_war_leaderboard_includes_stats_without_user_row(self):
        db.update_civil_war_stats(self.db_path, 12345, True, '@missing_user')

        leaderboard = db.get_civil_war_leaderboard(self.db_path)

        self.assertEqual(leaderboard, [])

    def test_civil_war_leaderboard_falls_back_to_user_id_without_display_name(self):
        db.update_civil_war_stats(self.db_path, 12345, True)

        leaderboard = db.get_civil_war_leaderboard(self.db_path)

        self.assertEqual(leaderboard, [])

    def test_create_missing_users_from_civil_war_stats(self):
        db.update_civil_war_stats(self.db_path, 12345, True, '@missing_user')

        db.create_missing_users_from_civil_war_stats(self.db_path)

        user = db.get_user(self.db_path, 12345)
        self.assertEqual(user[0], 12345)
        self.assertEqual(user[1], '-')
        self.assertEqual(user[2], '@missing_user')
        self.assertIsNone(user[3])
        self.assertEqual(user[4], 'я не заполнял профиль')
        self.assertEqual(user[5], 0)
        self.assertEqual(user[6], 0)

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

    def test_civil_war_lowest_winrate_includes_stats_without_user_row(self):
        db.update_civil_war_stats(self.db_path, 12345, False, '@missing_user')

        lowest_winrate = db.get_civil_war_lowest_winrate(self.db_path)

        self.assertIsNone(lowest_winrate)

    def test_civil_war_season_snapshot(self):
        winner = create_user({'user_id': 1, 'name': 'Winner', 'tg_username': '@winner', 'birthday': '01.01.2000',
                              'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        loser = create_user({'user_id': 2, 'name': 'Loser', 'tg_username': '@loser', 'birthday': '01.01.2000',
                             'wishlist_url': 'https://example2.com', 'money_gifts': False, 'funny_gifts': True})
        db.add_user(self.db_path, winner)
        db.add_user(self.db_path, loser)
        db.update_civil_war_stats(self.db_path, 1, True, '@winner')
        db.update_civil_war_stats(self.db_path, 2, False, '@loser')
        leaderboard = db.get_civil_war_leaderboard(self.db_path)

        season_id = db.create_civil_war_season(self.db_path, 'Season One', leaderboard)

        seasons = db.get_civil_war_seasons(self.db_path)
        season = db.get_civil_war_season_entries(self.db_path, str(season_id))
        self.assertEqual(seasons[0][0], season_id)
        self.assertEqual(seasons[0][1], 'Season One')
        self.assertEqual(season[0], season_id)
        self.assertEqual(season[1], 'Season One')
        self.assertEqual(len(season[3]), 2)
        self.assertEqual(season[3][0][2], '@winner')

    def test_command_cooldown_persistence(self):
        last_used_at = datetime(2026, 5, 15, 12, 0, 0)
        db.upsert_command_last_used_at(self.db_path, 'stats', last_used_at)

        saved_last_used_at = db.get_command_last_used_at(self.db_path, 'stats')

        self.assertEqual(saved_last_used_at, last_used_at)

    def test_verified_private_chat_requires_user_and_start(self):
        self.assertFalse(db.has_verified_private_chat(self.db_path, 1))
        db.mark_bot_private_chat_started(self.db_path, 1)
        self.assertFalse(db.has_verified_private_chat(self.db_path, 1))

        user = create_user({'user_id': 1, 'name': 'Test User', 'tg_username': '@test_user', 'birthday': '01.01.2000',
                            'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, user)

        self.assertTrue(db.has_verified_private_chat(self.db_path, 1))

    def test_process_mafia_daily_actions_applies_damage_after_protection(self):
        attacker = create_user({'user_id': 1, 'name': 'Attacker', 'tg_username': '@attacker', 'birthday': '01.01.2000',
                                'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        target = create_user({'user_id': 2, 'name': 'Target', 'tg_username': '@target', 'birthday': '01.01.2000',
                              'wishlist_url': 'https://example2.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, attacker)
        db.add_user(self.db_path, target)
        for _ in range(5):
            db.update_civil_war_stats(self.db_path, 2, True)
        db.add_mafia_daily_action(self.db_path, 1, 'attack', 2)
        db.add_mafia_daily_action(self.db_path, 1, 'attack', 2)
        db.add_mafia_daily_action(self.db_path, 2, 'protect')

        damaged, defended = db.process_mafia_daily_actions(self.db_path)

        self.assertEqual(damaged, [('@target', 1, 2, 1)])
        self.assertEqual(defended, [])
        self.assertEqual(db.get_civil_war_stats(self.db_path, 2), (5, 4))

    def test_process_mafia_daily_actions_does_not_repeat_processed_damage(self):
        attacker = create_user({'user_id': 1, 'name': 'Attacker', 'tg_username': '@attacker', 'birthday': '01.01.2000',
                                'wishlist_url': 'https://example1.com', 'money_gifts': True, 'funny_gifts': True})
        target = create_user({'user_id': 2, 'name': 'Target', 'tg_username': '@target', 'birthday': '01.01.2000',
                              'wishlist_url': 'https://example2.com', 'money_gifts': True, 'funny_gifts': True})
        db.add_user(self.db_path, attacker)
        db.add_user(self.db_path, target)
        for _ in range(3):
            db.update_civil_war_stats(self.db_path, 2, True)
        db.add_mafia_daily_action(self.db_path, 1, 'attack', 2)

        first_damaged, first_defended = db.process_mafia_daily_actions(self.db_path)
        second_damaged, second_defended = db.process_mafia_daily_actions(self.db_path)

        self.assertEqual(first_damaged, [('@target', 1, 1, 0)])
        self.assertEqual(first_defended, [])
        self.assertEqual(second_damaged, [])
        self.assertEqual(second_defended, [])
        self.assertEqual(db.get_civil_war_stats(self.db_path, 2), (3, 2))

    def test_rat_points_persistence(self):
        self.assertEqual(db.get_rat_points(self.db_path), 1)
        db.set_rat_points(self.db_path, 3)
        self.assertEqual(db.get_rat_points(self.db_path), 3)
        db.create_rat_pending(self.db_path, 1, 3, source_chat_id=-100, source_message_thread_id=77)
        self.assertEqual(db.get_rat_pending(self.db_path, 1), (3, -100, 77))
        self.assertEqual(db.get_rat_pending_points(self.db_path, 1), 3)
        db.delete_rat_pending(self.db_path, 1)
        self.assertIsNone(db.get_rat_pending_points(self.db_path, 1))

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
