import os

from dotenv import load_dotenv

from core.database import db_manager
from core.security import PasswordHasher
from models.repositories.calendar_repository import PostgresCalendarRepository
from models.repositories.category_repository import PostgresCategoryRepository
from models.repositories.user_repository import PostgresUserRepository
from models.user import User
from presenters.calendar_presenter import CalendarPresenter

load_dotenv()

def initialize_database():
    """
    Inicializa o banco de dados e os dados iniciais.

    Esta função deve ser executada separadamente,
    durante a preparação do ambiente, e não durante
    a importação da aplicação pela Vercel.
    """

    print("[BOOTSTRAP] Iniciando configuração do banco de dados...")

    # Inicialização do esquema
    db_manager.init_schema()

    user_repo = PostgresUserRepository()
    cal_repo = PostgresCalendarRepository()

    # Verifica se o usuário coordenador já existe
    default_user = user_repo.get_by_email(
        "coordenador@senai.br"
    )

    # Criação do usuário inicial, caso necessário
    if not default_user:

        initial_password = os.getenv(
            "COORDENADOR_INITIAL_PASSWORD"
        )

        if not initial_password:
            raise RuntimeError(
                "Defina a variável de ambiente "
                "COORDENADOR_INITIAL_PASSWORD "
                "para criar o usuário coordenador."
            )

        seeded_user = User(
            id=None,
            name="Coordenador Pedagógico",
            email="coordenador@senai.br",
            password_hash=PasswordHasher.hash_password(
                initial_password
            ),
            role="coordenador"
        )

        default_user = user_repo.create(seeded_user)

        print(
            "[BOOTSTRAP] Usuário coordenador criado com sucesso."
        )

    # Verifica se o calendário inicial já foi criado
    if db_manager.get_setting("initial_calendar_seeded") != "true":

        cal_presenter = CalendarPresenter(cal_repo)

        active_calendar = cal_presenter.get_or_create_default(
            user_id=default_user.id if default_user else None
        )

        category_repo = PostgresCategoryRepository()

        # Criação das categorias iniciais
        if not category_repo.list_all():

            for category in active_calendar.categories:

                category_repo.create(
                    category["id"],
                    category["title"]
                )

        db_manager.set_setting(
            "initial_calendar_seeded",
            "true"
        )

    print(
        "[BOOTSTRAP] Banco de dados e calendário "
        "inicializados com sucesso!"
    )

initialize_database()

