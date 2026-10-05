"""Admin API — Phase 10 complete implementation.

Endpoints:
  /api/admin/overview
  /api/admin/health
  /api/admin/knowledge       (list, create, search, filters)
  /api/admin/knowledge/{id}  (get single)
  /api/admin/knowledge/{id}  PATCH (edit)
  /api/admin/knowledge/{id}/verify
  /api/admin/knowledge/{id}/unverify
  /api/admin/knowledge/{id}/archive
  /api/admin/knowledge/{id}/restore
  /api/admin/rag/status
  /api/admin/rag/reindex
  /api/admin/rag/query-preview
  /api/admin/faculty
  /api/admin/departments
  /api/admin/facilities
  /api/admin/users
  /api/admin/appointments/analytics
  /api/admin/ai/analytics
  /api/admin/audit-logs
"""
from __future__ import annotations

import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.web_mvp import store, knowledge
from app.web_mvp.auth import require_admin
from app.web_mvp.embeddings import get_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _audit(payload: dict, action: str, target_type: str, target_id: str, result: str = "SUCCESS") -> None:
    entry = {
        "timestamp": _now(),
        "admin_id": payload.get("sub", ""),
        "admin_email": payload.get("email", ""),
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "result": result,
    }
    try:
        import asyncio
        asyncio.create_task(store.insert_one("audit_logs", entry))
    except RuntimeError:
        # No running loop (e.g. tests) — write synchronously via _memory
        store._memory.setdefault("audit_logs", []).append(entry)


def _doc_id(doc: dict) -> str:
    return str(doc.get("id") or doc.get("source") or "")


def _rec(doc: dict) -> dict:
    return doc.get("original_record") or {}


