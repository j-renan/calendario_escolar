import re

from core.security import PasswordHasher, TokenProvider, USER_ROLES
from core.exceptions import AuthenticationError, ValidationError
from models.user import User
from models.repositories.base import IUserRepository

class AuthPresenter:
    """
    MVP Presenter for Authentication.
    Coordinates between User Domain Model and HTTP View.
    """
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    def register(self, name: str, email: str, password: str, role: str = "coordenador") -> dict:
        if not isinstance(name, str) or not isinstance(email, str) or not isinstance(password, str):
            raise ValidationError("Nome, e-mail e senha devem ser textos.")
        if not name.strip() or not email.strip() or not password:
            raise ValidationError("Nome, e-mail e senha são obrigatórios.")

        if len(password) < 8:
            raise ValidationError("A senha deve possuir no mínimo 8 caracteres.")

        email = email.strip().lower()
        name = name.strip()
        if len(name) > 120 or len(email) > 180 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValidationError("Informe um nome e um e-mail válidos.")
        role = role.strip().lower() if isinstance(role, str) else ""
        if role not in USER_ROLES:
            raise ValidationError("Perfil de usuário inválido.")

        existing = self.user_repo.get_by_email(email)
        if existing:
            raise ValidationError("Este e-mail já está cadastrado no sistema.")

        password_hash = PasswordHasher.hash_password(password)
        new_user = User(
            id=None,
            name=name,
            email=email,
            password_hash=password_hash,
            role=role
        )
        saved_user = self.user_repo.create(new_user)
        token = TokenProvider.generate_token(saved_user.id, saved_user.email, saved_user.role)

        return {
            "message": "Usuário registrado com sucesso.",
            "token": token,
            "user": saved_user.to_dict()
        }

    def login(self, email: str, password: str) -> dict:
        if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password:
            raise ValidationError("E-mail e senha são obrigatórios.")

        user = self.user_repo.get_by_email(email.strip())
        if not user or not user.is_active or not PasswordHasher.verify_password(password, user.password_hash):
            raise AuthenticationError("E-mail ou senha incorretos.")

        token = TokenProvider.generate_token(user.id, user.email, user.role)
        return {
            "message": "Login realizado com sucesso.",
            "token": token,
            "user": user.to_dict()
        }

    def get_profile(self, user_id: int) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Usuário não encontrado.")
        return user.to_dict()
