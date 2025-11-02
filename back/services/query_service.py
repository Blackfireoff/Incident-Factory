import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from database import query_db
from search_engine import (
    ensure_index,
    get_opensearch_client,
    search_incidents_with_filters,
    search_recent_incidents,
)


CHEM_PATTERNS = [
    r"\bacetone\b",
    r"\bac[ée]tone\b",
    r"\bhydraulic oil\b",
    r"\bhuile hydraulique\b",
    r"\bsolvent\b",
    r"\bsolvant(s)?\b",
    r"\bproduits?\s+chimiques?\b",
    r"\bchemical(s)?\b",
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
    "les",
    "des",
    "dans",
    "avec",
    "pour",
    "par",
    "sur",
    "quoi",
    "quel",
    "quels",
    "quelle",
    "quelles",
    "une",
    "lors",
    "d'",
    "des",
    "est",
    "sont",
    "un",
    "une",
    "de",
    "et",
    "ou",
    "the",
    "what",
    "were",
    "was",
    "when",
    "how",
    "why",
    "a",
    "an",
    "aux",
    "quel",
    "quelle",
    "quelles",
    "quels",
    "quoi",
    "qui",
    "où",
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
ISO_DATE_PATTERN = re.compile(
    r"\b(20\d{2}|19\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"
)
SLASH_DATE_PATTERN = re.compile(
    r"\b(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(20\d{2}|19\d{2})\b"
)
MONTH_NAME_PATTERN = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(20\d{2}|19\d{2})\b",
    flags=re.I,
)
MONTH_NAME_MAP = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}
RECENT_HINTS = {
    "recent",
    "récent",
    "recente",
    "récente",
    "recemment",
    "récemment",
    "recentes",
    "récents",
}

NO_CONTEXT_REPLY = "Je ne sais pas sur la base du contexte fourni."


def process_ai_query_request(
    data: Dict,
    chat_service,
    model_id: str,
    index_name: str,
) -> Tuple[int, Dict]:
    msg = (data or {}).get("message") or (data or {}).get("question")
    if not msg:
        return 400, {
            "status": "error",
            "message": "Provide 'message' (or 'question') in the JSON body",
        }

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
                ou_name_patterns=ou_patterns,
            )
            answer_text = format_filtered_count_answer(
                type_filter,
                classification_filters,
                total,
                rows,
            )
            return 200, {
                "status": "success",
                "question": msg,
                "stats_count": total,
                "answer": answer_text,
                "source": "analytics",
            }

        stats = get_top_classifications(limit=10, ou_name_patterns=ou_patterns)
        answer_text = format_stats_answer(stats)
        return 200, {
            "status": "success",
            "question": msg,
            "stats_count": len(stats),
            "answer": answer_text,
            "source": "analytics",
        }

    ctx = _fetch_context_from_os(msg, limit=10, index_name=index_name)
    system_prompt, user_prompt = _build_prompts(msg, ctx)

    response = chat_service.bedrock.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"temperature": 0.0, "maxTokens": 400, "topP": 1.0},
    )

    answer_raw = response["output"]["message"]["content"][0]["text"]
    enforced_answer = enforce_answer_policy(answer_raw, ctx)
    if enforced_answer is None:
        answer = build_default_answer(ctx)
    else:
        answer = enforced_answer

    return 200, {
        "status": "success",
        "question": msg,
        "context_count": len(ctx),
        "answer": answer,
        "source": "rag",
    }


def extract_must_phrases(question: str) -> List[str]:
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


def _select_action_sentences(description: str, max_sentences: int = 2) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", description.strip())
    selected: List[str] = []
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


def extract_iso_dates(question: str) -> List[str]:
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


def extract_event_ids(question: str) -> List[int]:
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


def extract_type_and_classifications(question: str) -> Tuple[Optional[str], List[str]]:
    tokens = [
        token.upper() for token in re.findall(r"[A-Z]{2,}(?:_[A-Z]+)?", question)
    ]
    if not tokens:
        return None, []

    if len(tokens) == 1:
        return None, tokens

    type_candidate = tokens[0]
    classifications = tokens[1:] or []
    return type_candidate, classifications


