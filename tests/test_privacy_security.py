"""Automated Privacy, Security, and Data Protection Regression Suite.

Verifies:
1. No official faculty email IDs in demo data, fixtures, or registry.
2. Synthetic accounts can register, authenticate, and perform role workflows.
3. Privacy Gateway redacts emails, phones, JWTs, API keys, and connection strings from LLM payloads.
4. Privacy Gateway pre-transmission inspection and safe fallback on errors.
5. RBAC boundaries (student, professor, admin separation).
6. Cross-professor isolation (no accessing or approving other professors' appointments).
7. Deterministic faculty lookup preventing hallucinations (Stephen in Data Science).
8. Multilingual support (English, Telugu, Roman Telugu).
9. Appointment lifecycle (creation, approval, rejection, rescheduling, cancellation).
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from app.web_mvp import store
from app.web_mvp.main import app
from app.web_mvp.privacy_gateway import privacy_gateway, PrivacyGatewayError
from app.web_mvp.services import answer_chat, _deterministic_faculty_lookup


@pytest.fixture
def client():
    store.reset_demo_data()
    with TestClient(app) as test_client:
        yield test_client


def future_workday():
    candidate = date.today() + timedelta(days=2)
    while candidate.weekday() in (5, 6):  # Skip weekend
        candidate += timedelta(days=1)
    return candidate.isoformat()


# =============================================================================
# 1. Official Email Audit & Synthetic Demodata Verification
# =============================================================================

def test_no_official_faculty_emails_in_registry_and_demo_data():
    """Ensure no official faculty email addresses exist in demo/sample data files."""
    root = Path(__file__).resolve().parents[1]

    # 1. Demo professors json
    demo_profs_path = root / "data" / "demo_professors.json"
    demo_profs = json.loads(demo_profs_path.read_text(encoding="utf-8"))
    for p in demo_profs:
        email = p.get("email") or ""
        assert not email.endswith("@rgmcet.edu.in"), f"Found official email in demo_professors: {email}"
        if email:
            assert email.endswith("@example.com"), f"Demo email not on reserved example domain: {email}"

    # 2. Official faculty registry
    registry_path = root / "official_faculty_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for f in registry:
        off_email = f.get("official_email") or ""
        assert not off_email.endswith("@rgmcet.edu.in"), f"Official faculty email not redacted in registry: {off_email}"
        if off_email:
            assert off_email.endswith("@example.com"), f"Registry email not on example domain: {off_email}"

    # 3. Seed database script
    seed_path = root / "scripts" / "seed_database.py"
    seed_content = seed_path.read_text(encoding="utf-8")
    assert "@rgmcet.edu.in" not in seed_content
    assert "@rgmcet.dev" not in seed_content
    assert "student1@example.com" in seed_content
    assert "hod.cse.ds@example.com" in seed_content


# =============================================================================
# 2. Synthetic Account Authentication & Workflows
# =============================================================================

def test_synthetic_accounts_login_and_workflows(client):
    """Verify synthetic accounts can register, receive admin approval, and log in."""
    # Register synthetic professor
    prof_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Synthetic Professor",
            "email": "professor1@example.com",
            "password": "Password123!",
            "role": "professor",
            "department": "Computer Science and Engineering",
        },
    )
    assert prof_reg.status_code == 201
    prof_uid = prof_reg.json()["user_id"]
    assert prof_reg.json()["approval_status"] == "PENDING"

    # Register synthetic admin
    admin_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Admin User",
            "email": "admin@example.com",
            "password": "AdminPassword123!",
            "role": "admin",
        },
    )
    assert admin_reg.status_code == 201
    admin_token = admin_reg.json()["access_token"]

    # Admin approves synthetic professor
    appr_res = client.post(
        f"/api/admin/users/{prof_uid}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert appr_res.status_code == 200

    # Approved professor can log in
    prof_login = client.post(
        "/api/auth/login",
        json={"email": "professor1@example.com", "password": "Password123!"},
    )
    assert prof_login.status_code == 200
    assert prof_login.json()["approval_status"] == "APPROVED"


# =============================================================================
# 3. Privacy Gateway Redactions
# =============================================================================

def test_privacy_gateway_redaction_email_and_credentials():
    """Verify email addresses, phone numbers, JWTs, DB URIs, and API keys are redacted."""
    raw_prompt = (
        "Contact HOD at hod.cseds@rgmcet.edu.in or alt phone +91 9849348501. "
        "Session: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSig "
        "Mongo: mongodb+srv://cluster0.example.mongodb.net/prod_db "
        "Gemini key: AIzaSyD-EXAMPLEKEY1234567890abcdefghijk "
        "OpenAI key: sk-abcdefghijklmnopqrstuvwxyz123456"
    )

    sanitized, stats = privacy_gateway.sanitize_text(raw_prompt)

    assert "[REDACTED_EMAIL]" in sanitized
    assert "hod.cseds@rgmcet.edu.in" not in sanitized

    assert "[REDACTED_PHONE]" in sanitized
    assert "9849348501" not in sanitized

    assert "[REDACTED_TOKEN]" in sanitized
    assert "eyJhbGci" not in sanitized

    assert "[REDACTED_DB_CONNECTION]" in sanitized
    assert "mongodb+srv" not in sanitized

    assert "[REDACTED_API_KEY]" in sanitized
    assert "AIzaSyD" not in sanitized
    assert "sk-abcdef" not in sanitized

    assert stats["emails"] >= 1
    assert stats["phones"] >= 1
    assert stats["tokens"] >= 1
    assert stats["db_uris"] >= 1
    assert stats["api_keys"] >= 2


def test_privacy_gateway_outbound_payload_inspection_rejects_leaks():
    """Verify outbound payload deep inspector rejects unredacted sensitive values."""
    clean_payload = {
        "model": "gemini-2.5-flash",
        "contents": [{"parts": [{"text": "Hello world with [REDACTED_EMAIL]"}]}],
    }
    # Should pass without error
    privacy_gateway.verify_outbound_payload(clean_payload)

    # Injected leak should raise PrivacyGatewayError
    leaky_payload = {
        "model": "gemini-2.5-flash",
        "contents": [{"parts": [{"text": "Send notice to prof@rgmcet.edu.in"}]}],
    }
    with pytest.raises(PrivacyGatewayError, match="unredacted email"):
        privacy_gateway.verify_outbound_payload(leaky_payload)


@pytest.mark.asyncio
async def test_privacy_gateway_safe_fallback_on_error():
    """Verify privacy gateway errors abort outbound calls safely without leaking data."""
    from app.web_mvp import llm

    with patch.object(privacy_gateway, "sanitize_request", side_effect=Exception("Gateway error")):
        # complete() must catch the error, log sanitized metadata, and return None (safe fallback)
        result = await llm.complete("System prompt", "User prompt with confidential data")
        assert result is None


# =============================================================================
# 4. RBAC & Cross-Professor Isolation
# =============================================================================

def test_rbac_and_cross_professor_isolation(client):
    """Verify student/professor boundaries and ensure Professor A cannot modify Professor B's data."""
    # Setup Admin
    admin_reg = client.post(
        "/api/auth/register",
        json={"name": "Admin", "email": "sec.admin@example.com", "password": "AdminPassword123!", "role": "admin"},
    )
    admin_tok = admin_reg.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_tok}"}

    # Register Professor A
    prof_a_reg = client.post(
        "/api/auth/register",
        json={"name": "Dr. Prof A", "email": "prof.a@example.com", "password": "Pass123!A", "role": "professor"},
    )
    client.post(f"/api/admin/users/{prof_a_reg.json()['user_id']}/approve", headers=admin_headers)
    prof_a_tok = client.post("/api/auth/login", json={"email": "prof.a@example.com", "password": "Pass123!A"}).json()["access_token"]
    prof_a_headers = {"Authorization": f"Bearer {prof_a_tok}"}

    # Register Professor B
    prof_b_reg = client.post(
        "/api/auth/register",
        json={"name": "Dr. Prof B", "email": "prof.b@example.com", "password": "Pass123!B", "role": "professor"},
    )
    client.post(f"/api/admin/users/{prof_b_reg.json()['user_id']}/approve", headers=admin_headers)
    prof_b_tok = client.post("/api/auth/login", json={"email": "prof.b@example.com", "password": "Pass123!B"}).json()["access_token"]
    prof_b_headers = {"Authorization": f"Bearer {prof_b_tok}"}

    # Register Student
    stu_reg = client.post(
        "/api/auth/register",
        json={"name": "Student X", "email": "student.x@example.com", "password": "Pass123!S", "role": "student"},
    )
    stu_tok = stu_reg.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_tok}"}

    # 1. Student cannot access admin endpoints
    assert client.get("/api/admin/users", headers=stu_headers).status_code == 403
    assert client.get("/api/admin/overview", headers=stu_headers).status_code == 403

    # 2. Student books appointment with Professor B
    prof_b_id = prof_b_reg.json()["professor_id"]
    appt_res = client.post(
        "/api/appointments",
        headers=stu_headers,
        json={
            "student_id": "student-x-id",
            "student_name": "Student X",
            "professor_id": prof_b_id,
            "date": future_workday(),
            "start_time": "10:00",
            "end_time": "10:30",
            "reason": "Thesis Guidance",
        },
    )
    assert appt_res.status_code == 201
    appt_id = appt_res.json()["appointment_id"]

    # 3. Professor A attempts to approve Professor B's appointment -> Must be forbidden (403)
    attack_appr = client.post(f"/api/appointments/{appt_id}/approve", headers=prof_a_headers)
    assert attack_appr.status_code == 403

    # 4. Professor B approves own appointment -> Must succeed (200)
    legit_appr = client.post(f"/api/appointments/{appt_id}/approve", headers=prof_b_headers)
    assert legit_appr.status_code == 200
    assert legit_appr.json()["status"] == "APPROVED"


