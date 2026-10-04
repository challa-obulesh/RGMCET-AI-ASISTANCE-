"""RAG 2.0 retrieval from local Vector Store."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.web_mvp.embeddings import get_embedding
from app.web_mvp.vector_store import VectorStore

_store = None

def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


async def retrieve_verified(
    query: str,
    intent: str,
    entity: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve verified official records matching query semantics via embeddings."""
    store = get_store()
    
    # Generate query embedding
    combined_query = f"{query} {entity or ''}".strip()
    query_emb = await get_embedding(combined_query)
    
    if not query_emb:
        return []
        
    lowered_query = combined_query.casefold()
    if "salary" in lowered_query:
        return []
        
    # Map intent to allowed kinds
    allowed_kinds = {
        "CAMPUS_INFORMATION": {"college", "contact", "facility", "department"},
        "DEPARTMENT_INFORMATION": {"department", "college"},
        "FACILITY_INFORMATION": {"facility", "college"},
        "FACULTY_INFORMATION": {"faculty", "department"},
        "PROFESSOR_INFORMATION": {"faculty"},
    }.get(intent)
    
    filters = {}
    if allowed_kinds:
        filters["allowed_kinds"] = allowed_kinds
        
    # Query vector store and candidates for hybrid re-ranking
    candidates = store.documents
    if allowed_kinds:
        candidates = [d for d in candidates if d.get("kind") in allowed_kinds]

    # Precalculate vector similarities if query_emb is available
    vec_scores: dict[str, float] = {}
    if query_emb:
        def cosine_sim(v1: list[float], v2: list[float]) -> float:
            dot = sum(a * b for a, b in zip(v1, v2))
            m1 = math.sqrt(sum(a * a for a in v1))
            m2 = math.sqrt(sum(b * b for b in v2))
            return (dot / (m1 * m2)) if (m1 > 0 and m2 > 0) else 0.0

        for doc in candidates:
            doc_emb = doc.get("embedding")
            doc_id = str(doc.get("id") or doc.get("source") or "")
            if doc_emb:
                vec_scores[doc_id] = max(0.0, cosine_sim(query_emb, doc_emb))

    # Re-ranking using hybrid metadata boosting to preserve exact match logic
    lowered_query = combined_query.casefold()
    ranked = []
    
    # Handle broad lists specially just like Phase 5 did
    is_broad_dept = intent == "DEPARTMENT_INFORMATION" and ("department" in lowered_query or "branch" in lowered_query or "విభాగాలు" in lowered_query or "శాఖలు" in lowered_query) and (not entity or entity == "RGMCET")
    is_broad_fac = intent == "FACILITY_INFORMATION" and ("facilit" in lowered_query or "సదుపాయాలు" in lowered_query) and not entity
    is_broad_prof = intent == "FACULTY_INFORMATION" and ("faculty" in lowered_query or "staff" in lowered_query) and "hod" not in lowered_query
    
    if is_broad_dept:
        for d in candidates:
            if d.get("kind") == "department":
                ranked.append((1.0, d))
    elif is_broad_fac:
        for d in candidates:
            if d.get("kind") == "facility":
                ranked.append((1.0, d))
    elif is_broad_prof:
        for d in candidates:
            if d.get("kind") == "faculty":
                ranked.append((1.0, d))
    else:
        for doc in candidates:
            doc_id = str(doc.get("id") or doc.get("source") or "")
            score = 1.0 + vec_scores.get(doc_id, 0.0) * 2.0
            record = doc.get("original_record", {})
            searchable = str(record).casefold()
            title_name = f"{record.get('title', '')} {record.get('name', '')} {record.get('department', '')}".casefold()
            
            # Boost exact entity matches
            if entity:
                ent_lower = entity.casefold()
                if ent_lower in title_name:
                    score += 25.0
                elif ent_lower in searchable:
                    score += 15.0

            # Boost specific department queries (e.g. CSE Data Science)
            if "cse" in lowered_query or "data science" in lowered_query:
                if "data science" in title_name or "cseds" in searchable:
                    score += 30.0
                
            # Boost HOD if asked
            if intent == "FACULTY_INFORMATION":
                if doc.get("kind") == "faculty":
                    score += 1.0
                if ("hod" in lowered_query or "head" in lowered_query) and record.get("is_hod"):
                    score += 30.0
                    
            # Boost library if asked
            if ("library" in lowered_query or "గ్రంథాలయం" in lowered_query or "granthalayam" in lowered_query) and "library" in searchable:
                score += 30.0

            # Boost laboratory if asked
            if ("laboratory" in lowered_query or "lab" in lowered_query) and ("laboratory" in searchable or "lab" in searchable):
                score += 25.0

            # Boost campus/college general info
            if intent == "CAMPUS_INFORMATION" or "about rgmcet" in lowered_query or "tell me about" in lowered_query:
                if doc.get("kind") == "college":
                    score += 20.0
                
            ranked.append((score, doc))
            
    ranked.sort(key=lambda x: x[0], reverse=True)
    
    # If no keywords matched and similarity is baseline 1.0 for specific intent, return empty
    if not (is_broad_dept or is_broad_fac or is_broad_prof) and ranked and ranked[0][0] <= 1.0:
        return []

    final_records = []
    # If it was a broad query, return all matches, else top 1 (as in Phase 6)
    limit = len(ranked) if (is_broad_dept or is_broad_fac or is_broad_prof) else 1
    
    for score, doc in ranked[:limit]:
        record = dict(doc.get("original_record", {}))
        # inject kind and metadata for LLM tracing
        record["kind"] = doc.get("kind")
        if doc.get("source_url") and not record.get("source", "").startswith("http"):
            record["source"] = doc.get("source_url")
        record["_rag_metadata"] = {
            "source": doc.get("source"),
            "source_url": doc.get("source_url"),
            "department": doc.get("department"),
            "last_checked": doc.get("last_checked")
        }
        final_records.append(record)
        
    return final_records