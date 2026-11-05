from typing import Optional

import psycopg2

from core.database import db_manager
from core.exceptions import ConflictError
from models.repositories.base import ICategoryRepository


class PostgresCategoryRepository(ICategoryRepository):
    def list_all(self, active_only: bool = False):
        query = """
            SELECT id, code, name, is_active, created_at, updated_at
            FROM course_categories
        """
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name, id;"
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_by_id(self, category_id: int) -> Optional[dict]:
        query = """
            SELECT id, code, name, is_active, created_at, updated_at
            FROM course_categories WHERE id = %s;
        """
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, (category_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create(self, code: str, name: str) -> dict:
        query = """
            INSERT INTO course_categories (code, name)
            VALUES (%s, %s)
            RETURNING id, code, name, is_active, created_at, updated_at;
        """
        try:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute(query, (code, name))
                return dict(cursor.fetchone())
        except psycopg2.errors.UniqueViolation as error:
            raise ConflictError("Já existe uma categoria com este nome ou código.") from error

    def update(self, category_id: int, name: str, is_active: bool) -> Optional[dict]:
        query = """
            UPDATE course_categories
            SET name = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, code, name, is_active, created_at, updated_at;
        """
        try:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute(query, (name, is_active, category_id))
                row = cursor.fetchone()
                return dict(row) if row else None
        except psycopg2.errors.UniqueViolation as error:
            raise ConflictError("Já existe uma categoria com este nome.") from error

    def delete(self, category_id: int) -> bool:
        with db_manager.get_cursor(commit=True) as cursor:
            cursor.execute(
                "DELETE FROM course_categories WHERE id = %s RETURNING id;",
                (category_id,)
            )
            return cursor.fetchone() is not None
