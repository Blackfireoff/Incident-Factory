import base64
import io
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import matplotlib

# Force non-interactive backend (CLI/server environments)
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from database import query_db


MACHINE_KEYWORDS = [
    "machine",
    "press",
    "lathe",
    "tour",
    "robot",
    "equipement",
    "équipement",
    "equipment",
]

INJURY_KEYWORDS = ["injury", "blessure", "trauma"]

CORRECTIVE_KEYWORDS = ["mesure", "corrective", "action corrective", "correction"]

EMPLOYEE_KEYWORDS = [
    "employe",
    "employés",
    "employées",
    "employee",
    "employees",
    "personnel",
    "collaborateur",
    "collaborateurs",
    "personne",
    "personnes",
    "agent",
    "agents",
    "worker",
    "workers",
]

REPORT_KEYWORDS = [
    "declare",
    "déclar",
    "declar",
    "signale",
    "signal",
    "rapport",
    "report",
]

EVENT_KEYWORDS = ["evenement", "évènement", "événement", "incidents", "incident"]

YEAR_PATTERNS = [
    r"par\s+(annee|année|an)",
    r"pour\s+chaque\s+annee",
    r"pour\s+chaque\s+année",
    r"chaque\s+annee",
    r"par\s+year",
    r"per\s+year",
    r"each\s+year",
]

CLASSIFICATION_HINT_PATTERN = re.compile(
    r"(INJURY|FIRST_AID|LOST_TIME|NEAR_MISS|FIRE|CHEMICAL_SPILL)", re.I
)

SUPPORTED_SCENARIOS = {
    "incidents_per_year": "Evolution du volume d'incidents par année",
    "machine_injuries": "Typologie des incidents liés aux machines (classification INJURY)",
    "corrective_measure_effectiveness": "Mesures correctives les plus utilisées",
    "top_reporters": "Employés ayant déclaré le plus d'événements",
}


@dataclass
class ChartData:
    title: str
    x_label: str
    y_label: str
    categories: List[str]
    values: List[float]
    caption: Optional[str] = None


@dataclass
class ChartResult:
    chart_data: ChartData
    image_base64: str
    image_mime: str = "image/png"
    scenario: Optional[str] = None


@dataclass
class AnalyticsDataset:
    scenario: str
    chart_data: ChartData
    orientation: str = "horizontal"


def _normalize_question(question: str) -> str:
    return question.lower()


def classify_question(question: str) -> Optional[str]:
    normalized = _normalize_question(question)

    if any(re.search(pattern, normalized) for pattern in YEAR_PATTERNS):
        return "incidents_per_year"

    if any(word in normalized for word in EMPLOYEE_KEYWORDS) and (
        any(word in normalized for word in REPORT_KEYWORDS)
        or any(word in normalized for word in EVENT_KEYWORDS)
    ):
        return "top_reporters"

    if any(word in normalized for word in MACHINE_KEYWORDS) and any(
        kw in normalized for kw in INJURY_KEYWORDS
    ):
        return "machine_injuries"

    if any(word in normalized for word in CORRECTIVE_KEYWORDS):
        return "corrective_measure_effectiveness"

    return None


def _collect_machine_injury_stats(limit: int = 10) -> Tuple[List[str], List[int]]:
    sql = """
        SELECT
            COALESCE(r.name, 'Non specifie') AS risk_name,
            COUNT(*) AS incident_count
        FROM event e
        LEFT JOIN event_risk er ON er.event_id = e.event_id
        LEFT JOIN risk r ON r.risk_id = er.risk_id
        WHERE e.classification = 'INJURY'
        GROUP BY risk_name
        ORDER BY incident_count DESC, risk_name ASC
        LIMIT %s;
    """
    rows = query_db(sql, params=(limit,))

    if not rows:
        return [], []

    filtered = []
    for row in rows:
        name = row["risk_name"] or "Non specifie"
        if any(keyword in name.lower() for keyword in MACHINE_KEYWORDS):
            filtered.append(row)

    data_source = filtered if filtered else rows
    labels = [row["risk_name"] or "Non specifie" for row in data_source]
    values = [int(row["incident_count"]) for row in data_source]
    return labels, values


