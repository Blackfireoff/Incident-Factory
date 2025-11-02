# services/sql_service.py

import os
from database import query_db, get_db_connection
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Tuple

# Liste des tables à exposer à l'IA (basé sur votre UML)
INCLUDED_TABLES = [
    'event', 
    'person', 
    'organizational_unit', 
    'risk', 
    'corrective_measure',
    'event_employee',
    'event_risk',
    'event_corrective_measure'
]

def get_database_schema() -> str:
    """
    Construit une représentation textuelle du schéma de la BDD
    que le LLM peut comprendre (similaire à l'UML).
    """
    print("Construction du schéma de la base de données pour le LLM (avec indices corrigés)...")
    schema_str = "Schéma de la base de données PostgreSQL :\n\n"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        for table_name in INCLUDED_TABLES:
            schema_str += f"Table: {table_name}\n"
            
            # Obtenir les colonnes
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            columns = cursor.fetchall()
            for col in columns:
                schema_str += f"  - {col['column_name']} ({col['data_type']})\n"
                
                # --- CORRECTION : Mise à jour des indices selon votre instruction ---
                if table_name == 'event' and col['column_name'] == 'type':
                    # INJURY a été retiré d'ici
                    schema_str += "    (Indices de valeurs: 'NEAR_MISS', 'CHEMICAL_SPILL', 'EQUIPMENT_FAILURE', 'FIRE_ALARM')\n"
                if table_name == 'event' and col['column_name'] == 'classification':
                    # INJURY a été ajouté ici
                    schema_str += "    (Indices de valeurs: 'INJURY', 'EHS', 'ENVIRONMENT', 'OPERATIONS')\n"
                if table_name == 'risk' and col['column_name'] == 'gravity':
                    schema_str += "    (Indices de valeurs: 'Low', 'Medium', 'High', 'Critical')\n"
                # --- FIN DES CORRECTIONS ---

            # Obtenir les clés étrangères (relations)
            cursor.execute("""
                SELECT
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s;
            """, (table_name,))
            fks = cursor.fetchall()
            if fks:
                schema_str += "  Relations:\n"
                for fk in fks:
                    schema_str += f"    - {fk['column_name']} -> {fk['foreign_table_name']}({fk['foreign_column_name']})\n"
            
            schema_str += "\n"
            
        print("Schéma construit (avec indices corrigés).")
        return schema_str
        
    except Exception as e:
        print(f"Erreur lors de la construction du schéma: {e}")
        return "Erreur: Impossible de récupérer le schéma."
    finally:
        if conn:
            conn.close()

def execute_safe_sql(sql_query: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Exécute une requête SQL générée par l'IA de manière sécurisée.
    - N'autorise que les requêtes SELECT.
    - Ajoute une limite de sécurité.
    """
    # SÉCURITÉ 1: Ne rien autoriser d'autre que SELECT
    if not sql_query.strip().upper().startswith("SELECT"):
        raise ValueError("Requête non autorisée. Seules les requêtes SELECT sont permises.")
        
    # SÉCURITÉ 2: Empêcher les requêtes trop volumineuses (bon pour les diagrammes)
    safe_query = sql_query
    if "LIMIT" not in sql_query.upper():
        safe_query += " LIMIT 200" # Limite par défaut
        
    print(f"Exécution SQL sécurisée: {safe_query}")
    
    conn = None
    try:
        # Utiliser query_db pour lire les résultats
        results = query_db(safe_query, fetch_all=True)
        
        # Obtenir les noms des colonnes pour les diagrammes
        columns = []
        if results:
            columns = list(results[0].keys())
            
        return results, columns
        
    except Exception as e:
        print(f"Erreur lors de l'exécution SQL: {e}")
        # Renvoyer l'erreur pour que le LLM puisse la corriger
        return [{"Erreur": str(e)}], []