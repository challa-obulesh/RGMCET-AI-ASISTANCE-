"""Lightweight JSON-based vector store for development environment."""

from __future__ import annotations

import json
import math
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VECTOR_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "rgmcet_knowledge" / "vector_store.json"

class VectorStore:
    def __init__(self, path: Path = VECTOR_STORE_PATH):
        self.path = path
        self.documents: list[dict[str, Any]] = []
        self._load()
        
    def _load(self):
        if self.path.exists():
            try:
                self.documents = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load vector store: {e}")
                self.documents = []
        else:
            self.documents = []
            
    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.documents, ensure_ascii=False, indent=2), encoding="utf-8")
        
    def add_documents(self, documents: list[dict[str, Any]]):
        """Add chunks to store with embeddings."""
        # Replace documents with same source to avoid duplication during update
        sources_to_update = {doc.get("source") for doc in documents if doc.get("source")}
        if sources_to_update:
            self.documents = [d for d in self.documents if d.get("source") not in sources_to_update]
            
        self.documents.extend(documents)
        self._save()
        
    def search(self, query_embedding: list[float], top_k: int = 5, threshold: float = 0.5, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Compute cosine similarity and return top matches."""
        if not query_embedding or not self.documents:
            return []
            
        def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(b * b for b in vec2))
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            return dot_product / (magnitude1 * magnitude2)
            
        results = []
        for doc in self.documents:
            # Check filters
            if filters:
                match = True
                for k, v in filters.items():
                    if k == "allowed_kinds" and doc.get("kind") not in v:
                        match = False
                        break
                    elif k != "allowed_kinds" and doc.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
                    
            doc_embedding = doc.get("embedding")
            if not doc_embedding:
                continue
                
            score = cosine_similarity(query_embedding, doc_embedding)
            if score >= threshold:
                # Remove embedding from returned doc to save memory
                ret_doc = {k: v for k, v in doc.items() if k != "embedding"}
                results.append((score, ret_doc))
                
        results.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in results[:top_k]]
