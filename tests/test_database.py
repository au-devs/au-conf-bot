import unittest
import os
from db.database import create_database, add_user, get_db_users, get_db_tables


class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Создаем тестовую базу перед каждым тестом
        self.db_path = 'users_test.sqlite'
        create_database(self.db_path)

    def tearDown(self):
        # Удаляем тестовую базу после каждого теста
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_and_get_users(self):
        # Добавляем три пользователя
        add_user(self.db_path, "@user1")
        add_user(self.db_path, "@user2")
        add_user(self.db_path, "@user3")

        # Получаем список пользователей
        users = get_db_users(self.db_path)

        # Проверяем, что три пользователя добавлены
        self.assertEqual(len(users), 3)

        # Проверяем, что имена пользователей соответствуют ожидаемым
        expected_usernames = ["@user1", "@user2", "@user3"]
        for user, expected_username in zip(users, expected_usernames):
            self.assertEqual(user[2], expected_username)

    def test_sql_injection_attempt(self):
        # Попытка SQL-инъекции
        sql_injection_attempt = "user1'); DROP TABLE users; --"

        # Пытаемся добавить пользователя с подозрительным именем
        add_user(self.db_path, sql_injection_attempt)

        # Проверяем, что таблица users не была удалена
        tables = get_db_tables(self.db_path)
        self.assertIn(('users',), tables)

        # Проверяем, что файл базы данных существует
        self.assertTrue(os.path.exists(self.db_path))


if __name__ == '__main__':
    unittest.main()
