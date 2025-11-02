from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, date
from decimal import Decimal
from database import query_db
from fastapi import Request
from services.bedrock_service import BedrockChatService
from opensearchpy import OpenSearch
import boto3
import json
from typing import List, Optional, Tuple
import re
import unicodedata
from services.bedrock_service import MODEL_ID
from services.analytics_service import (
    generate_chart_from_question,
    generate_summary_report,
)


from search_engine import (
    get_opensearch_client,
    ensure_index,
    index_incident,
    search_incidents_with_filters,
    search_recent_incidents,
)

CHEM_PATTERNS = [
    r"\bacetone\b", r"\bac[ée]tone\b",
    r"\bhydraulic oil\b", r"\bhuile hydraulique\b",
    r"\bsolvent\b", r"\bsolvant(s)?\b",
    r"\bproduits?\s+chimiques?\b",
    r"\bchemical(s)?\b"
]
UNIT_PATTERN = r"\bUNIT-\d{3}\b"
AREA_PATTERNS = [r"Hazardous Waste Management", r"Chemical Storage", r"Mixing facility"]
ACTION_HINTS = [
    "mesure",
    "action",
    "immédiate",
    "immediate",
    "contain",
    "évac",
    "neutralis",
    "isoler",
    "isolation",
    "fermeture",
    "secure",
]
STOPWORDS = {
    "les", "des", "dans", "avec", "pour", "par", "sur", "quoi", "quel", "quels",
    "quelle", "quelles", "une", "lors", "d'", "des", "est", "sont", "un", "une",
    "de", "et", "ou", "the", "what", "were", "was", "when", "how", "why", "a",
    "an", "aux", "quel", "quelle", "quelles", "quels", "quoi", "qui", "où"
}
WORD_PATTERN = re.compile(r"[a-zA-Z0-9À-ÖØ-öø-ÿ-]+")
TOKEN_SYNONYMS = {
    "incidant": {"incident"},
    "incidants": {"incident", "incidents"},
    "incidents": {"incident"},
    "produits": {"produit"},
    "produit": {"product"},
    "chimiques": {"chimique", "chemical", "chemicals"},
    "chimique": {"chemical"},
    "recement": {"recent", "recentement"},
    "recentement": {"recent"},
    "recemment": {"recent"},
}
ISO_DATE_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b")
SLASH_DATE_PATTERN = re.compile(r"\b(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(20\d{2}|19\d{2})\b")
MONTH_NAME_PATTERN = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(20\d{2}|19\d{2})\b",
    flags=re.I
)
MONTH_NAME_MAP = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "aout": 8, "août": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12
}
RECENT_HINTS = {"recent", "récent", "recente", "récente", "recemment", "récemment", "recentes", "récents"}

NO_CONTEXT_REPLY = "Je ne sais pas sur la base du contexte fourni."


def extract_must_phrases(question: str) -> list[str]:
    q = question.lower()
    must = set()

    for m in re.findall(UNIT_PATTERN, question):
        must.add(m)

    for pat in CHEM_PATTERNS:
        if re.search(pat, q, flags=re.I):
            if "acetone" in pat:
                must.add("acetone")
            if "hydraulic oil" in pat or "huile" in pat:
                must.add("hydraulic oil")
            if "solvent" in pat:
                must.add("solvent")
            if "solvant" in pat:
                must.add("solvent")
            if "produits" in pat or "chemical" in pat:
                must.add("produits chimiques")
                must.add("chemical")

    for ap in AREA_PATTERNS:
        if re.search(ap, question, flags=re.I):
            must.add(ap)

    return [m for m in must if m]


def _select_action_sentences(description: str, max_sentences: int = 2) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", description.strip())
    selected: list[str] = []
    for sent in sentences:
        sent_clean = sent.strip()
        if not sent_clean:
            continue
        lower = sent_clean.lower()
        if any(hint in lower for hint in ACTION_HINTS):
            selected.append(sent_clean)
        if len(selected) >= max_sentences:
            break
    return selected


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()


def extract_question_keywords(question: str) -> set[str]:
    keywords: set[str] = set()
    normalized_stopwords = getattr(extract_question_keywords, "_norm_stopwords", None)
    if normalized_stopwords is None:
        normalized_stopwords = {_normalize_text(sw) for sw in STOPWORDS}
        extract_question_keywords._norm_stopwords = normalized_stopwords

    for match in WORD_PATTERN.finditer(question):
        token = match.group()
        token_norm = _normalize_text(token)
        if len(token_norm) < 3:
            continue
        if token_norm in normalized_stopwords:
            continue

        keywords.add(token_norm)

        if token_norm.endswith("s") and len(token_norm) > 3:
            keywords.add(token_norm[:-1])

        for syn in TOKEN_SYNONYMS.get(token_norm, set()):
            keywords.add(_normalize_text(syn))

    return keywords


