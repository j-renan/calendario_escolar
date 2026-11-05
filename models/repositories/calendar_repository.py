import json
import psycopg2
from typing import Optional, List, Dict, Any
from datetime import datetime
from core.database import db_manager
from core.exceptions import ConflictError
from models.calendar import SchoolCalendar
from models.repositories.base import ICalendarRepository

class PostgresCalendarRepository(ICalendarRepository):
    """PostgreSQL implementation of ICalendarRepository."""

    def _row_to_entity(self, row: dict) -> SchoolCalendar:
        data_json = row.get("data_json", {})
        if isinstance(data_json, str):
            data_json = json.loads(data_json)

        categories = data_json.get("categories", [])
        months = data_json.get("months", [])
        compensations = data_json.get("compensations", [])

        signature_date_val = row.get("signature_date")
        if isinstance(signature_date_val, datetime):
            signature_date_val = signature_date_val.strftime("%d/%m/%Y %H:%M:%S")

        return SchoolCalendar(
            id=row["id"],
            title=row["title"],
            unit_code=row["unit_code"],
            semester_year=row["semester_year"],
            status=row["status"],
            version=row["version"],
            director_name=row["director_name"],
            director_signature_status=row["director_signature_status"],
            signature_date=signature_date_val,
            signature_hash=data_json.get("signature_hash"),
            workload_note=row["workload_note"],
            categories=categories,
            months=months,
            compensations=compensations,
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def get_by_id(self, calendar_id: int) -> Optional[SchoolCalendar]:
        query = """
            SELECT id, title, unit_code, semester_year, status, version,
                   director_name, director_signature_status, signature_date,
                   workload_note, data_json, created_by, updated_at, created_at
            FROM calendars
            WHERE id = %s;
        """
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, (calendar_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def get_latest(self) -> Optional[SchoolCalendar]:
        query = """
            SELECT id, title, unit_code, semester_year, status, version,
                   director_name, director_signature_status, signature_date,
                   workload_note, data_json, created_by, updated_at, created_at
            FROM calendars
            ORDER BY id DESC
            LIMIT 1;
        """
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_entity(row)

    def get_by_period(self, semester_year: str) -> Optional[SchoolCalendar]:
        query = """
            SELECT id, title, unit_code, semester_year, status, version,
                   director_name, director_signature_status, signature_date,
                   workload_note, data_json, created_by, updated_at, created_at
            FROM calendars WHERE semester_year = %s LIMIT 1;
        """
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, (semester_year,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def create(self, calendar: SchoolCalendar) -> SchoolCalendar:
        query = """
            INSERT INTO calendars (
                title, unit_code, semester_year, status, version,
                director_name, director_signature_status, signature_date,
                workload_note, data_json, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at, updated_at;
        """
        data_payload = {
            "categories": calendar.categories,
            "months": calendar.months,
            "compensations": calendar.compensations,
            "signature_hash": calendar.signature_hash
        }
        sig_date = datetime.strptime(calendar.signature_date, "%d/%m/%Y %H:%M:%S") if calendar.signature_date else None

        try:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute(query, (
                    calendar.title,
                    calendar.unit_code,
                    calendar.semester_year,
                    calendar.status,
                    calendar.version,
                    calendar.director_name,
                    calendar.director_signature_status,
                    sig_date,
                    calendar.workload_note,
                    json.dumps(data_payload),
                    calendar.created_by
                ))
                res = cursor.fetchone()
                calendar.id = res["id"]
                calendar.created_at = res["created_at"]
                calendar.updated_at = res["updated_at"]
                return calendar
        except psycopg2.errors.UniqueViolation as error:
            raise ConflictError(f"Já existe um calendário para {calendar.semester_year}.") from error

    def update(self, calendar: SchoolCalendar) -> SchoolCalendar:
        query = """
            UPDATE calendars
            SET title = %s,
                unit_code = %s,
                semester_year = %s,
                status = %s,
                version = %s,
                director_name = %s,
                director_signature_status = %s,
                signature_date = %s,
                workload_note = %s,
                data_json = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING updated_at;
        """
        data_payload = {
            "categories": calendar.categories,
            "months": calendar.months,
            "compensations": calendar.compensations,
            "signature_hash": calendar.signature_hash
        }
        sig_date = datetime.strptime(calendar.signature_date, "%d/%m/%Y %H:%M:%S") if calendar.signature_date else None

        with db_manager.get_cursor(commit=True) as cursor:
            cursor.execute(query, (
                calendar.title,
                calendar.unit_code,
                calendar.semester_year,
                calendar.status,
                calendar.version,
                calendar.director_name,
                calendar.director_signature_status,
                sig_date,
                calendar.workload_note,
                json.dumps(data_payload),
                calendar.id
            ))
            res = cursor.fetchone()
            if res:
                calendar.updated_at = res["updated_at"]
            return calendar

    def list_all(self) -> List[Dict[str, Any]]:
        query = """
            SELECT id, title, unit_code, semester_year, status, version,
                   director_name, director_signature_status, created_at, updated_at
            FROM calendars
            ORDER BY id DESC;
        """
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete(self, calendar_id: int) -> bool:
        with db_manager.get_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM calendars WHERE id = %s RETURNING id;", (calendar_id,))
            return cursor.fetchone() is not None

    def add_history(self, calendar_id: int, action: str, snapshot: dict, user_id: Optional[int]) -> int:
        query = """
            INSERT INTO calendar_history (calendar_id, action, snapshot_json, user_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        with db_manager.get_cursor(commit=True) as cursor:
            cursor.execute(query, (calendar_id, action, json.dumps(snapshot), user_id))
            res = cursor.fetchone()
            return res["id"]

    def get_history(self, calendar_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        query = """
            SELECT h.id, h.calendar_id, h.action, h.snapshot_json, h.created_at, u.name as user_name
            FROM calendar_history h
            LEFT JOIN users u ON h.user_id = u.id
            WHERE h.calendar_id = %s
            ORDER BY h.id DESC
            LIMIT %s;
        """
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, (calendar_id, limit))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("snapshot_json"), str):
                    item["snapshot_json"] = json.loads(item["snapshot_json"])
                if isinstance(item.get("created_at"), datetime):
                    item["created_at"] = item["created_at"].strftime("%d/%m/%Y %H:%M:%S")
                result.append(item)
            return result
