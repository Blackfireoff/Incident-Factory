from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, date
from decimal import Decimal
from database import query_db
from fastapi import Request
from opensearchpy import OpenSearch
from services.opensearch_service import get_opensearch_client, ensure_index, INDEX_NAME
import boto3
import json
from typing import List, Optional, Tuple
import re
import unicodedata
from fastapi.middleware.cors import CORSMiddleware
from ai_router import router as ai_api_router

origins = [
    "*"
]





INDEX_NAME = "incidents"
app = FastAPI(title="FireTeams API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     # évite "*" si tu utilises des cookies/credentials
    allow_credentials=True,    # mets False si tu veux pouvoir utiliser "*"
    allow_methods=["*"],       # GET, POST, PUT, DELETE, OPTIONS…
    allow_headers=["*"],       # Autorise tous les headers (dont Content-Type, Authorization, etc.)
)

app.include_router(ai_api_router)

# Fonction pour convertir les datetime, date et Decimal en types JSON-serialisables
def convert_datetime_to_str(obj):
    """Convertit les objets datetime, date et Decimal en types JSON-serialisables"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj


@app.on_event("startup")
def setup_search():
    """S'assure que l'index OpenSearch existe au démarrage"""
    client = get_opensearch_client()
    ensure_index(client, INDEX_NAME)


@app.get("/")
async def root():
    return {"message": "FireTeams API is running"}

@app.get("/db/status")
async def db_status():
    """Route pour vérifier la connexion à la base de données"""
    try:
        version = query_db("SELECT version();", fetch_one=True)
        db_info = query_db("SELECT current_database(), current_user;", fetch_one=True)
        
        return JSONResponse({
            "status": "success",
            "message": "Connexion à la base de données réussie",
            "database": db_info["current_database"],
            "user": db_info["current_user"],
            "postgres_version": version["version"]
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur de connexion à la base de données: {str(e)}"
            }
        )

@app.get("/db/tables")
async def get_tables():
    """Route pour lister les tables de la base de données"""
    try:
        tables = query_db("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        return JSONResponse({
            "status": "success",
            "tables": [table["table_name"] for table in tables]
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des tables: {str(e)}"
            }
        )

@app.get("/get_events")
async def get_events(
    offset: int = 0,
    limit: int = Query(20, ge=1, le=200),
    event_id: Optional[int] = Query(None),
    employee_matricule: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None, alias="type"),
    classification: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Route pour récupérer les événements avec pagination et filtres optionnels"""
    try:
        # Validation: offset doit être >= 0
        if offset < 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Offset must be a non-negative integer"
                }
            )

        if start_date and end_date and end_date < start_date:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "end_date must be greater than or equal to start_date"
                }
            )

        sanitized_employee = employee_matricule.strip() if employee_matricule else None
        sanitized_type = event_type.strip() if event_type else None
        sanitized_classification = classification.strip() if classification else None

        filters_sql: list[str] = []
        filter_params: list = []

        if event_id is not None:
            filters_sql.append("e.event_id = %s")
            filter_params.append(event_id)

        if sanitized_employee:
            filters_sql.append("p.matricule ILIKE %s")
            filter_params.append(f"%{sanitized_employee}%")

        if sanitized_type:
            filters_sql.append("e.type = %s")
            filter_params.append(sanitized_type)

        if sanitized_classification:
            filters_sql.append("e.classification = %s")
            filter_params.append(sanitized_classification)

        if start_date:
            filters_sql.append("DATE(e.start_datetime) >= %s")
            filter_params.append(start_date)

        if end_date:
            filters_sql.append("DATE(e.start_datetime) <= %s")
            filter_params.append(end_date)

        where_clause = ""
        if filters_sql:
            where_clause = "WHERE " + " AND ".join(filters_sql)

        count_query = f"""
            SELECT COUNT(*) as total_event
            FROM event e
            LEFT JOIN person p ON e.declared_by_id = p.person_id
            {where_clause};
        """
        count_params = tuple(filter_params)
        total_count_rows = query_db(count_query, params=count_params if count_params else None)
        total_count_value = total_count_rows[0]["total_event"] if total_count_rows else 0
        
        # Récupérer les lignes avec tous les champs nécessaires pour l'interface Incident
        events_query = f"""
            SELECT 
                e.event_id,
                e.description,
                e.type,
                e.classification,
                e.start_datetime,
                e.end_datetime,
                p.person_id,
                p.matricule,
                p.name,
                p.family_name,
                p.role
            FROM event e
            LEFT JOIN person p ON e.declared_by_id = p.person_id
            {where_clause}
            ORDER BY e.event_id
            LIMIT %s OFFSET %s;
        """
        events_params = tuple(filter_params + [limit, offset])
        events = query_db(events_query, params=events_params)
        
        # Transformer les résultats pour correspondre à l'interface Incident simplifiée
        events_payload: list[dict] = []
        for event in events:
            reporter = None
            if event["person_id"]:
                reporter = {
                    "id": event["person_id"],
                    "matricule": event["matricule"],
                    "name": event["name"],
                    "family_name": event["family_name"],
                    "role": event["role"],
                }

            events_payload.append(
                {
                    "id": event["event_id"],
                    "type": event["type"],
                    "classification": event["classification"],
                    "start_datetime": event["start_datetime"],
                    "end_datetime": event["end_datetime"],
                    "description": event["description"],
                    "person": reporter,
                }
            )

        # Convertir les datetime en strings pour la sérialisation JSON
        events_serializable = convert_datetime_to_str(events_payload)

        return JSONResponse(
            {
                "status": "success",
                "offset": offset,
                "total_count": total_count_value,
                "count": len(events_serializable),
                "events": events_serializable,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des événements: {str(e)}"
            }
        )

