from datetime import datetime, timezone
from functools import wraps
import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from core.exceptions import AuthenticationError

EDITOR_ROLES = ("diretor", "coordenador", "opp")
USER_ROLES = (*EDITOR_ROLES, "colaborador")

class PasswordHasher:
    """SRP: Handles password hashing and verification."""
    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password)

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return check_password_hash(hashed, password)

class TokenProvider:
    """SRP: Handles JWT encoding and decoding."""
    @staticmethod
    def generate_token(user_id: int, email: str, role: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "user_id": user_id,
            "email": email,
            "role": role,
            "iat": now,
            "exp": now + Config.JWT_ACCESS_TOKEN_EXPIRES
        }
        return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expirado. Por favor, realize login novamente.")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Token de autenticação inválido.")

def jwt_required(optional=False):
    """Decorator to protect endpoints with JWT authentication."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            token = None
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()

            if not token:
                if optional:
                    g.current_user = None
                    return f(*args, **kwargs)
                return jsonify({"error": "Token de autenticação ausente ou inválido"}), 401

            try:
                payload = TokenProvider.decode_token(token)
            except AuthenticationError as e:
                return jsonify({"error": e.message}), e.status_code
            except Exception:
                return jsonify({"error": "Falha na validação do token"}), 401

            from models.repositories.user_repository import PostgresUserRepository
            user = PostgresUserRepository().get_by_id(payload["user_id"])
            if not user or not user.is_active:
                return jsonify({"error": "Conta desativada ou inexistente. Faça contato com um administrador."}), 401
            payload["role"] = user.role
            g.current_user = payload

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def roles_required(*roles):
    allowed_roles = {role.lower() for role in roles}

    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            role = str(g.current_user.get("role", "")).lower()
            if role not in allowed_roles:
                return jsonify({"error": "Você não tem permissão para executar esta ação."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
