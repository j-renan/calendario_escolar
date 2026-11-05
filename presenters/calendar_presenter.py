import hashlib
import html
import io
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from core.exceptions import NotFoundError, ValidationError
from models.calendar import SchoolCalendar
from models.repositories.base import ICalendarRepository
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

class CalendarPresenter:
    """
    MVP Presenter for Calendar operations.
    Encapsulates business rules, calculations, approval flows, and undo/redo snapshots.
    """
    def __init__(self, calendar_repo: ICalendarRepository):
        self.calendar_repo = calendar_repo

    def get_or_create_default(self, user_id: Optional[int] = None) -> SchoolCalendar:
        calendar = self.calendar_repo.get_latest()
        if not calendar:
            default_cal = SchoolCalendar.create_default_2026(created_by=user_id)
            calendar = self.calendar_repo.create(default_cal)
            self.calendar_repo.add_history(calendar.id, "Criação Inicial do Calendário 2º/2026", calendar.to_dict(), user_id)
        return calendar

    def get_by_id(self, calendar_id: int) -> SchoolCalendar:
        calendar = self.calendar_repo.get_by_id(calendar_id)
        if not calendar:
            raise NotFoundError(f"Calendário #{calendar_id} não encontrado.")
        return calendar

    def create_for_period(
        self,
        year: int,
        semester: int,
        categories: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> SchoolCalendar:
        if isinstance(year, bool) or not isinstance(year, int) or year < 2000 or year > 2200:
            raise ValidationError("Informe um ano entre 2000 e 2200.")
        if isinstance(semester, bool) or semester not in (1, 2):
            raise ValidationError("O semestre deve ser 1 ou 2.")
        if not categories:
            raise ValidationError("Cadastre ou selecione ao menos uma categoria ativa.")

        semester_year = f"{semester}º / {year}"
        if self.calendar_repo.get_by_period(semester_year):
            raise ValidationError(f"Já existe um calendário para {semester_year}.")

        calendar = SchoolCalendar.create_for_period(year, semester, categories, created_by=user_id)
        calendar = self.calendar_repo.create(calendar)
        self.calendar_repo.add_history(
            calendar.id,
            f"Criação do Calendário {semester_year}",
            calendar.to_dict(),
            user_id
        )
        return calendar

    def save_draft(self, calendar_id: int, payload: dict, user_id: Optional[int] = None) -> SchoolCalendar:
        calendar = self.get_by_id(calendar_id)

        # Update fields if provided
        if "title" in payload:
            calendar.title = payload["title"]
        if "unit_code" in payload:
            calendar.unit_code = payload["unit_code"]
        if "semester_year" in payload and payload["semester_year"] != calendar.semester_year:
            raise ValidationError("O ano e o semestre não podem ser alterados após a criação.")
        if "categories" in payload:
            calendar.categories = payload["categories"]
        if "months" in payload:
            calendar.months = payload["months"]
        if "compensations" in payload:
            calendar.compensations = payload["compensations"]
        if "workload_note" in payload:
            calendar.workload_note = payload["workload_note"]

        calendar.status = "rascunho"
        calendar.calculate_totals()
        updated = self.calendar_repo.update(calendar)
        self.calendar_repo.add_history(calendar.id, "Salvo como Rascunho", updated.to_dict(), user_id)
        return updated

    def publish(self, calendar_id: int, user_id: Optional[int] = None) -> SchoolCalendar:
        calendar = self.get_by_id(calendar_id)
        calendar.status = "publicado"

        # Bump version or update timestamp
        today_str = datetime.now().strftime("%d/%m/%Y")
        current_ver = calendar.version
        try:
            if "Versão " in current_ver:
                num_part = current_ver.split("Versão ")[1].split(" - ")[0]
                new_num = int(num_part) + 1
                calendar.version = f"Versão {new_num:02d} - {today_str}"
            else:
                calendar.version = f"Versão 02 - {today_str}"
        except Exception:
            calendar.version = f"Versão Oficial - {today_str}"

        calendar.calculate_totals()
        updated = self.calendar_repo.update(calendar)
        self.calendar_repo.add_history(calendar.id, f"Publicação ({calendar.version})", updated.to_dict(), user_id)
        return updated

    def sign_digital_approval(self, calendar_id: int, director_name: str, user_id: Optional[int] = None) -> SchoolCalendar:
        calendar = self.get_by_id(calendar_id)
        if not director_name:
            director_name = "Tiago Roberto Ferreira"

        now_dt = datetime.now()
        date_str = now_dt.strftime("%d/%m/%Y %H:%M:%S")

        # Generate cryptographic validation signature
        raw_token = f"{calendar.id}-{director_name}-{date_str}-SENAI-SP-CFP-5.10"
        signature_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:16].upper()

        calendar.director_name = director_name
        calendar.director_signature_status = "Assinado Digitalmente"
        calendar.signature_date = date_str
        calendar.signature_hash = f"SENAI-AUTH-{signature_hash}"

        updated = self.calendar_repo.update(calendar)
        self.calendar_repo.add_history(calendar.id, f"Assinatura Digital por {director_name}", updated.to_dict(), user_id)
        return updated

    def update_day_cell(
        self,
        calendar_id: int,
        month_index: int,
        day: int,
        new_type: str,
        new_title: str,
        milestone: Optional[str] = None,
        category_ids: Optional[List[Any]] = None,
        user_id: Optional[int] = None
    ) -> SchoolCalendar:
        calendar = self.get_by_id(calendar_id)
        allowed_types = {"letivo", "feriado", "inicio_aulas", "nao_letivo", "compensacao", "domingo"}
        if new_type not in allowed_types:
            raise ValidationError("Classificação de dia inválida.")
        if not isinstance(day, int) or day < 1 or day > 31:
            raise ValidationError("Dia do mês inválido.")

        # Locate month and day cell
        target_month = None
        for m in calendar.months:
            if m.get("month_index") == month_index:
                target_month = m
                break

        if not target_month:
            raise NotFoundError(f"Mês com índice {month_index} não encontrado.")

        month_abbrs = {
            1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
            7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
        }
        date_value = f"{day:02d}/{month_index:02d}/{target_month['year']}"
        if new_type == "inicio_aulas":
            if milestone not in ("inicio", "termino"):
                raise ValidationError("Selecione se a data representa início ou término das aulas.")
            if not isinstance(category_ids, list) or not category_ids:
                raise ValidationError("Selecione ao menos uma categoria de curso.")
            selected_ids = {str(category_id) for category_id in category_ids}
            matched_categories = [
                category for category in calendar.categories
                if str(category.get("id")) in selected_ids
            ]
            if len(matched_categories) != len(selected_ids):
                raise ValidationError("Uma ou mais categorias selecionadas não pertencem a este calendário.")
            field_name = "start_date" if milestone == "inicio" else "end_date"
            for category in calendar.categories:
                if category.get("start_date") == date_value:
                    category["start_date"] = "-"
                if category.get("end_date") == date_value:
                    category["end_date"] = "-"
            for category in matched_categories:
                category[field_name] = date_value
            if not (new_title or "").strip():
                new_title = "Início das aulas" if milestone == "inicio" else "Término das aulas"
        else:
            for category in calendar.categories:
                if category.get("start_date") == date_value:
                    category["start_date"] = "-"
                if category.get("end_date") == date_value:
                    category["end_date"] = "-"

        found = False
        updated_cell = None
        for week in target_month.get("calendar_weeks", []):
            for cell in week:
                if cell.get("day") == day:
                    cell["type"] = new_type
                    if new_title is not None:
                        cell["title"] = new_title
                    updated_cell = cell
                    found = True
                    break
            if found:
                break

        if not found:
            raise NotFoundError(f"Dia {day} não encontrado no mês.")

        date_label = f"{day:02d}/{month_index:02d}"
        target_month["events"] = [
            event for event in (target_month.get("events") or [])
            if not (
                (date_match := re.match(r"^\s*(\d{1,2})(?:/|$)", str(event.get("date_label", ""))))
                and int(date_match.group(1)) == day
            )
        ]
        event_title = (updated_cell.get("title") or "").strip()
        generic_titles = {"dia letivo", "domingo", "sábado"}
        if event_title and event_title.casefold() not in generic_titles:
            color_type = {
                "feriado": "red",
                "inicio_aulas": "green",
                "compensacao": "blue"
            }.get(new_type, "blue")
            target_month.setdefault("events", []).append({
                "date_label": date_label,
                "description": event_title,
                "color_type": color_type
            })

        # Recalculate school days count for month
        school_days_count = 0
        for week in target_month.get("calendar_weeks", []):
            for cell in week:
                if cell.get("day") and cell.get("type") in ["letivo", "inicio_aulas", "compensacao"]:
                    school_days_count += 1

        # Synchronize course days
        for course_title in target_month.get("course_days", {}):
            target_month["course_days"][course_title] = school_days_count

        # Map to category month short code
        abbr = next(
            (month.get("month_abbr") for month in calendar.months if month.get("month_index") == month_index),
            month_abbrs.get(month_index)
        )
        if abbr:
            for cat in calendar.categories:
                if abbr in cat.get("monthly_days", {}):
                    cat["monthly_days"][abbr] = school_days_count

        calendar.calculate_totals()
        updated = self.calendar_repo.update(calendar)
        self.calendar_repo.add_history(calendar.id, f"Alteração no dia {day:02d} ({target_month['month_name']}) para {new_type}", updated.to_dict(), user_id)
        return updated

    def get_history(self, calendar_id: int) -> List[Dict[str, Any]]:
        return self.calendar_repo.get_history(calendar_id)

    def restore_history_snapshot(self, calendar_id: int, history_id: int, user_id: Optional[int] = None) -> SchoolCalendar:
        history_list = self.calendar_repo.get_history(calendar_id, limit=50)
        target_snapshot = None
        for h in history_list:
            if h["id"] == history_id:
                target_snapshot = h.get("snapshot_json")
                break

        if not target_snapshot:
            raise NotFoundError("Snapshot histórico não encontrado.")

        calendar = self.get_by_id(calendar_id)
        calendar.title = target_snapshot.get("title", calendar.title)
        calendar.unit_code = target_snapshot.get("unit_code", calendar.unit_code)
        calendar.semester_year = target_snapshot.get("semester_year", calendar.semester_year)
        calendar.status = target_snapshot.get("status", calendar.status)
        calendar.version = target_snapshot.get("version", calendar.version)
        calendar.director_name = target_snapshot.get("director_name", calendar.director_name)
        calendar.director_signature_status = target_snapshot.get("director_signature_status", calendar.director_signature_status)
        calendar.signature_date = target_snapshot.get("signature_date", calendar.signature_date)
        calendar.signature_hash = target_snapshot.get("signature_hash", calendar.signature_hash)
        calendar.workload_note = target_snapshot.get("workload_note", calendar.workload_note)
        calendar.categories = target_snapshot.get("categories", calendar.categories)
        calendar.months = target_snapshot.get("months", calendar.months)
        calendar.compensations = target_snapshot.get("compensations", calendar.compensations)

        calendar.calculate_totals()
        updated = self.calendar_repo.update(calendar)
        self.calendar_repo.add_history(calendar.id, f"Desfazer / Restauração do snapshot #{history_id}", updated.to_dict(), user_id)
        return updated

    def generate_pdf_bytes(self, calendar_id: int) -> bytes:
        """Generates a complete, high-fidelity PDF export of the school calendar."""
        calendar = self.get_by_id(calendar_id)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=18,
            leftMargin=18,
            topMargin=16,
            bottomMargin=16
        )

        elements = []
        styles = getSampleStyleSheet()
        month_title_style = ParagraphStyle(
            "MonthTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            textColor=colors.white,
            fontSize=8,
        )
        palette = {
            "blue": "#002B49",
            "red": "#EF4444",
            "green": "#10B981",
            "yellow": "#F59E0B",
            "light_red": "#FEF2F2",
            "white": "#FFFFFF",
            "light_gray": "#F1F5F9",
            "border": "#E2E8F0",
            "text": "#0F172A",
            "secondary_text": "#475569",
        }

        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#002B49'),
            alignment=1, # Center
            spaceAfter=4
        )

        sub_style = ParagraphStyle(
            'HeaderSub',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.HexColor('#D32F2F'),
            alignment=1
        )

        # Header Table with Logo, Title, and CFP / SEM/ANO boxes
        logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "img", "logo_senai.png")
        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=120, height=35)
        else:
            img = Paragraph("<b>SENAI</b>", styles['Normal'])

        center_header = Paragraph("<b>CALENDÁRIO ESCOLAR</b><br/><font size=8 color='#555'>SENAI SÃO PAULO - DEPARTAMENTO REGIONAL</font>", title_style)

        right_header = Paragraph(f"""
            <table width="100%">
                <tr><td align="right"><b>UNIDADE:</b> {calendar.unit_code}</td></tr>
                <tr><td align="right"><b>SEM/ANO:</b> {calendar.semester_year}</td></tr>
                <tr><td align="right"><font size=7 color='#666'>{calendar.status.upper()} | {calendar.version}</font></td></tr>
            </table>
        """, styles['Normal'])

        hdr_table = Table([[img, center_header, right_header]], colWidths=[140, 480, 180])
        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(hdr_table)
        elements.append(Spacer(1, 6))

        all_month_abbrs = {
            1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
            7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
        }
        month_abbrs = [
            month.get("month_abbr") or all_month_abbrs.get(month.get("month_index"), "")
            for month in calendar.months
        ]
        if not month_abbrs:
            month_abbrs = ["JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        cat_data = [["CATEGORIA DO CURSO", "INÍCIO", "TÉRMINO", *month_abbrs, "TOTAL"]]
        for c in calendar.categories:
            m = c.get("monthly_days", {})
            cat_data.append([
                c.get("title", ""),
                c.get("start_date", ""),
                c.get("end_date", ""),
                *[str(m.get(month_abbr, 0)) for month_abbr in month_abbrs],
                str(c.get("total_days", 0))
            ])

        total_column = len(cat_data[0]) - 1
        cat_table = Table(
            cat_data,
            colWidths=[180, 70, 70, *([45] * len(month_abbrs)), 60]
        )
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (total_column, 1), (total_column, -1), colors.HexColor('#FFF3CD')),
            ('FONTNAME', (total_column, 1), (total_column, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (total_column, 1), (total_column, -1), colors.HexColor('#D32F2F')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(cat_table)
        elements.append(Spacer(1, 8))

        # 6 Months Grid Table (2 Columns: Left = Jul, Ago, Set; Right = Out, Nov, Dez)
        # We will format this into a structured 2-column layout
        left_months = [m for m in calendar.months if m.get("column") == "left"]
        right_months = [m for m in calendar.months if m.get("column") == "right"]

        def render_month_block(m):
            m_data = []
            m_data.append([Paragraph(f"<b>{m.get('month_name')} / {m.get('year')}</b>", styles['Normal']), "EVENTOS"])
            
            # Subtable for calendar weeks
            cal_rows = [["D", "2ª", "3ª", "4ª", "5ª", "6ª", "S"]]
            for w in m.get("calendar_weeks", []):
                row = []
                for cell in w:
                    d = cell.get("day")
                    row.append(str(d) if d else "")
                cal_rows.append(row)

            # Events text
            event_colors = {
                "red": palette["red"],
                "green": palette["green"],
                "blue": "#3B82F6",
            }
            events_text = "<br/>".join(
                f"<font color='{event_colors.get(ev.get('color_type'), palette['secondary_text'])}'>"
                f"• <b>{html.escape(str(ev.get('date_label', '')))}</b>: "
                f"{html.escape(str(ev.get('description', '')))}</font>"
                for ev in m.get("events", [])
            )
            if not events_text:
                events_text = "Sem eventos especiais registrados."

            ev_p = Paragraph(f"<font size=6.5>{events_text}</font>", styles['Normal'])

            # Subtable
            cell_rows = [[
                Paragraph(f"<b>{day}</b>", styles["Normal"])
                for day in cal_rows[0]
            ]]
            day_colors = {
                "feriado": (palette["red"], palette["white"]),
                "inicio_aulas": (palette["green"], palette["white"]),
                "nao_letivo": (palette["yellow"], palette["white"]),
                "compensacao": ("#3B82F6", palette["white"]),
                "domingo": (palette["light_red"], palette["red"]),
                "letivo": (palette["white"], palette["text"]),
                "normal": (palette["white"], palette["text"]),
                "empty": (palette["white"], palette["text"]),
            }
            cell_styles = []
            for row_index, week in enumerate(m.get("calendar_weeks", []), start=1):
                rendered_row = []
                for column_index, cell in enumerate(week):
                    day = cell.get("day")
                    day_type = cell.get("type", "empty") if day else "empty"
                    background, foreground = day_colors.get(
                        day_type, (palette["white"], palette["text"])
                    )
                    rendered_row.append(Paragraph(
                        f"<font color='{foreground}'>{html.escape(str(day))}</font>",
                        styles["Normal"]
                    ) if day else "")
                    if day:
                        cell_styles.append(
                            ("BACKGROUND", (column_index, row_index), (column_index, row_index),
                             colors.HexColor(background))
                        )
                cell_rows.append(rendered_row)

            sub_t = Table(cell_rows, colWidths=[24] * 7)
            sub_t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(palette["light_gray"])),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 6.5),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor(palette["border"])),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                *cell_styles,
            ]))

            footer_p = Paragraph(f"<i><font size=6 color='#666'>{m.get('footer_note')}</font></i>", styles['Normal'])

            block_t = Table([
                [
                    Paragraph(html.escape(str(m.get("month_name", ""))), month_title_style),
                    Paragraph("EVENTOS DO MÊS", month_title_style)
                ],
                [sub_t, ev_p],
                [footer_p, ""]
            ], colWidths=[180, 210])
            block_t.setStyle(TableStyle([
                ('SPAN', (0, 2), (1, 2)),
                ('VALIGN', (0, 1), (-1, 1), 'TOP'),
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor(palette["blue"])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('INNERGRID', (0, 0), (-1, 1), 0.3, colors.HexColor('#EEEEEE')),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            return block_t

        two_col_rows = []
        for i in range(max(len(left_months), len(right_months))):
            l_block = render_month_block(left_months[i]) if i < len(left_months) else ""
            r_block = render_month_block(right_months[i]) if i < len(right_months) else ""
            two_col_rows.append([l_block, r_block])

        months_table = Table(two_col_rows, colWidths=[395, 395])
        months_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(months_table)
        elements.append(Spacer(1, 6))

        # Bottom Footer: Compensations & Approval
        comp_data = [["DIAS A COMPENSAR", "DIAS DE COMPENSAÇÃO", "OBSERVAÇÕES"]]
        for row in calendar.compensations:
            comp_data.append([row.get("dias_a_compensar", ""), row.get("dias_compensacao", ""), row.get("observacao", "")])

        comp_table = Table(comp_data, colWidths=[110, 110, 170])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E9ECEF')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6.5),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        left_bottom = Table([
            [Paragraph("<b>DIAS A COMPENSAR / COMPENSAÇÃO</b>", styles['Normal'])],
            [comp_table],
            [Paragraph(f"<b>{calendar.version}</b>", styles['Normal'])]
        ], colWidths=[390])
        left_bottom.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))

        # Director Approval Box
        approval_color = '#155724' if calendar.director_signature_status == "Assinado Digitalmente" else '#856404'
        approval_bg = '#D4EDDA' if calendar.director_signature_status == "Assinado Digitalmente" else '#FFF3CD'
        sig_text = f"""
            <b>APROVAÇÃO DA DIREÇÃO</b><br/>
            <b>Diretor:</b> {calendar.director_name}<br/>
            <b>Status:</b> <font color="{approval_color}">{calendar.director_signature_status}</font><br/>
            <b>Data/Hora:</b> {calendar.signature_date or 'Pendente'}<br/>
            <b>Autenticação:</b> {calendar.signature_hash or 'Não assinado'}<br/>
            <i>{calendar.workload_note}</i>
        """
        right_bottom = Table([[Paragraph(sig_text, styles['Normal'])]], colWidths=[390])
        right_bottom.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor(approval_bg)),
            ('BOX', (0, 0), (0, 0), 1, colors.HexColor(approval_color)),
            ('TOPPADDING', (0, 0), (0, 0), 4),
            ('BOTTOMPADDING', (0, 0), (0, 0), 4),
            ('LEFTPADDING', (0, 0), (0, 0), 8),
            ('RIGHTPADDING', (0, 0), (0, 0), 8),
        ]))

        bottom_table = Table([[left_bottom, right_bottom]], colWidths=[395, 395])
        bottom_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(bottom_table)
        elements.append(Spacer(1, 8))

        legend_items = [
            ("Feriados", palette["red"], palette["white"]),
            ("Início / Término das aulas", palette["green"], palette["white"]),
            ("Dias não letivos / Recesso / Férias", palette["yellow"], palette["white"]),
            ("Dias de compensação / Sábado letivo", "#3B82F6", palette["white"]),
            ("Domingo", palette["light_red"], palette["red"]),
            ("Dias letivos normais", palette["white"], palette["text"]),
        ]
        legend_rows = []
        legend_styles = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette["border"])),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for row_index in range(2):
            row = []
            for column_index in range(3):
                item_index = row_index * 3 + column_index
                label, background, _ = legend_items[item_index]
                swatch_column = column_index * 2
                row.extend([
                    "",
                    Paragraph(
                        html.escape(label),
                        ParagraphStyle(
                            "LegendItem",
                            parent=styles["Normal"],
                            fontName="Helvetica",
                            fontSize=7,
                            textColor=colors.HexColor(palette["secondary_text"]),
                        )
                    )
                ])
                legend_styles.extend([
                    ("BACKGROUND", (swatch_column, row_index), (swatch_column, row_index),
                     colors.HexColor(background)),
                    ("BOX", (swatch_column, row_index), (swatch_column, row_index),
                     0.5, colors.HexColor(palette["border"])),
                ])
            legend_rows.append(row)

        legend_table = Table(
            legend_rows,
            colWidths=[12, 237, 12, 237, 12, 237],
            rowHeights=[20, 20]
        )
        legend_table.setStyle(TableStyle([
            *legend_styles,
        ]))
        elements.append(Paragraph("<b>LEGENDA</b>", styles["Normal"]))
        elements.append(Spacer(1, 3))
        elements.append(legend_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
