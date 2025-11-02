from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime, date
from decimal import Decimal
from database import query_db
from fastapi import Request
from services.bedrock_service import BedrockChatService
from opensearchpy import OpenSearch
import boto3
import json
from services.bedrock_service import MODEL_ID
from services.chart_service import (
    SUPPORTED_SCENARIOS,
    generate_chart_from_question,
)
from services.summary_service import generate_summary_report
from services.query_service import process_ai_query_request


from search_engine import (
    get_opensearch_client,
    ensure_index,
    index_incident,
    search_incidents_with_filters,
    search_recent_incidents,
)

INDEX_NAME = "incidents"
app = FastAPI(title="FireTeams API")
chat_service = BedrockChatService()

# --- Chart & summary generation endpoints ---

@app.post("/ai/chart")
async def ai_chart(request: Request):
    """
    Génère un graphique PNG encodé en base64 à partir d'une question analytique.
    Body JSON attendu: { "question": "..."} ou { "message": "..." }
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        data = {}

    question = (data or {}).get("question") or (data or {}).get("message")
    if not question:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Provide 'question' (or 'message') in the JSON body",
            },
        )

    try:
        chart_result = generate_chart_from_question(question)
        if not chart_result:
            supported_hint = ", ".join(SUPPORTED_SCENARIOS.values())
            return JSONResponse(
                status_code=404,
                content={
                    "status": "not_found",
                    "question": question,
                    "message": (
                        "Aucun graphique généré pour cette question. "
                        f"Scénarios pris en charge : {supported_hint}."
                    ),
                },
            )

        chart = {
            "title": chart_result.chart_data.title,
            "x_label": chart_result.chart_data.x_label,
            "y_label": chart_result.chart_data.y_label,
            "categories": chart_result.chart_data.categories,
            "values": chart_result.chart_data.values,
            "caption": chart_result.chart_data.caption,
            "image_base64": chart_result.image_base64,
            "image_mime": chart_result.image_mime,
        }

        return JSONResponse(
            {
                "status": "success",
                "question": question,
                "chart": chart,
                "scenario": chart_result.scenario,
            }
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la génération du graphique: {str(exc)}",
            },
        )


@app.post("/ai/summary")
async def ai_summary(request: Request):
    """
    Génère un rapport synthétique au format Markdown.
    """
    try:
        await request.json()
    except json.JSONDecodeError:
        pass
    except Exception:
        pass

    try:
        report = generate_summary_report()
        return JSONResponse(
            {
                "status": "success",
                "format": "markdown",
                "suggested_filename": "synthese_incidents.txt",
                "report": report,
            }
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la génération du rapport: {str(exc)}",
            },
        )


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

def index_events_in_opensearch(os_client):
    events = query_db("SELECT event_id, description FROM event WHERE description IS NOT NULL;")

    for ev in events:
        embedding = generate_embedding(ev["description"])  # fonction à créer (via Bedrock)
        doc = {
            "event_id": ev["event_id"],
            "description": ev["description"],
            "embedding": embedding
        }
        os_client.index(index="events_vector_index", id=ev["event_id"], body=doc)

    print(f"✅ {len(events)} événements indexés dans OpenSearch")

def generate_embedding(text: str):
    bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text})
    )

    embedding = json.loads(response["body"].read())["embedding"]
    return embedding

def search_similar_context(query: str, os_client):
    query_vector = generate_embedding(query)

    search_body = {
        "size": 3,  # nombre de documents similaires à renvoyer
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": 3
                }
            }
        }
    }

    response = os_client.search(index="events_vector_index", body=search_body)
    return [hit["_source"]["description"] for hit in response["hits"]["hits"]]

def answer_question_with_context(question: str):
    os_client = OpenSearch(hosts=[{"host": "localhost", "port": 9200}])
    context_docs = search_similar_context(question, os_client)

    context_text = "\n\n".join(context_docs)

    system_prompt = """
    Tu es un assistant expert en analyse d'évènements.
    Utilise le contexte fourni pour répondre à la question de manière claire et précise.
    Si le contexte ne contient pas la réponse, indique-le explicitement.
    """

    user_prompt = f"Contexte:\n{context_text}\n\nQuestion: {question}"

    # Créer le client Bedrock
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"
    )

    response = bedrock_client.converse(
        modelId="arn:aws:bedrock:us-east-1:010526273152:inference-profile/us.meta.llama3-2-11b-instruct-v1:0",
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"temperature": 0.7, "maxTokens": 1000}
    )

    return response["output"]["message"]["content"][0]["text"]



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
async def get_events(offset: int = 0):
    """Route pour récupérer les 20 premières lignes de la table event avec pagination"""
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
        
        # Récupérer les 20 premières lignes avec tous les champs nécessaires pour l'interface Incident
        events = query_db("""
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
            ORDER BY e.event_id
            LIMIT 20 OFFSET %s;
        """, params=(offset,))
        
        # Transformer les résultats pour correspondre à l'interface Incident
        incidents = []
        for event in events:
            incident = {
                "id": event['event_id'],
                "type": event['type'],
                "classification": event['classification'],
                "start_date": event['start_datetime'],
                "end_date": event['end_datetime'],
                "description": event['description'],
                "reporter": None
            }
            
            # Construire l'objet Person si la personne existe
            if event['person_id']:
                incident["reporter"] = {
                    "id": event['person_id'],
                    "matricule": event['matricule'],
                    "name": event['name'],
                    "family_name": event['family_name'],
                    "role": event['role']
                }
            
            incidents.append(incident)
        
        # Convertir les datetime en strings pour la sérialisation JSON
        incidents_serializable = convert_datetime_to_str(incidents)
        
        return JSONResponse({
            "status": "success",
            "offset": offset,
            "count": len(incidents_serializable),
            "events": incidents_serializable
        })
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
                "start_date": event["start_datetime"],
                "end_date": event["end_datetime"],
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
                "type": row["classification"],
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
                p_owner.family_name AS owner_family_name
            FROM event_corrective_measure ecm
            INNER JOIN corrective_measure cm ON ecm.measure_id = cm.measure_id
            INNER JOIN person p_owner ON cm.owner_id = p_owner.person_id
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
                    "id": emp['person_id'],
                    "matricule": emp['matricule'],
                    "name": emp['name'],
                    "family_name": emp['family_name']
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
                    }
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
    

@app.post("/ai/analyze_event")
async def analyze_event(request: Request):
    """
    Route pour analyser un rapport d'évènement via Llama 3.2
    Exemple de corps JSON :
    {
        "text": "Un incendie s'est déclaré dans le local technique à 9h45..."
    }
    """
    try:
        data = await request.json()
        text = data.get("text")
        if not text:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Champ 'text' manquant dans la requête"}
            )

        ai_response = chat_service.analyze_event(text)
        return JSONResponse({
            "status": "success",
            "analysis": ai_response
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )
    
@app.post("/ai/analyze_event/{event_id}")
async def analyze_event_from_db(event_id: int):
    """Analyse un évènement via l'IA sans l'enregistrer dans la BDD"""
    try:
        # Récupère la description de l'évènement
        event = query_db("""
            SELECT description FROM event WHERE event_id = %s;
        """, params=(event_id,), fetch_one=True)

        if not event:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"Évènement avec ID {event_id} introuvable"}
            )

        # Appel du modèle IA avec la description
        ai_response = chat_service.analyze_event(event["description"])

        # Retourne simplement la réponse IA sans insertion
        return JSONResponse({
            "status": "success",
            "event_id": event_id,
            "description": event["description"],
            "analysis": ai_response
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
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

@app.post("/ai/query")
async def ai_query(request: Request):
    """
    Body JSON: { "message": "...", "ou": "optionnel" }  (ou "question")
    - "ou": force un filtre ILIKE sur OU.name (ex: "ateliers de production")
    Returns: { status, question, stats_count|context_count, answer }
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        data = {}
    except Exception:
        data = {}

    try:
        status_code, payload = process_ai_query_request(
            data=data,
            chat_service=chat_service,
            model_id=MODEL_ID,
            index_name=INDEX_NAME,
        )
        return JSONResponse(status_code=status_code, content=payload)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Erreur lors du traitement: {str(e)}"})

@app.get("/stats/classification")
async def stats_classification():
    """Route de debug pour voir les stats brutes"""
    try:
        stats = get_top_classifications(limit=20, ou_name_patterns=None)
        return {"status": "success", "items": [{"classification": c, "count": n} for c, n in stats]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
