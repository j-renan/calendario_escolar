from flask import Blueprint, jsonify, request

from core.exceptions import AppException
from core.security import EDITOR_ROLES, roles_required
from models.repositories.category_repository import PostgresCategoryRepository
from presenters.category_presenter import CategoryPresenter

category_bp = Blueprint("category_bp", __name__, url_prefix="/api/categories")
category_presenter = CategoryPresenter(PostgresCategoryRepository())


@category_bp.route("", methods=["GET"])
@roles_required(*EDITOR_ROLES)
def list_categories():
    active_only = request.args.get("active_only", "false").lower() == "true"
    return jsonify(category_presenter.list_categories(active_only=active_only)), 200


@category_bp.route("", methods=["POST"])
@roles_required(*EDITOR_ROLES)
def create_category():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    try:
        return jsonify(category_presenter.create(data.get("name", ""))), 201
    except AppException as error:
        return jsonify({"error": error.message}), error.status_code


@category_bp.route("/<int:category_id>", methods=["PUT"])
@roles_required(*EDITOR_ROLES)
def update_category(category_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    if not isinstance(data.get("is_active"), bool):
        return jsonify({"error": "is_active deve ser verdadeiro ou falso."}), 400
    try:
        updated = category_presenter.update(category_id, data.get("name", ""), data["is_active"])
        return jsonify(updated), 200
    except AppException as error:
        return jsonify({"error": error.message}), error.status_code


@category_bp.route("/<int:category_id>", methods=["DELETE"])
@roles_required(*EDITOR_ROLES)
def delete_category(category_id: int):
    try:
        category_presenter.delete(category_id)
        return jsonify({"message": "Categoria excluída com sucesso."}), 200
    except AppException as error:
        return jsonify({"error": error.message}), error.status_code
