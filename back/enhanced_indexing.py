# enhanced_indexing.py

import sys
from database import query_db, get_db_connection
from services.opensearch_service import (
    get_opensearch_client, 
    ensure_index, 
    index_incident
)
from opensearchpy import OpenSearch
from typing import List, Dict, Any
import json

# Nom de l'index défini dans main.py et opensearch_service.py
INDEX_NAME = "incidents" 

def fetch_rich_events() -> List[Dict[str, Any]]:
    """
    Récupère tous les événements de Postgres avec leurs données liées
    en utilisant les aggrégations JSON de Postgres, basées sur l'UML.
    """
    print("Récupération des données enrichies depuis PostgreSQL...")
    
    # Cette requête utilise LEFT JOIN et json_agg pour agréger toutes
    # les données liées en objets/tableaux JSON directement dans la BDD.
    
    sql = """
    SELECT
        e.event_id,
        e.type,
        e.classification,
        e.description,
        e.start_datetime,
        e.end_datetime,
        
        -- Unité organisationnelle (relation 1-1)
        json_build_object(
            'unit_id', ou.unit_id,
            'name', ou.name,
            'location', ou.location,
            'identifier', ou.identifier
        ) AS organizational_unit,
        
        -- Personne ayant déclaré (relation 1-1)
        json_build_object(
            'person_id', p_decl.person_id,
            'name', p_decl.name,
            'family_name', p_decl.family_name,
            'matricule', p_decl.matricule
        ) AS declared_by,
        
        -- Risques liés (relation N-N, via sous-requête)
        COALESCE(
            (
                SELECT json_agg(json_build_object(
                    'risk_id', r.risk_id,
                    'name', r.name,
                    'gravity', r.gravity,
                    'probability', r.probability
                ))
                FROM event_risk er
                JOIN risk r ON er.risk_id = r.risk_id
                WHERE er.event_id = e.event_id
            ),
            '[]'::json
        ) AS risks,
        
        -- Mesures correctives (relation N-N, via sous-requête)
        COALESCE(
            (
                SELECT json_agg(json_build_object(
                    'measure_id', cm.measure_id,
                    'name', cm.name,
                    'description', cm.description,
                    'cost', cm.cost,
                    'implementation_date', cm.implementation_date,
                    'owner_name', p_owner.name || ' ' || p_owner.family_name
                ))
                FROM event_corrective_measure ecm
                JOIN corrective_measure cm ON ecm.measure_id = cm.measure_id
                LEFT JOIN person p_owner ON cm.owner_id = p_owner.person_id
                WHERE ecm.event_id = e.event_id
            ),
            '[]'::json
        ) AS corrective_measures,
        
        -- Employés impliqués (relation N-N, via sous-requête)
        COALESCE(
            (
                SELECT json_agg(json_build_object(
                    'person_id', p_emp.person_id,
                    'name', p_emp.name,
                    'family_name', p_emp.family_name,
                    'matricule', p_emp.matricule,
                    'involvement_type', ee.involvement_type
                ))
                FROM event_employee ee
                JOIN person p_emp ON ee.person_id = p_emp.person_id
                WHERE ee.event_id = e.event_id
            ),
            '[]'::json
        ) AS involved_employees
        
    FROM event e
    LEFT JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
    LEFT JOIN person p_decl ON e.declared_by_id = p_decl.person_id
    
    GROUP BY e.event_id, ou.unit_id, p_decl.person_id
    ORDER BY e.event_id;
    """
    
    try:
        # query_db retourne une liste de RealDictRow (similaires à des dicts)
        results = query_db(sql, fetch_all=True)
        
        # Convertir les RealDictRow en vrais dicts et parser les strings JSON
        # (psycopg2 < 3 ne décode pas auto json_agg en dicts quand il vient de RealDictCursor)
        final_results = []
        for row in results:
            dict_row = dict(row)
            for key in ['risks', 'corrective_measures', 'involved_employees', 'organizational_unit', 'declared_by']:
                if isinstance(dict_row.get(key), str):
                    dict_row[key] = json.loads(dict_row[key])
                elif dict_row.get(key) is None:
                     dict_row[key] = [] if key in ['risks', 'corrective_measures', 'involved_employees'] else {}
            final_results.append(dict_row)

        print(f"Terminé. {len(final_results)} événements récupérés et parsés.")
        return final_results
    except Exception as e:
        print(f"Erreur fatale lors de la requête SQL: {e}")
        sys.exit(1)