# =============================================================================
# 5. Deterministic Non-Hallucination Faculty Lookup (Phase 4)
# =============================================================================

@pytest.mark.asyncio
async def test_stephen_faculty_deterministic_no_match():
    """Verify 'Stephen in Data Science' returns deterministic no-match without hallucinations."""
    reply, intent, lang, _, verified, sources = await answer_chat(
        "Is there any Data Science faculty member named Stephen?",
        session_id=None,
        student_id="test-student",
    )

    assert intent == "FACULTY_INFORMATION"
    assert verified is True
    assert "No matching faculty member named Stephen was found in the verified Data Science faculty records." in reply
    # Must cite verified Data Science faculty directory
    assert any("cseds_faculty1.php" in s.get("url", "") for s in sources)


@pytest.mark.asyncio
async def test_stephen_multilingual_deterministic_no_match():
    """Verify Roman Telugu and Telugu Stephen queries produce deterministic no-match."""
    # Roman Telugu
    reply_rt, _, _, _, _, _ = await answer_chat(
        "Data Science lo Stephen ane faculty member unnara?",
        session_id=None,
        student_id="test-student",
    )
    assert "Stephen" in reply_rt
    assert "dorakaledu" in reply_rt

    # Telugu
    reply_te, _, _, _, _, _ = await answer_chat(
        "డేటా సైన్స్ విభాగంలో Stephen అనే ఫ్యాకల్టీ ఉన్నారా?",
        session_id=None,
        student_id="test-student",
    )
    assert "Stephen" in reply_te
    assert "కనుగొనబడలేదు" in reply_te