def extract_iso_dates(question: str) -> list[str]:
    text = question
    dates = set()
    for match in ISO_DATE_PATTERN.finditer(text):
        year, month, day = match.groups()
        try:
            iso = datetime(int(year), int(month), int(day)).date().isoformat()
            dates.add(iso)
        except ValueError:
            continue

    for match in SLASH_DATE_PATTERN.finditer(text):
        day, month, year = match.groups()
        try:
            iso = datetime(int(year), int(month), int(day)).date().isoformat()
            dates.add(iso)
        except ValueError:
            continue

    for match in MONTH_NAME_PATTERN.finditer(text):
        day, month_name, year = match.groups()
        month_key = month_name.lower()
        month_num = MONTH_NAME_MAP.get(month_key)
        if not month_num:
            continue
        try:
            iso = datetime(int(year), month_num, int(day)).date().isoformat()
            dates.add(iso)
        except ValueError:
            continue

    return sorted(dates)


def extract_event_ids(question: str) -> list[int]:
    pattern = re.compile(r"(?:event[_\s-]?id\s*[:=]?\s*|event\s+)(\d{2,6})", flags=re.I)
    ids = []
    for match in pattern.finditer(question):
        try:
            ids.append(int(match.group(1)))
        except ValueError:
            continue
    return ids


def has_recent_hint(question: str) -> bool:
    normalized = _normalize_text(question)
    return any(hint in normalized for hint in RECENT_HINTS)


def extract_type_and_classifications(question: str) -> tuple[Optional[str], List[str]]:
    tokens = [
        token.upper()
        for token in re.findall(r"[A-Z]{2,}(?:_[A-Z]+)?", question)
    ]
    if not tokens:
        return None, []

    if len(tokens) == 1:
        return None, tokens

    type_candidate = tokens[0]
    classifications = tokens[1:] or []
    return type_candidate, classifications


def build_date_filters(iso_dates: list[str]) -> list[dict]:
    if not iso_dates:
        return []

    date_clauses = []
    for iso in iso_dates:
        start = f"{iso}T00:00:00"
        end = f"{iso}T23:59:59"
        date_clauses.append({
            "bool": {
                "should": [
                    {"range": {"start_datetime": {"gte": start, "lte": end}}},
                    {"range": {"end_datetime": {"gte": start, "lte": end}}},
                    {"bool": {
                        "must": [
                            {"range": {"start_datetime": {"lte": end}}},
                            {"range": {"end_datetime": {"gte": start}}}
                        ]
                    }}
                ],
                "minimum_should_match": 1
            }
        })

    if not date_clauses:
        return []

    return [{
        "bool": {
            "should": date_clauses,
            "minimum_should_match": 1
        }
    }]


def count_incidents_for_filters(
    type_filter: Optional[str],
    classification_filters: List[str],
    ou_name_patterns: Optional[List[str]] = None
) -> Tuple[int, List[Tuple[str, str, int]]]:
    joins = []
    where_clauses = []
    params: List[str] = []

    if ou_name_patterns:
        joins.append("INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id")
        ors = " OR ".join(["ou.name ILIKE %s"] * len(ou_name_patterns))
        where_clauses.append(f"({ors})")
    if type_filter:
        where_clauses.append("e.type = %s")
        params.append(type_filter)
    if classification_filters:
        placeholders = ", ".join(["%s"] * len(classification_filters))
        where_clauses.append(f"e.classification IN ({placeholders})")
        params.extend(classification_filters)

    where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

    sql = f"""
        SELECT
            e.type AS type,
            e.classification AS classification,
            COUNT(*) AS count
        FROM event e
        {' '.join(joins)}
        WHERE {where_sql}
        GROUP BY e.type, e.classification
        ORDER BY count DESC, classification ASC
    """

    rows = query_db(sql, params=tuple(params))
    typed_rows = []
    total = 0
    for r in rows:
        row_count = int(r["count"])
        total += row_count
        typed_rows.append((r["type"], r["classification"], row_count))

    return total, typed_rows


def format_filtered_count_answer(
    type_filter: Optional[str],
    classification_filters: List[str],
    total: int,
    rows: List[Tuple[str, str, int]]
) -> str:
    if not rows:
        target = ", ".join(classification_filters) if classification_filters else "toutes classes"
        if type_filter:
            return (
                f"Aucun incident trouvé pour le type {type_filter} et les classifications {target}."
            )
        return f"Aucun incident trouvé pour les classifications {target}."

    if type_filter and classification_filters:
        header = (
            f"Nombre d'incidents pour le type {type_filter} et les classifications "
            f"{', '.join(classification_filters)} : {total}"
        )
    elif type_filter:
        header = f"Nombre d'incidents pour le type {type_filter} : {total}"
    else:
        header = (
            f"Nombre d'incidents pour les classifications {', '.join(classification_filters)} : {total}"
        )

    details = [
        f"- {typ or 'N/A'} / {cls or 'N/A'} : {count}"
        for typ, cls, count in rows
    ]
    return header + "\n" + "\n".join(details)