@app.get("/get_basic_info")
async def get_basic_info():
    """Retourne des indicateurs globaux pour le tableau de bord"""
    try:
        total_incidents_row = query_db(
            "SELECT COUNT(*) AS total FROM event;", fetch_one=True
        )
        critical_risk_row = query_db(
            """
            SELECT COUNT(DISTINCT er.event_id) AS total
            FROM event_risk er
            INNER JOIN risk r ON er.risk_id = r.risk_id
            WHERE r.gravity ILIKE 'critical%';
            """,
            fetch_one=True,
        )
        no_corrective_row = query_db(
            """
            SELECT COUNT(*) AS total
            FROM event e
            LEFT JOIN event_corrective_measure ecm ON e.event_id = ecm.event_id
            WHERE ecm.event_id IS NULL;
            """,
            fetch_one=True,
        )
        total_cost_row = query_db(
            """
            SELECT COALESCE(SUM(cm.cost), 0) AS total_cost
            FROM event_corrective_measure ecm
            INNER JOIN corrective_measure cm ON ecm.measure_id = cm.measure_id;
            """,
            fetch_one=True,
        )

        payload = convert_datetime_to_str(
            {
                "total_event_count": total_incidents_row["total"] if total_incidents_row else 0,
                "total_critical_risk_count": critical_risk_row["total"] if critical_risk_row else 0,
                "total_no_corrective_measure_count": no_corrective_row["total"] if no_corrective_row else 0,
                "total_corrective_measure_cost": total_cost_row["total_cost"] if total_cost_row else 0,
            }
        )

        return JSONResponse({"status": "success", "data": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des informations de base: {str(e)}",
            },
        )

@app.get("/get_most_recent_incidents")
async def get_most_recent_incidents(limit: int = 5):
    """Retourne les incidents les plus récents"""
    try:
        if limit <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Limit must be a positive integer",
                },
            )

        events = query_db(
            """
            SELECT
                e.event_id,
                e.type,
                e.classification,
                e.start_datetime,
                e.end_datetime,
                p.person_id,
                p.matricule,
                p.name,
                p.family_name,
                p.role
            FROM event e
            LEFT JOIN person p ON e.declared_by_id = p.person_id
            ORDER BY e.start_datetime DESC NULLS LAST, e.event_id DESC
            LIMIT %s;
            """,
            params=(limit,),
        )

        incidents: list[dict] = []
        for event in events:
            incident = {
                "id": event["event_id"],
                "type": event["type"],
                "classification": event["classification"],
                "start_datetime": event["start_datetime"],
                "end_datetime": event["end_datetime"],
                "reporter": None,
            }

            if event["person_id"]:
                incident["reporter"] = {
                    "id": event["person_id"],
                    "matricule": event["matricule"],
                    "name": event["name"],
                    "family_name": event["family_name"],
                    "role": event["role"],
                }

            incidents.append(incident)

        payload = convert_datetime_to_str(incidents)
        return JSONResponse({"incidents": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des incidents récents: {str(e)}",
            },
        )

