import re

from flask import Blueprint, g, jsonify, request

from core.exceptions import AppException, NotFoundError, ValidationError
from core.security import EDITOR_ROLES, PasswordHasher, USER_ROLES, roles_required
from models.repositories.user_repository import PostgresUserRepository
from presenters.auth_presenter import AuthPresenter
from models.user import User

user_bp = Blueprint("user_bp", __name__, url_prefix="/api/users")
user_repository = PostgresUserRepository()
auth_presenter = AuthPresenter(user_repository)


def has_active_director() -> bool:
    return any(user.is_active and user.role.lower() == "diretor" for user in user_repository.list_all())


@user_bp.route("", methods=["GET"])
@roles_required(*EDITOR_ROLES)
def list_users():
    return jsonify([user.to_dict() for user in user_repository.list_all()]), 200


@user_bp.route("", methods=["POST"])
@roles_required(*EDITOR_ROLES)
def create_user():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    role = data.get("role", "coordenador")
    role = role.strip().lower() if isinstance(role, str) else ""
    if role not in USER_ROLES:
        return jsonify({"error": "Perfil de usuário inválido."}), 422
    if (
        role == "diretor"
        and g.current_user["role"] != "diretor"
        and has_active_director()
    ):
        return jsonify({"error": "Somente um Diretor pode cadastrar outro Diretor."}), 403
    try:
        result = auth_presenter.register(
            name=data.get("name", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            role=role
        )
        return jsonify({"message": result["message"], "user": result["user"]}), 201
    except AppException as error:
        return jsonify({"error": error.message}), error.status_code


@user_bp.route("/<int:user_id>", methods=["PUT"])
@roles_required(*EDITOR_ROLES)
def update_user(user_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    user = user_repository.get_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado."}), 404
    if g.current_user["role"] != "diretor" and user.role == "diretor":
        return jsonify({"error": "Somente um Diretor pode alterar uma conta de Diretor."}), 403
    if "is_active" not in data or not isinstance(data["is_active"], bool):
        return jsonify({"error": "is_active deve ser verdadeiro ou falso."}), 400
    if user_id == g.current_user["user_id"] and not data["is_active"]:
        return jsonify({"error": "Não é possível desativar o próprio usuário."}), 400

    name = data.get("name", user.name)
    email = data.get("email", user.email)
    role = data.get("role", user.role)
    role = role.strip().lower() if isinstance(role, str) else ""
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        return jsonify({"error": "Nome inválido."}), 422
    if not isinstance(email, str) or len(email.strip()) > 180 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
        return jsonify({"error": "E-mail inválido."}), 422
    if role not in USER_ROLES:
        return jsonify({"error": "Perfil inválido."}), 422
    if g.current_user["role"] != "diretor":
        if role == "diretor" and user.role != "diretor" and has_active_director():
            return jsonify({"error": "Somente um Diretor pode atribuir esse perfil."}), 403
        if user.role == "diretor" and role != "diretor":
            return jsonify({"error": "Somente um Diretor pode alterar o perfil de outro Diretor."}), 403
    existing = user_repository.get_by_email(email.strip())
    if existing and existing.id != user_id:
        return jsonify({"error": "Este e-mail já está cadastrado no sistema."}), 422

    password = data.get("password")
    if password is not None:
        if not isinstance(password, str) or len(password) < 8:
            return jsonify({"error": "A senha deve possuir no mínimo 8 caracteres."}), 422
        user.password_hash = PasswordHasher.hash_password(password)

    user.name = name.strip()
    user.email = email.strip().lower()
    user.role = role
    user.is_active = data["is_active"]
    try:
        updated = user_repository.update(user)
        if not updated:
            raise NotFoundError("Usuário não encontrado.")
        return jsonify(updated.to_dict()), 200
    except AppException as error:
        return jsonify({"error": error.message}), error.status_code


@user_bp.route("/<int:user_id>", methods=["DELETE"])
@roles_required(*EDITOR_ROLES)
def delete_user(user_id: int):
    user = user_repository.get_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado."}), 404
    if user_id == g.current_user["user_id"]:
        return jsonify({"error": "Não é possível excluir o próprio usuário."}), 400
    if g.current_user["role"] != "diretor" and user.role == "diretor":
        return jsonify({"error": "Somente um Diretor pode excluir uma conta de Diretor."}), 403
    if user.role == "diretor" and user.is_active and has_active_director():
        active_directors = [
            item for item in user_repository.list_all()
            if item.is_active and item.role.lower() == "diretor"
        ]
        if len(active_directors) == 1:
            return jsonify({"error": "Não é possível excluir o último Diretor ativo."}), 409
    if not user_repository.delete(user_id):
        return jsonify({"error": "Usuário não encontrado."}), 404
    return jsonify({"message": "Usuário excluído com sucesso."}), 200
