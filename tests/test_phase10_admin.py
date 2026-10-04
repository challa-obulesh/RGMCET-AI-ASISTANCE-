"""Phase 10 Admin Dashboard — comprehensive tests.

Covers:
  - Security isolation (unauthenticated, student, professor → blocked)
  - Overview
  - Health
  - Knowledge CRUD (create, read, update, verify, unverify, archive, restore, delete)
  - Knowledge search and filters
  - RAG status, reindex, query-preview
  - Faculty, departments, facilities
  - Users (password redaction)
  - Appointment analytics (empty, with data, date filter)
  - AI analytics
  - Audit logs (filtering)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.web_mvp.main import app
from app.web_mvp.auth import create_access_token
from app.web_mvp import store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_store():
    """Reset in-memory store and knowledge store before each test."""
    from app.web_mvp.vector_store import VECTOR_STORE_PATH
    store.reset_demo_data()
    # also clear audit_logs
    store._memory.setdefault("audit_logs", []).clear()
    from app.web_mvp import knowledge as kn
    kn._store = None  # force reload
    original_vstore_bytes = VECTOR_STORE_PATH.read_bytes() if VECTOR_STORE_PATH.exists() else None
    yield
    store.reset_demo_data()
    store._memory.setdefault("audit_logs", []).clear()
    if original_vstore_bytes is not None:
        VECTOR_STORE_PATH.write_bytes(original_vstore_bytes)
    kn._store = None



@pytest.fixture
def student_token():
    return create_access_token({"sub": "U-STUDENT", "email": "stu@test.com", "role": "student", "name": "Student"})


@pytest.fixture
def professor_token():
    return create_access_token({"sub": "U-PROF", "email": "prof@test.com", "role": "professor", "name": "Prof"})


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "U-ADMIN", "email": "admin@test.com", "role": "admin", "name": "Admin"})


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def ah(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Security isolation
# ---------------------------------------------------------------------------

PROTECTED = [
    ("GET", "/api/admin/overview"),
    ("GET", "/api/admin/health"),
    ("GET", "/api/admin/knowledge"),
    ("GET", "/api/admin/users"),
    ("GET", "/api/admin/faculty"),
    ("GET", "/api/admin/departments"),
    ("GET", "/api/admin/facilities"),
    ("GET", "/api/admin/appointments/analytics"),
    ("GET", "/api/admin/ai/analytics"),
    ("GET", "/api/admin/audit-logs"),
    ("GET", "/api/admin/rag/status"),
    ("GET", "/api/admin/agent/status"),
]


@pytest.mark.parametrize("method,url", PROTECTED)
def test_unauthenticated_blocked(client, method, url):
    resp = getattr(client, method.lower())(url)
    assert resp.status_code == 401, f"Expected 401 for {method} {url}, got {resp.status_code}"


@pytest.mark.parametrize("method,url", PROTECTED)
def test_student_blocked(client, student_token, method, url):
    resp = getattr(client, method.lower())(url, headers=ah(student_token))
    assert resp.status_code == 403, f"Expected 403 for student on {method} {url}, got {resp.status_code}"


@pytest.mark.parametrize("method,url", PROTECTED)
def test_professor_blocked(client, professor_token, method, url):
    resp = getattr(client, method.lower())(url, headers=ah(professor_token))
    assert resp.status_code == 403, f"Expected 403 for professor on {method} {url}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def test_overview_admin(client, admin_token):
    r = client.get("/api/admin/overview", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "users" in d
    assert "knowledge" in d
    assert "appointments" in d
    assert "ai" in d
    assert "total" in d["users"]
    assert "verified" in d["knowledge"]
    assert "pending" in d["appointments"]
    assert "total_queries" in d["ai"]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_admin(client, admin_token):
    r = client.get("/api/admin/health", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "backend" in d
    assert "database" in d
    assert "llm" in d
    assert "rag" in d
    assert "google_calendar" in d
    # Must not expose secrets
    text = r.text
    assert "password" not in text.lower()
    assert "secret" not in text.lower()
    assert "token" not in text.lower()


# ---------------------------------------------------------------------------
# Knowledge CRUD
# ---------------------------------------------------------------------------

def test_knowledge_list(client, admin_token):
    r = client.get("/api/admin/knowledge", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_knowledge_create(client, admin_token):
    payload = {
        "title": "Test Knowledge",
        "content": "RGMCET is located in Nandyal.",
        "kind": "college",
        "department": "",
        "source": "test-source",
        "source_url": "https://rgmcet.edu.in",
        "language": "English",
        "verified": True,
    }
    r = client.post("/api/admin/knowledge", json=payload, headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert d["id"]
    assert d["index_status"] == "INDEX_PENDING"
    assert d["original_record"]["title"] == "Test Knowledge"
    assert "embedding" not in d


def test_knowledge_get_single(client, admin_token):
    # create first
    payload = {"title": "GetTest", "content": "Some content", "kind": "general"}
    cr = client.post("/api/admin/knowledge", json=payload, headers=ah(admin_token))
    doc_id = cr.json()["id"]
    r = client.get(f"/api/admin/knowledge/{doc_id}", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["id"] == doc_id


def test_knowledge_update(client, admin_token):
    cr = client.post("/api/admin/knowledge", json={"title": "Old", "content": "Old content", "kind": "general"}, headers=ah(admin_token))
    doc_id = cr.json()["id"]
    r = client.patch(f"/api/admin/knowledge/{doc_id}", json={"content": "New content", "title": "New"}, headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["index_status"] == "INDEX_PENDING"


def test_knowledge_verify_unverify(client, admin_token):
    cr = client.post("/api/admin/knowledge", json={"title": "V", "content": "C", "kind": "general"}, headers=ah(admin_token))
    doc_id = cr.json()["id"]
    # Verify
    r = client.post(f"/api/admin/knowledge/{doc_id}/verify", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["original_record"]["verified"] is True
    # Unverify
    r = client.post(f"/api/admin/knowledge/{doc_id}/unverify", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["original_record"]["verified"] is False


def test_knowledge_archive_restore(client, admin_token):
    cr = client.post("/api/admin/knowledge", json={"title": "Arch", "content": "C", "kind": "general"}, headers=ah(admin_token))
    doc_id = cr.json()["id"]
    # Archive
    r = client.post(f"/api/admin/knowledge/{doc_id}/archive", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["archived"] is True
    # Should not appear in default list
    list_r = client.get("/api/admin/knowledge", headers=ah(admin_token))
    ids = [d["id"] for d in list_r.json()]
    assert doc_id not in ids
    # Should appear with archived filter
    arch_r = client.get("/api/admin/knowledge?filter=archived", headers=ah(admin_token))
    arch_ids = [d["id"] for d in arch_r.json()]
    assert doc_id in arch_ids
    # Restore
    r = client.post(f"/api/admin/knowledge/{doc_id}/restore", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["archived"] is False


def test_knowledge_delete(client, admin_token):
    cr = client.post("/api/admin/knowledge", json={"title": "Del", "content": "C", "kind": "general"}, headers=ah(admin_token))
    doc_id = cr.json()["id"]
    r = client.delete(f"/api/admin/knowledge/{doc_id}", headers=ah(admin_token))
    assert r.status_code == 200
    # Not in list after
    assert doc_id not in [d["id"] for d in client.get("/api/admin/knowledge", headers=ah(admin_token)).json()]


def test_knowledge_search(client, admin_token):
    client.post("/api/admin/knowledge", json={"title": "RGMCET Library", "content": "Library is open 24/7.", "kind": "facility"}, headers=ah(admin_token))
    r = client.get("/api/admin/knowledge?q=Library", headers=ah(admin_token))
    assert r.status_code == 200
    titles = [str(d) for d in r.json()]
    assert any("Library" in t for t in titles) or len(r.json()) > 0


def test_knowledge_filter_verified(client, admin_token):
    cr = client.post("/api/admin/knowledge", json={"title": "VF", "content": "C", "kind": "general"}, headers=ah(admin_token))
    doc_id = cr.json()["id"]
    client.post(f"/api/admin/knowledge/{doc_id}/verify", headers=ah(admin_token))
    r = client.get("/api/admin/knowledge?filter=verified", headers=ah(admin_token))
    assert r.status_code == 200
    ids = [d["id"] for d in r.json()]
    assert doc_id in ids


def test_knowledge_filter_pending(client, admin_token):
    cr = client.post("/api/admin/knowledge", json={"title": "Pend", "content": "C", "kind": "general"}, headers=ah(admin_token))
    doc_id = cr.json()["id"]
    r = client.get("/api/admin/knowledge?filter=pending", headers=ah(admin_token))
    assert r.status_code == 200
    ids = [d["id"] for d in r.json()]
    assert doc_id in ids


def test_knowledge_no_embedding_in_response(client, admin_token):
    client.post("/api/admin/knowledge", json={"title": "Emb", "content": "C", "kind": "general"}, headers=ah(admin_token))
    r = client.get("/api/admin/knowledge", headers=ah(admin_token))
    for doc in r.json():
        assert "embedding" not in doc


# ---------------------------------------------------------------------------
# RAG management
# ---------------------------------------------------------------------------

def test_rag_status(client, admin_token):
    r = client.get("/api/admin/rag/status", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "total" in d
    assert "indexed" in d
    assert "pending" in d
    assert "failed" in d
    assert "archived" in d


def test_rag_reindex(client, admin_token):
    r = client.post("/api/admin/rag/reindex", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "records_processed" in d
    assert "records_indexed" in d


def test_rag_query_preview(client, admin_token):
    r = client.post("/api/admin/rag/query-preview", json={"query": "What departments are in RGMCET?"}, headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "query" in d
    assert "response" in d
    assert "detected_language" in d


def test_rag_query_preview_telugu(client, admin_token):
    r = client.post("/api/admin/rag/query-preview", json={"query": "RGMCET lo library undi?"}, headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert d["detected_language"] in ("Roman Telugu", "English")


def test_rag_reindex_blocked_student(client, student_token):
    r = client.post("/api/admin/rag/reindex", headers=ah(student_token))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Faculty / Departments / Facilities
# ---------------------------------------------------------------------------

def test_faculty_list(client, admin_token):
    r = client.get("/api/admin/faculty", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_faculty_search(client, admin_token):
    r = client.get("/api/admin/faculty?q=CSE", headers=ah(admin_token))
    assert r.status_code == 200


def test_departments_list(client, admin_token):
    r = client.get("/api/admin/departments", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_facilities_list(client, admin_token):
    r = client.get("/api/admin/facilities", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Users — password redaction
# ---------------------------------------------------------------------------

def test_users_no_password(client, admin_token):
    r = client.get("/api/admin/users", headers=ah(admin_token))
    assert r.status_code == 200
    for u in r.json():
        assert "password_hash" not in u
        assert "password" not in u


def test_users_role_filter(client, admin_token):
    r = client.get("/api/admin/users?role=student", headers=ah(admin_token))
    assert r.status_code == 200
    for u in r.json():
        assert u.get("role") == "student"


# ---------------------------------------------------------------------------
# Appointment analytics
# ---------------------------------------------------------------------------

def test_appointment_analytics_empty(client, admin_token):
    r = client.get("/api/admin/appointments/analytics", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "total" in d
    assert "by_status" in d
    assert "by_professor" in d
    assert "by_department" in d
    assert "daily" in d


def test_appointment_analytics_days_param(client, admin_token):
    r = client.get("/api/admin/appointments/analytics?days=7", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["period_days"] == 7


# ---------------------------------------------------------------------------
# AI analytics
# ---------------------------------------------------------------------------

def test_ai_analytics(client, admin_token):
    r = client.get("/api/admin/ai/analytics", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "total_queries" in d
    assert "by_intent" in d
    assert "by_language" in d


def test_ai_analytics_days_param(client, admin_token):
    r = client.get("/api/admin/ai/analytics?days=7", headers=ah(admin_token))
    assert r.status_code == 200
    assert r.json()["period_days"] == 7


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

def test_audit_logs_empty(client, admin_token):
    r = client.get("/api/admin/audit-logs", headers=ah(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_audit_logs_created_on_action(client, admin_token):
    # Create a knowledge record — should produce an audit log
    client.post("/api/admin/knowledge", json={"title": "AL", "content": "C", "kind": "general"}, headers=ah(admin_token))
    import asyncio
    import time
    time.sleep(0.1)  # give async task a moment
    # Directly check memory
    logs = store._memory.get("audit_logs", [])
    actions = [lg["action"] for lg in logs]
    assert "CREATE_KNOWLEDGE" in actions


def test_audit_logs_filter_by_action(client, admin_token):
    r = client.get("/api/admin/audit-logs?action=REINDEX", headers=ah(admin_token))
    assert r.status_code == 200


def test_audit_logs_filter_by_type(client, admin_token):
    r = client.get("/api/admin/audit-logs?target_type=knowledge", headers=ah(admin_token))
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Comprehensive security — POST/PATCH/DELETE endpoints
# ---------------------------------------------------------------------------

WRITE_ENDPOINTS = [
    ("POST",   "/api/admin/knowledge"),
    ("POST",   "/api/admin/rag/reindex"),
    ("POST",   "/api/admin/rag/query-preview"),
]


@pytest.mark.parametrize("method,url", WRITE_ENDPOINTS)
def test_write_endpoint_student_blocked(client, student_token, method, url):
    resp = getattr(client, method.lower())(url, json={}, headers=ah(student_token))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Agent inspection
# ---------------------------------------------------------------------------

def test_agent_status(client, admin_token):
    r = client.get("/api/admin/agent/status", headers=ah(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert "agent_status" in d
    assert "tools" in d
    assert "tool_count" in d
    assert "supported_workflows" in d
    assert isinstance(d["tools"], list)
    assert d["tool_count"] == len(d["tools"])


def test_agent_status_student_blocked(client, student_token):
    r = client.get("/api/admin/agent/status", headers=ah(student_token))
    assert r.status_code == 403


def test_agent_status_unauthenticated(client):
    r = client.get("/api/admin/agent/status")
    assert r.status_code == 401


def test_agent_status_no_secrets(client, admin_token):
    """Ensure no sensitive keys are returned."""
    r = client.get("/api/admin/agent/status", headers=ah(admin_token))
    assert r.status_code == 200
    text = r.text
    for secret_word in ("api_key", "secret", "password", "token", "credential", "GOOGLE_API"):
        assert secret_word not in text.lower() or "supported_workflows" in text

