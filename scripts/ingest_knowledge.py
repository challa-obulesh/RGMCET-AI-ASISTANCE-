"""Ingest knowledge JSON files, chunk, embed, and store in vector database."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.web_mvp.embeddings import get_embedding
from app.web_mvp.vector_store import VectorStore

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "rgmcet_knowledge"

def extract_text_for_embedding(record: dict) -> str:
    """Format a record as readable text for the embedding model."""
    parts = []
    if "title" in record:
        parts.append(record["title"])
    if "name" in record:
        parts.append(record["name"])
    if "designation" in record:
        parts.append(f"Designation: {record['designation']}")
    if "department" in record:
        parts.append(f"Department: {record['department']}")
    if "content" in record:
        parts.append(record["content"])
    if "facts" in record:
        for k, v in record["facts"].items():
            if isinstance(v, list) and all(isinstance(x, str) for x in v):
                parts.append(f"{k}: {', '.join(v)}")
            else:
                parts.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    if "aliases" in record:
        parts.append(f"Also known as: {', '.join(record['aliases'])}")
    
    return "\n".join(parts)

async def process_file(file_path: Path, kind: str):
    print(f"Processing {file_path.name}...")
    try:
        content = file_path.read_text(encoding="utf-8")
        records = json.loads(content)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return []

    documents = []
    for idx, record in enumerate(records):
        if not record.get("verified"):
            continue
            
        text_content = extract_text_for_embedding(record)
        if not text_content:
            continue
            
        # Create metadata
        doc = {
            "document_id": f"{file_path.stem}_{idx}",
            "source": file_path.name,
            "source_url": record.get("source", "Official RGMCET Data"),
            "title": record.get("title") or record.get("name") or "RGMCET Information",
            "department": record.get("department"),
            "kind": kind,
            "category": "academic",
            "verified": record.get("verified", False),
            "last_checked": datetime.now().isoformat(),
            "content": text_content,  # Used by LLM for context
            "original_record": record # Store original in case we need it
        }
        
        # Get embedding
        print(f"  Embedding: {doc['title']}...")
        embedding = await get_embedding(text_content)
        if embedding:
            doc["embedding"] = embedding
            documents.append(doc)
        else:
            print(f"  Failed to get embedding for: {doc['title']}")
            
    return documents

async def main():
    print("Starting Knowledge Ingestion Pipeline...")
    store = VectorStore()
    all_documents = []
    
    file_mappings = [
        ("college_info.json", "college"),
        ("departments.json", "department"),
        ("facilities.json", "facility"),
        ("timings.json", "contact")
    ]
    
    for filename, kind in file_mappings:
        path = DATA_DIR / filename
        if path.exists():
            docs = await process_file(path, kind)
            all_documents.extend(docs)
            
    faculty_dir = DATA_DIR / "faculty"
    if faculty_dir.exists():
        for path in sorted(faculty_dir.glob("*.json")):
            docs = await process_file(path, "faculty")
            all_documents.extend(docs)
            
    if all_documents:
        store.add_documents(all_documents)
        print(f"Successfully ingested {len(all_documents)} documents into Vector Store.")
    else:
        print("No documents were processed or embedded.")

if __name__ == "__main__":
    asyncio.run(main())
