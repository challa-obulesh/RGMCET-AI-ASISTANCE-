"""Phase 3 tests — authentication, authorization, and persistent appointments.

These tests run entirely against the in-memory demo store (no live MongoDB needed).
All 103 existing tests continue to pass; these are additive.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.web_mvp.main import app
from app.web_mvp import services, store as _store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    """Test client with LLM stubbed out (same pattern as existing tests)."""
    async def no_live_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(services.llm, "complete", no_live_llm)
    with TestClient(app) as test_client:
        yield test_client


def _register(client, name, email, password, role="student") -> dict:
    resp = client.post("/api/auth/register", json={
        "name": name, "email": email, "password": password, "role": role
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(client, email, password) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def future_workday_str() -> str:
    from datetime import date, timedelta
    candidate = date.today() + timedelta(days=1)
    while candidate.weekday() == 6:
        candidate += timedelta(days=1)
    return candidate.isoformat()


# ---------------------------------------------------------------------------
# Authentication — register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_student_returns_token_and_role(self, client):
        data = _register(client, "Alice", "alice@test.example", "Password123", "student")
        assert data["role"] == "student"
        assert data["access_token"]
        assert data["user_id"]
        assert data["name"] == "Alice"

    def test_register_professor_returns_professor_role(self, client):
        data = _register(client, "Prof Bob", "profbob@test.example", "Password123", "professor")
        assert data["role"] == "professor"

    def test_duplicate_email_returns_409(self, client):
        _register(client, "Carol", "carol@test.example", "Password123")
        resp = client.post("/api/auth/register", json={
            "name": "Carol2", "email": "carol@test.example", "password": "Password123", "role": "student"
        })
        assert resp.status_code == 409

    def test_short_password_is_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Dave", "email": "dave@test.example", "password": "123", "role": "student"
        })
        assert resp.status_code == 422

    def test_invalid_email_is_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Eve", "email": "not-an-email", "password": "Password123", "role": "student"
        })
        assert resp.status_code == 422

    def test_short_name_is_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "X", "email": "x@test.example", "password": "Password123", "role": "student"
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Authentication — login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_returns_valid_token(self, client):
        _register(client, "Frank", "frank@test.example", "Password123")
        data = _login(client, "frank@test.example", "Password123")
        assert data["access_token"]
        assert data["role"] == "student"

    def test_wrong_password_returns_401(self, client):
        _register(client, "Grace", "grace@test.example", "Password123")
        resp = client.post("/api/auth/login", json={
            "email": "grace@test.example", "password": "WrongPassword"
        })
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@test.example", "password": "Password123"
        })
        assert resp.status_code == 401

    def test_email_case_insensitive(self, client):
        _register(client, "Henry", "henry@test.example", "Password123")
        data = _login(client, "HENRY@TEST.EXAMPLE", "Password123")
        assert data["role"] == "student"


# ---------------------------------------------------------------------------
# Authentication — /me endpoint
# ---------------------------------------------------------------------------

class TestMe:
    def test_me_returns_profile_without_password(self, client):
        tok = _register(client, "Iris", "iris@test.example", "Password123")
        resp = client.get("/api/auth/me", headers=_auth_headers(tok["access_token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Iris"
        assert data["email"] == "iris@test.example"
        assert data["role"] == "student"
        assert "password" not in data
        assert "password_hash" not in data

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authorization — role-based access
# ---------------------------------------------------------------------------

class TestAuthorization:
    def test_student_cannot_approve_appointment(self, client):
        student = _register(client, "Jake", "jake@test.example", "Password123", "student")
        # Create an appointment as demo
        professor = client.get("/api/professors").json()[0]
        created = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "Auth test",
        }).json()
        appointment_id = created["appointment_id"]
        # Student tries to approve
        resp = client.post(
            f"/api/appointments/{appointment_id}/approve",
            headers=_auth_headers(student["access_token"]),
        )
        assert resp.status_code == 403

    def test_student_cannot_reject_appointment(self, client):
        student = _register(client, "Kim", "kim@test.example", "Password123", "student")
        professor = client.get("/api/professors").json()[0]
        created = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "Auth test reject",
        }).json()
        resp = client.post(
            f"/api/appointments/{created['appointment_id']}/reject",
            headers=_auth_headers(student["access_token"]),
        )
        assert resp.status_code == 403

    def test_student_cannot_access_another_students_appointment(self, client):
        student_a = _register(client, "LiamA", "liama@test.example", "Password123", "student")
        student_b = _register(client, "LiamB", "liamb@test.example", "Password123", "student")
        professor = client.get("/api/professors").json()[0]
        created = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "Student A appointment",
        }, headers=_auth_headers(student_a["access_token"])).json()
        # Student B tries to read Student A's appointment
        resp = client.get(
            f"/api/appointments/{created['appointment_id']}",
            headers=_auth_headers(student_b["access_token"]),
        )
        assert resp.status_code == 403

    def test_student_cannot_cancel_another_students_appointment(self, client):
        student_a = _register(client, "MaiaA", "maiaa@test.example", "Password123", "student")
        student_b = _register(client, "MaiaB", "maiab@test.example", "Password123", "student")
        professor = client.get("/api/professors").json()[0]
        created = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "Student A only",
        }, headers=_auth_headers(student_a["access_token"])).json()
        resp = client.post(
            f"/api/appointments/{created['appointment_id']}/cancel",
            headers=_auth_headers(student_b["access_token"]),
        )
        assert resp.status_code == 403

    def test_professor_cannot_create_appointment(self, client):
        professor_user = _register(client, "Prof Nora", "nora@test.example", "Password123", "professor")
        professor = client.get("/api/professors").json()[0]
        resp = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "Professor cannot book",
        }, headers=_auth_headers(professor_user["access_token"]))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Authenticated appointment flow
# ---------------------------------------------------------------------------

class TestAuthenticatedAppointments:
    def test_authenticated_student_creates_appointment_with_own_id(self, client):
        student = _register(client, "Oliver", "oliver@test.example", "Password123", "student")
        professor = client.get("/api/professors").json()[0]
        resp = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "Meeting with professor",
        }, headers=_auth_headers(student["access_token"]))
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "PENDING_APPROVAL"
        assert data["student_id"] == student["user_id"]

    def test_authenticated_student_sees_own_appointments_only(self, client):
        student_a = _register(client, "PaigA", "paiga@test.example", "Password123", "student")
        student_b = _register(client, "PaigB", "paigb@test.example", "Password123", "student")
        professor = client.get("/api/professors").json()[0]
        client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "Only for Student A",
        }, headers=_auth_headers(student_a["access_token"]))
        # Student B lists appointments — should be empty
        resp = client.get("/api/appointments", headers=_auth_headers(student_b["access_token"]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_student_can_cancel_own_appointment(self, client):
        student = _register(client, "Quinn", "quinn@test.example", "Password123", "student")
        professor = client.get("/api/professors").json()[0]
        created = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday_str(),
            "start_time": "10:00",
            "reason": "To be cancelled",
        }, headers=_auth_headers(student["access_token"])).json()
        resp = client.post(
            f"/api/appointments/{created['appointment_id']}/cancel",
            headers=_auth_headers(student["access_token"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"


# ---------------------------------------------------------------------------
# Database — in-memory CRUD
# ---------------------------------------------------------------------------

class TestDatabaseCRUD:
    @pytest.mark.asyncio
    async def test_insert_and_find_user(self, client):
        user_doc = {
            "user_id": "TEST-USER-CRUD-001",
            "name": "Test User",
            "email": "testcrud@example.dev",
            "password_hash": "hashed",
            "role": "student",
        }
        inserted = await _store.insert_one("users", user_doc)
        assert inserted["user_id"] == "TEST-USER-CRUD-001"
        found = await _store.find_one("users", {"user_id": "TEST-USER-CRUD-001"})
        assert found is not None
        assert found["name"] == "Test User"
        assert "created_at" in found

    @pytest.mark.asyncio
    async def test_insert_and_retrieve_appointment(self, client):
        doc = {
            "appointment_id": "APT-TEST-CRUD-001",
            "student_id": "student-crud",
            "professor_id": "PROF-DEMO-001",
            "professor_name": "Test Professor",
            "date": future_workday_str(),
            "start_time": "11:00",
            "end_time": "11:30",
            "reason": "CRUD test",
            "status": "PENDING_APPROVAL",
            "slot_reserved": True,
        }
        inserted = await _store.insert_appointment(doc)
        assert inserted is not None
        found = await _store.find_one("appointments", {"appointment_id": "APT-TEST-CRUD-001"})
        assert found["status"] == "PENDING_APPROVAL"

    @pytest.mark.asyncio
    async def test_update_appointment_status(self, client):
        doc = {
            "appointment_id": "APT-TEST-UPDATE-001",
            "student_id": "student-update",
            "professor_id": "PROF-DEMO-001",
            "professor_name": "Test Professor",
            "date": future_workday_str(),
            "start_time": "13:00",
            "end_time": "13:30",
            "reason": "Update test",
            "status": "PENDING_APPROVAL",
            "slot_reserved": True,
        }
        await _store.insert_appointment(doc)
        updated = await _store.transition_appointment(
            "APT-TEST-UPDATE-001",
            {"PENDING_APPROVAL"},
            {"status": "APPROVED", "slot_reserved": True},
        )
        assert updated is not None
        assert updated["status"] == "APPROVED"


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hashed_password_is_not_plaintext(self):
        from app.web_mvp.auth import hash_password
        hashed = hash_password("MySecret123")
        assert hashed != "MySecret123"
        assert len(hashed) > 20

    def test_correct_password_verifies(self):
        from app.web_mvp.auth import hash_password, verify_password
        hashed = hash_password("MySecret123")
        assert verify_password("MySecret123", hashed) is True

    def test_wrong_password_fails_verification(self):
        from app.web_mvp.auth import hash_password, verify_password
        hashed = hash_password("MySecret123")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        from app.web_mvp.auth import hash_password
        h1 = hash_password("MySecret123")
        h2 = hash_password("MySecret123")
        # bcrypt salts mean the hashes should differ
        assert h1 != h2


# ---------------------------------------------------------------------------
# JWT token
# ---------------------------------------------------------------------------

class TestJWT:
    def test_token_encodes_and_decodes_role(self):
        from app.web_mvp.auth import create_access_token, decode_token
        token = create_access_token({"sub": "U001", "role": "professor", "name": "Prof X"})
        payload = decode_token(token)
        assert payload["sub"] == "U001"
        assert payload["role"] == "professor"

    def test_invalid_token_raises_401(self):
        from fastapi import HTTPException
        from app.web_mvp.auth import decode_token
        with pytest.raises(HTTPException) as exc_info:
            decode_token("bad.token.here")
        assert exc_info.value.status_code == 401

    def test_protected_endpoint_without_token_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_professor_dashboard_endpoint_requires_professor_role(self, client):
        student = _register(client, "Rosa", "rosa@test.example", "Password123", "student")
        resp = client.get("/api/professor/appointments", headers=_auth_headers(student["access_token"]))
        assert resp.status_code == 403