def _knowledge_list(vstore, q: str | None = None, filter_status: str | None = None) -> list[dict]:
    docs = list(vstore.documents)

    # Text search
    if q:
        q_lower = q.lower()
        docs = [d for d in docs if (
            q_lower in str(_rec(d).get("name", "")).lower()
            or q_lower in str(_rec(d).get("title", "")).lower()
            or q_lower in d.get("content", "").lower()
            or q_lower in d.get("kind", "").lower()
            or q_lower in str(_rec(d).get("department", "")).lower()
        )]

    # Status filters
    if filter_status == "verified":
        docs = [d for d in docs if _rec(d).get("verified")]
    elif filter_status == "unverified":
        docs = [d for d in docs if not _rec(d).get("verified")]
    elif filter_status == "indexed":
        docs = [d for d in docs if d.get("index_status") == "INDEXED"]
    elif filter_status == "pending":
        docs = [d for d in docs if d.get("index_status") == "INDEX_PENDING"]
    elif filter_status == "failed":
        docs = [d for d in docs if d.get("index_status") == "INDEX_FAILED"]
    elif filter_status == "archived":
        docs = [d for d in docs if d.get("archived")]

    if filter_status != "archived":
        docs = [d for d in docs if not d.get("archived")]

    # Return without embedding to save payload size; ensure every doc has an 'id'
    result = []
    for d in docs:
        out = {k: v for k, v in d.items() if k != "embedding"}
        if "id" not in out:
            out["id"] = out.get("source", "")
        result.append(out)
    return result


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@router.get("/overview")
async def overview() -> dict[str, Any]:
    users = await store.find_many("users")
    appointments = await store.find_many("appointments")
    chats = await store.find_many("chat_sessions")

    vstore = knowledge.get_store()
    records = vstore.documents
    non_archived = [r for r in records if not r.get("archived")]
    verified = len([r for r in non_archived if _rec(r).get("verified")])
    indexed = len([r for r in non_archived if r.get("index_status") == "INDEXED"])
    pending_idx = len([r for r in non_archived if r.get("index_status") in ("INDEX_PENDING", None)])

    appt_by_status: Counter = Counter(a.get("status", "UNKNOWN") for a in appointments)

    # AI analytics — count turns
    total_turns = sum(len(s.get("turns", [])) for s in chats)
    intent_counts: Counter = Counter()
    lang_counts: Counter = Counter()
    for s in chats:
        for t in s.get("turns", []):
            intent_counts[t.get("intent", "UNKNOWN")] += 1
            lang_counts[t.get("language", "Unknown")] += 1

    return {
        "users": {
            "total": len(users),
            "students": len([u for u in users if u.get("role") == "student"]),
            "professors": len([u for u in users if u.get("role") == "professor"]),
            "admins": len([u for u in users if u.get("role") == "admin"]),
        },
        "knowledge": {
            "total": len(non_archived),
            "verified": verified,
            "unverified": len(non_archived) - verified,
            "indexed": indexed,
            "pending": pending_idx,
            "archived": len([r for r in records if r.get("archived")]),
        },
        "appointments": {
            "total": len(appointments),
            "pending": appt_by_status.get("PENDING_APPROVAL", 0),
            "approved": appt_by_status.get("APPROVED", 0),
            "rejected": appt_by_status.get("REJECTED", 0),
            "cancelled": appt_by_status.get("CANCELLED", 0),
            "completed": appt_by_status.get("COMPLETED", 0),
        },
        "ai": {
            "total_queries": total_turns,
            "by_intent": dict(intent_counts.most_common(10)),
            "by_language": dict(lang_counts.most_common()),
        },
    }


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def admin_health() -> dict[str, Any]:
    from app.web_mvp.llm import configured_provider
    from app.web_mvp.store import demo_mode_active, store_ready
    from app.web_mvp.vector_store import VECTOR_STORE_PATH

    vstore = knowledge.get_store()
    rag_docs = len(vstore.documents)
    rag_indexed = len([d for d in vstore.documents if d.get("index_status") == "INDEXED"])

    return {
        "backend": {"status": "OK", "version": "0.3.0"},
        "database": {
            "status": "demo" if demo_mode_active() else ("connected" if store_ready() else "unavailable"),
            "demo_mode": demo_mode_active(),
        },
        "llm": {
            "provider": configured_provider() or "none",
            "status": "configured" if configured_provider() else "not_configured",
        },
        "rag": {
            "status": "OK",
            "total_documents": rag_docs,
            "indexed": rag_indexed,
            "store_path": str(VECTOR_STORE_PATH),
        },
        "google_calendar": {
            "status": "not_configured",
            "note": "Optional integration — configure GOOGLE_CALENDAR credentials to enable",
        },
        "environment": {
            "demo_mode": demo_mode_active(),
        },
    }


# ---------------------------------------------------------------------------
# Knowledge CRUD
# ---------------------------------------------------------------------------

