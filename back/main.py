from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from decimal import Decimal

# Charger les variables d'environnement
load_dotenv()

app = FastAPI(title="FireTeams API")

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

# Fonction pour obtenir la connexion à la base de données
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "events"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres")
        )
        return conn
    except Exception as e:
        raise Exception(f"Erreur de connexion à la base de données: {str(e)}")

@app.get("/")
async def root():
    return {"message": "FireTeams API is running"}

@app.get("/db/status")
async def db_status():
    """Route pour vérifier la connexion à la base de données"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test de connexion simple
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer la liste des tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
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
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer les 20 premières lignes avec uniquement les champs demandés
        cursor.execute("""
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
        """, (offset,))
        events = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
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
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer les détails de l'événement
        cursor.execute("""
            SELECT 
                e.event_id,
                e.description,
                e.declared_by_id,
                e.start_datetime,
                e.end_datetime,
                e.organizational_unit_id,
                e.type,
                e.classification
            FROM event e
            WHERE e.event_id = %s;
        """, (event_id,))
        event = cursor.fetchone()
        
        if not event:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Événement avec l'ID {event_id} introuvable"
                }
            )
        
        # Récupérer les détails de la personne qui a déclaré l'événement
        declared_by = None
        if event['declared_by_id']:
            cursor.execute("""
                SELECT person_id, matricule, name, family_name, role
                FROM person
                WHERE person_id = %s;
            """, (event['declared_by_id'],))
            declared_by = cursor.fetchone()
        
        # Récupérer les détails de l'unité organisationnelle
        organizational_unit = None
        if event['organizational_unit_id']:
            cursor.execute("""
                SELECT unit_id, identifier, name, location
                FROM organizational_unit
                WHERE unit_id = %s;
            """, (event['organizational_unit_id'],))
            organizational_unit = cursor.fetchone()
        
        # Récupérer les employés impliqués
        cursor.execute("""
            SELECT 
                p.person_id,
                p.matricule,
                p.name,
                p.family_name,
                p.role,
                ee.involvement_type
            FROM event_employee ee
            JOIN person p ON ee.person_id = p.person_id
            WHERE ee.event_id = %s;
        """, (event_id,))
        employees = cursor.fetchall()
        
        # Récupérer les risques associés
        cursor.execute("""
            SELECT 
                r.risk_id,
                r.name,
                r.gravity,
                r.probability
            FROM event_risk er
            JOIN risk r ON er.risk_id = r.risk_id
            WHERE er.event_id = %s;
        """, (event_id,))
        risks = cursor.fetchall()
        
        # Récupérer les mesures correctives
        cursor.execute("""
            SELECT 
                cm.measure_id,
                cm.name,
                cm.description,
                cm.owner_id,
                cm.implementation_date,
                cm.cost,
                cm.organizational_unit_id,
                p.matricule AS owner_matricule,
                p.name AS owner_name,
                p.family_name AS owner_family_name
            FROM event_corrective_measure ecm
            JOIN corrective_measure cm ON ecm.measure_id = cm.measure_id
            LEFT JOIN person p ON cm.owner_id = p.person_id
            WHERE ecm.event_id = %s;
        """, (event_id,))
        corrective_measures = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Construire la réponse
        result = {
            "event_id": event['event_id'],
            "description": event['description'],
            "type": event['type'],
            "classification": event['classification'],
            "start_datetime": event['start_datetime'],
            "end_datetime": event['end_datetime'],
            "declared_by": declared_by,
            "organizational_unit": organizational_unit,
            "employees": list(employees) if employees else [],
            "risks": list(risks) if risks else [],
            "corrective_measures": list(corrective_measures) if corrective_measures else []
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

