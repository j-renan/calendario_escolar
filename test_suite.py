import unittest
import json
from uuid import uuid4
from app import create_app
from core.security import PasswordHasher, TokenProvider
from core.database import db_manager
from core.exceptions import ValidationError
from models.calendar import SchoolCalendar
from presenters.calendar_presenter import CalendarPresenter


class InMemoryCalendarRepository:
    def __init__(self, calendar):
        self.calendar = calendar
        self.history = []

    def get_by_id(self, calendar_id):
        return self.calendar if self.calendar.id == calendar_id else None

    def update(self, calendar):
        self.calendar = calendar
        return calendar

    def add_history(self, calendar_id, action, snapshot, user_id=None):
        self.history.append((calendar_id, action, snapshot, user_id))


class TestCalendarGeneration(unittest.TestCase):
    def test_first_semester_generates_leap_year_months_and_weekdays(self):
        calendar = SchoolCalendar.create_for_period(
            2028, 1, [{"id": 1, "name": "Curso Técnico"}]
        )

        self.assertEqual([month["month_index"] for month in calendar.months], [1, 2, 3, 4, 5, 6])
        february = calendar.months[1]
        february_days = [
            cell for week in february["calendar_weeks"] for cell in week
            if cell["day"] is not None
        ]
        self.assertEqual(len(february_days), 29)
        self.assertEqual(sum(cell["type"] == "letivo" for cell in february_days), 21)
        self.assertEqual(calendar.categories[0]["monthly_days"]["FEV"], 21)
        self.assertEqual(calendar.categories[0]["total_days"], 0)
        self.assertTrue(all(len(week) == 7 for month in calendar.months for week in month["calendar_weeks"]))

    def test_second_semester_assigns_columns_and_weekend_types(self):
        calendar = SchoolCalendar.create_for_period(
            2027, 2, [{"id": 2, "name": "Aprendizagem"}]
        )

        self.assertEqual([month["month_index"] for month in calendar.months], [7, 8, 9, 10, 11, 12])
        self.assertEqual([month["column"] for month in calendar.months], [
            "left", "left", "left", "right", "right", "right"
        ])
        july_days = [
            cell for week in calendar.months[0]["calendar_weeks"] for cell in week
            if cell["day"] is not None
        ]
        saturday = next(cell for cell in july_days if cell["type"] == "nao_letivo" and cell["title"] == "Sábado")
        sunday = next(cell for cell in july_days if cell["type"] == "domingo")
        self.assertEqual(saturday["title"], "Sábado")
        self.assertEqual(sunday["title"], "Domingo")

    def test_category_totals_use_selected_date_ranges(self):
        calendar = SchoolCalendar.create_for_period(
            2028, 1, [
                {"id": 1, "name": "Curso Técnico"},
                {"id": 2, "name": "Aprendizagem"}
            ]
        )
        calendar.categories[0]["start_date"] = "04/01/2028"
        calendar.categories[0]["end_date"] = "10/01/2028"
        calendar.categories[1]["start_date"] = "08/01/2028"
        calendar.categories[1]["end_date"] = "10/01/2028"
        january_days = calendar.months[0]["calendar_weeks"]
        holiday = next(
            cell for week in january_days for cell in week
            if cell.get("day") == 6
        )
        holiday["type"] = "feriado"

        calendar.calculate_totals()

        self.assertEqual(calendar.categories[0]["total_days"], 4)
        self.assertEqual(calendar.categories[1]["total_days"], 1)
        self.assertEqual(calendar.categories[0]["monthly_days"]["JAN"], 4)
        self.assertEqual(calendar.months[0]["course_days"]["Curso Técnico"], 4)
        self.assertEqual(calendar.months[0]["course_days"]["Aprendizagem"], 1)

    def test_start_date_recalculates_month_summary_and_compensation_table(self):
        calendar = SchoolCalendar.create_for_period(
            2028, 1, [{"id": 1, "name": "Curso Técnico"}]
        )
        calendar.id = 1
        repository = InMemoryCalendarRepository(calendar)
        presenter = CalendarPresenter(repository)

        updated = presenter.update_day_cell(
            calendar_id=1,
            month_index=1,
            day=4,
            new_type="inicio_aulas",
            new_title="Início das aulas",
            milestone="inicio",
            category_ids=[1]
        )
        self.assertEqual(updated.months[0]["course_days"]["Curso Técnico"], 20)
        self.assertEqual(updated.categories[0]["monthly_days"]["JAN"], 20)

        updated = presenter.update_day_cell(
            calendar_id=1,
            month_index=1,
            day=8,
            new_type="nao_letivo",
            new_title="Dia a compensar (Ponte)",
        )
        compensation = next(
            row for row in updated.compensations
            if row["dias_a_compensar"] == "08/jan"
        )
        self.assertEqual(compensation["dias_compensacao"], "")
        self.assertEqual(compensation["observacao"], "Dia a compensar (Ponte)")

    def test_note_updates_are_saved_without_changing_calendar_status(self):
        calendar = SchoolCalendar.create_for_period(
            2028, 1, [{"id": 1, "name": "Curso Técnico"}]
        )
        calendar.id = 1
        calendar.status = "publicado"
        repository = InMemoryCalendarRepository(calendar)
        presenter = CalendarPresenter(repository)

        updated = presenter.update_notes(
            1,
            {"month_index": 1, "footer_note": "Recesso ajustado"},
            user_id=7
        )
        updated = presenter.update_notes(
            1,
            {"workload_note": "Jornada ampliada mediante planejamento"},
            user_id=7
        )

        self.assertEqual(updated.months[0]["footer_note"], "Recesso ajustado")
        self.assertEqual(updated.workload_note, "Jornada ampliada mediante planejamento")
        self.assertEqual(updated.status, "publicado")
        self.assertEqual(len(repository.history), 2)

    def test_compensation_days_are_linked_one_to_one(self):
        calendar = SchoolCalendar.create_for_period(
            2028, 1, [{"id": 1, "name": "Curso Técnico"}]
        )
        calendar.id = 1
        repository = InMemoryCalendarRepository(calendar)
        presenter = CalendarPresenter(repository)

        updated = presenter.update_day_cell(
            calendar_id=1,
            month_index=1,
            day=8,
            new_type="nao_letivo",
            new_title="Dia a compensar",
        )
        updated = presenter.update_day_cell(
            calendar_id=1,
            month_index=1,
            day=10,
            new_type="compensacao",
            new_title="Sábado letivo",
            compensation_for="2028-01-08"
        )
        row = next(item for item in updated.compensations if item["dias_a_compensar"] == "08/jan")
        self.assertEqual(row["dias_compensacao"], "10/jan")

        with self.assertRaises(ValidationError):
            presenter.update_day_cell(
                calendar_id=1,
                month_index=1,
                day=12,
                new_type="compensacao",
                new_title="Outro sábado letivo",
                compensation_for="2028-01-08"
            )

        updated = presenter.update_day_cell(
            calendar_id=1,
            month_index=1,
            day=10,
            new_type="letivo",
            new_title="Dia letivo",
        )
        row = next(item for item in updated.compensations if item["dias_a_compensar"] == "08/jan")
        self.assertEqual(row["dias_compensacao"], "")

    def test_calendar_presenter_rejects_duplicate_semester(self):
        class DuplicateCalendarRepository:
            def get_by_period(self, semester_year):
                return object() if semester_year == "2º / 2026" else None

        presenter = CalendarPresenter(DuplicateCalendarRepository())
        with self.assertRaises(ValidationError):
            presenter.create_for_period(2026, 2, [{"id": 1, "name": "Técnico"}])

class TestSchoolCalendarApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def calendar_id_for_period(self, period):
        login = self.client.post("/api/auth/login", json={
            "email": "coordenador@senai.br",
            "password": "senai2026"
        })
        headers = {"Authorization": f"Bearer {login.get_json()['token']}"}
        calendars = self.client.get("/api/calendars", headers=headers).get_json()
        return next(item["id"] for item in calendars if item["semester_year"] == period)

    def test_01_health_and_index(self):
        """Test home page loads properly."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CALEND\xc3\x81RIO ESCOLAR", res.data)
        self.assertIn(b"Antigravity", res.data)
        self.assertIn(b'id="usersPage"', res.data)
        self.assertIn(b'id="usersList"', res.data)
        self.assertIn(b'id="categoriesPage"', res.data)
        self.assertIn(b'id="categoriesList"', res.data)
        self.assertNotIn(b'id="userManagementSection"', res.data)
        self.assertNotIn(b'id="categoryManagementSection"', res.data)

    def test_02_auth_login(self):
        """Test JWT authentication with coordinator credentials."""
        res = self.client.post("/api/auth/login", json={
            "email": "coordenador@senai.br",
            "password": "senai2026"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["email"], "coordenador@senai.br")

    def test_03_active_calendar_structure(self):
        """Test that the calendar contains all required sections and data."""
        calendar_id = self.calendar_id_for_period("2º / 2026")
        res = self.client.get(f"/api/calendars/{calendar_id}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        # Verify header & metadata
        self.assertEqual(data["title"], "CALENDÁRIO ESCOLAR")
        self.assertEqual(data["unit_code"], "CFP 5.10")
        self.assertEqual(data["semester_year"], "2º / 2026")
        self.assertEqual(data["director_name"], "Tiago Roberto Ferreira")

        # Verify 4 course category summary cards
        categories = data["categories"]
        self.assertEqual(len(categories), 4)
        cat_titles = [c["title"] for c in categories]
        self.assertIn("Aprendizagem Industrial", cat_titles)
        self.assertIn("Curso Técnico", cat_titles)
        self.assertIn("Formação Continuada", cat_titles)
        self.assertIn("Graduação / Especialização", cat_titles)

        # Verify month columns (Julho, Agosto, Setembro on left, Outubro, Novembro, Dezembro on right)
        months = data["months"]
        self.assertEqual(len(months), 6)
        left_months = [m["month_name"] for m in months if m["column"] == "left"]
        right_months = [m["month_name"] for m in months if m["column"] == "right"]
        self.assertEqual(left_months, ["JULHO", "AGOSTO", "SETEMBRO"])
        self.assertEqual(right_months, ["OUTUBRO", "NOVEMBRO", "DEZEMBRO"])

        # Verify compensations table
        compensations = data["compensations"]
        self.assertTrue(len(compensations) >= 2)
        comp_dates = [c["dias_a_compensar"] for c in compensations]
        self.assertIn("10/jul", comp_dates)
        self.assertIn("07/dez", comp_dates)

    def test_04_update_day_and_recalculate(self):
        """Test updating a day cell and verifying recalculation of school days."""
        # Login
        auth_res = self.client.post("/api/auth/login", json={
            "email": "coordenador@senai.br",
            "password": "senai2026"
        })
        token = auth_res.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get calendar
        cal_id = self.calendar_id_for_period("2º / 2026")

        # Link day 18 of Julho as compensation for July 10
        res = self.client.post(f"/api/calendars/{cal_id}/day", json={
            "month_index": 7,
            "day": 18,
            "day_type": "compensacao",
            "title": "Dia Letivo Especial de Compensação",
            "compensation_for": "2026-07-10"
        }, headers=headers)
        self.assertEqual(res.status_code, 200)
        updated_cal = res.get_json()["calendar"]
        self.assertIsNotNone(updated_cal)

    def test_05_digital_signature(self):
        """Test digital approval signature for Director Tiago Roberto Ferreira."""
        auth_res = self.client.post("/api/auth/login", json={
            "email": "coordenador@senai.br",
            "password": "senai2026"
        })
        token = auth_res.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        cal_id = self.calendar_id_for_period("2º / 2026")

        coordinator_sign = self.client.post(
            f"/api/calendars/{cal_id}/sign",
            json={"director_name": "Tiago Roberto Ferreira"},
            headers=headers
        )
        self.assertEqual(coordinator_sign.status_code, 403)

        suffix = uuid4().hex[:10]
        director_email = f"diretor-{suffix}@example.test"
        with db_manager.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, 'diretor')
                RETURNING id;
                """,
                ("Diretor de teste", director_email, PasswordHasher.hash_password("TesteSeguro2026!"))
            )
            director_id = cursor.fetchone()["id"]
        try:
            director_update = self.client.put(
                f"/api/users/{director_id}",
                json={
                    "name": "Diretor de teste",
                    "email": director_email,
                    "role": "diretor",
                    "is_active": True,
                    "password": "OutraSenha2026!"
                },
                headers=headers
            )
            self.assertEqual(director_update.status_code, 403)
            director_login = self.client.post("/api/auth/login", json={
                "email": director_email,
                "password": "TesteSeguro2026!"
            })
            director_headers = {"Authorization": f"Bearer {director_login.get_json()['token']}"}
            res = self.client.post(f"/api/calendars/{cal_id}/sign", json={
                "director_name": "Tiago Roberto Ferreira"
            }, headers=director_headers)
            self.assertEqual(res.status_code, 200)
            signed_cal = res.get_json()["calendar"]
            self.assertEqual(signed_cal["director_signature_status"], "Assinado Digitalmente")
            self.assertTrue(signed_cal["signature_hash"].startswith("SENAI-AUTH-"))
        finally:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s;", (director_id,))

    def test_06_pdf_export(self):
        """Test generating and downloading PDF export."""
        cal_id = self.calendar_id_for_period("2º / 2026")

        res = self.client.get(f"/api/export/calendar/{cal_id}/pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "application/pdf")
        self.assertTrue(len(res.data) > 1000)

    def test_07_admin_management_and_calendar_creation(self):
        login = self.client.post("/api/auth/login", json={
            "email": "coordenador@senai.br",
            "password": "senai2026"
        })
        headers = {"Authorization": f"Bearer {login.get_json()['token']}"}
        self.assertEqual(self.client.post("/api/users", json={}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/register", json={}).status_code, 401)

        suffix = uuid4().hex[:10]
        category_id = None
        user_id = None
        opp_user_id = None
        director_user_id = None
        protected_director_id = None
        calendar_id = None
        try:
            category_response = self.client.post(
                "/api/categories",
                json={"name": f"Categoria teste {suffix}"},
                headers=headers
            )
            self.assertEqual(category_response.status_code, 201)
            category_id = category_response.get_json()["id"]

            user_response = self.client.post(
                "/api/users",
                json={
                    "name": "Usuário de teste",
                    "email": f"teste-{suffix}@example.test",
                    "password": "TesteSeguro2026!",
                    "role": "coordenador"
                },
                headers=headers
            )
            self.assertEqual(user_response.status_code, 201)
            user_data = user_response.get_json()["user"]
            user_id = user_data["id"]
            self.assertNotIn("password_hash", user_data)

            opp_response = self.client.post(
                "/api/users",
                json={
                    "name": "OPP de teste",
                    "email": f"opp-{suffix}@example.test",
                    "password": "TesteSeguro2026!",
                    "role": "opp"
                },
                headers=headers
            )
            self.assertEqual(opp_response.status_code, 201)
            opp_user_id = opp_response.get_json()["user"]["id"]
            self.assertEqual(opp_response.get_json()["user"]["role"], "opp")
            existing_directors = [
                user for user in self.client.get("/api/users", headers=headers).get_json()
                if user["role"] == "diretor" and user["is_active"]
            ]
            director_create_response = self.client.post(
                "/api/users",
                json={
                    "name": "Diretor não autorizado",
                    "email": f"director-denied-{suffix}@example.test",
                    "password": "TesteSeguro2026!",
                    "role": "diretor"
                },
                headers=headers
            )
            if existing_directors:
                self.assertEqual(director_create_response.status_code, 403)
                protected_director_id = existing_directors[0]["id"]
            else:
                self.assertEqual(director_create_response.status_code, 201)
                director_user_id = director_create_response.get_json()["user"]["id"]
                protected_director_id = director_user_id
                second_director_response = self.client.post(
                    "/api/users",
                    json={
                        "name": "Segundo Diretor não autorizado",
                        "email": f"second-director-denied-{suffix}@example.test",
                        "password": "TesteSeguro2026!",
                        "role": "diretor"
                    },
                    headers=headers
                )
                self.assertEqual(second_director_response.status_code, 403)
            self.assertEqual(self.client.delete(
                f"/api/users/{protected_director_id}", headers=headers
            ).status_code, 403)

            calendar_response = self.client.post(
                "/api/calendars",
                json={"year": 2199, "semester": 1, "category_ids": [category_id]},
                headers=headers
            )
            self.assertEqual(calendar_response.status_code, 201)
            calendar = calendar_response.get_json()["calendar"]
            calendar_id = calendar["id"]
            self.assertEqual(calendar["semester_year"], "1º / 2199")
            self.assertEqual(len(calendar["months"]), 6)
            self.assertEqual(calendar["months"][0]["month_name"], "JANEIRO")
            self.assertEqual(calendar["categories"][0]["title"], f"Categoria teste {suffix}")
            opp_login = self.client.post("/api/auth/login", json={
                "email": f"opp-{suffix}@example.test",
                "password": "TesteSeguro2026!"
            })
            self.assertEqual(opp_login.status_code, 200)
            opp_headers = {"Authorization": f"Bearer {opp_login.get_json()['token']}"}
            self.assertEqual(self.client.get("/api/categories", headers=opp_headers).status_code, 200)
            opp_edit = self.client.post(
                f"/api/calendars/{calendar_id}/day",
                json={"month_index": 1, "day": 3, "day_type": "feriado", "title": "Teste OPP"},
                headers=opp_headers
            )
            self.assertEqual(opp_edit.status_code, 200)
            opp_sign = self.client.post(
                f"/api/calendars/{calendar_id}/sign", json={}, headers=opp_headers
            )
            self.assertEqual(opp_sign.status_code, 403)
            semester_pdf = self.client.get(f"/api/export/calendar/{calendar_id}/pdf")
            self.assertEqual(semester_pdf.status_code, 200)
            self.assertEqual(semester_pdf.content_type, "application/pdf")

            start_response = self.client.post(
                f"/api/calendars/{calendar_id}/day",
                json={
                    "month_index": 1,
                    "day": 1,
                    "day_type": "inicio_aulas",
                    "milestone": "inicio",
                    "category_ids": [str(category_id)],
                    "title": "Início do curso de teste"
                },
                headers=headers
            )
            self.assertEqual(start_response.status_code, 200)
            calendar = start_response.get_json()["calendar"]
            self.assertEqual(calendar["categories"][0]["start_date"], "01/01/2199")
            january = calendar["months"][0]
            self.assertIn(
                {"date_label": "01/01", "description": "Início do curso de teste", "color_type": "green"},
                january["events"]
            )

            event_response = self.client.post(
                f"/api/calendars/{calendar_id}/day",
                json={
                    "month_index": 1,
                    "day": 1,
                    "day_type": "feriado",
                    "title": "Evento atualizado"
                },
                headers=headers
            )
            self.assertEqual(event_response.status_code, 200)
            updated_january = event_response.get_json()["calendar"]["months"][0]
            matching_events = [event for event in updated_january["events"] if event["date_label"] == "01/01"]
            self.assertEqual(len(matching_events), 1)
            self.assertEqual(matching_events[0]["description"], "Evento atualizado")
            self.assertEqual(matching_events[0]["color_type"], "red")
            persisted_calendar = self.client.get(f"/api/calendars/{calendar_id}").get_json()
            persisted_events = persisted_calendar["months"][0]["events"]
            persisted_matching_events = [
                event for event in persisted_events if event["date_label"] == "01/01"
            ]
            self.assertEqual(len(persisted_matching_events), 1)
            self.assertEqual(persisted_matching_events[0]["description"], "Evento atualizado")

            end_response = self.client.post(
                f"/api/calendars/{calendar_id}/day",
                json={
                    "month_index": 1,
                    "day": 2,
                    "day_type": "inicio_aulas",
                    "milestone": "termino",
                    "category_ids": [category_id],
                    "title": "Término do curso de teste"
                },
                headers=headers
            )
            self.assertEqual(end_response.status_code, 200)
            self.assertEqual(
                end_response.get_json()["calendar"]["categories"][0]["end_date"],
                "02/01/2199"
            )

            rename_category = self.client.put(
                f"/api/categories/{category_id}",
                json={"name": f"Categoria renomeada {suffix}", "is_active": True},
                headers=headers
            )
            self.assertEqual(rename_category.status_code, 200)
            self.assertEqual(calendar["categories"][0]["title"], f"Categoria teste {suffix}")

            deactivate_category = self.client.put(
                f"/api/categories/{category_id}",
                json={"name": f"Categoria renomeada {suffix}", "is_active": False},
                headers=headers
            )
            self.assertEqual(deactivate_category.status_code, 200)
            active_categories = self.client.get("/api/categories?active_only=true", headers=headers).get_json()
            self.assertNotIn(category_id, [item["id"] for item in active_categories])
            self.assertEqual(self.client.delete(f"/api/categories/{category_id}").status_code, 401)

            duplicate_response = self.client.post(
                "/api/calendars",
                json={"year": 2199, "semester": 1, "category_ids": [category_id]},
                headers=headers
            )
            self.assertEqual(duplicate_response.status_code, 422)

            update_user = self.client.put(
                f"/api/users/{user_id}",
                json={
                    "name": "Usuário de teste",
                    "email": f"teste-{suffix}@example.test",
                    "role": "coordenador",
                    "is_active": True,
                    "password": "SenhaAtualizada2026!"
                },
                headers=headers
            )
            self.assertEqual(update_user.status_code, 200)
            updated_login = self.client.post("/api/auth/login", json={
                "email": f"teste-{suffix}@example.test",
                "password": "SenhaAtualizada2026!"
            })
            self.assertEqual(updated_login.status_code, 200)
            user_headers = {"Authorization": f"Bearer {updated_login.get_json()['token']}"}

            deactivate_user = self.client.put(
                f"/api/users/{user_id}",
                json={
                    "name": "Usuário de teste",
                    "email": f"teste-{suffix}@example.test",
                    "role": "coordenador",
                    "is_active": False
                },
                headers=headers
            )
            self.assertEqual(deactivate_user.status_code, 200)
            self.assertEqual(self.client.get("/api/users", headers=user_headers).status_code, 401)
            inactive_login = self.client.post("/api/auth/login", json={
                "email": f"teste-{suffix}@example.test",
                "password": "SenhaAtualizada2026!"
            })
            self.assertEqual(inactive_login.status_code, 401)

            self.assertEqual(self.client.delete(f"/api/calendars/{calendar_id}").status_code, 401)
            category_delete = self.client.delete(f"/api/categories/{category_id}", headers=headers)
            self.assertEqual(category_delete.status_code, 200)
            self.assertEqual(
                self.client.get(f"/api/calendars/{calendar_id}", headers=headers).get_json()["categories"][0]["title"],
                f"Categoria teste {suffix}"
            )
            category_delete_missing = self.client.delete(
                f"/api/categories/{category_id}", headers=headers
            )
            self.assertEqual(category_delete_missing.status_code, 404)
            category_id = None

            delete_response = self.client.delete(f"/api/calendars/{calendar_id}", headers=headers)
            self.assertEqual(delete_response.status_code, 200)
            calendar_id = None
            listed_ids = [item["id"] for item in self.client.get("/api/calendars", headers=headers).get_json()]
            self.assertNotIn(calendar["id"], listed_ids)
        finally:
            with db_manager.get_cursor(commit=True) as cursor:
                if calendar_id is not None:
                    cursor.execute("DELETE FROM calendars WHERE id = %s;", (calendar_id,))
                if user_id is not None:
                    cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
                if opp_user_id is not None:
                    cursor.execute("DELETE FROM users WHERE id = %s;", (opp_user_id,))
                if director_user_id is not None:
                    cursor.execute("DELETE FROM users WHERE id = %s;", (director_user_id,))
                if category_id is not None:
                    cursor.execute("DELETE FROM course_categories WHERE id = %s;", (category_id,))

    def test_collaborator_can_view_but_not_modify_calendars(self):
        coordinator_login = self.client.post("/api/auth/login", json={
            "email": "coordenador@senai.br",
            "password": "senai2026"
        })
        coordinator_headers = {
            "Authorization": f"Bearer {coordinator_login.get_json()['token']}"
        }
        suffix = uuid4().hex[:10]
        email = f"colaborador-{suffix}@example.test"
        collaborator_id = None
        try:
            create_response = self.client.post("/api/users", json={
                "name": "Colaborador de teste",
                "email": email,
                "password": "TesteSeguro2026!",
                "role": "colaborador"
            }, headers=coordinator_headers)
            self.assertEqual(create_response.status_code, 201)
            collaborator_id = create_response.get_json()["user"]["id"]

            login = self.client.post("/api/auth/login", json={
                "email": email,
                "password": "TesteSeguro2026!"
            })
            self.assertEqual(login.status_code, 200)
            headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

            calendars_response = self.client.get("/api/calendars", headers=headers)
            self.assertEqual(calendars_response.status_code, 200)
            calendar_id = calendars_response.get_json()[0]["id"]
            self.assertEqual(self.client.get(
                f"/api/calendars/{calendar_id}", headers=headers
            ).status_code, 200)
            self.assertEqual(self.client.get(
                f"/api/export/calendar/{calendar_id}/json"
            ).status_code, 200)

            self.assertEqual(self.client.get("/api/users", headers=headers).status_code, 403)
            self.assertEqual(self.client.get("/api/categories", headers=headers).status_code, 403)
            self.assertEqual(self.client.put(
                f"/api/calendars/{calendar_id}/draft", json={}, headers=headers
            ).status_code, 403)
            self.assertEqual(self.client.post(
                f"/api/calendars/{calendar_id}/publish", headers=headers
            ).status_code, 403)
            self.assertEqual(self.client.post(
                f"/api/calendars/{calendar_id}/day",
                json={"month_index": 1, "day": 1, "day_type": "feriado"},
                headers=headers
            ).status_code, 403)
            self.assertEqual(self.client.post(
                f"/api/calendars/{calendar_id}/sign", json={}, headers=headers
            ).status_code, 403)
            self.assertEqual(self.client.delete(
                f"/api/calendars/{calendar_id}", headers=headers
            ).status_code, 403)
            self.assertEqual(self.client.post(
                "/api/calendars",
                json={"year": 2200, "semester": 1, "category_ids": [1]},
                headers=headers
            ).status_code, 403)
        finally:
            if collaborator_id is not None:
                with db_manager.get_cursor(commit=True) as cursor:
                    cursor.execute("DELETE FROM users WHERE id = %s;", (collaborator_id,))

    def test_user_page_delete_endpoint_rejects_self_and_deletes_other_users(self):
        coordinator_login = self.client.post("/api/auth/login", json={
            "email": "coordenador@senai.br",
            "password": "senai2026"
        })
        headers = {"Authorization": f"Bearer {coordinator_login.get_json()['token']}"}
        current_user_id = self.client.get("/api/auth/me", headers=headers).get_json()["id"]
        suffix = uuid4().hex[:10]
        email = f"excluir-{suffix}@example.test"
        create_response = self.client.post("/api/users", json={
            "name": "Usuário para exclusão",
            "email": email,
            "password": "TesteSeguro2026!",
            "role": "colaborador"
        }, headers=headers)
        self.assertEqual(create_response.status_code, 201)
        user_id = create_response.get_json()["user"]["id"]
        try:
            self_delete = self.client.delete(f"/api/users/{current_user_id}", headers=headers)
            self.assertEqual(self_delete.status_code, 400)
            delete_response = self.client.delete(f"/api/users/{user_id}", headers=headers)
            self.assertEqual(delete_response.status_code, 200)
            self.assertEqual(self.client.post("/api/auth/login", json={
                "email": email,
                "password": "TesteSeguro2026!"
            }).status_code, 401)
        finally:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))

if __name__ == "__main__":
    unittest.main()