def _collect_corrective_measure_stats(
    limit: int = 10, classification_filter: Optional[str] = None
) -> Tuple[List[str], List[int]]:
    where_clause = ""
    params: List[str] = []

    if classification_filter:
        where_clause = "AND e.classification = %s"
        params.append(classification_filter.upper())

    sql = f"""
        SELECT
            cm.name AS measure_name,
            COUNT(DISTINCT e.event_id) AS event_count
        FROM corrective_measure cm
        INNER JOIN event_corrective_measure ecm ON cm.measure_id = ecm.measure_id
        INNER JOIN event e ON e.event_id = ecm.event_id
        WHERE 1=1
        {where_clause}
        GROUP BY cm.name
        ORDER BY event_count DESC, cm.name ASC
        LIMIT %s;
    """
    params.append(limit)
    rows = query_db(sql, params=tuple(params))

    labels = [row["measure_name"] for row in rows]
    values = [int(row["event_count"]) for row in rows]
    return labels, values


def _build_percentage_caption(values: List[int]) -> Optional[str]:
    total = sum(values)
    if total == 0:
        return None

    percentages = [
        f"{round((value / total) * 100)}%"
        for value in values[: min(len(values), 5)]
    ]
    return "Top parts: " + ", ".join(percentages)


def _render_horizontal_bar(chart_data: ChartData) -> str:
    fig, ax = plt.subplots(figsize=(10, max(4, len(chart_data.categories) * 0.6)))
    y_positions = range(len(chart_data.categories))
    ax.barh(y_positions, chart_data.values, color="#1f77b4")
    ax.set_yticks(y_positions)
    ax.set_yticklabels(chart_data.categories)
    ax.set_xlabel(chart_data.x_label)
    ax.set_ylabel(chart_data.y_label)
    ax.set_title(chart_data.title)
    ax.invert_yaxis()

    for idx, value in enumerate(chart_data.values):
        ax.text(
            value + max(chart_data.values) * 0.01,
            idx,
            f"{value}",
            va="center",
            fontsize=9,
        )

    if chart_data.caption:
        fig.text(0.01, 0.01, chart_data.caption, ha="left", fontsize=9)

    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def _render_vertical_bar(chart_data: ChartData) -> str:
    fig_width = max(6, len(chart_data.categories) * 0.7)
    fig, ax = plt.subplots(figsize=(fig_width, 5))
    positions = range(len(chart_data.categories))
    ax.bar(positions, chart_data.values, color="#1f77b4")
    ax.set_xlabel(chart_data.x_label)
    ax.set_ylabel(chart_data.y_label)
    ax.set_title(chart_data.title)

    rotation = 0
    if len(chart_data.categories) > 6:
        rotation = 45
    ax.set_xticks(list(positions))
    ax.set_xticklabels(
        chart_data.categories,
        rotation=rotation,
        ha="right" if rotation else "center",
    )

    for idx, value in enumerate(chart_data.values):
        ax.text(
            idx,
            value + max(chart_data.values) * 0.02,
            f"{value}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    if chart_data.caption:
        fig.text(0.01, 0.01, chart_data.caption, ha="left", fontsize=9)

    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def build_dataset(question: str) -> Optional[AnalyticsDataset]:
    scenario = classify_question(question)
    if not scenario:
        return None

    if scenario == "incidents_per_year":
        labels, values, caption = _collect_incidents_per_year()
        if not labels:
            return None
        chart_data = ChartData(
            title="Nombre d'incidents par année",
            x_label="Année",
            y_label="Nombre d'incidents",
            categories=labels,
            values=values,
            caption=caption,
        )
        return AnalyticsDataset(
            scenario=scenario,
            chart_data=chart_data,
            orientation="vertical",
        )

    if scenario == "top_reporters":
        labels, values, caption = _collect_top_reporters()
        if not labels:
            return None
        chart_data = ChartData(
            title="Employés ayant déclaré le plus d'événements",
            x_label="Incidents déclarés",
            y_label="Employé",
            categories=labels,
            values=values,
            caption=caption,
        )
        return AnalyticsDataset(
            scenario=scenario,
            chart_data=chart_data,
            orientation="horizontal",
        )

    if scenario == "machine_injuries":
        labels, values = _collect_machine_injury_stats()
        if not labels:
            return None
        chart_data = ChartData(
            title="Incidents par type de machine (classification INJURY)",
            x_label="Nombre d'incidents",
            y_label="Type de machine / risque",
            categories=labels,
            values=values,
            caption=_build_percentage_caption(values),
        )
        return AnalyticsDataset(
            scenario=scenario,
            chart_data=chart_data,
            orientation="horizontal",
        )

    if scenario == "corrective_measure_effectiveness":
        classification_filter = _extract_classification_filter(question)
        labels, values = _collect_corrective_measure_stats(
            classification_filter=classification_filter
        )
        if not labels:
            return None
        title = (
            "Mesures correctives les plus mobilisees"
            if not classification_filter
            else f"Mesures correctives pour {classification_filter}"
        )
        chart_data = ChartData(
            title=title,
            x_label="Incidents traites",
            y_label="Mesure corrective",
            categories=labels,
            values=values,
            caption=_build_percentage_caption(values),
        )
        return AnalyticsDataset(
            scenario=scenario,
            chart_data=chart_data,
            orientation="horizontal",
        )

    return None


def generate_chart_from_question(question: str) -> Optional[ChartResult]:
    dataset = build_dataset(question)
    if not dataset:
        return None

    if dataset.orientation == "vertical":
        image_b64 = _render_vertical_bar(dataset.chart_data)
    else:
        image_b64 = _render_horizontal_bar(dataset.chart_data)

    return ChartResult(
        chart_data=dataset.chart_data,
        image_base64=image_b64,
        scenario=dataset.scenario,
    )


def _collect_incidents_per_year(limit: int = 15) -> Tuple[List[str], List[int], Optional[str]]:
    sql = """
        SELECT
            EXTRACT(YEAR FROM e.start_datetime) AS year,
            COUNT(*) AS total
        FROM event e
        GROUP BY year
        ORDER BY year ASC;
    """
    rows = query_db(sql)
    if not rows:
        return [], [], None

    caption = None
    if limit and len(rows) > limit:
        rows = rows[-limit:]
        caption = f"Affichage des {limit} dernières années."

    labels = [str(int(row["year"])) for row in rows if row["year"] is not None]
    values = [int(row["total"]) for row in rows if row["year"] is not None]

    if not labels:
        return [], [], None

    return labels, values, caption


def _collect_top_reporters(limit: int = 10) -> Tuple[List[str], List[int], Optional[str]]:
    sql = """
        SELECT
            p.person_id,
            p.name,
            p.family_name,
            COALESCE(p.role, '') AS role,
            COUNT(*) AS total
        FROM event e
        INNER JOIN person p ON e.declared_by_id = p.person_id
        GROUP BY p.person_id, p.name, p.family_name, p.role
        ORDER BY total DESC, p.person_id ASC
        LIMIT %s;
    """
    rows = query_db(sql, params=(limit,))

    if not rows:
        return [], [], None

    labels: List[str] = []
    values: List[int] = []

    for row in rows:
        name_parts = [row.get("name") or "", row.get("family_name") or ""]
        label = " ".join(part for part in name_parts if part).strip() or f"ID {row['person_id']}"
        role = row.get("role")
        if role:
            label = f"{label} ({role})"
        labels.append(label)
        values.append(int(row["total"]))

    caption = None
    if len(rows) == limit:
        caption = f"Top {limit} déclarants."

    return labels, values, caption


def _extract_classification_filter(question: str) -> Optional[str]:
    match = CLASSIFICATION_HINT_PATTERN.search(question or "")
    if not match:
        return None
    return match.group(1).upper()
