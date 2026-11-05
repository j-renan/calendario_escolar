import json
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from config import Config

class DatabaseManager:
    """
    Singleton Database Manager managing connection pooling for PostgreSQL.
    Adheres to Single Responsibility Principle (SRP) for DB lifecycle.
    """
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_pool()
        return cls._instance

    def _init_pool(self):
        params = Config.get_db_connection_params()
        self._pool = SimpleConnectionPool(
            minconn=1,
            maxconn=20,
            **params
        )

    @contextmanager
    def get_connection(self):
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit=True):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def init_schema(self):
        """Initializes tables if they do not exist."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(180) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'coordenador',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
            """,
            """
            UPDATE users SET role = 'diretor' WHERE LOWER(role) = 'admin';
            """,
            """
            CREATE TABLE IF NOT EXISTS course_categories (
                id SERIAL PRIMARY KEY,
                code VARCHAR(140) UNIQUE NOT NULL,
                name VARCHAR(120) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key VARCHAR(120) PRIMARY KEY,
                value TEXT NOT NULL
            );
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_course_categories_name
            ON course_categories (LOWER(name));
            """,
            """
            CREATE TABLE IF NOT EXISTS calendars (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL DEFAULT 'CALENDÁRIO ESCOLAR',
                unit_code VARCHAR(50) NOT NULL DEFAULT 'CFP 5.10',
                semester_year VARCHAR(50) NOT NULL DEFAULT '2º / 2026',
                status VARCHAR(30) NOT NULL DEFAULT 'rascunho',
                version VARCHAR(50) NOT NULL DEFAULT 'Versão 01 - 06/10/2026',
                director_name VARCHAR(150) NOT NULL DEFAULT 'Tiago Roberto Ferreira',
                director_signature_status VARCHAR(50) DEFAULT 'Pendente',
                signature_date TIMESTAMP NULL,
                workload_note TEXT DEFAULT '* Ampliação da Jornada de trabalho',
                data_json JSONB NOT NULL,
                created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_calendars_semester_year
            ON calendars (semester_year);
            """,
            """
            CREATE TABLE IF NOT EXISTS calendar_history (
                id SERIAL PRIMARY KEY,
                calendar_id INTEGER REFERENCES calendars(id) ON DELETE CASCADE,
                action VARCHAR(100) NOT NULL,
                snapshot_json JSONB NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
        with self.get_cursor(commit=True) as cursor:
            for query in queries:
                cursor.execute(query)

    def get_setting(self, key):
        with self.get_cursor(commit=False) as cursor:
            cursor.execute("SELECT value FROM app_settings WHERE key = %s;", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    def set_setting(self, key, value):
        with self.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO app_settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
                """,
                (key, value)
            )

db_manager = DatabaseManager()
