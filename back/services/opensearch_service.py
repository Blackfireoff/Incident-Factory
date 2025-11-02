# services/opensearch_service.py

from opensearchpy import OpenSearch, NotFoundError
from typing import List, Optional, Dict, Any
import os
INDEX_NAME = "incidents"



# Host par défaut pour OpenSearch lancé via Docker
OS_HOST = os.getenv("OS_HOST", "localhost")
OS_PORT = int(os.getenv("OS_PORT", 9200))
# Utilisez des credentials si vous en avez configuré
OS_AUTH = ('admin', 'FireTeams@2025!') # Adaptez ('admin', 'admin') ou commentez si pas d'auth

def get_opensearch_client() -> OpenSearch:
    """Crée et retourne un client OpenSearch."""
    client_args = {
        "hosts": [{'host': OS_HOST, 'port': OS_PORT}],
        "http_auth": OS_AUTH,
        "use_ssl": True, # Mettre à True si vous utilisez HTTPS
        "verify_certs": False,
        "ssl_assert_hostname": False,
        "ssl_show_warn": False,
    }
    # Ne pas passer http_auth si non défini
    if not OS_AUTH[0]:
        del client_args["http_auth"]
        
    return OpenSearch(**client_args)

def create_index_mapping(index_name: str):
    """
    Définit le mapping "riche" pour l'index des incidents.
    Ce mapping est crucial pour le RAG.
    """
    return {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "default": {
                            "type": "standard"
                        },
                        "french_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding", "french_elision", "french_stop", "french_stemmer"]
                        }
                    },
                    "filter": {
                        "french_elision": {
                            "type": "elision",
                            "articles": ["l", "m", "t", "qu", "n", "s", "j", "d", "c", "jusqu", "quoiqu", "lorsqu", "puisqu"],
                            "articles_case": True
                        },
                        "french_stop": {
                            "type": "stop",
                            "stopwords": "_french_"
                        },
                        "french_stemmer": {
                            "type": "stemmer",
                            "language": "light_french"
                        }
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "event_id": {"type": "integer"},
                "type": {"type": "keyword"},
                "classification": {"type": "keyword"},
                "start_datetime": {"type": "date"},
                "end_datetime": {"type": "date"},
                "description": {"type": "text", "analyzer": "french_analyzer"},
                
                # Le champ de recherche principal pour le RAG
                "full_text_search": {"type": "text", "analyzer": "french_analyzer"},
                
                # --- Données structurées jointes (basées sur l'UML) ---
                "organizational_unit": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "text", "analyzer": "french_analyzer"},
                        "location": {"type": "text", "analyzer": "french_analyzer"}
                    }
                },
                "declared_by": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "text"},
                        "family_name": {"type": "text"},
                        "matricule": {"type": "keyword"}
                    }
                },
                "risks": {
                    "type": "nested", # Utiliser 'nested' pour les listes d'objets
                    "properties": {
                        "name": {"type": "text", "analyzer": "french_analyzer"},
                        "gravity": {"type": "keyword"},
                        "probability": {"type": "keyword"}
                    }
                },
                "corrective_measures": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text", "analyzer": "french_analyzer"},
                        "description": {"type": "text", "analyzer": "french_analyzer"},
                        "cost": {"type": "double"},
                        "owner_name": {"type": "text"}
                    }
                },
                "involved_employees": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text"}, # Doit être 'text' pour la recherche floue
                        "family_name": {"type": "text"}, # Doit être 'text'
                        "involvement_type": {"type": "keyword"}
                    }
                }
            }
        }
    }

# --- FONCTION ensure_index (INCHANGÉE) ---
def ensure_index(client: OpenSearch, index_name: str):
    """
    S'assure que l'index existe avec le bon mapping (utilisé par main.py).
    """
    if not client.indices.exists(index=index_name):
        print(f"Création de l'index '{index_name}'...")
        try:
            index_body = create_index_mapping(index_name)
            client.indices.create(index=index_name, body=index_body)
            print(f"Index '{index_name}' créé avec succès.")
        except Exception as e:
            print(f"Erreur lors de la création de l'index: {e}")
            raise
    else:
        print(f"L'index '{index_name}' existe déjà.")

# --- FONCTION index_incident (INCHANGÉE) ---
def index_incident(client: OpenSearch, index_name: str, doc_id: int, doc_body: dict):
    """Indexe un document (incident) dans OpenSearch (utilisé par main.py et enhanced_indexing.py)."""
    try:
        client.index(
            index=index_name,
            id=doc_id,
            body=doc_body,
            refresh=False 
        )
    except Exception as e:
        print(f"Erreur lors de l'indexation du doc {doc_id}: {e}")

# --- FONCTION search_semantic_incidents (REMPLACÉE) ---
def search_semantic_incidents(
    client: OpenSearch,
    index_name: str,
    query_text: str,
    size: int = 3
) -> Dict[str, Any]:
    """
    Exécute la recherche sémantique/textuelle pour le RAG.
    CORRIGÉE pour inclure les employés et améliorer la recherche de mots-clés.
    """
    
    # 1. Recherche de texte principale (pour les descriptions, noms, etc.)
    base_match = {
        "simple_query_string": {
            "query": query_text,
            "fields": [
                "full_text_search^5", 
                "description^3", 
                "risks.name^2", 
                "corrective_measures.name^2",
                "involved_employees.name", 
                "involved_employees.family_name"
            ],
            # --- CORRECTION : Le "AND" était trop strict ---
            "default_operator": "OR" 
        }
    }
    
    # 2. Recherche de mot-clé (pour "INJURY", "NEAR_MISS", etc.)
    keyword_match = {
        "multi_match": {
            "query": query_text,
            "fields": ["type^5", "classification^5"],
            "type": "best_fields", 
            "fuzziness": "AUTO"
        }
    }
    
    # 3. Requêtes imbriquées (Nested)
    risks_nested = {
        "nested": {
            "path": "risks",
            "query": { "match": { "risks.name": {"query": query_text, "fuzziness": "AUTO"} } }
        }
    }
    
    measures_nested = {
        "nested": {
            "path": "corrective_measures",
            "query": { "match": { "corrective_measures.name": {"query": query_text, "fuzziness": "AUTO"} } }
        }
    }

    employees_nested = {
        "nested": {
            "path": "involved_employees",
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["involved_employees.name", "involved_employees.family_name"],
                    "fuzziness": "AUTO"
                }
            }
        }
    }

    # Combinaison : Doit correspondre à l'un de ces blocs
    search_body = {
        "size": size,
        "query": {
            "bool": {
                "should": [
                    base_match,
                    keyword_match,
                    risks_nested,
                    measures_nested,
                    employees_nested
                ],
                "minimum_should_match": 1 
            }
        },
        "highlight": {
            "fields": {
                "full_text_search": {},
                "description": {}
            },
            "fragment_size": 150,
            "number_of_fragments": 3
        }
    }

    try:
        print(f"Exécution de la recherche RAG (Corrigée v2) pour: '{query_text}'")
        return client.search(index=index_name, body=search_body)
    except NotFoundError:
        print(f"Erreur: Index '{index_name}' non trouvé lors de la recherche.")
        return {"hits": {"hits": [], "total": {"value": 0}}}
    except Exception as e:
        print(f"Erreur lors de la recherche OpenSearch: {e}")
        return {"hits": {"hits": [], "total": {"value": 0}}}