def enforce_answer_policy(answer: str, ctx: List[dict]) -> Optional[str]:
    stripped = (answer or "").strip()
    if not ctx or all(not c.get("fragments") for c in ctx):
        return NO_CONTEXT_REPLY

    if stripped == NO_CONTEXT_REPLY:
        return NO_CONTEXT_REPLY
    if stripped.startswith(NO_CONTEXT_REPLY):
        return NO_CONTEXT_REPLY

    event_id_counts = {c.get("event_id"): len(c.get("fragments", [])) for c in ctx}
    allowed_event_ids = {eid for eid, count in event_id_counts.items() if count > 0}
    pattern = re.compile(r"event_id\s*[:=]\s*(\d+)", re.I)
    found_ids = {int(eid) for eid in pattern.findall(answer or "") if str(eid).isdigit()}

    if found_ids and not found_ids.issubset(allowed_event_ids):
        return None
    if not found_ids:
        return None
    return answer


def build_default_answer(ctx: List[dict], max_points: int = 6) -> str:
    usable = [c for c in ctx if c.get("fragments")]
    if not usable:
        return NO_CONTEXT_REPLY

    lines = []
    citations = []
    for c in usable[:max_points]:
        event_id = c.get("event_id")
        citations.append(f"event_id:{event_id}")
        frag = c.get("fragments", [])[0]
        start = c.get("start_datetime") or "?"
        typ = c.get("type") or "Incident"
        classification = c.get("classification")
        label_parts = [typ]
        if classification:
            label_parts.append(classification)
        label = " / ".join(label_parts)
        lines.append(f"- {label} ({start}) : \"{frag}\" [event_id:{event_id}]")

    if len(lines) < 3 and len(usable) > len(lines):
        for c in usable[len(lines):min(len(usable), max_points)]:
            event_id = c.get("event_id")
            citations.append(f"event_id:{event_id}")
            frag_list = c.get("fragments", [])
            frag = frag_list[0] if frag_list else ""
            start = c.get("start_datetime") or "?"
            typ = c.get("type") or "Incident"
            lines.append(f"- {typ} ({start}) : \"{frag}\" [event_id:{event_id}]")

    citations_text = f"Citations: [{', '.join(dict.fromkeys(citations))}]"
    return "\n".join(lines + [citations_text])

# --- Distribution helpers: SQL + pourcentages déterministes ---

def is_distribution_question(text: str) -> bool:
    patterns = [
        r"(principaux|top|plus\s+(fr[ée]quents?|courants?)|r[ée]partition|classement|types?\s+d[' ]incident)",
        r"(combien|nombre)\s+d[' ]?incidents?",
    ]
    return any(re.search(pat, text, re.I) for pat in patterns)

def extract_ou_patterns(text: str) -> Optional[List[str]]:
    """
    Détecte grosso modo 'ateliers de production' et proches.
    Retourne une liste de patterns pour OU.name ILIKE.
    """
    patterns = []
    if re.search(r"(atelier|ateliers?)", text, re.I):
        patterns += ["%atelier%"]
    if re.search(r"(production|prod\b)", text, re.I):
        patterns += ["%production%", "%prod%"]
    if re.search(r"(usine|manufactur|ligne)", text, re.I):
        patterns += ["%usine%", "%manufactur%", "%ligne%"]
    return patterns or None

def get_top_classifications(limit: int = 10, ou_name_patterns: Optional[List[str]] = None) -> List[Tuple[str, int]]:
    """
    Retourne [(classification, count)] triés décroissant.
    Si ou_name_patterns est fourni, filtre sur organizational_unit.name ILIKE.
    """
    if ou_name_patterns:
        ors = " OR ".join(["ou.name ILIKE %s"] * len(ou_name_patterns))
        sql = f"""
            SELECT e.classification, COUNT(*) AS count
            FROM event e
            INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
            WHERE {ors}
            GROUP BY e.classification
            ORDER BY count DESC
            LIMIT %s;
        """
        params = tuple(ou_name_patterns) + (limit,)
    else:
        sql = """
            SELECT e.classification, COUNT(*) AS count
            FROM event e
            GROUP BY e.classification
            ORDER BY count DESC
            LIMIT %s;
        """
        params = (limit,)

    rows = query_db(sql, params=params)
    return [(r["classification"], int(r["count"])) for r in rows]

def _percentages_that_sum_to_100(counts: List[int]) -> List[int]:
    """Largest remainder: plancher + redistribution du reliquat aux plus grosses parts."""
    total = sum(counts) or 1
    raw = [c * 100.0 / total for c in counts]
    floors = [int(x) for x in raw]
    remainder = 100 - sum(floors)
    order = sorted(range(len(raw)), key=lambda i: (raw[i] - floors[i]), reverse=True)
    for i in range(remainder):
        floors[order[i]] += 1
    return floors

def format_stats_answer(stats: List[Tuple[str, int]]) -> str:
    """
    Réponse déterministe:
    - Tri assuré par SQL
    - Pourcentages qui totalisent 100
    - Libellés replicés tels quels
    """
    if not stats:
        return "Je ne sais pas sur la base du contexte fourni."
    
    labels = [c for c, _ in stats]
    counts = [n for _, n in stats]
    perc = _percentages_that_sum_to_100(counts)
    
    lines = [f"{i+1}. {labels[i]} ({counts[i]}) - {perc[i]}%" for i in range(len(stats))]
    return "Les principaux types d'incidents sont :\n\n" + "\n".join(lines)

INDEX_NAME = "incidents"
app = FastAPI(title="FireTeams API")
chat_service = BedrockChatService()

