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


def _normalize_question(question: str) -> str:
    return question.lower()


def classify_question(question: str) -> Optional[str]:
    normalized = _normalize_question(question)

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


def generate_chart_from_question(question: str) -> Optional[ChartResult]:
    chart_type = classify_question(question)

    if chart_type == "machine_injuries":
        labels, values = _collect_machine_injury_stats()
        if not labels:
            return None
        data = ChartData(
            title="Incidents par type de machine (classification INJURY)",
            x_label="Nombre d'incidents",
            y_label="Type de machine / risque",
            categories=labels,
            values=values,
            caption=_build_percentage_caption(values),
        )
        image_b64 = _render_horizontal_bar(data)
        return ChartResult(chart_data=data, image_base64=image_b64)

    if chart_type == "corrective_measure_effectiveness":
        classification_match = re.search(
            r"(INJURY|FIRST_AID|LOST_TIME|NEAR_MISS|FIRE|CHEMICAL_SPILL)", question, re.I
        )
        classification_filter = (
            classification_match.group(1).upper() if classification_match else None
        )
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
        data = ChartData(
            title=title,
            x_label="Incidents traites",
            y_label="Mesure corrective",
            categories=labels,
            values=values,
            caption=_build_percentage_caption(values),
        )
        image_b64 = _render_horizontal_bar(data)
        return ChartResult(chart_data=data, image_base64=image_b64)

    return None


def generate_summary_report() -> str:
    total_incidents_row = query_db(
        "SELECT COUNT(*) AS total FROM event;", fetch_one=True
    )
    total_incidents = total_incidents_row["total"] if total_incidents_row else 0

    top_types = query_db(
        """
        SELECT e.type, COUNT(*) AS total
        FROM event e
        GROUP BY e.type
        ORDER BY total DESC, e.type ASC
        LIMIT 5;
        """
    )

    top_classifications = query_db(
        """
        SELECT e.classification, COUNT(*) AS total
        FROM event e
        GROUP BY e.classification
        ORDER BY total DESC, e.classification ASC
        LIMIT 5;
        """
    )

    top_measures = query_db(
        """
        SELECT cm.name, COUNT(DISTINCT ecm.event_id) AS total
        FROM corrective_measure cm
        INNER JOIN event_corrective_measure ecm ON cm.measure_id = ecm.measure_id
        GROUP BY cm.name
        ORDER BY total DESC, cm.name ASC
        LIMIT 5;
        """
    )

    latest_events = query_db(
        """
        SELECT e.event_id, e.start_datetime, e.type, e.classification
        FROM event e
        ORDER BY e.start_datetime DESC
        LIMIT 3;
        """
    )

    report_lines = [
        "<h1>Synthese des incidents</h1>",
        "",
        f"- Total d'incidents enregistrés : **{total_incidents}**",
        "",
        "<h2>Top types d'incidents</h2>",
    ]

    if top_types:
        for row in top_types:
            report_lines.append(f"- {row['type']}: {row['total']}")
    else:
        report_lines.append("- Donnees non disponibles")

    report_lines.append("")
    report_lines.append("<h2>Top classifications</h2>")
    if top_classifications:
        for row in top_classifications:
            report_lines.append(f"- {row['classification']}: {row['total']}")
    else:
        report_lines.append("- Donnees non disponibles")

    report_lines.append("")
    report_lines.append("<h2>Mesures correctives les plus mobilisees</h2>")
    if top_measures:
        for row in top_measures:
            report_lines.append(f"- {row['name']}: {row['total']} incidents")
    else:
        report_lines.append("- Donnees non disponibles")

    report_lines.append("")
    report_lines.append("<h2>Derniers incidents declares</h2>")
    if latest_events:
        for row in latest_events:
            report_lines.append(
                f"- Event {row['event_id']} | {row['start_datetime']} | {row['type']} / {row['classification']}"
            )
    else:
        report_lines.append("- Aucun incident recent trouve")

    report_lines.append("")
    report_lines.append("_Fichier genere en markdown_")
    return "<br>".join(report_lines)