@app.get("/get_top_organization")
async def get_top_organization(limit: int = 5):
    """Retourne les unités organisationnelles avec le plus d'incidents"""
    try:
        if limit <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Limit must be a positive integer",
                },
            )

        rows = query_db(
            """
            SELECT
                ou.unit_id,
                ou.identifier,
                ou.name,
                ou.location,
                COUNT(*) AS total
            FROM event e
            INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
            GROUP BY ou.unit_id, ou.identifier, ou.name, ou.location
            ORDER BY total DESC, ou.unit_id ASC
            LIMIT %s;
            """,
            params=(limit,),
        )

        top_entries = [
            {
                "organization": {
                    "id": row["unit_id"],
                    "identifier": row["identifier"],
                    "name": row["name"],
                    "location": row["location"],
                },
                "value": row["total"],
            }
            for row in rows
        ]

        return JSONResponse({"top_organization": top_entries})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des organisations principales: {str(e)}",
            },
        )

@app.get("/get_incident_by_type")
async def get_incident_by_type():
    """Retourne le nombre total d'incidents par type"""
    try:
        rows = query_db(
            """
            SELECT
                e.type,
                COUNT(*) AS total
            FROM event e
            GROUP BY e.type
            ORDER BY total DESC, e.type ASC;
            """
        )

        payload = [
            {
                "type": row["type"],
                "value": row["total"],
            }
            for row in rows
        ]

        return JSONResponse({"incidents_by_type": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des incidents par type: {str(e)}",
            },
        )

@app.get("/get_incident_by_classification")
async def get_incident_by_classification(limit: int = 5):
    """Retourne le nombre total d'incidents par classification (max 5)"""
    try:
        if limit <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Limit must be a positive integer",
                },
            )

        rows = query_db(
            """
            SELECT
                e.classification,
                COUNT(*) AS total
            FROM event e
            GROUP BY e.classification
            ORDER BY total DESC, e.classification ASC
            LIMIT %s;
            """,
            params=(limit,),
        )

        payload = [
            {
                "classification": row["classification"],
                "value": row["total"],
            }
            for row in rows
        ]

        return JSONResponse({"incidents": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des incidents par classification: {str(e)}",
            },
        )

