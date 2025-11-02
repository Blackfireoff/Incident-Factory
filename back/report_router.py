# report_router.py

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.bedrock_service import BedrockService
import services.sql_service as sql_service
import services.pdf_service as pdf_service
import json
import io

# --- IMPORTATIONS CRITIQUES (copiées de ai_router.py) ---
from datetime import datetime, date
from decimal import Decimal
import psycopg2.extras
from services.opensearch_service import (
    get_opensearch_client, 
    search_semantic_incidents, 
    INDEX_NAME
)
# --- FIN DES IMPORTS ---


# Initialiser les services
try:
    bedrock_service = BedrockService()
except Exception as e:
    print(f"Erreur critique: Impossible d'initialiser BedrockService: {e}")
    bedrock_service = None 

# Pré-charger le schéma
DB_SCHEMA = sql_service.get_database_schema()

router = APIRouter(prefix="/ai", tags=["AI Reporting"])

class AIReportRequest(BaseModel):
    query: str

# --- FONCTION DE CONVERSION (copiée de ai_router.py) ---
def convert_datetime_to_str(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, psycopg2.extras.RealDictRow): 
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj
# --- FIN DE LA FONCTION ---

# --- FONCTION DE CONTEXTE RAG (TRADUITE) ---
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


@router.post("/report")
async def handle_ai_report(request: AIReportRequest):
    """
    Endpoint de génération de rapport PDF Hybride:
    1.  Décide de l'outil (SQL ou Search)
    2.  Si SQL -> Génère un PDF de tableau
    3.  Si Search -> Génère un PDF de texte
    """
    if not bedrock_service:
        raise HTTPException(
            status_code=503, 
            detail="Bedrock service is not initialized."
        )

    user_query = request.query
    
    try:
        # --- NOUVELLE LOGIQUE : AGENT HYBRIDE ---
        print(f"Report Agent: Deciding route for query: '{user_query}'")
        tool_choice = bedrock_service.decide_tool(user_query)
        print(f"Report Agent: Tool chosen: {tool_choice}")

        if tool_choice == "sql":
            # --- ROUTE SQL (Pour les PDF de tableaux) ---
            
            # ÉTAPE 1: Générer le SQL
            print(f"Report Agent: Generating SQL for: '{user_query}'")
            sql_query = bedrock_service.generate_sql_query(DB_SCHEMA, user_query)
            
            # ÉTAPE 2: Exécuter le SQL
            print(f"Report Agent: Executing: '{sql_query}'")
            try:
                sql_results, columns = sql_service.execute_safe_sql(sql_query)
                serializable_results = convert_datetime_to_str(sql_results)
                data_payload = {"columns": columns, "rows": serializable_results}
                
                if serializable_results and "Error" in serializable_results[0]:
                     raise HTTPException(status_code=400, detail=f"SQL Error: {serializable_results[0]['Error']}")

            except Exception as e:
                print(f"Error during SQL execution/serialization: {repr(e)}")
                if isinstance(e, ValueError):
                    raise HTTPException(status_code=400, detail=str(e))
                raise HTTPException(status_code=500, detail=f"SQL Error: {repr(e)}")

            # ÉTAPE 3: Générer le PDF de Tableau
            print("Report Agent: Generating table PDF...")
            pdf_bytes = pdf_service.create_report_pdf(
                title=f"Data Report: {user_query}", # TRADUIT
                query=sql_query,
                data=data_payload
            )

        else:
            # --- ROUTE RAG (Pour les PDF de texte) ---
            
            # ÉTAPE 1: Chercher dans OpenSearch
            os_client = get_opensearch_client()
            search_results = search_semantic_incidents(os_client, INDEX_NAME, user_query, size=3)
            hits = search_results.get("hits", {}).get("hits", [])

            # ÉTAPE 2: Formater le contexte
            context = format_rag_context_from_hits(hits)
            
            # ÉTAPE 3: Générer la réponse finale (le texte)
            ai_response_text = bedrock_service.generate_rag_response(context, user_query)
            
            # ÉTAPE 4: Générer le PDF de Texte
            print("Report Agent: Generating text PDF...")
            pdf_bytes = pdf_service.create_text_report_pdf(
                title=f"Analysis Report: {user_query}", # TRADUIT
                content=ai_response_text
            )

        # ÉTAPE FINALE: Retourner le PDF en streaming
        pdf_stream = io.BytesIO(pdf_bytes)
        
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=incident_report.pdf"
            }
        )
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        error_message = repr(e)
        print(f"Major report agent error: {error_message}")
        raise HTTPException(status_code=500, detail=f"Agent error: {error_message}")