def build_date_filters(iso_dates: List[str]) -> List[dict]:
    if not iso_dates:
        return []

    date_clauses = []
    for iso in iso_dates:
        start = f"{iso}T00:00:00"
        end = f"{iso}T23:59:59"
        date_clauses.append(
            {
                "bool": {
                    "should": [
                        {"range": {"start_datetime": {"gte": start, "lte": end}}},
                        {"range": {"end_datetime": {"gte": start, "lte": end}}},
                        {
                            "bool": {
                                "must": [
                                    {
                                        "range": {
                                            "start_datetime": {
                                                "lte": end
                                            }
                                        }
                                    },
                                    {
                                        "range": {
                                            "end_datetime": {
                                                "gte": start
                                            }
                                        }
                                    },
                                ]
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    if not date_clauses:
        return []

    return [
        {
            "bool": {
                "should": date_clauses,
                "minimum_should_match": 1,
            }
        }
    ]


def count_incidents_for_filters(
    type_filter: Optional[str],
    classification_filters: List[str],
    ou_name_patterns: Optional[List[str]] = None,
) -> Tuple[int, List[Tuple[str, str, int]]]:
    joins = []
    where_clauses = []
    params: List[str] = []

    if ou_name_patterns:
        joins.append(
            "INNER JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id"
        )
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
    typed_rows: List[Tuple[str, str, int]] = []
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
    rows: List[Tuple[str, str, int]],
) -> str:
    if not rows:
        target = (
            ", ".join(classification_filters)
            if classification_filters
            else "toutes classes"
        )
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


def enforce_answer_policy(answer: str, ctx: List[Dict]) -> Optional[str]:
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


def build_default_answer(ctx: List[Dict], max_points: int = 6) -> str:
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
        for c in usable[len(lines) : min(len(usable), max_points)]:
            event_id = c.get("event_id")
            citations.append(f"event_id:{event_id}")
            frag_list = c.get("fragments", [])
            frag = frag_list[0] if frag_list else ""
            start = c.get("start_datetime") or "?"
            typ = c.get("type") or "Incident"
            lines.append(f"- {typ} ({start}) : \"{frag}\" [event_id:{event_id}]")

    citations_text = f"Citations: [{', '.join(dict.fromkeys(citations))}]"
    return "\n".join(lines + [citations_text])


def is_distribution_question(text: str) -> bool:
    patterns = [
        r"(principaux|top|plus\s+(fr[ée]quents?|courants?)|r[ée]partition|classement|types?\s+d[' ]incident)",
        r"(combien|nombre)\s+d[' ]?incidents?",
    ]
    return any(re.search(pat, text, re.I) for pat in patterns)


def extract_ou_patterns(text: str) -> Optional[List[str]]:
    patterns = []
    if re.search(r"(atelier|ateliers?)", text, re.I):
        patterns += ["%atelier%"]
    if re.search(r"(production|prod\b)", text, re.I):
        patterns += ["%production%", "%prod%"]
    if re.search(r"(usine|manufactur|ligne)", text, re.I):
        patterns += ["%usine%", "%manufactur%", "%ligne%"]
    return patterns or None


def get_top_classifications(
    limit: int = 10,
    ou_name_patterns: Optional[List[str]] = None,
) -> List[Tuple[str, int]]:
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
    total = sum(counts) or 1
    raw = [c * 100.0 / total for c in counts]
    floors = [int(x) for x in raw]
    remainder = 100 - sum(floors)
    order = sorted(
        range(len(raw)), key=lambda i: (raw[i] - floors[i]), reverse=True
    )
    for i in range(remainder):
        floors[order[i]] += 1
    return floors


def format_stats_answer(stats: List[Tuple[str, int]]) -> str:
    if not stats:
        return "Je ne sais pas sur la base du contexte fourni."

    labels = [c for c, _ in stats]
    counts = [n for _, n in stats]
    perc = _percentages_that_sum_to_100(counts)

    lines = [
        f"{i+1}. {labels[i]} ({counts[i]}) - {perc[i]}%" for i in range(len(stats))
    ]
    return "Les principaux types d'incidents sont :\n\n" + "\n".join(lines)


def _fetch_context_from_os(
    query: str,
    limit: int,
    index_name: str,
) -> List[Dict]:
    client = get_opensearch_client()
    ensure_index(client, index_name)
    must_phrases = extract_must_phrases(query)
    question_keywords = extract_question_keywords(query)
    normalized_terms = {
        _normalize_text(term) for term in (list(question_keywords) + must_phrases)
    }
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
            {"event_id": {"order": "asc"}},
        ]
    elif recent_hint and not strict_filters:
        sort = [
            {"start_datetime": {"order": "desc", "missing": "_last"}},
            {"event_id": {"order": "desc"}},
        ]

    search_size = max(
        limit,
        len(event_ids) or 0,
        len(iso_dates) * 2 or 0,
        5 if strict_filters else limit,
    )
    min_score = 1.0 if (must_phrases and not strict_filters) else None

    res = search_incidents_with_filters(
        client=client,
        index_name=index_name,
        query=query,
        must_phrases=must_phrases,
        filters=filters if filters else None,
        sort=sort,
        size=search_size,
        min_score=min_score,
    ) or {}

    def build_context_from_hits(
        hits: List[dict], require_match: bool, max_items: int
    ) -> List[Dict]:
        context_items: List[Dict] = []
        for h in hits:
            src = h.get("_source", {})
            hl = h.get("highlight", {}).get("description", []) or []
            raw_desc = (src.get("description") or "").strip()
            fragments: List[str] = []
            seen = set()

            def add_fragment(text: str, require_match_inner: bool = True):
                trimmed = text.strip()
                if not trimmed:
                    return
                norm = _normalize_text(trimmed)
                if (
                    require_match_inner
                    and require_match
                    and normalized_terms
                    and not any(term in norm for term in normalized_terms)
                ):
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

            context_items.append(
                {
                    "event_id": src.get("event_id"),
                    "type": src.get("type"),
                    "classification": src.get("classification"),
                    "start_datetime": src.get("start_datetime"),
                    "end_datetime": src.get("end_datetime"),
                    "fragments": fragments,
                }
            )

            if len(context_items) >= max_items:
                break

        return context_items

    hits = res.get("hits", {}).get("hits", [])
    ctx = build_context_from_hits(hits, require_match=True, max_items=limit)
    if not ctx:
        ctx = build_context_from_hits(hits, require_match=False, max_items=limit)

    if not ctx and not strict_filters:
        recent_size = max(limit, 10)
        recent_res = search_recent_incidents(client, index_name, size=recent_size) or {}
        recent_hits = recent_res.get("hits", {}).get("hits", [])
        ctx = build_context_from_hits(
            recent_hits, require_match=len(normalized_terms) > 0, max_items=limit
        )

        if not ctx:
            ctx = build_context_from_hits(
                recent_hits, require_match=False, max_items=limit
            )

    return ctx


def _build_prompts(user_message: str, ctx: List[Dict]) -> Tuple[str, str]:
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
