from database import query_db


def _build_default_summary() -> str:
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


def generate_summary_report() -> str:
    return _build_default_summary()
