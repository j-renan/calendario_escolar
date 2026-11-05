import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration following 12-factor principles."""
    SECRET_KEY = os.getenv("SECRET_KEY", "senai-calendario-secret-key-2026-super-secure")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-calendario-auth-token-secret-2026")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRE_HOURS", "12")))
    
    # PostgreSQL Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "calendario_escolar")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
    PGSSLMODE = os.getenv("PGSSLMODE", "disable")
    PGCHANNELBINDING = os.getenv("PGCHANNELBINDING", "disable")
    
    @classmethod
    def get_db_connection_params(cls):
        if cls.DB_HOST == "localhost":
            return {
                "host": cls.DB_HOST,
                "port": cls.DB_PORT,
                "dbname": cls.DB_NAME,
                "user": cls.DB_USER,
                "password": cls.DB_PASSWORD,
                "sslmode": "disable",
                "channel_binding": "disable",
            }
        else:
            return {
                "host": cls.DB_HOST,
                "port": cls.DB_PORT,
                "dbname": cls.DB_NAME,
                "user": cls.DB_USER,
                "password": cls.DB_PASSWORD,
                "sslmode": cls.PGSSLMODE,
                "channel_binding": cls.PGCHANNELBINDING,
            }