@pytest.mark.asyncio
async def test_verified_existing_faculty_deterministic_match():
    """Verify query for Penchala Prasad returns verified match."""
    reply, intent, _, _, verified, sources = await answer_chat(
        "Is there any Data Science faculty member named Penchala Prasad?",
        session_id=None,
        student_id="test-student",
    )
    assert verified is True
    assert "Dr. P. Penchala Prasad" in reply
    assert "Associate Professor" in reply
    assert any("PenchalaPrasad.pdf" in s.get("url", "") or "cseds_faculty1.php" in s.get("url", "") for s in sources)


# =============================================================================
# 6. Appointment Lifecycle with Synthetic Demo Accounts
# =============================================================================

def test_complete_appointment_lifecycle_synthetic_accounts(client):
    """Test create -> approve -> reschedule -> cancel lifecycle with synthetic accounts."""
    # 1. Admin setup
    admin_reg = client.post(
        "/api/auth/register",
        json={"name": "Lifecycle Admin", "email": "life.admin@example.com", "password": "AdminPassword123!", "role": "admin"},
    )
    admin_tok = admin_reg.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_tok}"}

    # 2. Professor setup
    prof_reg = client.post(
        "/api/auth/register",
        json={"name": "Dr. Lifecycle Prof", "email": "life.prof@example.com", "password": "ProfPassword123!", "role": "professor"},
    )
    prof_uid = prof_reg.json()["user_id"]
    prof_id = prof_reg.json()["professor_id"]
    client.post(f"/api/admin/users/{prof_uid}/approve", headers=admin_headers)
    prof_tok = client.post("/api/auth/login", json={"email": "life.prof@example.com", "password": "ProfPassword123!"}).json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_tok}"}

    # 3. Student setup
    stu_reg = client.post(
        "/api/auth/register",
        json={"name": "Lifecycle Student", "email": "life.student@example.com", "password": "StudentPassword123!", "role": "student"},
    )
    stu_tok = stu_reg.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_tok}"}

    # 4. Create appointment
    test_date = future_workday()
    create_res = client.post(
        "/api/appointments",
        headers=stu_headers,
        json={
            "student_id": "life-student-id",
            "student_name": "Lifecycle Student",
            "professor_id": prof_id,
            "date": test_date,
            "start_time": "14:00",
            "end_time": "14:30",
            "reason": "Project Review",
        },
    )
    assert create_res.status_code == 201
    appt_id = create_res.json()["appointment_id"]
    assert create_res.json()["status"] == "PENDING_APPROVAL"

    # 5. Professor approves
    appr_res = client.post(f"/api/appointments/{appt_id}/approve", headers=prof_headers)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"

    # 6. Reschedule appointment
    next_date = (date.fromisoformat(test_date) + timedelta(days=1)).isoformat()
    while date.fromisoformat(next_date).weekday() in (5, 6):
        next_date = (date.fromisoformat(next_date) + timedelta(days=1)).isoformat()

    resched_res = client.patch(
        f"/api/appointments/{appt_id}/reschedule",
        headers=prof_headers,
        json={"date": next_date, "start_time": "15:00"},
    )
    assert resched_res.status_code == 200
    assert resched_res.json()["date"] == next_date
    assert resched_res.json()["start_time"] == "15:00"

    # 7. Cancel appointment
    cancel_res = client.post(f"/api/appointments/{appt_id}/cancel", headers=stu_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"


# =============================================================================
# 7. Mocked Outbound Payload Inspection (Gemini & OpenAI)
# =============================================================================

@pytest.mark.asyncio
async def test_mocked_gemini_outbound_payload_has_no_sensitive_data():
    """Verify intercepted Gemini HTTP payload contains only sanitized text."""
    from app.web_mvp import llm, config
    from unittest.mock import MagicMock

    captured_payloads = []

    async def mock_post(self, url, headers=None, json=None):
        captured_payloads.append(json)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Sanitized response"}]}}]
        }
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    with patch.object(config, "GEMINI_API_KEY", "test-gemini-key"), \
         patch.object(config, "LLM_PROVIDER", "gemini"), \
         patch("httpx.AsyncClient.post", new=mock_post):

        sensitive_sys = "System prompt referencing admin@rgmcet.edu.in and password='SecretPassword123!'"
        sensitive_usr = "Student contact 9849348501, token eyJhbGciOiJIUzI1NiJ9.demo.sig and mongodb://usr:pwd@host:27017/db"

        result = await llm.complete(sensitive_sys, sensitive_usr)
        assert result == "Sanitized response"
        assert len(captured_payloads) == 1

        payload = captured_payloads[0]
        sys_text = payload["systemInstruction"]["parts"][0]["text"]
        assert "admin@rgmcet.edu.in" not in sys_text
        assert "[REDACTED_EMAIL]" in sys_text
        assert "SecretPassword123!" not in sys_text

        usr_text = payload["contents"][0]["parts"][0]["text"]
        assert "9849348501" not in usr_text
        assert "[REDACTED_PHONE]" in usr_text
        assert "eyJhbGci" not in usr_text
        assert "[REDACTED_TOKEN]" in usr_text
        assert "mongodb://" not in usr_text
        assert "[REDACTED_DB_CONNECTION]" in usr_text