# --- Chart & summary generation endpoints ---

@app.post("/ai/chart")
async def ai_chart(request: Request):
    """
    Génère un graphique PNG encodé en base64 à partir d'une question analytique.
    Body JSON attendu: { "question": "..."} ou { "message": "..." }
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        data = {}

    question = (data or {}).get("question") or (data or {}).get("message")
    if not question:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Provide 'question' (or 'message') in the JSON body",
            },
        )

    try:
        chart_result = generate_chart_from_question(question)
        if not chart_result:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "not_found",
                    "question": question,
                    "message": (
                        "Aucun graphique généré pour cette question. "
                        "Vérifiez que la requête cible des machines ou des mesures correctives."
                    ),
                },
            )

        chart = {
            "title": chart_result.chart_data.title,
            "x_label": chart_result.chart_data.x_label,
            "y_label": chart_result.chart_data.y_label,
            "categories": chart_result.chart_data.categories,
            "values": chart_result.chart_data.values,
            "caption": chart_result.chart_data.caption,
            "image_base64": chart_result.image_base64,
            "image_mime": chart_result.image_mime,
        }

        return JSONResponse(
            {
                "status": "success",
                "question": question,
                "chart": chart,
            }
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la génération du graphique: {str(exc)}",
            },
        )


@app.post("/ai/summary")
async def ai_summary(request: Request):
    """
    Génère un rapport synthétique au format Markdown.
    """
    try:
        await request.json()
    except json.JSONDecodeError:
        pass
    except Exception:
        pass

    try:
        report = generate_summary_report()
        return JSONResponse(
            {
                "status": "success",
                "format": "markdown",
                "suggested_filename": "synthese_incidents.txt",
                "report": report,
            }
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la génération du rapport: {str(exc)}",
            },
        )


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

def index_events_in_opensearch(os_client):
    events = query_db("SELECT event_id, description FROM event WHERE description IS NOT NULL;")

    for ev in events:
        embedding = generate_embedding(ev["description"])  # fonction à créer (via Bedrock)
        doc = {
            "event_id": ev["event_id"],
            "description": ev["description"],
            "embedding": embedding
        }
        os_client.index(index="events_vector_index", id=ev["event_id"], body=doc)

    print(f"✅ {len(events)} événements indexés dans OpenSearch")

def generate_embedding(text: str):
    bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text})
    )

    embedding = json.loads(response["body"].read())["embedding"]
    return embedding

def search_similar_context(query: str, os_client):
    query_vector = generate_embedding(query)

    search_body = {
        "size": 3,  # nombre de documents similaires à renvoyer
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": 3
                }
            }
        }
    }

    response = os_client.search(index="events_vector_index", body=search_body)
    return [hit["_source"]["description"] for hit in response["hits"]["hits"]]

def answer_question_with_context(question: str):
    os_client = OpenSearch(hosts=[{"host": "localhost", "port": 9200}])
    context_docs = search_similar_context(question, os_client)

    context_text = "\n\n".join(context_docs)

    system_prompt = """
    Tu es un assistant expert en analyse d'évènements.
    Utilise le contexte fourni pour répondre à la question de manière claire et précise.
    Si le contexte ne contient pas la réponse, indique-le explicitement.
    """

    user_prompt = f"Contexte:\n{context_text}\n\nQuestion: {question}"

    # Créer le client Bedrock
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"
    )

    response = bedrock_client.converse(
        modelId="arn:aws:bedrock:us-east-1:010526273152:inference-profile/us.meta.llama3-2-11b-instruct-v1:0",
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"temperature": 0.7, "maxTokens": 1000}
    )

    return response["output"]["message"]["content"][0]["text"]

def _fetch_context_from_os(query: str, limit: int = 3) -> List[dict]:
    client = get_opensearch_client()
    ensure_index(client, INDEX_NAME)
    must_phrases = extract_must_phrases(query)
    question_keywords = extract_question_keywords(query)
    normalized_terms = {_normalize_text(term) for term in (list(question_keywords) + must_phrases)}
    normalized_terms = {t for t in normalized_terms if t}

    event_ids = extract_event_ids(query)
    iso_dates = extract_iso_dates(query)
    recent_hint = has_recent_hint(query)

    filters: List[dict] = []
    if event_ids:
        filters.append({"terms": {"event_id": [str(eid) for eid in event_ids]}})
    filters.extend(build_date_filters(iso_dates))

    strict_filters = bool(filters)

    sort: Optional[List[dict]] = None
    if iso_dates and not event_ids:
        sort = [
            {"start_datetime": {"order": "asc", "missing": "_last"}},
            {"event_id": {"order": "asc"}}
        ]
    elif recent_hint and not strict_filters:
        sort = [
            {"start_datetime": {"order": "desc", "missing": "_last"}},
            {"event_id": {"order": "desc"}}
        ]

    search_size = max(limit, len(event_ids) or 0, len(iso_dates) * 2 or 0, 5 if strict_filters else limit)
    min_score = 1.0 if (must_phrases and not strict_filters) else None

    res = search_incidents_with_filters(
        client=client,
        index_name=INDEX_NAME,
        query=query,
        must_phrases=must_phrases,
        filters=filters if filters else None,
        sort=sort,
        size=search_size,
        min_score=min_score
    ) or {}

    def build_context_from_hits(hits: List[dict], require_match: bool, max_items: int) -> List[dict]:
        context_items: List[dict] = []
        for h in hits:
            s = h.get("_source", {})
            hl = h.get("highlight", {}).get("description", []) or []
            raw_desc = (s.get("description") or "").strip()
            fragments: list[str] = []
            seen = set()

            def add_fragment(text: str, require_match_inner: bool = True):
                trimmed = text.strip()
                if not trimmed:
                    return
                norm = _normalize_text(trimmed)
                if require_match_inner and require_match and normalized_terms and not any(term in norm for term in normalized_terms):
                    return
                if trimmed in seen:
                    return
                fragments.append(trimmed)
                seen.add(trimmed)

            cleaned_highlights = [re.sub(r"<[^>]+>", "", frag) for frag in hl[:5]]
            for frag in cleaned_highlights:
                add_fragment(frag)

            if raw_desc:
                for sent in _select_action_sentences(raw_desc):
                    add_fragment(sent)

            if not fragments:
                for frag in cleaned_highlights:
                    add_fragment(frag, require_match_inner=False)

            if not fragments and raw_desc:
                add_fragment(raw_desc[:400], require_match_inner=False)

            if not fragments:
                continue

            context_items.append({
                "event_id": s.get("event_id"),
                "type": s.get("type"),
                "classification": s.get("classification"),
                "start_datetime": s.get("start_datetime"),
                "end_datetime": s.get("end_datetime"),
                "fragments": fragments
            })

            if len(context_items) >= max_items:
                break

        return context_items

    hits = res.get("hits", {}).get("hits", [])
    ctx = build_context_from_hits(hits, require_match=True, max_items=limit)
    if not ctx:
        ctx = build_context_from_hits(hits, require_match=False, max_items=limit)

    if not ctx and not strict_filters:
        recent_size = max(limit, 10)
        recent_res = search_recent_incidents(client, INDEX_NAME, size=recent_size) or {}
        recent_hits = recent_res.get("hits", {}).get("hits", [])
        ctx = build_context_from_hits(recent_hits, require_match=len(normalized_terms) > 0, max_items=limit)

        if not ctx:
            ctx = build_context_from_hits(recent_hits, require_match=False, max_items=limit)

    return ctx

def _build_prompts(user_message: str, ctx: List[dict]) -> tuple[str, str]:
    system_prompt = (
        "Tu es un assistant EXTRACTIF. Tu DOIS répondre uniquement avec des informations présentes "
        "dans le CONTEXTE (fragments) fourni ci-dessous. "
        "Chaque puce doit correspondre à une information explicite du contexte. "
        "Interdictions: ne pas inventer, ne pas fusionner des éléments de fragments sans lien, "
        "ne pas extrapoler à partir d'autres incidents. "
        "Si le contexte ne contient pas la réponse, réponds exactement: "
        "\"Je ne sais pas sur la base du contexte fourni.\" sans ajouter d'autre texte. "
        "Ajoute une courte citation entre guillemets après chaque puce, et cite les event_id utilisés."
    )

    if ctx:
        blocks = []
        for c in ctx:
            start_dt = c.get("start_datetime") or "?"
            end_dt = c.get("end_datetime") or "?"
            prefix = f"[event_id={c.get('event_id')}; start={start_dt}; end={end_dt}]"
            for frag in c.get("fragments", []):
                blocks.append(f"{prefix} {frag}")
        context_text = "\n".join(blocks)
    else:
        context_text = "(aucun contexte trouvé)"

    user_prompt = (
        f"Question: {user_message}\n\n"
        f"CONTEXT FRAGMENTS:\n{context_text}\n\n"
        "Consignes de sortie:\n"
        "- Réponds en puces, 3 à 6 points maximum.\n"
        "- Chaque puce = une mesure/action/constat présent dans un fragment, avec une mini-citation exacte entre guillemets.\n"
        "- Termine par: Citations: [event_id:...]\n"
        "- Si le contexte ne permet pas de répondre, réponds exactement \"Je ne sais pas sur la base du contexte fourni.\" sans ajouter aucun autre texte (pas de proverbes, pas de conclusion).\n"
    )
    return system_prompt, user_prompt


@app.on_event("startup")
def setup_search():
    """S'assure que l'index OpenSearch existe au démarrage"""
    client = get_opensearch_client()
    ensure_index(client, INDEX_NAME)


@app.get("/")
async def root():
    return {"message": "FireTeams API is running"}

@app.get("/db/status")
async def db_status():
    """Route pour vérifier la connexion à la base de données"""
    try:
        version = query_db("SELECT version();", fetch_one=True)
        db_info = query_db("SELECT current_database(), current_user;", fetch_one=True)
        
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
        tables = query_db("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
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
        
        # Récupérer les 20 premières lignes avec tous les champs nécessaires pour l'interface Incident
        events = query_db("""
            SELECT 
                e.event_id,
                e.description,
                e.type,
                e.classification,
                e.start_datetime,
                e.end_datetime,
                p.person_id,
                p.matricule,
                p.name,
                p.family_name,
                p.role
            FROM event e
            LEFT JOIN person p ON e.declared_by_id = p.person_id
            ORDER BY e.event_id
            LIMIT 20 OFFSET %s;
        """, params=(offset,))
        
        # Transformer les résultats pour correspondre à l'interface Incident
        incidents = []
        for event in events:
            incident = {
                "id": event['event_id'],
                "type": event['type'],
                "classification": event['classification'],
                "start_date": event['start_datetime'],
                "end_date": event['end_datetime'],
                "description": event['description'],
                "reporter": None
            }
            
            # Construire l'objet Person si la personne existe
            if event['person_id']:
                incident["reporter"] = {
                    "id": event['person_id'],
                    "matricule": event['matricule'],
                    "name": event['name'],
                    "family_name": event['family_name'],
                    "role": event['role']
                }
            
            incidents.append(incident)
        
        # Convertir les datetime en strings pour la sérialisation JSON
        incidents_serializable = convert_datetime_to_str(incidents)
        
        return JSONResponse({
            "status": "success",
            "offset": offset,
            "count": len(incidents_serializable),
            "events": incidents_serializable
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des événements: {str(e)}"
            }
        )

@app.get("/get_basic_info")
async def get_basic_info():
    """Retourne des indicateurs globaux pour le tableau de bord"""
    try:
        total_incidents_row = query_db(
            "SELECT COUNT(*) AS total FROM event;", fetch_one=True
        )
        critical_risk_row = query_db(
            """
            SELECT COUNT(DISTINCT er.event_id) AS total
            FROM event_risk er
            INNER JOIN risk r ON er.risk_id = r.risk_id
            WHERE r.gravity ILIKE 'critical%';
            """,
            fetch_one=True,
        )
        no_corrective_row = query_db(
            """
            SELECT COUNT(*) AS total
            FROM event e
            LEFT JOIN event_corrective_measure ecm ON e.event_id = ecm.event_id
            WHERE ecm.event_id IS NULL;
            """,
            fetch_one=True,
        )
        total_cost_row = query_db(
            """
            SELECT COALESCE(SUM(cm.cost), 0) AS total_cost
            FROM event_corrective_measure ecm
            INNER JOIN corrective_measure cm ON ecm.measure_id = cm.measure_id;
            """,
            fetch_one=True,
        )

        payload = convert_datetime_to_str(
            {
                "total_event_count": total_incidents_row["total"] if total_incidents_row else 0,
                "total_critical_risk_count": critical_risk_row["total"] if critical_risk_row else 0,
                "total_no_corrective_measure_count": no_corrective_row["total"] if no_corrective_row else 0,
                "total_corrective_measure_cost": total_cost_row["total_cost"] if total_cost_row else 0,
            }
        )

        return JSONResponse({"status": "success", "data": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des informations de base: {str(e)}",
            },
        )

@app.get("/get_most_recent_incidents")
async def get_most_recent_incidents(limit: int = 5):
    """Retourne les incidents les plus récents"""
    try:
        if limit <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Limit must be a positive integer",
                },
            )

        events = query_db(
            """
            SELECT
                e.event_id,
                e.type,
                e.classification,
                e.start_datetime,
                e.end_datetime,
                p.person_id,
                p.matricule,
                p.name,
                p.family_name,
                p.role
            FROM event e
            LEFT JOIN person p ON e.declared_by_id = p.person_id
            ORDER BY e.start_datetime DESC NULLS LAST, e.event_id DESC
            LIMIT %s;
            """,
            params=(limit,),
        )

        incidents: list[dict] = []
        for event in events:
            incident = {
                "id": event["event_id"],
                "type": event["type"],
                "classification": event["classification"],
                "start_date": event["start_datetime"],
                "end_date": event["end_datetime"],
                "reporter": None,
            }

            if event["person_id"]:
                incident["reporter"] = {
                    "id": event["person_id"],
                    "matricule": event["matricule"],
                    "name": event["name"],
                    "family_name": event["family_name"],
                    "role": event["role"],
                }

            incidents.append(incident)

        payload = convert_datetime_to_str(incidents)
        return JSONResponse({"incidents": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des incidents récents: {str(e)}",
            },
        )

@app.get("/get_top_organization")
async def get_top_organization(limit: int = 5):
    """Retourne les unités organisationnelles avec le plus d'incidents"""
    try:
        if limit <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Limit must be a positive integer",
                },
            )

        rows = query_db(
            """
            SELECT
                ou.unit_id,
                ou.identifier,
                ou.name,
                ou.location,
                COUNT(*) AS total
            FROM event e
            INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
            GROUP BY ou.unit_id, ou.identifier, ou.name, ou.location
            ORDER BY total DESC, ou.unit_id ASC
            LIMIT %s;
            """,
            params=(limit,),
        )

        top_entries = [
            {
                "organization": {
                    "id": row["unit_id"],
                    "identifier": row["identifier"],
                    "name": row["name"],
                    "location": row["location"],
                },
                "value": row["total"],
            }
            for row in rows
        ]

        return JSONResponse({"top_organization": top_entries})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des organisations principales: {str(e)}",
            },
        )

