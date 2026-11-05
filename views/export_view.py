from flask import Blueprint, send_file, Response, jsonify
import io
import json
from core.exceptions import AppException
from models.repositories.calendar_repository import PostgresCalendarRepository
from presenters.calendar_presenter import CalendarPresenter

export_bp = Blueprint("export_bp", __name__, url_prefix="/api/export")

calendar_repository = PostgresCalendarRepository()
calendar_presenter = CalendarPresenter(calendar_repository)

@export_bp.route("/calendar/<int:calendar_id>/pdf", methods=["GET"])
def export_pdf(calendar_id: int):
    try:
        pdf_bytes = calendar_presenter.generate_pdf_bytes(calendar_id)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"Calendario_Escolar_{calendar_id}.pdf"
        )
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500

@export_bp.route("/calendar/<int:calendar_id>/json", methods=["GET"])
def export_json(calendar_id: int):
    try:
        calendar = calendar_presenter.get_by_id(calendar_id)
        json_data = json.dumps(calendar.to_dict(), indent=2, ensure_ascii=False)
        return Response(
            json_data,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=calendario_senai_{calendar_id}.json"}
        )
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": f"Erro ao exportar JSON: {str(e)}"}), 500
