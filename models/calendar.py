from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import calendar
import json

@dataclass
class DayEntry:
    day: int
    day_type: str # 'letivo', 'feriado', 'inicio_aulas', 'nao_letivo', 'compensacao'
    title: str = ""
    is_active_month: bool = True

@dataclass
class MonthEvent:
    date_label: str
    description: str
    color_type: str # 'blue', 'red', 'green'

@dataclass
class MonthData:
    month_name: str
    year: int
    month_index: int # 7 = Julho, etc.
    calendar_weeks: List[List[Dict[str, Any]]]
    events: List[Dict[str, Any]]
    footer_note: str
    course_days: Dict[str, int] # e.g. {"Aprendizagem Industrial": 5, "Curso Técnico": 5, ...}

@dataclass
class CourseCategory:
    id: str
    title: str
    start_date: str
    end_date: str
    monthly_days: Dict[str, int] # {"JUL": 5, "AGO": 21, ...}
    total_days: int

@dataclass
class CompensationRow:
    dias_a_compensar: str
    dias_compensacao: str
    observacao: str

@dataclass
class SchoolCalendar:
    id: Optional[int]
    title: str = "CALENDÁRIO ESCOLAR"
    unit_code: str = "CFP 5.10"
    semester_year: str = "2º / 2026"
    status: str = "rascunho" # 'rascunho', 'publicado'
    version: str = "Versão 01 - 06/10/2026"
    director_name: str = "Tiago Roberto Ferreira"
    director_signature_status: str = "Pendente" # 'Pendente', 'Assinado Digitalmente'
    signature_date: Optional[str] = None
    signature_hash: Optional[str] = None
    workload_note: str = "* Ampliação da Jornada de trabalho"
    categories: List[Dict[str, Any]] = field(default_factory=list)
    months: List[Dict[str, Any]] = field(default_factory=list)
    compensations: List[Dict[str, Any]] = field(default_factory=list)
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def calculate_totals(self):
        """Recalculates category counts for each month and the selected date range."""
        month_abbrs = {
            1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
            7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
        }
        for cat in self.categories:
            start_date = cat.get("start_date", "-")
            end_date = cat.get("end_date", "-")
            start = datetime.strptime(start_date, "%d/%m/%Y").date() if start_date != "-" else None
            end = datetime.strptime(end_date, "%d/%m/%Y").date() if end_date != "-" else None
            total_days = 0
            can_calculate_total = start is not None and end is not None and start <= end
            monthly_days = cat.setdefault("monthly_days", {})

            for month in self.months:
                month_index = month["month_index"]
                year = month["year"]
                month_abbr = month.get("month_abbr") or month_abbrs.get(month_index)
                days_in_month = 0
                for week in month.get("calendar_weeks", []):
                    for cell in week:
                        day = cell.get("day")
                        if day is None or cell.get("type") not in {
                            "letivo", "inicio_aulas", "compensacao"
                        }:
                            continue
                        current_date = datetime(year, month_index, day).date()
                        if start is not None and current_date < start:
                            continue
                        if end is not None and current_date > end:
                            continue
                        days_in_month += 1
                        if can_calculate_total:
                            total_days += 1

                if month_abbr:
                    monthly_days[month_abbr] = days_in_month
                month.setdefault("course_days", {})[cat["title"]] = days_in_month

            cat["total_days"] = total_days if can_calculate_total else 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "unit_code": self.unit_code,
            "semester_year": self.semester_year,
            "status": self.status,
            "version": self.version,
            "director_name": self.director_name,
            "director_signature_status": self.director_signature_status,
            "signature_date": self.signature_date,
            "signature_hash": self.signature_hash,
            "workload_note": self.workload_note,
            "categories": self.categories,
            "months": self.months,
            "compensations": self.compensations,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def create_default_2026(cls, created_by: Optional[int] = None) -> "SchoolCalendar":
        """Factory method to instantiate the official SENAI 2º / 2026 semester calendar."""
        categories = [
            {
                "id": "aprendizagem",
                "title": "Aprendizagem Industrial",
                "start_date": "27/07/2026",
                "end_date": "18/12/2026",
                "monthly_days": {"JUL": 5, "AGO": 21, "SET": 21, "OUT": 21, "NOV": 19, "DEZ": 14},
                "total_days": 101
            },
            {
                "id": "tecnico",
                "title": "Curso Técnico",
                "start_date": "27/07/2026",
                "end_date": "18/12/2026",
                "monthly_days": {"JUL": 5, "AGO": 21, "SET": 21, "OUT": 21, "NOV": 19, "DEZ": 14},
                "total_days": 101
            },
            {
                "id": "formacao_continuada",
                "title": "Formação Continuada",
                "start_date": "20/07/2026",
                "end_date": "18/12/2026",
                "monthly_days": {"JUL": 10, "AGO": 21, "SET": 21, "OUT": 21, "NOV": 19, "DEZ": 14},
                "total_days": 106
            },
            {
                "id": "graduacao",
                "title": "Graduação / Especialização",
                "start_date": "03/08/2026",
                "end_date": "18/12/2026",
                "monthly_days": {"JUL": 0, "AGO": 21, "SET": 21, "OUT": 21, "NOV": 19, "DEZ": 14},
                "total_days": 96
            }
        ]

        # Calendar generation for Julho to Dezembro 2026
        # Weeks structure: each week is list of 7 days [D, 2ª, 3ª, 4ª, 5ª, 6ª, S]
        # Day dict: {"day": int|None, "type": "letivo"|"feriado"|"inicio_aulas"|"nao_letivo"|"compensacao"|"normal", "title": str}

        # 1. JULHO 2026 (Starts on Wednesday = index 3)
        julho_weeks = [
            [
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": 1, "type": "nao_letivo", "title": "Férias / Recesso Escolar"},
                {"day": 2, "type": "nao_letivo", "title": "Férias / Recesso Escolar"},
                {"day": 3, "type": "nao_letivo", "title": "Férias / Recesso Escolar"},
                {"day": 4, "type": "nao_letivo", "title": "Férias / Recesso Escolar"}
            ],
            [
                {"day": 5, "type": "domingo", "title": "Domingo"},
                {"day": 6, "type": "nao_letivo", "title": "Férias / Recesso Escolar"},
                {"day": 7, "type": "nao_letivo", "title": "Férias / Recesso Escolar"},
                {"day": 8, "type": "nao_letivo", "title": "Férias / Recesso Escolar"},
                {"day": 9, "type": "feriado", "title": "Revolução Constitucionalista de 1932"},
                {"day": 10, "type": "nao_letivo", "title": "Dia a compensar (Ponte 9 de Julho)"},
                {"day": 11, "type": "nao_letivo", "title": "Recesso Escolar"}
            ],
            [
                {"day": 12, "type": "domingo", "title": "Domingo"},
                {"day": 13, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": 14, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": 15, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": 16, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": 17, "type": "nao_letivo", "title": "Fim do Recesso Escolar Docente"},
                {"day": 18, "type": "compensacao", "title": "Dia de compensação (Ponte 10/Jul)"}
            ],
            [
                {"day": 19, "type": "domingo", "title": "Domingo"},
                {"day": 20, "type": "inicio_aulas", "title": "Início Formação Continuada / Planejamento"},
                {"day": 21, "type": "letivo", "title": "Planejamento Pedagógico / Aulas FC"},
                {"day": 22, "type": "letivo", "title": "Planejamento Pedagógico / Aulas FC"},
                {"day": 23, "type": "letivo", "title": "Planejamento Pedagógico / Aulas FC"},
                {"day": 24, "type": "letivo", "title": "Planejamento Pedagógico / Aulas FC"},
                {"day": 25, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 26, "type": "domingo", "title": "Domingo"},
                {"day": 27, "type": "inicio_aulas", "title": "Início das Aulas (Aprendizagem e Técnico)"},
                {"day": 28, "type": "letivo", "title": "Dia Letivo"},
                {"day": 29, "type": "letivo", "title": "Dia Letivo"},
                {"day": 30, "type": "letivo", "title": "Dia Letivo"},
                {"day": 31, "type": "letivo", "title": "Dia Letivo"},
                {"day": None, "type": "empty", "title": ""}
            ]
        ]

        # 2. AGOSTO 2026 (Starts on Saturday = index 6)
        agosto_weeks = [
            [
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": 1, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 2, "type": "domingo", "title": "Domingo"},
                {"day": 3, "type": "inicio_aulas", "title": "Início das Aulas Graduação / Especialização"},
                {"day": 4, "type": "letivo", "title": "Dia Letivo"},
                {"day": 5, "type": "letivo", "title": "Dia Letivo"},
                {"day": 6, "type": "letivo", "title": "Dia Letivo"},
                {"day": 7, "type": "letivo", "title": "Dia Letivo"},
                {"day": 8, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 9, "type": "domingo", "title": "Domingo - Dia dos Pais"},
                {"day": 10, "type": "letivo", "title": "Dia Letivo"},
                {"day": 11, "type": "letivo", "title": "Dia Letivo"},
                {"day": 12, "type": "letivo", "title": "Dia Letivo"},
                {"day": 13, "type": "letivo", "title": "Dia Letivo"},
                {"day": 14, "type": "letivo", "title": "Dia Letivo"},
                {"day": 15, "type": "normal", "title": "Sábado / Reunião Pedagógica"}
            ],
            [
                {"day": 16, "type": "domingo", "title": "Domingo"},
                {"day": 17, "type": "letivo", "title": "Dia Letivo"},
                {"day": 18, "type": "letivo", "title": "Dia Letivo"},
                {"day": 19, "type": "letivo", "title": "Dia Letivo"},
                {"day": 20, "type": "letivo", "title": "Dia Letivo"},
                {"day": 21, "type": "letivo", "title": "Dia Letivo"},
                {"day": 22, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 23, "type": "domingo", "title": "Domingo"},
                {"day": 24, "type": "letivo", "title": "Dia Letivo"},
                {"day": 25, "type": "letivo", "title": "Dia Letivo"},
                {"day": 26, "type": "letivo", "title": "Dia Letivo"},
                {"day": 27, "type": "letivo", "title": "Dia Letivo"},
                {"day": 28, "type": "letivo", "title": "Dia Letivo"},
                {"day": 29, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 30, "type": "domingo", "title": "Domingo"},
                {"day": 31, "type": "letivo", "title": "Dia Letivo"},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""}
            ]
        ]

        # 3. SETEMBRO 2026 (Starts on Tuesday = index 2)
        setembro_weeks = [
            [
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": 1, "type": "letivo", "title": "Dia Letivo"},
                {"day": 2, "type": "letivo", "title": "Dia Letivo"},
                {"day": 3, "type": "letivo", "title": "Dia Letivo"},
                {"day": 4, "type": "letivo", "title": "Dia Letivo"},
                {"day": 5, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 6, "type": "domingo", "title": "Domingo"},
                {"day": 7, "type": "feriado", "title": "Independência do Brasil"},
                {"day": 8, "type": "letivo", "title": "Dia Letivo"},
                {"day": 9, "type": "letivo", "title": "Dia Letivo"},
                {"day": 10, "type": "letivo", "title": "Dia Letivo"},
                {"day": 11, "type": "letivo", "title": "Dia Letivo"},
                {"day": 12, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 13, "type": "domingo", "title": "Domingo"},
                {"day": 14, "type": "letivo", "title": "Dia Letivo"},
                {"day": 15, "type": "letivo", "title": "Dia Letivo"},
                {"day": 16, "type": "letivo", "title": "Dia Letivo"},
                {"day": 17, "type": "letivo", "title": "Dia Letivo"},
                {"day": 18, "type": "letivo", "title": "Dia Letivo"},
                {"day": 19, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 20, "type": "domingo", "title": "Domingo"},
                {"day": 21, "type": "letivo", "title": "Dia Nacional de Luta da Pessoa com Deficiência"},
                {"day": 22, "type": "letivo", "title": "Dia Letivo"},
                {"day": 23, "type": "letivo", "title": "Dia Letivo"},
                {"day": 24, "type": "letivo", "title": "Dia Letivo"},
                {"day": 25, "type": "letivo", "title": "Dia Letivo"},
                {"day": 26, "type": "compensacao", "title": "Sábado Letivo (Compensação 07/Dez / Mostra Tecnológica)"}
            ],
            [
                {"day": 27, "type": "domingo", "title": "Domingo"},
                {"day": 28, "type": "letivo", "title": "Dia Letivo"},
                {"day": 29, "type": "letivo", "title": "Dia Letivo"},
                {"day": 30, "type": "letivo", "title": "Dia Letivo"},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""}
            ]
        ]

        # 4. OUTUBRO 2026 (Starts on Thursday = index 4)
        outubro_weeks = [
            [
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": 1, "type": "letivo", "title": "Dia Letivo"},
                {"day": 2, "type": "letivo", "title": "Dia Letivo"},
                {"day": 3, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 4, "type": "domingo", "title": "Domingo"},
                {"day": 5, "type": "letivo", "title": "Dia Letivo"},
                {"day": 6, "type": "letivo", "title": "Dia Letivo"},
                {"day": 7, "type": "letivo", "title": "Dia Letivo"},
                {"day": 8, "type": "letivo", "title": "Dia Letivo"},
                {"day": 9, "type": "letivo", "title": "Dia Letivo"},
                {"day": 10, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 11, "type": "domingo", "title": "Domingo"},
                {"day": 12, "type": "feriado", "title": "Nossa Senhora Aparecida / Dia das Crianças"},
                {"day": 13, "type": "letivo", "title": "Dia Letivo"},
                {"day": 14, "type": "letivo", "title": "Dia Letivo"},
                {"day": 15, "type": "nao_letivo", "title": "Dia do Professor (Não Letivo)"},
                {"day": 16, "type": "letivo", "title": "Dia Letivo"},
                {"day": 17, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 18, "type": "domingo", "title": "Domingo"},
                {"day": 19, "type": "letivo", "title": "Dia Letivo"},
                {"day": 20, "type": "letivo", "title": "Dia Letivo"},
                {"day": 21, "type": "letivo", "title": "Dia Letivo"},
                {"day": 22, "type": "letivo", "title": "Dia Letivo"},
                {"day": 23, "type": "letivo", "title": "Dia Letivo"},
                {"day": 24, "type": "normal", "title": "Sábado - Feira de Profissões SENAI"}
            ],
            [
                {"day": 25, "type": "domingo", "title": "Domingo"},
                {"day": 26, "type": "letivo", "title": "Dia Letivo"},
                {"day": 27, "type": "letivo", "title": "Dia Letivo"},
                {"day": 28, "type": "letivo", "title": "Dia Letivo"},
                {"day": 29, "type": "letivo", "title": "Dia Letivo"},
                {"day": 30, "type": "letivo", "title": "Dia Letivo"},
                {"day": 31, "type": "normal", "title": "Sábado"}
            ]
        ]

        # 5. NOVEMBRO 2026 (Starts on Sunday = index 0)
        novembro_weeks = [
            [
                {"day": 1, "type": "domingo", "title": "Domingo"},
                {"day": 2, "type": "feriado", "title": "Finados"},
                {"day": 3, "type": "letivo", "title": "Dia Letivo"},
                {"day": 4, "type": "letivo", "title": "Dia Letivo"},
                {"day": 5, "type": "letivo", "title": "Dia Letivo"},
                {"day": 6, "type": "letivo", "title": "Dia Letivo"},
                {"day": 7, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 8, "type": "domingo", "title": "Domingo"},
                {"day": 9, "type": "letivo", "title": "Dia Letivo"},
                {"day": 10, "type": "letivo", "title": "Dia Letivo"},
                {"day": 11, "type": "letivo", "title": "Dia Letivo"},
                {"day": 12, "type": "letivo", "title": "Dia Letivo"},
                {"day": 13, "type": "letivo", "title": "Dia Letivo"},
                {"day": 14, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 15, "type": "feriado", "title": "Proclamação da República"},
                {"day": 16, "type": "letivo", "title": "Dia Letivo"},
                {"day": 17, "type": "letivo", "title": "Dia Letivo"},
                {"day": 18, "type": "letivo", "title": "Dia Letivo"},
                {"day": 19, "type": "letivo", "title": "Dia Letivo"},
                {"day": 20, "type": "feriado", "title": "Dia Nacional da Consciência Negra"},
                {"day": 21, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 22, "type": "domingo", "title": "Domingo"},
                {"day": 23, "type": "letivo", "title": "Dia Letivo"},
                {"day": 24, "type": "letivo", "title": "Dia Letivo"},
                {"day": 25, "type": "letivo", "title": "Dia Letivo"},
                {"day": 26, "type": "letivo", "title": "Dia Letivo"},
                {"day": 27, "type": "letivo", "title": "Dia Letivo"},
                {"day": 28, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 29, "type": "domingo", "title": "Domingo"},
                {"day": 30, "type": "letivo", "title": "Dia Letivo"},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""}
            ]
        ]

        # 6. DEZEMBRO 2026 (Starts on Tuesday = index 2)
        dezembro_weeks = [
            [
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""},
                {"day": 1, "type": "letivo", "title": "Dia Letivo"},
                {"day": 2, "type": "letivo", "title": "Dia Letivo"},
                {"day": 3, "type": "letivo", "title": "Dia Letivo"},
                {"day": 4, "type": "letivo", "title": "Dia Letivo"},
                {"day": 5, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 6, "type": "domingo", "title": "Domingo"},
                {"day": 7, "type": "nao_letivo", "title": "Dia a compensar (Ponte)"},
                {"day": 8, "type": "letivo", "title": "Dia Letivo"},
                {"day": 9, "type": "letivo", "title": "Dia Letivo"},
                {"day": 10, "type": "letivo", "title": "Dia Letivo"},
                {"day": 11, "type": "letivo", "title": "Dia Letivo"},
                {"day": 12, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 13, "type": "domingo", "title": "Domingo"},
                {"day": 14, "type": "letivo", "title": "Dia Letivo"},
                {"day": 15, "type": "letivo", "title": "Dia Letivo"},
                {"day": 16, "type": "letivo", "title": "Dia Letivo"},
                {"day": 17, "type": "letivo", "title": "Dia Letivo"},
                {"day": 18, "type": "inicio_aulas", "title": "Término do Semestre Letivo"},
                {"day": 19, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 20, "type": "domingo", "title": "Domingo"},
                {"day": 21, "type": "nao_letivo", "title": "Exames Finais / Conselho de Classe"},
                {"day": 22, "type": "nao_letivo", "title": "Exames Finais / Conselho de Classe"},
                {"day": 23, "type": "nao_letivo", "title": "Conselho de Classe e Encerramento"},
                {"day": 24, "type": "nao_letivo", "title": "Véspera de Natal (Recesso)"},
                {"day": 25, "type": "feriado", "title": "Natal"},
                {"day": 26, "type": "normal", "title": "Sábado"}
            ],
            [
                {"day": 27, "type": "domingo", "title": "Domingo"},
                {"day": 28, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": 29, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": 30, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": 31, "type": "nao_letivo", "title": "Recesso Escolar"},
                {"day": None, "type": "empty", "title": ""},
                {"day": None, "type": "empty", "title": ""}
            ]
        ]

        months = [
            {
                "month_name": "JULHO",
                "year": 2026,
                "month_index": 7,
                "column": "left",
                "calendar_weeks": julho_weeks,
                "events": [
                    {"date_label": "09/07", "description": "Revolução Constitucionalista", "color_type": "red"},
                    {"date_label": "10/07", "description": "Dia a compensar (Ponte)", "color_type": "blue"},
                    {"date_label": "18/07", "description": "Dia de compensação (Sábado Letivo)", "color_type": "green"},
                    {"date_label": "20/07", "description": "Início Formação Continuada / Planejamento", "color_type": "green"},
                    {"date_label": "27/07", "description": "Início Aulas Aprendizagem e Técnico", "color_type": "green"}
                ],
                "footer_note": "Felicidade na escola - Acolhimento e Integração 2026",
                "course_days": {
                    "Aprendizagem Industrial": 5,
                    "Curso Técnico": 5,
                    "Formação Continuada": 10,
                    "Graduação / Especialização": 0
                }
            },
            {
                "month_name": "AGOSTO",
                "year": 2026,
                "month_index": 8,
                "column": "left",
                "events": [
                    {"date_label": "03/08", "description": "Início Aulas Graduação / Especialização", "color_type": "green"},
                    {"date_label": "09/08", "description": "Dia dos Pais", "color_type": "blue"},
                    {"date_label": "15/08", "description": "Reunião Pedagógica Docente", "color_type": "blue"}
                ],
                "calendar_weeks": agosto_weeks,
                "footer_note": "Agosto Lilás: Campanha de Conscientização, Respeito e Cuidado",
                "course_days": {
                    "Aprendizagem Industrial": 21,
                    "Curso Técnico": 21,
                    "Formação Continuada": 21,
                    "Graduação / Especialização": 21
                }
            },
            {
                "month_name": "SETEMBRO",
                "year": 2026,
                "month_index": 9,
                "column": "left",
                "calendar_weeks": setembro_weeks,
                "events": [
                    {"date_label": "07/09", "description": "Independência do Brasil", "color_type": "red"},
                    {"date_label": "21/09", "description": "Dia Nacional de Luta da Pessoa com Deficiência", "color_type": "blue"},
                    {"date_label": "26/09", "description": "Mostra Tecnológica SENAI (Compensação 07/Dez)", "color_type": "green"}
                ],
                "footer_note": "Setembro Amarelo: Valorização da Vida, Saúde Mental e Empatia",
                "course_days": {
                    "Aprendizagem Industrial": 21,
                    "Curso Técnico": 21,
                    "Formação Continuada": 21,
                    "Graduação / Especialização": 21
                }
            },
            {
                "month_name": "OUTUBRO",
                "year": 2026,
                "month_index": 10,
                "column": "right",
                "calendar_weeks": outubro_weeks,
                "events": [
                    {"date_label": "12/10", "description": "Nossa Senhora Aparecida / Dia das Crianças", "color_type": "red"},
                    {"date_label": "15/10", "description": "Dia do Professor (Não Letivo)", "color_type": "blue"},
                    {"date_label": "24/10", "description": "Feira de Profissões e Inovação", "color_type": "green"}
                ],
                "footer_note": "Outubro Rosa: Prevenção, Saúde e Conscientização",
                "course_days": {
                    "Aprendizagem Industrial": 21,
                    "Curso Técnico": 21,
                    "Formação Continuada": 21,
                    "Graduação / Especialização": 21
                }
            },
            {
                "month_name": "NOVEMBRO",
                "year": 2026,
                "month_index": 11,
                "column": "right",
                "calendar_weeks": novembro_weeks,
                "events": [
                    {"date_label": "02/11", "description": "Finados", "color_type": "red"},
                    {"date_label": "15/11", "description": "Proclamação da República", "color_type": "red"},
                    {"date_label": "20/11", "description": "Dia Nacional da Consciência Negra", "color_type": "red"}
                ],
                "footer_note": "Novembro Azul: Cuidado com a Saúde do Homem e Prevenção",
                "course_days": {
                    "Aprendizagem Industrial": 19,
                    "Curso Técnico": 19,
                    "Formação Continuada": 19,
                    "Graduação / Especialização": 19
                }
            },
            {
                "month_name": "DEZEMBRO",
                "year": 2026,
                "month_index": 12,
                "column": "right",
                "calendar_weeks": dezembro_weeks,
                "events": [
                    {"date_label": "07/12", "description": "Dia a compensar (Ponte)", "color_type": "blue"},
                    {"date_label": "18/12", "description": "Término do Semestre Letivo", "color_type": "green"},
                    {"date_label": "21 a 23/12", "description": "Conselho de Classe e Exames", "color_type": "blue"},
                    {"date_label": "25/12", "description": "Natal", "color_type": "red"}
                ],
                "footer_note": "Encerramento do 2º Semestre Letivo de 2026",
                "course_days": {
                    "Aprendizagem Industrial": 14,
                    "Curso Técnico": 14,
                    "Formação Continuada": 14,
                    "Graduação / Especialização": 14
                }
            }
        ]

        compensations = [
            {
                "dias_a_compensar": "10/jul",
                "dias_compensacao": "18/jul",
                "observacao": "Ponte Revolução Constitucionalista (Sexta p/ Sábado)"
            },
            {
                "dias_a_compensar": "07/dez",
                "dias_compensacao": "26/set",
                "observacao": "Compensação Segunda-feira p/ Sábado Mostra Tecnológica"
            }
        ]

        return cls(
            id=None,
            title="CALENDÁRIO ESCOLAR",
            unit_code="CFP 5.10",
            semester_year="2º / 2026",
            status="rascunho",
            version="Versão 01 - 06/10/2026",
            director_name="Tiago Roberto Ferreira",
            director_signature_status="Pendente",
            signature_date=None,
            signature_hash=None,
            workload_note="* Ampliação da Jornada de trabalho",
            categories=categories,
            months=months,
            compensations=compensations,
            created_by=created_by
        )

    @classmethod
    def create_for_period(
        cls,
        year: int,
        semester: int,
        categories: List[Dict[str, Any]],
        created_by: Optional[int] = None
    ) -> "SchoolCalendar":
        month_names = {
            1: ("JANEIRO", "JAN"), 2: ("FEVEREIRO", "FEV"), 3: ("MARÇO", "MAR"),
            4: ("ABRIL", "ABR"), 5: ("MAIO", "MAI"), 6: ("JUNHO", "JUN"),
            7: ("JULHO", "JUL"), 8: ("AGOSTO", "AGO"), 9: ("SETEMBRO", "SET"),
            10: ("OUTUBRO", "OUT"), 11: ("NOVEMBRO", "NOV"), 12: ("DEZEMBRO", "DEZ")
        }
        month_indexes = range(1, 7) if semester == 1 else range(7, 13)
        month_data = []
        categories_data = []

        for category in categories:
            categories_data.append({
                "id": category["id"],
                "title": category["name"],
                "start_date": "-",
                "end_date": "-",
                "monthly_days": {},
                "total_days": 0
            })

        for month_index in month_indexes:
            month_name, month_abbr = month_names[month_index]
            first_weekday, days_in_month = calendar.monthrange(year, month_index)
            first_sunday_index = (first_weekday + 1) % 7
            cells = [
                {"day": None, "type": "empty", "title": "", "is_active_month": False}
                for _ in range(first_sunday_index)
            ]
            month_school_days = 0

            for day in range(1, days_in_month + 1):
                weekday = calendar.weekday(year, month_index, day)
                is_school_day = weekday < 5
                day_type = "letivo" if is_school_day else ("domingo" if weekday == 6 else "nao_letivo")
                title = "Dia letivo" if is_school_day else ("Domingo" if weekday == 6 else "Sábado")
                cells.append({
                    "day": day,
                    "type": day_type,
                    "title": title,
                    "is_active_month": True
                })
                month_school_days += int(is_school_day)

            while len(cells) % 7:
                cells.append({"day": None, "type": "empty", "title": "", "is_active_month": False})
            weeks = [cells[offset:offset + 7] for offset in range(0, len(cells), 7)]
            course_days = {}
            for category_data in categories_data:
                category_data["monthly_days"][month_abbr] = month_school_days
                course_days[category_data["title"]] = month_school_days
            month_data.append({
                "month_name": month_name,
                "month_abbr": month_abbr,
                "year": year,
                "month_index": month_index,
                "column": "left" if len(month_data) < 3 else "right",
                "calendar_weeks": weeks,
                "events": [],
                "footer_note": "Calendário-base: revise feriados, recessos e eventos.",
                "course_days": course_days
            })

        return cls(
            id=None,
            semester_year=f"{semester}º / {year}",
            categories=categories_data,
            months=month_data,
            compensations=[],
            created_by=created_by
        )
