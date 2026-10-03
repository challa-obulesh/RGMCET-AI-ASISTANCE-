# Phase 7 RAG Audit

## Embedding Method
**Currently Used:** A naive lightweight Bag-of-Words (BoW) hashing mechanism (`_hash_bow_embedding` in `embeddings.py`).
**Real Semantic Embedding?** No. It simply splits text into words, hashes them, and populates a 128-dimensional sparse vector. It lacks true semantic understanding (e.g., it cannot equate "staff" with "faculty" unless hardcoded rules exist).

## Vector Store
**Currently Used:** A custom local JSON-based vector store (`app/web_mvp/vector_store.py`).
It stores embeddings in memory and persists them to `data/rgmcet_knowledge/vector_store.json`.

## Chunking Strategy
Documents are extracted at the logical unit level (e.g., an individual faculty member, a specific department overview) rather than arbitrary character splits. This is handled by `scripts/ingest_knowledge.py` which creates discrete JSON records per entity.

## Similarity Calculation
It uses basic Cosine Similarity (`sum(A_i * B_i)`) on the generated vectors.

## Metadata Filtering
The vector store supports filtering via an `allowed_kinds` set. In `knowledge.py`, intent mapping (e.g., `FACULTY_INFORMATION`) is used to restrict the search to specific document kinds (e.g., `{"faculty", "department"}`).

## Source Preservation
The original `source` (URL/page name) and `last_checked` date are preserved during ingestion and stored within the `original_record` field of the vector store. They are injected as `_rag_metadata` during retrieval.

## Hallucination Prevention
1. The LLM is instructed to only answer using provided evidence.
2. A strict threshold is used in the vector store (e.g. 0.15).
3. Hardcoded filters exist for non-applicable concepts (e.g., instantly returning no results for "salary").

## Fallback Mechanism
If the LLM provider fails, `_local_verified_answer` generates a direct string from the retrieved metadata (e.g., listing department names).

## Interaction with AI Agent
The `retrieve_verified()` function acts as the bridge. When an intent like `FACULTY_INFORMATION` is detected, it queries the vector store, formats the top-k results into a string block, and prefixes the LLM prompt with "VERIFIED RGMCET KNOWLEDGE".

## Verdict & Action Plan
The RAG architecture is functionally correct, but the **Embedding Layer** needs a complete overhaul. Hashing-based vectors are inadequate for an industry-level semantic RAG system. We will replace this with a hosted embedding provider (Gemini API) managed by an `EmbeddingProvider` abstraction that degrades gracefully.
