from typing import Optional
import psycopg2
from core.database import db_manager
from core.exceptions import ConflictError
from models.user import User
from models.repositories.base import IUserRepository

class PostgresUserRepository(IUserRepository):
    """PostgreSQL implementation of IUserRepository."""

    def get_by_id(self, user_id: int) -> Optional[User]:
        query = "SELECT id, name, email, password_hash, role, is_active, created_at FROM users WHERE id = %s;"
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return User(**row)

    def get_by_email(self, email: str) -> Optional[User]:
        query = "SELECT id, name, email, password_hash, role, is_active, created_at FROM users WHERE LOWER(email) = LOWER(%s);"
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, (email,))
            row = cursor.fetchone()
            if not row:
                return None
            return User(**row)

    def create(self, user: User) -> User:
        query = """
            INSERT INTO users (name, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at;
        """
        try:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute(query, (user.name, user.email.lower(), user.password_hash, user.role, user.is_active))
                res = cursor.fetchone()
                user.id = res["id"]
                user.created_at = res["created_at"]
                return user
        except psycopg2.errors.UniqueViolation as error:
            raise ConflictError("Este e-mail já está cadastrado no sistema.") from error

    def count(self) -> int:
        query = "SELECT COUNT(*) as total FROM users;"
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query)
            res = cursor.fetchone()
            return res["total"] if res else 0

    def list_all(self):
        query = """
            SELECT id, name, email, password_hash, role, is_active, created_at
            FROM users ORDER BY name, id;
        """
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query)
            return [User(**row) for row in cursor.fetchall()]

    def update(self, user: User) -> User:
        query = """
            UPDATE users
            SET name = %s, email = %s, password_hash = %s, role = %s, is_active = %s
            WHERE id = %s
            RETURNING id, name, email, password_hash, role, is_active, created_at;
        """
        try:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute(query, (
                    user.name, user.email.lower(), user.password_hash, user.role, user.is_active, user.id
                ))
                row = cursor.fetchone()
                return User(**row) if row else None
        except psycopg2.errors.UniqueViolation as error:
            raise ConflictError("Este e-mail já está cadastrado no sistema.") from error

    def delete(self, user_id: int) -> bool:
        with db_manager.get_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s RETURNING id;", (user_id,))
            return cursor.fetchone() is not None