@pytest.mark.asyncio
async def test_mocked_openai_outbound_payload_has_no_sensitive_data():
    """Verify intercepted OpenAI HTTP payload contains only sanitized text."""
    from app.web_mvp import llm, config
    from unittest.mock import MagicMock

    captured_payloads = []

    async def mock_post(self, url, headers=None, json=None):
        captured_payloads.append(json)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "OpenAI sanitized response"}}]
        }
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    with patch.object(config, "GEMINI_API_KEY", ""), \
         patch.object(config, "OPENAI_API_KEY", "sk-test-key-1234567890abcdef"), \
         patch.object(config, "LLM_PROVIDER", "openai"), \
         patch("httpx.AsyncClient.post", new=mock_post):

        sensitive_sys = "Contact faculty at hod.cseds@rgmcet.edu.in"
        sensitive_usr = "API Key AIzaSyD-1234567890abcdef1234567890 and phone 9849348501"

        result = await llm.complete(sensitive_sys, sensitive_usr)
        assert result == "OpenAI sanitized response"
        assert len(captured_payloads) == 1

        payload = captured_payloads[0]
        sys_msg = payload["messages"][0]["content"]
        assert "hod.cseds@rgmcet.edu.in" not in sys_msg
        assert "[REDACTED_EMAIL]" in sys_msg

        usr_msg = payload["messages"][1]["content"]
        assert "AIzaSyD" not in usr_msg
        assert "[REDACTED_API_KEY]" in usr_msg
        assert "9849348501" not in usr_msg
        assert "[REDACTED_PHONE]" in usr_msg


def test_faculty_lookup_distinguishes_absence_from_nonexistence():
    """Verify faculty lookup clarifies absence in verified records rather than asserting non-existence in reality."""
    res = _deterministic_faculty_lookup("UnknownProfessorName", "CSE (Data Science)")
    assert res is not None
    reply, verified, sources = res
    assert verified is True
    assert "No matching faculty member named UnknownProfessorName was found in the verified Data Science faculty records" in reply
    assert "verified faculty records" in reply

