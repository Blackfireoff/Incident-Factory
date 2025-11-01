import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Charger les variables d'environnement
load_dotenv()

def get_db_connection():
    """Crée et retourne une connexion à la base de données PostgreSQL"""
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

def query_db(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = True):
    """
    Exécute une requête SQL et retourne les résultats
    
    Args:
        query: La requête SQL à exécuter
        params: Les paramètres pour la requête (tuple)
        fetch_one: Si True, retourne un seul résultat (fetchone)
        fetch_all: Si True, retourne tous les résultats (fetchall). Ignoré si fetch_one=True
    
    Returns:
        Les résultats de la requête (dict ou list de dict)
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        
        return result
    except Exception as e:
        raise Exception(f"Erreur lors de l'exécution de la requête: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

