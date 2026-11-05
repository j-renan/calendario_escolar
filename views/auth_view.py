from flask import Blueprint, request, jsonify, g
from core.security import EDITOR_ROLES, jwt_required, roles_required
from core.exceptions import AppException
from models.repositories.user_repository import PostgresUserRepository
from presenters.auth_presenter import AuthPresenter

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

user_repository = PostgresUserRepository()
auth_presenter = AuthPresenter(user_repository)

@auth_bp.route("/register", methods=["POST"])
@roles_required(*EDITOR_ROLES)
def register():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    try:
        res = auth_presenter.register(
            name=data.get("name", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            role="coordenador"
        )
        return jsonify(res), 201
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro interno ao cadastrar: {str(e)}"}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    try:
        res = auth_presenter.login(
            email=data.get("email", ""),
            password=data.get("password", "")
        )
        return jsonify(res), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao autenticar: {str(e)}"}), 500

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    try:
        user_id = g.current_user["user_id"]
        res = auth_presenter.get_profile(user_id)
        return jsonify(res), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao obter perfil: {str(e)}"}), 500
