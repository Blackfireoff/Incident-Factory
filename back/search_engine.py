# search_engine.py
from opensearchpy import OpenSearch
import os

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
    """Crée l’index s’il n’existe pas"""
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body={
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
            "mappings": {
                "properties": {
                    "event_id": {"type": "integer"},
                    "type": {"type": "keyword"},
                    "classification": {"type": "keyword"},
                    "description": {"type": "text", "analyzer": "french"},
                    "start_datetime": {"type": "date"},
                    "end_datetime": {"type": "date"}
                }
            }
        })

def index_incident(client, index_name: str, document_id: int, body: dict):
    client.index(index=index_name, id=document_id, body=body)

def search_incidents(client, index_name: str, query: str):
    body = {
        "query": {
            "simple_query_string": {
                "query": query,
                "fields": ["description", "type", "classification"],
                "default_operator": "and"
            }
        }
    }
    return client.search(index=index_name, body=body)
