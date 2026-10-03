"""RAG 2.0 retrieval from local Vector Store."""

from __future__ import annotations

import json
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
        
    # Query vector store (fetch more for re-ranking)
    results = store.search(query_emb, top_k=50, threshold=0.01, filters=filters)
    
    # Re-ranking using hybrid metadata boosting to preserve exact match logic
    lowered_query = combined_query.casefold()
    ranked = []
    
    # Handle broad lists specially just like Phase 5 did
    is_broad_dept = intent == "DEPARTMENT_INFORMATION" and ("department" in lowered_query or "branch" in lowered_query or "విభాగాలు" in lowered_query or "శాఖలు" in lowered_query) and not entity
    is_broad_fac = intent == "FACILITY_INFORMATION" and ("facilit" in lowered_query or "సదుపాయాలు" in lowered_query) and not entity
    is_broad_prof = intent == "FACULTY_INFORMATION" and ("faculty" in lowered_query or "staff" in lowered_query) and "hod" not in lowered_query
    
    if is_broad_dept or is_broad_fac or is_broad_prof:
        # Just return everything allowed to emulate list fetch
        results = store.documents
        if filters:
            results = [d for d in results if d.get("kind") in allowed_kinds]
        for d in results:
            ranked.append((1.0, d))
    else:
        for doc in results:
            score = 1.0
            record = doc.get("original_record", {})
            searchable = str(record).casefold()
            
            # Boost exact entity matches
            if entity and entity.casefold() in searchable:
                score += 5.0
                
            # Boost HOD if asked
            if intent == "FACULTY_INFORMATION":
                if doc.get("kind") == "faculty":
                    score += 1.0
                if ("hod" in lowered_query or "head" in lowered_query) and record.get("is_hod"):
                    score += 10.0
                    
            # Boost library if asked
            if "library" in lowered_query and "library" in searchable:
                score += 5.0
                
            ranked.append((score, doc))
            
    ranked.sort(key=lambda x: x[0], reverse=True)
    
    # DEBUG PRINT
    for s, d in ranked[:5]:
        r = d.get('original_record', {})
        print(f"DEBUG RANKED: {r.get('name') or r.get('title')} - Score: {s}")
    
    final_records = []
    # If it was a broad query, return all matches, else top 1 (as in Phase 6)
    limit = len(ranked) if (is_broad_dept or is_broad_fac or is_broad_prof) else 1
    
    for score, doc in ranked[:limit]:
        record = doc.get("original_record", {})
        # inject kind and metadata for LLM tracing
        record["kind"] = doc.get("kind")
        record["_rag_metadata"] = {
            "source": doc.get("source"),
            "source_url": doc.get("source_url"),
            "department": doc.get("department"),
            "last_checked": doc.get("last_checked")
        }
        final_records.append(record)
        
    return final_records