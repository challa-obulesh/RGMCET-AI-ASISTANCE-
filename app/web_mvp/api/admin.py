"""Admin API for dashboard, knowledge management, and analytics."""
from __future__ import annotations

import logging
import uuid
from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.web_mvp import store, knowledge
from app.web_mvp.auth import require_admin
from app.web_mvp.vector_store import VectorStore
from app.web_mvp.embeddings import get_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

def _audit_log(admin_payload: dict, action: str, target_type: str, target_id: str, result: str):
    import asyncio
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "admin_id": admin_payload.get("sub"),
        "admin_email": admin_payload.get("email"),
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "result": result
    }
    asyncio.create_task(store.insert_one("audit_logs", log_entry))

@router.get("/overview")
async def overview() -> dict[str, Any]:
    users = await store.find_many("users")
    appointments = await store.find_many("appointments")
    chats = await store.find_many("chat_sessions")
    
    total_users = len(users)
    students = len([u for u in users if u.get("role") == "student"])
    professors = len([u for u in users if u.get("role") == "professor"])
    admins = len([u for u in users if u.get("role") == "admin"])
    
    vstore = knowledge.get_store()
    records = vstore.documents
    total_knowledge = len(records)
    verified = len([r for r in records if r.get("original_record", {}).get("verified")])
    
    pending = len([a for a in appointments if a.get("status") == "PENDING_APPROVAL"])
    completed = len([a for a in appointments if a.get("status") == "COMPLETED"])
    
    return {
        "users": {
            "total": total_users,
            "students": students,
            "professors": professors,
            "admins": admins
        },
        "knowledge": {
            "total": total_knowledge,
            "verified": verified,
            "unverified": total_knowledge - verified
        },
        "appointments": {
            "total": len(appointments),
            "pending": pending,
            "completed": completed
        },
        "chat": {
            "total": len(chats)
        },
        "system": {
            "database": "Healthy" if store.store_ready() else "Unavailable",
            "llm": "Available",
            "rag": "Ready"
        }
    }

@router.get("/knowledge")
async def get_knowledge() -> list[dict[str, Any]]:
    vstore = knowledge.get_store()
    return vstore.documents

@router.post("/knowledge")
async def create_knowledge(data: dict, payload: dict = Depends(require_admin)):
    vstore = knowledge.get_store()
    doc_id = str(uuid.uuid4())
    data["id"] = doc_id
    data["index_status"] = "INDEX_PENDING"
    vstore.documents.append(data)
    vstore._save()
    _audit_log(payload, "CREATE_KNOWLEDGE", "knowledge", doc_id, "SUCCESS")
    return data

@router.patch("/knowledge/{doc_id}")
async def update_knowledge(doc_id: str, data: dict, payload: dict = Depends(require_admin)):
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if str(doc.get("id")) == doc_id or doc.get("source") == doc_id:
            if "content" in data: doc["content"] = data["content"]
            if "original_record" in data: doc["original_record"] = data["original_record"]
            if "kind" in data: doc["kind"] = data["kind"]
            if "source" in data: doc["source"] = data["source"]
            doc["index_status"] = "INDEX_PENDING"
            vstore._save()
            _audit_log(payload, "EDIT_KNOWLEDGE", "knowledge", doc_id, "SUCCESS")
            return doc
    raise HTTPException(404, "Not found")

@router.delete("/knowledge/{doc_id}")
async def delete_knowledge(doc_id: str, payload: dict = Depends(require_admin)):
    vstore = knowledge.get_store()
    initial_len = len(vstore.documents)
    vstore.documents = [d for d in vstore.documents if str(d.get("id")) != doc_id and d.get("source") != doc_id]
    if len(vstore.documents) < initial_len:
        vstore._save()
        _audit_log(payload, "DELETE_KNOWLEDGE", "knowledge", doc_id, "SUCCESS")
        return {"success": True}
    raise HTTPException(404, "Not found")

@router.post("/knowledge/{doc_id}/verify")
async def verify_knowledge(doc_id: str, payload: dict = Depends(require_admin)):
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if str(doc.get("id")) == doc_id or doc.get("source") == doc_id:
            doc.setdefault("original_record", {})["verified"] = True
            vstore._save()
            _audit_log(payload, "VERIFY_KNOWLEDGE", "knowledge", doc_id, "SUCCESS")
            return doc
    raise HTTPException(404, "Not found")

@router.post("/knowledge/{doc_id}/unverify")
async def unverify_knowledge(doc_id: str, payload: dict = Depends(require_admin)):
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if str(doc.get("id")) == doc_id or doc.get("source") == doc_id:
            doc.setdefault("original_record", {})["verified"] = False
            vstore._save()
            _audit_log(payload, "UNVERIFY_KNOWLEDGE", "knowledge", doc_id, "SUCCESS")
            return doc
    raise HTTPException(404, "Not found")

@router.post("/knowledge/reindex")
async def reindex_knowledge(payload: dict = Depends(require_admin)):
    vstore = knowledge.get_store()
    processed = 0
    indexed = 0
    errors = []
    for doc in vstore.documents:
        processed += 1
        if doc.get("index_status") == "INDEX_PENDING" or not doc.get("embedding"):
            try:
                emb = await get_embedding(doc["content"])
                if emb:
                    doc["embedding"] = emb
                    doc["index_status"] = "INDEXED"
                    indexed += 1
                else:
                    doc["index_status"] = "INDEX_FAILED"
                    errors.append(f"Failed embedding for {doc.get('source')}")
            except Exception as e:
                doc["index_status"] = "INDEX_FAILED"
                errors.append(str(e))
    vstore._save()
    _audit_log(payload, "REINDEX", "system", "rag", f"Processed {processed}, Indexed {indexed}")
    return {
        "success": len(errors) == 0,
        "records_processed": processed,
        "records_indexed": indexed,
        "errors": errors
    }

class PreviewQuery(BaseModel):
    query: str

@router.post("/knowledge/preview")
async def preview_knowledge(req: PreviewQuery, payload: dict = Depends(require_admin)):
    from app.web_mvp.agent import run_agent
    res = await run_agent(req.query, "admin-preview", "admin@rgmcet.edu.in", [])
    return {"result": res}

@router.get("/audit-logs")
async def get_audit_logs():
    logs = await store.find_many("audit_logs")
    return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)

@router.get("/users")
async def get_users():
    users = await store.find_many("users")
    # Redact passwords
    for u in users:
        u.pop("password_hash", None)
    return users

@router.get("/analytics/appointments")
async def get_appointment_analytics():
    appointments = await store.find_many("appointments")
    return appointments

@router.get("/analytics/chat")
async def get_chat_analytics():
    chats = await store.find_many("chat_sessions")
    return chats

@router.get("/faculty")
async def get_faculty():
    return await store.find_many("professors")

@router.get("/departments")
async def get_departments():
    vstore = knowledge.get_store()
    return [d for d in vstore.documents if d.get("kind") == "department"]

@router.get("/facilities")
async def get_facilities():
    vstore = knowledge.get_store()
    return [d for d in vstore.documents if d.get("kind") == "facility"]

