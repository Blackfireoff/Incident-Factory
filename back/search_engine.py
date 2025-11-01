# search_engine.py
from opensearchpy import OpenSearch
import os
from typing import List, Optional

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
        "_source": ["event_id", "type", "classification", "description", "start_datetime", "end_datetime"],
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


def search_incidents_targeted(client, index_name: str, query: str, must_phrases: list[str], size: int = 3):
    return search_incidents_with_filters(
        client=client,
        index_name=index_name,
        query=query,
        must_phrases=must_phrases,
        size=size,
        min_score=1.0,
    )


def search_incidents_with_filters(
    client,
    index_name: str,
    query: str,
    must_phrases: Optional[list[str]] = None,
    filters: Optional[List[dict]] = None,
    sort: Optional[List[dict]] = None,
    size: int = 5,
    min_score: Optional[float] = None,
):
    must_phrases = must_phrases or []
    must_clauses = []
    if query:
        must_clauses.append({
            "multi_match": {
                "query": query,
                "fields": ["description^3", "type^2", "classification"],
                "operator": "or",
                "fuzziness": "AUTO"
            }
        })

    for p in must_phrases:
        must_clauses.append({"match_phrase": {"description": p}})

    if not must_clauses:
        must_clauses.append({"match_all": {}})

    bool_query = {"must": must_clauses}
    if filters:
        bool_query["filter"] = filters

    body = {
        "_source": ["event_id", "type", "classification", "description", "start_datetime", "end_datetime"],
        "query": {"bool": bool_query},
        "size": size,
        "highlight": {
            "fields": {
                "description": {
                    "fragment_size": 220,
                    "number_of_fragments": 5,
                    "no_match_size": 0
                }
            }
        }
    }

    if sort:
        body["sort"] = sort
    if min_score is not None:
        body["min_score"] = min_score

    return client.search(index=index_name, body=body)


def search_recent_incidents(client, index_name: str, size: int = 10):
    """Fallback: récupère les incidents les plus récents par start_datetime."""
    body = {
        "_source": ["event_id", "type", "classification", "description", "start_datetime", "end_datetime"],
        "query": {"match_all": {}},
        "sort": [
            {"start_datetime": {"order": "desc", "missing": "_last"}},
            {"event_id": {"order": "desc"}}
        ],
        "size": size,
        "highlight": {
            "fields": {
                "description": {
                    "fragment_size": 220,
                    "number_of_fragments": 5,
                    "no_match_size": 0
                }
            }
        }
    }
    return client.search(index=index_name, body=body)
