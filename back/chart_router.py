# chart_router.py

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from services.bedrock_service import BedrockService
import services.sql_service as sql_service
import json

# --- IMPORTATIONS CRITIQUES (copiées de ai_router.py) ---
from datetime import datetime, date
from decimal import Decimal
import psycopg2.extras
# --- FIN DES IMPORTS ---

# Initialiser les services
try:
    bedrock_service = BedrockService()
except Exception as e:
    print(f"Erreur critique: Impossible d'initialiser BedrockService: {e}")
    bedrock_service = None 

# Pré-charger le schéma
DB_SCHEMA = sql_service.get_database_schema()

router = APIRouter(prefix="/ai", tags=["AI Charting"])

class AIChartRequest(BaseModel):
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


@router.post("/chart")
async def handle_ai_chart(request: AIChartRequest):
    """
    Endpoint de génération de graphique:
    1.  Force la génération SQL
    2.  Exécute le SQL
    3.  Demande à l'IA d'analyser les données pour un graphique
    4.  Retourne les données brutes + l'analyse de l'IA
    """
    if not bedrock_service:
        raise HTTPException(
            status_code=503, 
            detail="Le service Bedrock n'est pas initialisé."
        )

    user_query = request.query
    
    try:
        # ÉTAPE 1: Générer le SQL
        print(f"Agent Graphique: Génération SQL pour: '{user_query}'")
        sql_query = bedrock_service.generate_sql_query(DB_SCHEMA, user_query)
        
        # ÉTAPE 2: Exécuter le SQL
        print(f"Agent Graphique: Exécution: '{sql_query}'")
        try:
            sql_results, columns = sql_service.execute_safe_sql(sql_query) # <-- 'columns' est récupéré ici
            serializable_results = convert_datetime_to_str(sql_results)
            context_json = json.dumps(serializable_results)
            data_payload = {"columns": columns, "rows": serializable_results}
            
            # Gérer les cas d'erreur SQL avant d'appeler Bedrock
            if serializable_results and "Erreur" in serializable_results[0]:
                 return {
                    "type": "error",
                    "analysis": {"chart_type": "list", "title": "Erreur SQL", "insight": serializable_results[0]["Erreur"]},
                    "data": data_payload,
                    "query": sql_query
                }

        except Exception as e:
            print(f"Erreur lors de l'exécution/sérialisation SQL: {repr(e)}")
            raise HTTPException(status_code=500, detail=f"Erreur SQL: {repr(e)}")

        # ÉTAPE 3: Demander à l'IA d'analyser les données
        print("Agent Graphique: Génération de l'analyse du graphique...")
        
        # --- CORRECTION ICI ---
        # Assurez-vous que 'columns' est bien passé en troisième argument
        chart_analysis = bedrock_service.generate_chart_analysis(user_query, context_json, columns)
        # --- FIN DE LA CORRECTION ---
        
        # ÉTAPE 4: Retourner le package de données pour le frontend
        return {
            "type": "chart",
            "analysis": chart_analysis, # ex: {"chart_type": "bar", "title": "...", "index": "name", "categories": ["count"]}
            "data": data_payload,
            "query": sql_query
        }

    except Exception as e:
        error_message = repr(e)
        print(f"Erreur majeure dans l'agent graphique: {error_message}")
        raise HTTPException(status_code=500, detail=f"Erreur de l'agent: {error_message}")