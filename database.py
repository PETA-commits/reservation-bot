import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_file="clients.db"):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """Создание таблицы clients"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                reserved_by TEXT,
                reserved_by_url TEXT,
                reserved_at TEXT,
                UNIQUE(platform, username)
            )
        ''')
        conn.commit()
        conn.close()

    def add_client(self, platform, username, url):
        """Добавление нового клиента"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO clients (platform, username, url)
                VALUES (?, ?, ?)
            ''', (platform, username, url))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def check_client(self, platform, username):
        """Проверка, существует ли клиент и занят ли он"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM clients 
            WHERE platform = ? AND username = ?
        ''', (platform, username))
        result = cursor.fetchone()
        conn.close()
        return result

    def reserve_client(self, platform, username, reserved_by, reserved_by_url):
        """Бронирование клиента"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE clients 
            SET reserved_by = ?, reserved_by_url = ?, reserved_at = ?
            WHERE platform = ? AND username = ? AND reserved_by IS NULL
        ''', (reserved_by, reserved_by_url, datetime.now().isoformat(), platform, username))

        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False

    def get_all_clients(self):
        """Получение всех клиентов (для статистики)"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients ORDER BY reserved_at DESC')
        result = cursor.fetchall()
        conn.close()
        return resultpasfc