def build_full_text_field(doc: Dict[str, Any]) -> str:
    """
    Crée un champ textuel unique pour la recherche en concaténant
    toutes les informations textuelles pertinentes.
    """
    texts: List[str] = []
    
    texts.append(doc.get("description") or "")
    texts.append(doc.get("type") or "")
    texts.append(doc.get("classification") or "")
    
    if doc.get("organizational_unit"):
        texts.append(doc["organizational_unit"].get("name", ""))
        texts.append(doc["organizational_unit"].get("location", ""))

    if doc.get("declared_by"):
        texts.append(doc["declared_by"].get("name", ""))
        texts.append(doc["declared_by"].get("family_name", ""))
        
    if doc.get("risks"):
        for risk in doc["risks"]:
            texts.append(risk.get("name", ""))
            
    if doc.get("corrective_measures"):
        for measure in doc["corrective_measures"]:
            texts.append(measure.get("name", ""))
            texts.append(measure.get("description", ""))
            
    if doc.get("involved_employees"):
        for emp in doc["involved_employees"]:
            texts.append(emp.get("name", ""))
            texts.append(emp.get("family_name", ""))

    return " ".join(filter(None, texts))

def main_indexing():
    """
    Script principal pour l'indexation enrichie.
    """
    print("Démarrage du script d'indexation enrichie...")
    
    # 1. Vérifier la connexion à la BDD
    try:
        conn = get_db_connection()
        conn.close()
        print("Connexion PostgreSQL vérifiée.")
    except Exception as e:
        print(f"Échec de la connexion à PostgreSQL: {e}")
        print("Vérifiez vos variables d'environnement (DB_HOST, DB_USER, etc.)")
        sys.exit(1)
        
    # 2. Obtenir le client OpenSearch et (re)créer l'index
    try:
        os_client = get_opensearch_client()
        if not os_client.ping():
            raise Exception("Ping OpenSearch a échoué. Vérifiez que le service tourne.")
        
        # Optionnel: Supprimer l'ancien index pour repartir à zéro
        if os_client.indices.exists(index=INDEX_NAME):
            print(f"Suppression de l'ancien index '{INDEX_NAME}'...")
            os_client.indices.delete(index=INDEX_NAME)
            
        # S'assure que l'index existe avec le bon mapping
        ensure_index(os_client, INDEX_NAME)
        print("Client OpenSearch connecté et index (re)créé.")
    except Exception as e:
        print(f"Échec de la connexion à OpenSearch: {e}")
        sys.exit(1)
        
    # 3. Récupérer les données de Postgres
    events_data = fetch_rich_events()
    
    if not events_data:
        print("Aucun événement trouvé dans la base de données. Arrêt.")
        return

    # 4. Préparer et indexer les documents
    print(f"Indexation de {len(events_data)} documents dans '{INDEX_NAME}'...")
    count = 0
    for doc in events_data:
        event_id = doc["event_id"]
        
        # Créer le champ de recherche aggrégé
        doc["full_text_search"] = build_full_text_field(doc)
        
        try:
            index_incident(os_client, INDEX_NAME, event_id, doc)
            count += 1
            if count % 100 == 0:
                print(f"  ... {count}/{len(events_data)} indexés")
        except Exception as e:
            print(f"Erreur lors de l'indexation du document {event_id}: {e}")

    # Forcer un rafraîchissement de l'index à la fin
    os_client.indices.refresh(index=INDEX_NAME)
    print(f"\nIndexation terminée. {count} documents traités.")
    print(f"Vous pouvez maintenant utiliser l'endpoint RAG '/ai/query'.")

if __name__ == "__main__":
    main_indexing() 