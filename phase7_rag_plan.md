# Phase 7: RAG 2.0 + Official Knowledge System Plan

## 1. Current Knowledge Architecture
* **Storage:** Raw JSON files in `data/rgmcet_knowledge/` (college_info.json, departments.json, facilities.json, faculty/cseds.json).
* **Retrieval:** Simple token overlap (keyword matching) in `app/web_mvp/knowledge.py`.
* **Filtering:** Hardcoded intent-to-kind mappings (e.g., `DEPARTMENT_INFORMATION` -> `{"department"}`).
* **Limitations:** 
  - Token overlap is brittle. It fails to match semantically identical but lexically different phrases (e.g., "AI degree" vs "Data Science").
  - Monolingual keyword matching struggles heavily with Telugu and Roman Telugu variants.
  - JSON structures must follow a strict schema, limiting free-form document ingestion.
  - Cannot scale to large official PDFs or web scrapes efficiently without an index.

## 2. Proposed RAG Architecture
* **Ingestion Pipeline:** Reads RGMCET sources (JSONs or raw text/markdown), extracts content, adds metadata, chunks it, embeds it, and saves to a local vector store.
* **Vector Store:** A lightweight file-based vector database suitable for the development environment. For example, `chromadb` (if installed) or a lightweight local cosine-similarity implementation on numpy to avoid massive infrastructure. Given constraints ("Prefer a lightweight development-friendly vector store. Do NOT introduce unnecessary infrastructure."), we can implement a simple JSON+NumPy/PyTorch vector store or use `faiss-cpu`/`chromadb` if available, or just a pure python cosine similarity store over small chunks.
* **Embedding Strategy:** Use a free/lightweight local model (like `sentence-transformers` / `all-MiniLM-L6-v2`) or Google Gemini embeddings API (`models/text-embedding-004`). Gemini Embeddings API is highly preferable here as we already have a Gemini API key.
* **Retrieval Strategy:** 
  1. Generate embedding for user query.
  2. Compute cosine similarity against all document chunks.
  3. Filter by metadata (department, kind, intent mappings if applicable).
  4. Return top-k chunks exceeding a relevance threshold.
* **Chunking Strategy:** 
  - Max chunk size: ~500-1000 characters.
  - Overlap: ~100 characters.
  - Granularity: Preserve semantic boundaries (e.g. keep HOD info with department).
* **Metadata Strategy:** Each chunk will carry:
  - `document_id`
  - `source`
  - `source_url`
  - `title`
  - `department` (if applicable)
  - `category`
  - `verified` (bool)
  - `last_checked`
* **Fallback & Hallucination Protection:** If maximum similarity score is below the threshold, return `[]` (empty). The LLM is instructed to explicitly state when evidence is insufficient, preventing hallucinations.

## 3. Testing Strategy
* **Unit Tests:** Vector store operations (add, search, filter), Chunking logic, Embedding wrapper.
* **RAG Tests:** Ensure the pipeline retrieves correct sources for varied phrasing, including Telugu and Roman Telugu.
* **Integration Tests:** Verify the AI agent seamlessly falls back to RAG for general knowledge queries and accurately reports sources in the response.
