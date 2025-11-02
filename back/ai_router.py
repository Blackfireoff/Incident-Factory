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


# --- FONCTION format_rag_context_from_hits (TRADUITE) ---
def format_rag_context_from_hits(hits: list) -> str:
    """
    Formats OpenSearch results into a clear context for the LLM.
    """
    if not hits:
        return "No context found." # TRADUIT
    
    context_str = "Here is the relevant incident context (RAG):\n\n" # TRADUIT
    
    for hit in hits:
        source = hit.get("_source", {})
        context_str += "--- Start Incident ---\n" # TRADUIT
        context_str += f"Event ID: {source.get('event_id')}\n" # TRADUIT
        context_str += f"Description: {source.get('description')}\n"
        
        if source.get('risks'):
            context_str += "Identified Risks:\n" # TRADUIT
            for risk in source['risks']:
                context_str += f"  - {risk.get('name')} (Gravity: {risk.get('gravity')})\n"
        
        if source.get('corrective_measures'):
            context_str += "Corrective Measures:\n" # TRADUIT
            for measure in source['corrective_measures']:
                context_str += f"  - {measure.get('name')}\n"
        
        if source.get('involved_employees'):
            context_str += "Involved Employees:\n" # TRADUIT
            for emp in source['involved_employees']:
                context_str += f"  - {emp.get('name')} {emp.get('family_name')}\n"
                
        context_str += "--- End Incident ---\n\n" # TRADUIT
        
    return context_str
# --- FIN DE LA TRADUCTION ---


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
            detail="Bedrock service is not initialized."
        )

    user_query = request.query
    
    try:
        # ÉTAPE 1: L'agent décide de l'outil
        print(f"Agent: Deciding route for query: '{user_query}'")
        tool_choice = bedrock_service.decide_tool(user_query)
        print(f"Agent: Tool chosen: {tool_choice}")

        if tool_choice == "sql":
            # --- ROUTE SQL (Text-to-SQL) ---
            
            # ÉTAPE 2 (SQL): Générer le SQL
            sql_query = bedrock_service.generate_sql_query(DB_SCHEMA, user_query)
            
            # ÉTAPE 3 (SQL): Exécuter le SQL
            try:
                sql_results, columns = sql_service.execute_safe_sql(sql_query)
                
                print(f"Agent SQL: DB returned {len(sql_results)} row(s).")

                serializable_results = convert_datetime_to_str(sql_results)
                
                context = json.dumps(serializable_results)
                data_payload = {"columns": columns, "rows": serializable_results}
            
            except Exception as e:
                print(f"Error during SQL serialization: {repr(e)}")
                context = json.dumps({"Error": str(e)})
                data_payload = None

            # ÉTAPE 4 (SQL): Générer la réponse finale
            print("Agent SQL: Generating response...")
            ai_response = bedrock_service.generate_rag_response(context, user_query)
            
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

            print(f"Agent RAG: OpenSearch returned {len(hits)} hit(s).")

            # ÉTAPE 3 (RAG): Formater le contexte
            context = format_rag_context_from_hits(hits)
            
            # ÉTAPE 4 (RAG): Générer la réponse finale
            print("Agent RAG: Generating response...")
            ai_response = bedrock_service.generate_rag_response(context, user_query)
            
            return {
                "response": ai_response, 
                "type": "search", 
                "context_hits": len(hits)
            }

    except Exception as e:
        error_message = repr(e)
        print(f"Major agent error: {error_message}")
        raise HTTPException(status_code=500, detail=f"Agent error: {error_message}")