@app.get("/{event_id}/details")
async def get_event_details(event_id: int):
    """Route pour récupérer tous les détails d'un événement"""
    try:
        # Récupérer les détails de l'événement avec inner join person
        event = query_db("""
            SELECT 
                e.event_id,
                e.description,
                e.start_datetime,
                e.end_datetime,
                e.type,
                e.classification,
                p.matricule,
                p.name,
                p.family_name,
                p.person_id
            FROM event e
            INNER JOIN person p ON e.declared_by_id = p.person_id
            WHERE e.event_id = %s;
        """, params=(event_id,), fetch_one=True)
        
        if not event:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Événement avec l'ID {event_id} introuvable"
                }
            )
        
        # Récupérer les employés impliqués avec inner join person
        employees = query_db("""
            SELECT 
                ee.person_id,
                ee.involvement_type,
                p.matricule,
                p.name,
                p.family_name
            FROM event_employee ee
            INNER JOIN person p ON ee.person_id = p.person_id
            WHERE ee.event_id = %s;
        """, params=(event_id,))
        
        # Récupérer l'unité organisationnelle
        organizational_unit = query_db("""
            SELECT 
                ou.identifier,
                ou.name, 
                ou.location, 
                ou.unit_id
            FROM event e
            INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
            WHERE e.event_id = %s;
        """, params=(event_id,), fetch_one=True)
        
        # Récupérer les mesures correctives avec inner join corrective_measure et person
        corrective_measures = query_db("""
            SELECT 
                cm.measure_id,
                cm.name,
                cm.implementation_date AS implementation,
                cm.description,
                cm.cost,
                cm.owner_id,
                p_owner.matricule AS owner_matricule,
                p_owner.name AS owner_name,
                p_owner.family_name AS owner_family_name,
                cm_ou.unit_id AS cm_ou_unit_id,
                cm_ou.identifier AS cm_ou_identifier,
                cm_ou.name AS cm_ou_name,
                cm_ou.location AS cm_ou_location
            FROM event_corrective_measure ecm
            INNER JOIN corrective_measure cm ON ecm.measure_id = cm.measure_id
            INNER JOIN person p_owner ON cm.owner_id = p_owner.person_id
            LEFT JOIN organizational_unit cm_ou ON cm.organizational_unit_id = cm_ou.unit_id
            WHERE ecm.event_id = %s;
        """, params=(event_id,))
        
        # Récupérer les risques avec inner join risk
        risks = query_db("""
            SELECT 
                r.risk_id,
                r.name,
                r.gravity,
                r.probability
            FROM event_risk er
            INNER JOIN risk r ON er.risk_id = r.risk_id
            WHERE er.event_id = %s;
        """, params=(event_id,))
        
        risks_payload = None
        if risks:
            risks_payload = [
                {
                    "id": r['risk_id'],
                    "name": r['name'],
                    "gravity": r['gravity'],
                    "probability": r['probability']
                }
                for r in risks
            ]
        
        # Construire la réponse selon la structure demandée
        result = {
            "id": event['event_id'],
            "description": event['description'],
            "start_datetime": event['start_datetime'],
            "end_datetime": event['end_datetime'],
            "type": event['type'],
            "classification": event['classification'],
            "person": {
                "id": event['person_id'],
                "matricule": event['matricule'],
                "name": event['name'],
                "family_name": event['family_name']
            },
            "employees": [
                {
                    "linked_person" : {
                        "id": emp['person_id'],
                        "matricule": emp['matricule'],
                        "name": emp['name'],
                        "family_name": emp['family_name']
                    },
                    "involvement_type" : emp['involvement_type']
                    
                }
                for emp in (employees if employees else [])
            ],
            "organizational_unit": {
                "id": organizational_unit['unit_id'] if organizational_unit else None,
                "identifier": organizational_unit['identifier'] if organizational_unit else None,
                "name": organizational_unit['name'] if organizational_unit else None,
                "location": organizational_unit['location'] if organizational_unit else None,
            } if organizational_unit else None,
            "corrective_measures": [
                {
                    "id": cm['measure_id'],
                    "name": cm['name'],
                    "implementation": cm['implementation'],
                    "description": cm['description'],
                    "cost": cm['cost'],
                    "owner": {
                        "id": cm['owner_id'],
                        "matricule": cm['owner_matricule'],
                        "name": cm['owner_name'],
                        "family_name": cm['owner_family_name']
                    },
                    "organization_unit": {
                        "id": cm['cm_ou_unit_id'],
                        "identifier": cm['cm_ou_identifier'],
                        "name": cm['cm_ou_name'],
                        "location": cm['cm_ou_location'],
                    } if cm['cm_ou_unit_id'] is not None else None
                }
                for cm in (corrective_measures if corrective_measures else [])
            ],
            "risks": risks_payload
        }
        
        # Convertir les datetime en strings pour la sérialisation JSON
        result_serializable = convert_datetime_to_str(result)
        
        return JSONResponse({
            "status": "success",
            "event": result_serializable
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des détails de l'événement: {str(e)}"
            }
        )
    



@app.post("/opensearch/index/all")
async def opensearch_index_all():
    """
    Charge tous les events depuis Postgres et indexe dans OpenSearch (full-text).
    """
    try:
        rows = query_db("""
            SELECT
              event_id,
              type,
              classification,
              start_datetime,
              end_datetime,
              description
            FROM event
            ORDER BY event_id
        """, fetch_one=False)

        client = get_opensearch_client()
        ensure_index(client, INDEX_NAME)

        count = 0
        for r in rows:
            doc_id = r["event_id"]
            index_incident(client, INDEX_NAME, doc_id, {
                "event_id": r["event_id"],
                "type": r.get("type"),
                "classification": r.get("classification"),
                "start_datetime": r.get("start_datetime"),
                "end_datetime": r.get("end_datetime"),
                "description": r.get("description"),
            })
            count += 1

        return {"status": "indexed", "count": count}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/opensearch/count")
async def opensearch_count():
    """Retourne le nombre de documents indexés dans OpenSearch"""
    try:
        client = get_opensearch_client()
        ensure_index(client, INDEX_NAME)
        res = client.count(index=INDEX_NAME)
        return {"index": INDEX_NAME, "doc_count": res.get("count", 0)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
