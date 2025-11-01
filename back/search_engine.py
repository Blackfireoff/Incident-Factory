# search_engine.py
from opensearchpy import OpenSearch
import os

# --- OpenSearch index & queries (full-text) ---

INDEX_SETTINGS = {
    "settings": {
        "analysis": {
            "analyzer": {
                "french_text": {"type": "french"}
            }
        }
    },
    "mappings": {
        "properties": {
            "event_id": {"type": "keyword"},
            "type": {"type": "text", "analyzer": "french_text"},
            "classification": {"type": "text", "analyzer": "french_text"},
            "description": {"type": "text", "analyzer": "french_text"},
            "start_datetime": {"type": "date"},
            "end_datetime": {"type": "date"}
        }
    }
}

def get_opensearch_client():
    """Connexion HTTPS à OpenSearch (sécurité activée)"""
    return OpenSearch(
        hosts=[{"host": os.getenv("OS_HOST", "localhost"),
                "port": int(os.getenv("OS_PORT", 9200))}],
        use_ssl=True,                 # HTTPS
        verify_certs=False,           # en dev local (cert autosigné)
        http_auth=(os.getenv("OS_USER", "admin"),
                   os.getenv("OS_PASSWORD", "FireTeams@2025!"))
        # pas de ssl_show_warn=False -> les warnings restent visibles
    )

def ensure_index(client, index_name: str):
    """Crée l'index s'il n'existe pas avec les mappings full-text français"""
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=INDEX_SETTINGS)

def index_incident(client, index_name: str, document_id: int, body: dict):
    """Indexe un incident avec refresh=True pour visibilité immédiate en dev"""
    client.index(index=index_name, id=document_id, body=body, refresh=True)

def search_incidents(client, index_name: str, query: str):
    """Recherche full-text avec multi_match sur description, type, classification"""
    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["description^3", "type^2", "classification"],
                "operator": "or",
                "fuzziness": "AUTO"
            }
        },
        "size": 10
    }
    return client.search(index=index_name, body=body)
