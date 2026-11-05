import os
from flask import Flask, render_template, send_from_directory
from config import Config
from core.database import db_manager
from core.security import PasswordHasher
from models.repositories.user_repository import PostgresUserRepository
from models.repositories.calendar_repository import PostgresCalendarRepository
from models.repositories.category_repository import PostgresCategoryRepository
from presenters.calendar_presenter import CalendarPresenter
from models.user import User

from views.auth_view import auth_bp
from views.calendar_view import calendar_bp
from views.export_view import export_bp
from views.category_view import category_bp
from views.user_view import user_bp

def create_app():
    """Application Factory adhering to Single Responsibility and Open/Closed Principles."""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(user_bp)

    # Initialize database schema & seed initial user and calendar
    with app.app_context():
        try:
            db_manager.init_schema()
            user_repo = PostgresUserRepository()
            cal_repo = PostgresCalendarRepository()

            # Seed default coordinator user if empty
            default_user = user_repo.get_by_email("coordenador@senai.br")
            if not default_user:
                seeded_user = User(
                    id=None,
                    name="Coordenador Pedagógico",
                    email="coordenador@senai.br",
                    password_hash=PasswordHasher.hash_password("senai2026"),
                    role="coordenador"
                )
                default_user = user_repo.create(seeded_user)
                print(f"[BOOTSTRAP] Usuário padrão criado: coordenador@senai.br / senai2026")

            if db_manager.get_setting("initial_calendar_seeded") != "true":
                cal_presenter = CalendarPresenter(cal_repo)
                active_calendar = cal_presenter.get_or_create_default(
                    user_id=default_user.id if default_user else None
                )
                category_repo = PostgresCategoryRepository()
                if not category_repo.list_all():
                    for category in active_calendar.categories:
                        category_repo.create(category["id"], category["title"])
                db_manager.set_setting("initial_calendar_seeded", "true")
            print("[BOOTSTRAP] Banco de dados e Calendário 2º/2026 inicializados com sucesso!")
        except Exception as e:
            print(f"[BOOTSTRAP ERROR] Falha ao inicializar banco: {e}")

    @app.route("/")
    def index():
        return render_template("index.html")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