@app.get("/get_incident_by_type")
async def get_incident_by_type():
    """Retourne le nombre total d'incidents par type"""
    try:
        rows = query_db(
            """
            SELECT
                e.type,
                COUNT(*) AS total
            FROM event e
            GROUP BY e.type
            ORDER BY total DESC, e.type ASC;
            """
        )

        payload = [
            {
                "type": row["type"],
                "value": row["total"],
            }
            for row in rows
        ]

        return JSONResponse({"incidents_by_type": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des incidents par type: {str(e)}",
            },
        )

@app.get("/get_incident_by_classification")
async def get_incident_by_classification(limit: int = 5):
    """Retourne le nombre total d'incidents par classification (max 5)"""
    try:
        if limit <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Limit must be a positive integer",
                },
            )

        rows = query_db(
            """
            SELECT
                e.classification,
                COUNT(*) AS total
            FROM event e
            GROUP BY e.classification
            ORDER BY total DESC, e.classification ASC
            LIMIT %s;
            """,
            params=(limit,),
        )

        payload = [
            {
                "type": row["classification"],
                "value": row["total"],
            }
            for row in rows
        ]

        return JSONResponse({"incidents": payload})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur lors de la récupération des incidents par classification: {str(e)}",
            },
        )

@app.get("/{event_id}/details")
async def get_event_details(event_id: int):
    """Route pour récupérer tous les détails d'un événement"""
    try:
        # Récupérer les détails de l'événement avec inner join person
        event = query_db("""
            SELECT 
                e.event_id,
                e.description,
                e.start_datetime,
                e.end_datetime,
                e.type,
                e.classification,
                p.matricule,
                p.name,
                p.family_name,
                p.person_id
            FROM event e
            INNER JOIN person p ON e.declared_by_id = p.person_id
            WHERE e.event_id = %s;
        """, params=(event_id,), fetch_one=True)
        
        if not event:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Événement avec l'ID {event_id} introuvable"
                }
            )
        
        # Récupérer les employés impliqués avec inner join person
        employees = query_db("""
            SELECT 
                ee.person_id,
                p.matricule,
                p.name,
                p.family_name
            FROM event_employee ee
            INNER JOIN person p ON ee.person_id = p.person_id
            WHERE ee.event_id = %s;
        """, params=(event_id,))
        
        # Récupérer l'unité organisationnelle
        organizational_unit = query_db("""
            SELECT 
                ou.identifier,
                ou.name, 
                ou.location, 
                ou.unit_id
            FROM event e
            INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
            WHERE e.event_id = %s;
        """, params=(event_id,), fetch_one=True)
        
        # Récupérer les mesures correctives avec inner join corrective_measure et person
        corrective_measures = query_db("""
            SELECT 
                cm.measure_id,
                cm.name,
                cm.implementation_date AS implementation,
                cm.description,
                cm.cost,
                cm.owner_id,
                p_owner.matricule AS owner_matricule,
                p_owner.name AS owner_name,
                p_owner.family_name AS owner_family_name
            FROM event_corrective_measure ecm
            INNER JOIN corrective_measure cm ON ecm.measure_id = cm.measure_id
            INNER JOIN person p_owner ON cm.owner_id = p_owner.person_id
            WHERE ecm.event_id = %s;
        """, params=(event_id,))
        
        # Récupérer les risques avec inner join risk
        risks = query_db("""
            SELECT 
                r.risk_id,
                r.name,
                r.gravity,
                r.probability
            FROM event_risk er
            INNER JOIN risk r ON er.risk_id = r.risk_id
            WHERE er.event_id = %s;
        """, params=(event_id,))
        
        risks_payload = None
        if risks:
            risks_payload = [
                {
                    "id": r['risk_id'],
                    "name": r['name'],
                    "gravity": r['gravity'],
                    "probability": r['probability']
                }
                for r in risks
            ]
        
        # Construire la réponse selon la structure demandée
        result = {
            "id": event['event_id'],
            "description": event['description'],
            "start_datetime": event['start_datetime'],
            "end_datetime": event['end_datetime'],
            "type": event['type'],
            "classification": event['classification'],
            "person": {
                "id": event['person_id'],
                "matricule": event['matricule'],
                "name": event['name'],
                "family_name": event['family_name']
            },
            "employees": [
                {
                    "id": emp['person_id'],
                    "matricule": emp['matricule'],
                    "name": emp['name'],
                    "family_name": emp['family_name']
                }
                for emp in (employees if employees else [])
            ],
            "organizational_unit": {
                "id": organizational_unit['unit_id'] if organizational_unit else None,
                "identifier": organizational_unit['identifier'] if organizational_unit else None,
                "name": organizational_unit['name'] if organizational_unit else None,
                "location": organizational_unit['location'] if organizational_unit else None,
            } if organizational_unit else None,
            "corrective_measures": [
                {
                    "id": cm['measure_id'],
                    "name": cm['name'],
                    "implementation": cm['implementation'],
                    "description": cm['description'],
                    "cost": cm['cost'],
                    "owner": {
                        "id": cm['owner_id'],
                        "matricule": cm['owner_matricule'],
                        "name": cm['owner_name'],
                        "family_name": cm['owner_family_name']
                    }
                }
                for cm in (corrective_measures if corrective_measures else [])
            ],
            "risks": risks_payload
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
    

@app.post("/ai/analyze_event")
async def analyze_event(request: Request):
    """
    Route pour analyser un rapport d'évènement via Llama 3.2
    Exemple de corps JSON :
    {
        "text": "Un incendie s'est déclaré dans le local technique à 9h45..."
    }
    """
    try:
        data = await request.json()
        text = data.get("text")
        if not text:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Champ 'text' manquant dans la requête"}
            )

        ai_response = chat_service.analyze_event(text)
        return JSONResponse({
            "status": "success",
            "analysis": ai_response
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )
    
@app.post("/ai/analyze_event/{event_id}")
async def analyze_event_from_db(event_id: int):
    """Analyse un évènement via l'IA sans l'enregistrer dans la BDD"""
    try:
        # Récupère la description de l'évènement
        event = query_db("""
            SELECT description FROM event WHERE event_id = %s;
        """, params=(event_id,), fetch_one=True)

        if not event:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"Évènement avec ID {event_id} introuvable"}
            )

        # Appel du modèle IA avec la description
        ai_response = chat_service.analyze_event(event["description"])

        # Retourne simplement la réponse IA sans insertion
        return JSONResponse({
            "status": "success",
            "event_id": event_id,
            "description": event["description"],
            "analysis": ai_response
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )




@app.post("/opensearch/index/all")
async def opensearch_index_all():
    """
    Charge tous les events depuis Postgres et indexe dans OpenSearch (full-text).
    """
    try:
        rows = query_db("""
            SELECT
              event_id,
              type,
              classification,
              start_datetime,
              end_datetime,
              description
            FROM event
            ORDER BY event_id
        """, fetch_one=False)

        client = get_opensearch_client()
        ensure_index(client, INDEX_NAME)

        count = 0
        for r in rows:
            doc_id = r["event_id"]
            index_incident(client, INDEX_NAME, doc_id, {
                "event_id": r["event_id"],
                "type": r.get("type"),
                "classification": r.get("classification"),
                "start_datetime": r.get("start_datetime"),
                "end_datetime": r.get("end_datetime"),
                "description": r.get("description"),
            })
            count += 1

        return {"status": "indexed", "count": count}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/opensearch/count")
async def opensearch_count():
    """Retourne le nombre de documents indexés dans OpenSearch"""
    try:
        client = get_opensearch_client()
        ensure_index(client, INDEX_NAME)
        res = client.count(index=INDEX_NAME)
        return {"index": INDEX_NAME, "doc_count": res.get("count", 0)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/ai/query")
async def ai_query(request: Request):
    """
    Body JSON: { "message": "...", "ou": "optionnel" }  (ou "question")
    - "ou": force un filtre ILIKE sur OU.name (ex: "ateliers de production")
    Returns: { status, question, stats_count|context_count, answer }
    """
    try:
        data = await request.json()
        msg = (data or {}).get("message") or (data or {}).get("question")
        if not msg:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Provide 'message' (or 'question') in the JSON body"}
            )

        # --- 1) Chemin STATS: questions de distribution (pas de Bedrock)
        if is_distribution_question(msg):
            explicit_ou = (data or {}).get("ou")
            if explicit_ou:
                ou_patterns = [f"%{explicit_ou}%"]
            else:
                ou_patterns = extract_ou_patterns(msg)

            type_filter, classification_filters = extract_type_and_classifications(msg)

            if type_filter or classification_filters:
                total, rows = count_incidents_for_filters(
                    type_filter=type_filter,
                    classification_filters=classification_filters,
                    ou_name_patterns=ou_patterns
                )
                answer_text = format_filtered_count_answer(
                    type_filter,
                    classification_filters,
                    total,
                    rows
                )
                return JSONResponse({
                    "status": "success",
                    "question": msg,
                    "stats_count": total,
                    "answer": answer_text
                })

            stats = get_top_classifications(limit=10, ou_name_patterns=ou_patterns)
            answer_text = format_stats_answer(stats)

            return JSONResponse({"status": "success", "question": msg, "stats_count": len(stats), "answer": answer_text})

        # --- 2) Chemin RAG: fallback document-level via OpenSearch + Bedrock
        ctx = _fetch_context_from_os(msg, limit=10)
        system_prompt, user_prompt = _build_prompts(msg, ctx)

        response = chat_service.bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": 400, "topP": 1.0}
        )

        answer_raw = response["output"]["message"]["content"][0]["text"]
        enforced_answer = enforce_answer_policy(answer_raw, ctx)
        if enforced_answer is None:
            answer = build_default_answer(ctx)
        else:
            answer = enforced_answer

        return JSONResponse({"status": "success", "question": msg, "context_count": len(ctx), "answer": answer})

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Erreur lors du traitement: {str(e)}"})

@app.get("/stats/classification")
async def stats_classification():
    """Route de debug pour voir les stats brutes"""
    try:
        stats = get_top_classifications(limit=20, ou_name_patterns=None)
        return {"status": "success", "items": [{"classification": c, "count": n} for c, n in stats]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
