# ai_router.py

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from services.bedrock_service import BedrockService
from services.opensearch_service import (
    get_opensearch_client, 
    search_semantic_incidents, 
    INDEX_NAME
)
import services.sql_service as sql_service
import json

# --- IMPORTATIONS CRITIQUES AJOUTÉES ---
from datetime import datetime, date
from decimal import Decimal
import psycopg2.extras # <-- C'EST L'IMPORT QUI MANQUAIT
# --- FIN DES AJOUTS ---


# Initialiser les services
try:
    bedrock_service = BedrockService()
except Exception as e:
    print(f"Erreur critique: Impossible d'initialiser BedrockService: {e}")
    bedrock_service = None 

# Pré-charger le schéma au démarrage (meilleure performance)
DB_SCHEMA = sql_service.get_database_schema()

router = APIRouter(prefix="/ai", tags=["AI Chatbot (Agent)"])

class AIQueryRequest(BaseModel):
    query: str

# --- FONCTION DE CONVERSION (corrigée avec l'import) ---
def convert_datetime_to_str(obj):
    """Convertit les objets datetime, date, Decimal et RealDictRow en types JSON-serialisables"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    # Cette ligne fonctionne maintenant grâce à l'import
    elif isinstance(obj, psycopg2.extras.RealDictRow): 
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj
# --- FIN DE LA FONCTION ---


def format_rag_context_from_hits(hits: list) -> str:
    """
    Met en forme les résultats d'OpenSearch en un contexte clair pour le LLM.
    """
    if not hits:
        return "Aucun contexte trouvé."
    
    context_str = "Voici les incidents pertinents (contexte RAG) :\n\n"
    
    for hit in hits:
        source = hit.get("_source", {})
        context_str += "--- Début Incident ---\n"
        context_str += f"ID Événement: {source.get('event_id')}\n"
        context_str += f"Description: {source.get('description')}\n"
        
        if source.get('risks'):
            context_str += "Risques identifiés:\n"
            for risk in source['risks']:
                context_str += f"  - {risk.get('name')} (Gravité: {risk.get('gravity')})\n"
        
        if source.get('corrective_measures'):
            context_str += "Mesures correctives:\n"
            for measure in source['corrective_measures']:
                context_str += f"  - {measure.get('name')}\n"
        
        if source.get('involved_employees'):
            context_str += "Employés impliqués:\n"
            for emp in source['involved_employees']:
                context_str += f"  - {emp.get('name')} {emp.get('family_name')}\n"
                
        context_str += "--- Fin Incident ---\n\n"
        
    return context_str


@router.post("/query")
async def handle_ai_query(request: AIQueryRequest):
    """
    Endpoint de l'Agent Hybride:
    1.  Décide de l'outil (SQL ou Search)
    2.  Exécute l'outil choisi
    3.  Génère une réponse finale
    """
    if not bedrock_service:
        raise HTTPException(
            status_code=503, 
            detail="Le service Bedrock n'est pas initialisé."
        )

    user_query = request.query
    
    try:
        # ÉTAPE 1: L'agent décide de l'outil
        print(f"Agent: Décision pour la requête: '{user_query}'")
        tool_choice = bedrock_service.decide_tool(user_query)
        print(f"Agent: Outil choisi: {tool_choice}")

        if tool_choice == "sql":
            # --- ROUTE SQL (Text-to-SQL) ---
            
            # ÉTAPE 2 (SQL): Générer le SQL
            sql_query = bedrock_service.generate_sql_query(DB_SCHEMA, user_query)
            
            # ÉTAPE 3 (SQL): Exécuter le SQL
            try:
                sql_results, columns = sql_service.execute_safe_sql(sql_query)
                
                # --- CORRECTION APPLIQUÉE ---
                # Nettoyer les résultats AVANT json.dumps
                serializable_results = convert_datetime_to_str(sql_results)
                
                context = json.dumps(serializable_results)
                data_payload = {"columns": columns, "rows": serializable_results}
            
            except Exception as e:
                # Cette exception (NameError) est ce qui se passait
                print(f"Erreur lors de la sérialisation SQL: {repr(e)}")
                context = json.dumps({"Erreur": str(e)})
                data_payload = None

            # ÉTAPE 4 (SQL): Générer la réponse finale
            ai_response = bedrock_service.generate_rag_response(context, user_query)
            
            # Retourner la réponse ET les données brutes pour les diagrammes
            return {
                "response": ai_response, 
                "type": "sql", 
                "data": data_payload, 
                "query": sql_query
            }

        else:
            # --- ROUTE RECHERCHE (RAG) ---
            
            # ÉTAPE 2 (RAG): Chercher dans OpenSearch
            os_client = get_opensearch_client()
            search_results = search_semantic_incidents(os_client, INDEX_NAME, user_query, size=3)
            hits = search_results.get("hits", {}).get("hits", [])

            # ÉTAPE 3 (RAG): Formater le contexte
            context = format_rag_context_from_hits(hits)
            
            # ÉTAPE 4 (RAG): Générer la réponse finale
            ai_response = bedrock_service.generate_rag_response(context, user_query)
            
            return {
                "response": ai_response, 
                "type": "search", 
                "context_hits": len(hits)
            }

    except Exception as e:
        error_message = repr(e)
        print(f"Erreur majeure dans l'agent: {error_message}")
        raise HTTPException(status_code=500, detail=f"Erreur de l'agent: {error_message}")