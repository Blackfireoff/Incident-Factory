from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, date
from decimal import Decimal
from database import query_db
from fastapi import Request
from services.bedrock_service import BedrockChatService
from opensearchpy import OpenSearch
import boto3
import json
from typing import List
from services.bedrock_service import MODEL_ID 


from search_engine import get_opensearch_client, ensure_index, index_incident, search_incidents

INDEX_NAME = "incidents"
app = FastAPI(title="FireTeams API")
chat_service = BedrockChatService()

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

def _fetch_context_from_os(query: str, limit: int = 5) -> List[dict]:
    """Récupère le contexte depuis OpenSearch (recherche full-text)"""
    client = get_opensearch_client()
    ensure_index(client, INDEX_NAME)
    res = search_incidents(client, INDEX_NAME, query)  # multi_match sur description/type/classification
    hits = (res or {}).get("hits", {}).get("hits", [])[:limit]
    ctx = []
    for h in hits:
        s = h.get("_source", {})
        ctx.append({
            "event_id": s.get("event_id"),
            "type": s.get("type"),
            "classification": s.get("classification"),
            "start_datetime": s.get("start_datetime"),
            "end_datetime": s.get("end_datetime"),
            "description": s.get("description")
        })
    return ctx

def _build_prompts(user_message: str, ctx: List[dict]) -> tuple[str, str]:
    system_prompt = (
        "Tu es un assistant d'analyse d'incidents. Tu DOIS répondre uniquement à partir du CONTEXTE fourni, "
        "qui provient d'événements stockés en base PostgreSQL et indexés dans OpenSearch.\n\n"
        "Règles:\n"
        "- Si l'information n'est pas présente dans le contexte, réponds exactement: \"Je ne sais pas sur la base du contexte fourni.\"\n"
        "- Ne fais aucune supposition et n'invente pas de faits.\n"
        "- Cite toujours les événements pertinents sous la forme [event_id:123].\n"
        "- Si plusieurs explications sont plausibles, liste-les brièvement et indique un degré de confiance (faible/moyen/élevé).\n"
        "- Réponds en français, clair et concis. Pas d'URL externes, pas de code.\n\n"
        "Format de sortie:\n"
        "Réponse: <ta réponse courte et claire>\n"
        "Citations: [event_id:..., event_id:...]"
    )

    if ctx:
        blocks = []
        for c in ctx:
            blocks.append(
                f"[event_id={c.get('event_id')}] type={c.get('type')}, classification={c.get('classification')}, "
                f"start={c.get('start_datetime')}, end={c.get('end_datetime')}\n"
                f"{c.get('description') or ''}"
            )
        context_block = "\n\n".join(blocks)
    else:
        context_block = "(aucun contexte trouvé)"

    user_prompt = (
        f"Question: {user_message}\n\n"
        f"Contexte (incidents):\n{context_block}\n\n"
        "Consignes:\n"
        "- Utilise uniquement le contexte ci-dessus.\n"
        "- S'il est vide ou non pertinent, dis \"Je ne sais pas sur la base du contexte fourni.\"\n"
        "- Cite les event_id utilisés."
    )
    
    return system_prompt, user_prompt


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
        
        # Récupérer les 20 premières lignes avec uniquement les champs demandés
        events = query_db("""
            SELECT 
                e.event_id,
                p.matricule,
                e.type,
                e.classification AS classification,
                e.start_datetime AS start_datetime,
                e.end_datetime AS end_datetime
            FROM event e
            LEFT JOIN person p ON e.declared_by_id = p.person_id
            ORDER BY e.event_id
            LIMIT 20 OFFSET %s;
        """, params=(offset,))
        
        # Convertir les datetime en strings pour la sérialisation JSON
        events_serializable = convert_datetime_to_str(list(events))
        
        return JSONResponse({
            "status": "success",
            "offset": offset,
            "count": len(events_serializable),
            "events": events_serializable
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des événements: {str(e)}"
            }
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
                p.family_name
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
                ou.name
            FROM event e
            INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
            WHERE e.event_id = %s;
        """, params=(event_id,), fetch_one=True)
        
        # Récupérer les mesures correctives avec inner join corrective_measure et person
        corrective_measures = query_db("""
            SELECT 
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
                r.name,
                r.gravity,
                r.probability
            FROM event_risk er
            INNER JOIN risk r ON er.risk_id = r.risk_id
            WHERE er.event_id = %s;
        """, params=(event_id,))
        
        # Construire la réponse selon la structure demandée
        result = {
            "event_id": event['event_id'],
            "description": event['description'],
            "start_datetime": event['start_datetime'],
            "end_datetime": event['end_datetime'],
            "type": event['type'],
            "classification": event['classification'],
            "person": {
                "matricule": event['matricule'],
                "name": event['name'],
                "family_name": event['family_name']
            },
            "employees": [
                {
                    "person_id": emp['person_id'],
                    "matricule": emp['matricule'],
                    "name": emp['name'],
                    "family_name": emp['family_name']
                }
                for emp in (employees if employees else [])
            ],
            "organizational_unit": {
                "identifier": organizational_unit['identifier'] if organizational_unit else None,
                "name": organizational_unit['name'] if organizational_unit else None
            } if organizational_unit else None,
            "corrective_measures": [
                {
                    "name": cm['name'],
                    "implementation": cm['implementation'],
                    "description": cm['description'],
                    "cost": cm['cost'],
                    "owner_id": cm['owner_id'],
                    "owner": {
                        "matricule": cm['owner_matricule'],
                        "name": cm['owner_name'],
                        "family_name": cm['owner_family_name']
                    }
                }
                for cm in (corrective_measures if corrective_measures else [])
            ],
            "risks": [
                {
                    "name": r['name'],
                    "gravity": r['gravity'],
                    "probability": r['probability']
                }
                for r in (risks if risks else [])
            ]
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
    Body JSON: { "message": "..." }  (or { "question": "..." })
    Returns: { status, question, context_count, answer }
    """
    try:
        data = await request.json()
        msg = (data or {}).get("message") or (data or {}).get("question")
        if not msg:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Provide 'message' (or 'question') in the JSON body"}
            )

        # 1) retrieve context from OpenSearch full-text
        ctx = _fetch_context_from_os(msg, limit=1000)

        # 2) build prompts
        system_prompt, user_prompt = _build_prompts(msg, ctx)

        print(ctx)

        # 3) call Bedrock (re-use your client & model/profile)
        response = chat_service.bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"temperature": 0.2, "maxTokens": 600, "topP": 0.9}
        )

        answer = response["output"]["message"]["content"][0]["text"]

        return JSONResponse({
            "status": "success",
            "question": msg,
            "context_count": len(ctx),
            "answer": answer
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Erreur lors du traitement: {str(e)}"}
        )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




