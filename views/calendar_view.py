from flask import Blueprint, request, jsonify, g
from core.security import EDITOR_ROLES, USER_ROLES, jwt_required, roles_required
from core.exceptions import AppException, NotFoundError
from models.repositories.calendar_repository import PostgresCalendarRepository
from models.repositories.category_repository import PostgresCategoryRepository
from presenters.calendar_presenter import CalendarPresenter

calendar_bp = Blueprint("calendar_bp", __name__, url_prefix="/api/calendars")

calendar_repository = PostgresCalendarRepository()
calendar_presenter = CalendarPresenter(calendar_repository)
category_repository = PostgresCategoryRepository()


@calendar_bp.route("", methods=["GET"])
@roles_required(*USER_ROLES)
def list_calendars():
    try:
        return jsonify(calendar_repository.list_all()), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao listar calendários: {str(e)}"}), 500


@calendar_bp.route("", methods=["POST"])
@roles_required(*EDITOR_ROLES)
def create_calendar():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    year = data.get("year")
    semester = data.get("semester")
    category_ids = data.get("category_ids")
    if isinstance(year, bool) or not isinstance(year, int):
        return jsonify({"error": "Informe o ano como número inteiro."}), 400
    if isinstance(semester, bool) or not isinstance(semester, int):
        return jsonify({"error": "Informe o semestre como 1 ou 2."}), 400
    if not isinstance(category_ids, list) or not category_ids:
        return jsonify({"error": "Selecione ao menos uma categoria."}), 400
    try:
        categories_by_id = {
            category["id"]: category
            for category in category_repository.list_all(active_only=True)
        }
        selected = []
        for category_id in category_ids:
            if isinstance(category_id, bool) or not isinstance(category_id, int):
                return jsonify({"error": "Identificador de categoria inválido."}), 400
            category = categories_by_id.get(category_id)
            if not category:
                return jsonify({"error": f"Categoria ativa #{category_id} não encontrada."}), 422
            selected.append(category)
        calendar = calendar_presenter.create_for_period(
            year, semester, selected, user_id=g.current_user["user_id"]
        )
        return jsonify({"calendar": calendar.to_dict()}), 201
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao criar calendário: {str(e)}"}), 500

@calendar_bp.route("/active", methods=["GET"])
@jwt_required(optional=True)
def get_active_calendar():
    try:
        calendar = calendar_repository.get_latest()
        if not calendar:
            raise NotFoundError("Nenhum calendário cadastrado.")
        return jsonify(calendar.to_dict()), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar calendário ativo: {str(e)}"}), 500

@calendar_bp.route("/<int:calendar_id>", methods=["GET"])
@jwt_required(optional=True)
def get_calendar_by_id(calendar_id: int):
    try:
        calendar = calendar_presenter.get_by_id(calendar_id)
        return jsonify(calendar.to_dict()), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar calendário: {str(e)}"}), 500


@calendar_bp.route("/<int:calendar_id>", methods=["DELETE"])
@roles_required(*EDITOR_ROLES)
def delete_calendar(calendar_id: int):
    try:
        calendar = calendar_presenter.get_by_id(calendar_id)
        if not calendar_repository.delete(calendar_id):
            raise NotFoundError(f"Calendário #{calendar_id} não encontrado.")
        return jsonify({"message": f"Calendário {calendar.semester_year} excluído com sucesso."}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao excluir calendário: {str(e)}"}), 500

@calendar_bp.route("/<int:calendar_id>/draft", methods=["PUT"])
@roles_required(*EDITOR_ROLES)
def save_draft(calendar_id: int):
    data = request.get_json(silent=True) or {}
    try:
        user_id = g.current_user["user_id"]
        updated = calendar_presenter.save_draft(calendar_id, data, user_id=user_id)
        return jsonify({
            "message": "Rascunho salvo com sucesso!",
            "calendar": updated.to_dict()
        }), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar rascunho: {str(e)}"}), 500

@calendar_bp.route("/<int:calendar_id>/publish", methods=["POST"])
@roles_required(*EDITOR_ROLES)
def publish_calendar(calendar_id: int):
    try:
        user_id = g.current_user["user_id"]
        published = calendar_presenter.publish(calendar_id, user_id=user_id)
        return jsonify({
            "message": f"Calendário publicado com sucesso! {published.version}",
            "calendar": published.to_dict()
        }), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao publicar calendário: {str(e)}"}), 500

@calendar_bp.route("/<int:calendar_id>/sign", methods=["POST"])
@roles_required("diretor")
def sign_approval(calendar_id: int):
    data = request.get_json(silent=True) or {}
    director_name = data.get("director_name", "Tiago Roberto Ferreira")
    try:
        user_id = g.current_user["user_id"]
        signed = calendar_presenter.sign_digital_approval(calendar_id, director_name, user_id=user_id)
        return jsonify({
            "message": f"Calendário aprovado e assinado digitalmente por {director_name}!",
            "calendar": signed.to_dict()
        }), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao assinar aprovação: {str(e)}"}), 500

@calendar_bp.route("/<int:calendar_id>/day", methods=["POST"])
@roles_required(*EDITOR_ROLES)
def update_day(calendar_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "O corpo da requisição deve ser um objeto JSON."}), 400
    month_index = data.get("month_index")
    day = data.get("day")
    day_type = data.get("day_type")
    title = data.get("title")
    milestone = data.get("milestone")
    category_ids = data.get("category_ids", [])

    if (
        isinstance(month_index, bool) or not isinstance(month_index, int)
        or isinstance(day, bool) or not isinstance(day, int)
        or not isinstance(day_type, str) or not day_type
        or (title is not None and not isinstance(title, str))
        or not isinstance(category_ids, list)
    ):
        return jsonify({"error": "Parâmetros do dia inválidos ou incompletos."}), 400

    try:
        user_id = g.current_user["user_id"]
        updated = calendar_presenter.update_day_cell(
            calendar_id=calendar_id,
            month_index=month_index,
            day=day,
            new_type=day_type,
            new_title=title,
            milestone=milestone,
            category_ids=category_ids,
            user_id=user_id
        )
        return jsonify({
            "message": "Dia atualizado com sucesso!",
            "calendar": updated.to_dict()
        }), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao atualizar dia: {str(e)}"}), 500

@calendar_bp.route("/<int:calendar_id>/history", methods=["GET"])
@jwt_required()
def get_history(calendar_id: int):
    try:
        history = calendar_presenter.get_history(calendar_id)
        return jsonify(history), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar histórico: {str(e)}"}), 500

@calendar_bp.route("/<int:calendar_id>/history/<int:history_id>/restore", methods=["POST"])
@roles_required(*EDITOR_ROLES)
def restore_history(calendar_id: int, history_id: int):
    try:
        user_id = g.current_user["user_id"]
        restored = calendar_presenter.restore_history_snapshot(calendar_id, history_id, user_id=user_id)
        return jsonify({
            "message": "Versão restaurada com sucesso!",
            "calendar": restored.to_dict()
        }), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao restaurar versão: {str(e)}"}), 500