@router.get("/knowledge")
async def get_knowledge(
    q: str | None = Query(default=None),
    filter: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    vstore = knowledge.get_store()
    return _knowledge_list(vstore, q=q, filter_status=filter)


@router.get("/knowledge/{doc_id}")
async def get_knowledge_item(doc_id: str) -> dict[str, Any]:
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if _doc_id(doc) == doc_id:
            return {k: v for k, v in doc.items() if k != "embedding"}
    raise HTTPException(404, "Not found")


@router.post("/knowledge")
async def create_knowledge(data: dict, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    vstore = knowledge.get_store()
    new_id = str(uuid.uuid4())
    now = _now()
    doc = {
        "id": new_id,
        "content": data.get("content", ""),
        "kind": data.get("kind", "general"),
        "source": data.get("source", f"admin-created-{new_id}"),
        "source_url": data.get("source_url", ""),
        "department": data.get("department", ""),
        "language": data.get("language", "English"),
        "tags": data.get("tags", []),
        "index_status": "INDEX_PENDING",
        "archived": False,
        "created_at": now,
        "updated_at": now,
        "original_record": {
            "title": data.get("title", ""),
            "name": data.get("title", ""),
            "content": data.get("content", ""),
            "category": data.get("kind", "general"),
            "department": data.get("department", ""),
            "source": data.get("source", ""),
            "source_url": data.get("source_url", ""),
            "language": data.get("language", "English"),
            "tags": data.get("tags", []),
            "verified": data.get("verified", False),
            "created_at": now,
        },
    }
    vstore.documents.append(doc)
    vstore._save()
    await _audit(payload, "CREATE_KNOWLEDGE", "knowledge", new_id)
    return {k: v for k, v in doc.items() if k != "embedding"}


@router.patch("/knowledge/{doc_id}")
async def update_knowledge(doc_id: str, data: dict, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if _doc_id(doc) == doc_id:
            allowed = {"content", "kind", "source", "source_url", "department", "language", "tags"}
            for field in allowed:
                if field in data:
                    doc[field] = data[field]
            # Update original_record fields
            rec = doc.setdefault("original_record", {})
            for field in ("title", "name", "category", "department", "source", "source_url", "language", "tags", "verified"):
                if field in data:
                    rec[field] = data[field]
            if "content" in data:
                rec["content"] = data["content"]
            doc["index_status"] = "INDEX_PENDING"
            doc["updated_at"] = _now()
            vstore._save()
            await _audit(payload, "EDIT_KNOWLEDGE", "knowledge", doc_id)
            return {k: v for k, v in doc.items() if k != "embedding"}
    raise HTTPException(404, "Not found")


@router.post("/knowledge/{doc_id}/verify")
async def verify_knowledge(doc_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if _doc_id(doc) == doc_id:
            doc.setdefault("original_record", {})["verified"] = True
            doc["updated_at"] = _now()
            vstore._save()
            await _audit(payload, "VERIFY_KNOWLEDGE", "knowledge", doc_id)
            return {k: v for k, v in doc.items() if k != "embedding"}
    raise HTTPException(404, "Not found")


@router.post("/knowledge/{doc_id}/unverify")
async def unverify_knowledge(doc_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if _doc_id(doc) == doc_id:
            doc.setdefault("original_record", {})["verified"] = False
            doc["updated_at"] = _now()
            vstore._save()
            await _audit(payload, "UNVERIFY_KNOWLEDGE", "knowledge", doc_id)
            return {k: v for k, v in doc.items() if k != "embedding"}
    raise HTTPException(404, "Not found")


@router.post("/knowledge/{doc_id}/archive")
async def archive_knowledge(doc_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if _doc_id(doc) == doc_id:
            doc["archived"] = True
            doc["updated_at"] = _now()
            vstore._save()
            await _audit(payload, "ARCHIVE_KNOWLEDGE", "knowledge", doc_id)
            return {k: v for k, v in doc.items() if k != "embedding"}
    raise HTTPException(404, "Not found")


@router.post("/knowledge/{doc_id}/restore")
async def restore_knowledge(doc_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    vstore = knowledge.get_store()
    for doc in vstore.documents:
        if _doc_id(doc) == doc_id:
            doc["archived"] = False
            doc["updated_at"] = _now()
            vstore._save()
            await _audit(payload, "RESTORE_KNOWLEDGE", "knowledge", doc_id)
            return {k: v for k, v in doc.items() if k != "embedding"}
    raise HTTPException(404, "Not found")


@router.delete("/knowledge/{doc_id}")
async def delete_knowledge(doc_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    """Permanent delete — only for admin-created records. Official records should be archived."""
    vstore = knowledge.get_store()
    before = len(vstore.documents)
    vstore.documents = [d for d in vstore.documents if _doc_id(d) != doc_id]
    if len(vstore.documents) < before:
        vstore._save()
        await _audit(payload, "DELETE_KNOWLEDGE", "knowledge", doc_id)
        return {"success": True}
    raise HTTPException(404, "Not found")


# ---------------------------------------------------------------------------
# RAG management
# ---------------------------------------------------------------------------

@router.get("/rag/status")
async def rag_status() -> dict[str, Any]:
    vstore = knowledge.get_store()
    docs = vstore.documents
    non_archived = [d for d in docs if not d.get("archived")]
    indexed = [d for d in non_archived if d.get("index_status") == "INDEXED"]
    pending = [d for d in non_archived if d.get("index_status") in ("INDEX_PENDING", None)]
    failed = [d for d in non_archived if d.get("index_status") == "INDEX_FAILED"]
    return {
        "total": len(non_archived),
        "indexed": len(indexed),
        "pending": len(pending),
        "failed": len(failed),
        "archived": len([d for d in docs if d.get("archived")]),
        "last_index_time": None,  # not persisted; could be added to store metadata
        "index_ready": len(pending) == 0 and len(failed) == 0,
    }


@router.post("/rag/reindex")
async def rag_reindex(payload: dict = Depends(require_admin)) -> dict[str, Any]:
    vstore = knowledge.get_store()
    processed = 0
    indexed = 0
    errors: list[str] = []
    # Keep a snapshot for rollback
    snapshot = [dict(d) for d in vstore.documents]
    try:
        for doc in vstore.documents:
            if doc.get("archived"):
                continue
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
                        errors.append(f"No embedding for: {doc.get('source', doc.get('id', '?'))}")
                except Exception as exc:
                    doc["index_status"] = "INDEX_FAILED"
                    errors.append(str(exc))
        vstore._save()
    except Exception as exc:
        # Rollback
        vstore.documents = snapshot
        logger.error("RAG reindex failed, rolled back: %s", exc)
        await _audit(payload, "REINDEX", "system", "rag", f"FAILED: {exc}")
        return {"success": False, "error": str(exc), "records_processed": processed, "records_indexed": indexed}

    await _audit(payload, "REINDEX", "system", "rag", f"processed={processed} indexed={indexed} errors={len(errors)}")
    return {
        "success": True,
        "records_processed": processed,
        "records_indexed": indexed,
        "errors": errors,
    }


class PreviewRequest(BaseModel):
    query: str


@router.post("/rag/query-preview")
async def rag_query_preview(req: PreviewRequest, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    """Run the full RAG pipeline for admin inspection without persisting a session."""
    from app.web_mvp.agent import run_agent
    # run_agent(message, session_id, student_id) -> tuple(reply, intent, language, entity, verified, sources)
    result = await run_agent(req.query, "admin-preview", payload.get("sub", "admin"))
    if isinstance(result, tuple):
        reply, intent, language, entity, verified, sources = result
    else:
        reply, intent, language, verified, sources = str(result), "", "English", False, []
    # Detect language heuristically as fallback
    q = req.query
    if any(0x0C00 < ord(c) < 0x0C7F for c in q):
        language = "Telugu"
    elif any(kw in q.lower() for kw in ["lo ", "undi", "ela", "cheppandi", "cheppara", "vundi", "ledu"]):
        language = "Roman Telugu"
    return {
        "query": req.query,
        "detected_language": language,
        "response": reply,
        "sources": sources if isinstance(sources, list) else [],
        "intent": intent,
        "verified": verified,
    }


# ---------------------------------------------------------------------------
# Faculty / Department / Facility
# ---------------------------------------------------------------------------

@router.get("/faculty")
async def get_faculty(q: str | None = Query(default=None)) -> list[dict[str, Any]]:
    profs = await store.find_many("professors")
    if q:
        q_lower = q.lower()
        profs = [p for p in profs if q_lower in p.get("name", "").lower() or q_lower in p.get("department", "").lower()]
    return profs


@router.get("/departments")
async def get_departments(q: str | None = Query(default=None)) -> list[dict[str, Any]]:
    vstore = knowledge.get_store()
    docs = [d for d in vstore.documents if d.get("kind") == "department" and not d.get("archived")]
    if q:
        q_lower = q.lower()
        docs = [d for d in docs if q_lower in str(d).lower()]
    return [{k: v for k, v in d.items() if k != "embedding"} for d in docs]


@router.get("/facilities")
async def get_facilities(q: str | None = Query(default=None)) -> list[dict[str, Any]]:
    vstore = knowledge.get_store()
    docs = [d for d in vstore.documents if d.get("kind") == "facility" and not d.get("archived")]
    if q:
        q_lower = q.lower()
        docs = [d for d in docs if q_lower in str(d).lower()]
    return [{k: v for k, v in d.items() if k != "embedding"} for d in docs]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserStatusUpdateRequest(BaseModel):
    status: str
    reason: str | None = None


@router.get("/users")
async def get_users(role: str | None = Query(default=None)) -> list[dict[str, Any]]:
    users = await store.find_many("users")
    if role:
        users = [u for u in users if u.get("role") == role]
    safe = []
    for u in users:
        su = {k: v for k, v in u.items() if k not in ("password_hash", "password", "_id")}
        if "approval_status" not in su:
            su["approval_status"] = "APPROVED" if su.get("role") != "professor" else "PENDING"
        if "department" not in su:
            su["department"] = "General"
        safe.append(su)
    return safe


@router.patch("/users/{user_id}/status")
@router.patch("/professors/{user_id}/status")
async def update_user_status(
    user_id: str,
    req: UserStatusUpdateRequest,
    payload: dict = Depends(require_admin),
) -> dict[str, Any]:
    new_status = req.status.upper()
    if new_status not in {"APPROVED", "REJECTED", "SUSPENDED", "PENDING"}:
        raise HTTPException(400, "Invalid status. Must be APPROVED, REJECTED, SUSPENDED, or PENDING")
    user = await store.find_one("users", {"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    old_status = user.get("approval_status", "APPROVED")
    await store.update_one("users", {"user_id": user_id}, {"approval_status": new_status})
    if user.get("professor_id"):
        await store.update_one("professors", {"professor_id": user["professor_id"]}, {
            "approval_status": new_status,
            "application_approval_status": new_status,
            "active": new_status == "APPROVED",
        })
    action = f"{new_status}_USER" if user.get("role") != "professor" else f"{new_status}_PROFESSOR"
    await _audit(payload, action, "user", user_id, f"old_status={old_status} new_status={new_status} reason={req.reason or ''}")
    return {"success": True, "user_id": user_id, "status": new_status, "approval_status": new_status}


@router.post("/users/{user_id}/approve")
@router.post("/professors/{user_id}/approve")
async def approve_user(user_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    user = await store.find_one("users", {"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    await store.update_one("users", {"user_id": user_id}, {"approval_status": "APPROVED"})
    if user.get("professor_id"):
        await store.update_one("professors", {"professor_id": user["professor_id"]}, {
            "approval_status": "APPROVED",
            "application_approval_status": "APPROVED",
            "active": True,
        })
    await _audit(payload, "APPROVE_PROFESSOR", "user", user_id, "status=APPROVED")
    return {"success": True, "user_id": user_id, "status": "APPROVED", "approval_status": "APPROVED"}


@router.post("/users/{user_id}/reject")
@router.post("/professors/{user_id}/reject")
async def reject_user(user_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    user = await store.find_one("users", {"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    await store.update_one("users", {"user_id": user_id}, {"approval_status": "REJECTED"})
    if user.get("professor_id"):
        await store.update_one("professors", {"professor_id": user["professor_id"]}, {
            "approval_status": "REJECTED",
            "application_approval_status": "REJECTED",
            "active": False,
        })
    await _audit(payload, "REJECT_PROFESSOR", "user", user_id, "status=REJECTED")
    return {"success": True, "user_id": user_id, "status": "REJECTED", "approval_status": "REJECTED"}


@router.post("/users/{user_id}/suspend")
@router.post("/professors/{user_id}/suspend")
async def suspend_user(user_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    user = await store.find_one("users", {"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    await store.update_one("users", {"user_id": user_id}, {"approval_status": "SUSPENDED"})
    if user.get("professor_id"):
        await store.update_one("professors", {"professor_id": user["professor_id"]}, {
            "approval_status": "SUSPENDED",
            "application_approval_status": "SUSPENDED",
            "active": False,
        })
    await _audit(payload, "SUSPEND_PROFESSOR", "user", user_id, "status=SUSPENDED")
    return {"success": True, "user_id": user_id, "status": "SUSPENDED", "approval_status": "SUSPENDED"}


@router.post("/users/{user_id}/reactivate")
@router.post("/professors/{user_id}/reactivate")
async def reactivate_user(user_id: str, payload: dict = Depends(require_admin)) -> dict[str, Any]:
    user = await store.find_one("users", {"user_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    await store.update_one("users", {"user_id": user_id}, {"approval_status": "APPROVED"})
    if user.get("professor_id"):
        await store.update_one("professors", {"professor_id": user["professor_id"]}, {
            "approval_status": "APPROVED",
            "application_approval_status": "APPROVED",
            "active": True,
        })
    await _audit(payload, "REACTIVATE_PROFESSOR", "user", user_id, "status=APPROVED")
    return {"success": True, "user_id": user_id, "status": "APPROVED", "approval_status": "APPROVED"}


@router.get("/professors/approvals")
async def get_professor_approvals() -> list[dict[str, Any]]:
    """Return all professor user accounts and official registry linkage for admin approval."""
    users = await store.find_many("users", {"role": "professor"})
    profs = await store.find_many("professors")
    prof_by_id = {p.get("professor_id"): p for p in profs}

    result = []
    for u in users:
        p_id = u.get("professor_id")
        p_info = prof_by_id.get(p_id, {})
        result.append({
            "user_id": u.get("user_id"),
            "email": u.get("email"),
            "name": u.get("name") or p_info.get("name"),
            "professor_id": p_id,
            "department": p_info.get("department") or u.get("department") or "CSE (Data Science)",
            "designation": p_info.get("designation") or "Assistant Professor",
            "official_email": p_info.get("official_email") or u.get("email"),
            "official_source_verified": p_info.get("official_source_verified", True),
            "source_url": p_info.get("source_url", "https://www.rgmcet.edu.in/cseds_faculty1.php"),
            "approval_status": u.get("approval_status", "PENDING"),
            "application_approval_status": u.get("approval_status", "PENDING"),
            "registered_at": u.get("created_at"),
        })
    return result


# ---------------------------------------------------------------------------
# Appointments Management & Analytics
# ---------------------------------------------------------------------------

class AdminAppointmentOverrideRequest(BaseModel):
    status: str
    reason: str | None = None


@router.get("/appointments")
async def list_admin_appointments(
    status: str | None = Query(default=None),
    professor_id: str | None = Query(default=None),
    student_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    date: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    if professor_id:
        query["professor_id"] = professor_id
    if student_id:
        query["student_id"] = student_id
    if date:
        query["date"] = date

    appointments = await store.find_many("appointments", query)

    if q:
        q_lower = q.lower()
        appointments = [
            a for a in appointments
            if q_lower in str(a.get("student_name", "")).lower()
            or q_lower in str(a.get("student_id", "")).lower()
            or q_lower in str(a.get("professor_name", "")).lower()
            or q_lower in str(a.get("professor_id", "")).lower()
            or q_lower in str(a.get("reason", "")).lower()
            or q_lower in str(a.get("appointment_id", "")).lower()
        ]

    return sorted(appointments, key=lambda x: (x.get("date", ""), x.get("start_time", "")), reverse=True)


@router.patch("/appointments/{appointment_id}/override")
@router.post("/appointments/{appointment_id}/override")
async def override_appointment(
    appointment_id: str,
    req: AdminAppointmentOverrideRequest,
    payload: dict = Depends(require_admin),
) -> dict[str, Any]:
    target_status = req.status.upper()
    if target_status not in {"APPROVED", "REJECTED", "CANCELLED", "PENDING_APPROVAL", "PENDING"}:
        raise HTTPException(400, "Invalid target status")
    if target_status == "PENDING":
        target_status = "PENDING_APPROVAL"

    appointment = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appointment:
        raise HTTPException(404, "Appointment not found")

    old_status = appointment.get("status", "UNKNOWN")
    from app.web_mvp.calendar_service import calendar_service

    calendar_event_id = appointment.get("calendar_event_id")
    if target_status == "APPROVED" and not calendar_event_id:
        calendar_event_id = await calendar_service.create_event(appointment)
    elif target_status in {"REJECTED", "CANCELLED"} and calendar_event_id:
        await calendar_service.delete_event(calendar_event_id)
        calendar_event_id = None

    updates: dict[str, Any] = {
        "status": target_status,
        "slot_reserved": target_status in {"PENDING_APPROVAL", "APPROVED"},
    }
    if calendar_event_id is not None:
        updates["calendar_event_id"] = calendar_event_id

    await store.update_one("appointments", {"appointment_id": appointment_id}, updates)
    await _audit(
        payload,
        "ADMIN_OVERRIDE_APPOINTMENT",
        "appointment",
        appointment_id,
        f"old_status={old_status} new_status={target_status} reason={req.reason or ''}",
    )

    updated = await store.find_one("appointments", {"appointment_id": appointment_id})
    return updated or {"appointment_id": appointment_id, "status": target_status}

@router.get("/appointments/analytics")
async def appointment_analytics(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    appointments = await store.find_many("appointments")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    def in_range(a: dict) -> bool:
        ts = a.get("created_at") or a.get("date", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt >= cutoff
        except Exception:
            return True  # include if unparseable

    filtered = [a for a in appointments if in_range(a)]
    by_status: Counter = Counter(a.get("status", "UNKNOWN") for a in filtered)
    by_professor: Counter = Counter(a.get("professor_name", a.get("professor_id", "Unknown")) for a in filtered)
    by_dept: Counter = Counter(a.get("department", "Unknown") for a in filtered)

    # By day (last N days)
    daily: defaultdict = defaultdict(int)
    for a in filtered:
        ts = a.get("created_at") or a.get("date", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            daily[dt.date().isoformat()] += 1
        except Exception:
            pass

    return {
        "period_days": days,
        "total": len(filtered),
        "by_status": dict(by_status),
        "by_professor": dict(by_professor.most_common(10)),
        "by_department": dict(by_dept.most_common(10)),
        "daily": dict(sorted(daily.items())),
    }


@router.get("/ai/analytics")
async def ai_analytics(days: int = Query(default=30, ge=1, le=365)) -> dict[str, Any]:
    chats = await store.find_many("chat_sessions")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    total_queries = 0
    intent_counts: Counter = Counter()
    lang_counts: Counter = Counter()

    for s in chats:
        ts = s.get("updated_at") or s.get("created_at", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt < cutoff:
                continue
        except Exception:
            pass

        for t in s.get("turns", []):
            total_queries += 1
            intent_counts[t.get("intent", "UNKNOWN")] += 1
            lang_counts[t.get("language", "Unknown")] += 1

    return {
        "period_days": days,
        "total_queries": total_queries,
        "by_intent": dict(intent_counts.most_common(20)),
        "by_language": dict(lang_counts.most_common()),
    }


# ---------------------------------------------------------------------------
# AI Agent Inspection
# ---------------------------------------------------------------------------

@router.get("/agent/status")
async def agent_status() -> dict[str, Any]:
    """Safe agent inspection — lists tools and status. Never exposes secrets."""
    from app.web_mvp.tools import get_all_tool_definitions
    tools = get_all_tool_definitions()
    return {
        "agent_status": "active",
        "max_steps_per_turn": 4,
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "required_args": t.get("required", []),
                "parameters": list(t.get("parameters", {}).keys()),
            }
            for t in tools
        ],
        "supported_workflows": [
            "Search knowledge (RAG)",
            "Search professor by name/department",
            "Check professor availability",
            "List student appointments",
            "Create appointment (with confirmation)",
            "Reschedule appointment (with confirmation)",
            "Cancel appointment (with confirmation)",
        ],
        "tool_count": len(tools),
    }


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@router.get("/audit-logs")
async def audit_logs(
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict[str, Any]]:
    logs = await store.find_many("audit_logs")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    def passes(log: dict) -> bool:
        ts = log.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt < cutoff:
                return False
        except Exception:
            pass
        if action and action.lower() not in log.get("action", "").lower():
            return False
        if target_type and target_type.lower() not in log.get("target_type", "").lower():
            return False
        return True

    filtered = [lg for lg in logs if passes(lg)]
    return sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)
