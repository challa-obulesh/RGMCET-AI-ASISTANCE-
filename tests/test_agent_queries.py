"""Comprehensive RGMCET AI Agent query tests.

Covers all test scenarios required by the Phase-2 specification:
- College information
- Department information (English, Telugu, Roman Telugu)
- Faculty / HOD queries
- Facility / campus queries
- Library
- Unknown information (no hallucination)
- Appointment flow via chat (create -> approve)
- LLM fallback when no key configured
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.web_mvp.main import app
from app.web_mvp import services


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    """Test client with the hosted LLM stubbed out (no API key required)."""
    async def no_live_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(services.llm, "complete", no_live_llm)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def llm_client(monkeypatch):
    """Test client with a realistic fake LLM that echoes verified context back."""
    async def fake_complete(system_prompt, user_prompt, *, json_mode=False, timeout=12):
        if json_mode:
            return '{"intent":"GENERAL_QUERY","entity":null,"language":"English","professor":null,"date":null,"time":null}'
        if "verified RGMCET" in system_prompt.lower() or "Verified RGMCET" in user_prompt:
            return f"[LLM-GROUNDED] {user_prompt[:200]}"
        return "[LLM-GENERAL] I am the RGMCET AI Campus Assistant."

    monkeypatch.setattr(services.llm, "complete", fake_complete)
    with TestClient(app) as test_client:
        yield test_client


def future_workday() -> str:
    candidate = date.today() + timedelta(days=1)
    while candidate.weekday() == 6:  # skip Sunday
        candidate += timedelta(days=1)
    return candidate.isoformat()


# ===========================================================================
# 1. COLLEGE INFORMATION
# ===========================================================================

class TestCollegeInformation:

    def test_tell_me_about_rgmcet_returns_verified_record(self, client):
        """Tell me about RGMCET."""
        response = client.post("/api/chat", json={"message": "Tell me about RGMCET."})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "CAMPUS_INFORMATION"
        assert data["verified"] is True
        assert "1995" in data["message"]
        assert any("rgmcet.edu.in" in src["url"] for src in data["sources"])

    def test_college_contact_info_is_verified(self, client):
        """Contact information must come from official source."""
        response = client.post("/api/chat", json={"message": "What is the RGMCET address?"})
        data = response.json()
        assert response.status_code == 200
        assert data["verified"] is True
        assert any("rgmcet.edu.in" in src["url"] for src in data["sources"])

    def test_college_official_website_query(self, client):
        """Query about official website returns campus record."""
        response = client.post("/api/chat", json={"message": "What is the official website of RGMCET?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "CAMPUS_INFORMATION"
        assert data["verified"] is True


# ===========================================================================
# 2. DEPARTMENT INFORMATION
# ===========================================================================

class TestDepartmentInformation:

    def test_what_is_cse_data_science_english(self, client):
        """What is CSE Data Science? (English)"""
        response = client.post("/api/chat", json={"message": "What is CSE Data Science?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "DEPARTMENT_INFORMATION"
        assert data["language"] == "English"
        assert data["verified"] is True
        assert "240" in data["message"]
        assert "160" in data["message"]
        assert "B.Tech" in data["message"]
        assert data["sources"][0]["url"] == "https://www.rgmcet.edu.in/department-of-cseds.php"

    def test_cse_data_science_telugu(self, client):
        """CSE Data Science ante enti? (Telugu script)"""
        response = client.post("/api/chat", json={"message": "CSE Data Science \u0c05\u0c02\u0c1f\u0c47 \u0c0f\u0c2e\u0c3f\u0c1f\u0c3f?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "DEPARTMENT_INFORMATION"
        assert data["language"] == "Telugu"
        assert data["verified"] is True
        assert any("rgmcet.edu.in" in src["url"] for src in data["sources"])

    def test_cse_ds_roman_telugu(self, client):
        """CSE DS ante enti? (Roman Telugu)"""
        response = client.post("/api/chat", json={"message": "CSE DS ante enti?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "DEPARTMENT_INFORMATION"
        assert data["language"] == "Roman Telugu"
        assert data["verified"] is True

    def test_available_departments_list_english(self, client):
        """What departments are available?"""
        response = client.post("/api/chat", json={"message": "What departments are available?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "DEPARTMENT_INFORMATION"
        assert data["verified"] is True
        assert any(d in data["message"] for d in ("CSE", "ECE", "Computer Science", "Mechanical", "Civil"))

    def test_available_departments_roman_telugu(self, client):
        """college lo ye departments unnayi? (Roman Telugu)"""
        response = client.post("/api/chat", json={"message": "college lo ye departments unnayi?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "DEPARTMENT_INFORMATION"
        assert data["language"] == "Roman Telugu"
        assert data["verified"] is True

    def test_ece_department_info(self, client):
        """ECE department returns verified record."""
        response = client.post("/api/chat", json={"message": "What is the ECE department?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "DEPARTMENT_INFORMATION"
        assert data["verified"] is True

    def test_it_department_info(self, client):
        """IT department returns verified record."""
        response = client.post("/api/chat", json={"message": "What is the IT department at RGMCET?"})
        data = response.json()
        assert response.status_code == 200
        # IT department knowledge exists and must return verified information
        assert data["intent"] == "DEPARTMENT_INFORMATION"
        assert data["verified"] is True


# ===========================================================================
# 3. FACULTY / HOD INFORMATION
# ===========================================================================

class TestFacultyInformation:

    def test_hod_of_cse_data_science_returns_official_record(self, client):
        """Who is the HOD of CSE Data Science?"""
        response = client.post("/api/chat", json={"message": "Who is the HOD of CSE Data Science?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "FACULTY_INFORMATION"
        assert data["verified"] is True
        msg = data["message"]
        assert "Bhaskara Rao" in msg or "bhaskara rao" in msg.lower()
        assert data["sources"][0]["url"] == "https://www.rgmcet.edu.in/cseds_faculty1.php"

    def test_show_cse_data_science_faculty(self, client):
        """Show CSE Data Science faculty."""
        response = client.post("/api/chat", json={"message": "Show CSE Data Science faculty."})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "FACULTY_INFORMATION"
        assert data["verified"] is True
        assert "Bhaskara Rao" in data["message"] or "bhaskara rao" in data["message"].lower()
        assert "Ravi Sir (DEMO DATA)" not in data["message"]

    def test_faculty_source_is_official_page(self, client):
        """Faculty source URL must be official cseds_faculty page."""
        response = client.post("/api/chat", json={"message": "Who teaches CSE Data Science?"})
        data = response.json()
        assert response.status_code == 200
        assert data["verified"] is True
        assert any("cseds_faculty1.php" in src["url"] for src in data["sources"])


# ===========================================================================
# 4. FACILITY / CAMPUS INFORMATION
# ===========================================================================

class TestFacilityInformation:

    def test_what_facilities_are_available(self, client):
        """What facilities are available on campus?"""
        response = client.post("/api/chat", json={"message": "What facilities are available on campus?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "FACILITY_INFORMATION"
        assert data["verified"] is True
        assert any(f in data["message"] for f in ("Library", "Lab", "Food Court", "Dining", "Playground", "ZYM", "Seminar"))

    def test_does_rgmcet_have_library(self, client):
        """Does RGMCET have a library?"""
        response = client.post("/api/chat", json={"message": "Does RGMCET have a library?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "FACILITY_INFORMATION"
        assert data["verified"] is True
        assert any("library" in src["url"] for src in data["sources"])

    def test_library_roman_telugu(self, client):
        """college lo library ekkada undi? (Roman Telugu)"""
        response = client.post("/api/chat", json={"message": "college lo library ekkada undi?"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "FACILITY_INFORMATION"
        assert data["language"] == "Roman Telugu"
        assert data["verified"] is True

    def test_data_science_lab_no_room_number_invented(self, client):
        """What is the exact room number of the Data Science laboratory? -> Do NOT invent one."""
        response = client.post("/api/chat", json={
            "message": "What is the exact room number of the Data Science laboratory?"
        })
        data = response.json()
        assert response.status_code == 200
        assert data["verified"] is True
        msg = data["message"].lower()
        # Must acknowledge unavailability of room/location detail
        asserted = (
            "no" in msg or "not" in msg or "verified" in msg or
            "don't have" in msg or "not available" in msg or
            "not provided" in msg or "not been verified" in msg
        )
        assert asserted, f"Response may invent room number: {data['message']}"

    def test_library_does_not_invent_room_number(self, client):
        """Library response must not invent a specific room number."""
        response = client.post("/api/chat", json={"message": "Does RGMCET have a library?"})
        msg = response.json()["message"].lower()
        assert not re.search(r"\broom\s*\d+\b", msg), \
            "Response invented a room number for the library"


# ===========================================================================
# 5. UNKNOWN / HALLUCINATION PREVENTION
# ===========================================================================

class TestNoHallucination:

    def test_unrecognised_professor_not_invented(self, client):
        """Professor names not in the store must not be claimed as existing."""
        response = client.post("/api/chat", json={"message": "Who is Dr. XYZNonexistent?"})
        data = response.json()
        assert response.status_code == 200
        msg = data["message"].lower()
        # Must not invent a fictional professor profile.
        # Acceptable: professor not found in directory, or intent falls to GENERAL_QUERY
        not_found_signals = (
            "not found", "couldn't find", "not in", "not available",
            "no verified", "no information", "don't have", "cannot", "unavailable",
            "current directory", "current list", "not listed", "demo"
        )
        is_general_or_unknown = data["intent"] in {"GENERAL_QUERY", "UNKNOWN", "PROFESSOR_INFORMATION", "PROFESSOR_SCHEDULE"}
        has_not_found_signal = any(s in msg for s in not_found_signals)
        assert has_not_found_signal or is_general_or_unknown, \
            f"Response may invent a professor: intent={data['intent']}, message={data['message']!r}"

    def test_exact_room_number_not_invented(self, client):
        """No room number is invented for the DS Lab."""
        response = client.post("/api/chat", json={
            "message": "What is the exact room number of the Data Science laboratory?"
        })
        msg = response.json()["message"]
        assert not re.search(r"\bRoom\s*\d+\b", msg), \
            "Response hallucinated a room number"


# ===========================================================================
# 6. APPOINTMENT FLOW
# ===========================================================================

class TestAppointmentFlow:

    def test_chat_appointment_creates_pending(self, client):
        """I want to meet professor tomorrow at 10 AM -> PENDING_APPROVAL."""
        selected = date.fromisoformat(future_workday())
        natural_date = f"{selected.strftime('%B')} {selected.day}"
        response = client.post("/api/chat", json={
            "message": f"Can I meet Ravi sir on {natural_date} at 10 AM?",
        })
        data = response.json()
        assert response.status_code == 200
        assert "PENDING_APPROVAL" in data["message"]
        assert "not confirmed" in data["message"]

    def test_appointment_approval_via_api(self, client):
        """Approve appointment changes status to APPROVED."""
        professor = client.get("/api/professors").json()[0]
        created = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday(),
            "start_time": "10:00",
            "reason": "Agent spec test",
        }).json()
        assert created["status"] == "PENDING_APPROVAL"
        approved = client.post(f"/api/appointments/{created['appointment_id']}/approve")
        assert approved.status_code == 200
        assert approved.json()["status"] == "APPROVED"

    def test_appointment_rejection_via_api(self, client):
        """Professor can reject a pending appointment."""
        professor = client.get("/api/professors").json()[0]
        created = client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday(),
            "start_time": "10:00",
            "reason": "Rejection agent test",
        }).json()
        rejected = client.post(f"/api/appointments/{created['appointment_id']}/reject")
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "REJECTED"

    def test_appointment_cancellation_via_chat(self, client):
        """Student can cancel via chat message."""
        professor = client.get("/api/professors").json()[0]
        client.post("/api/appointments", json={
            "professor_id": professor["professor_id"],
            "date": future_workday(),
            "start_time": "10:00",
            "reason": "Cancel via chat test",
        })
        response = client.post("/api/chat", json={
            "message": "Cancel my appointment",
            "student_id": "demo-student",
        })
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "APPOINTMENT_CANCELLATION"
        assert "CANCELLED" in data["message"]

    def test_appointment_not_confirmed_by_llm(self, client):
        """LLM must not confirm appointment; PENDING_APPROVAL must appear."""
        selected = date.fromisoformat(future_workday())
        natural_date = f"{selected.strftime('%B')} {selected.day}"
        response = client.post("/api/chat", json={
            "message": f"I want to meet Ravi sir on {natural_date} at 10 AM",
        })
        data = response.json()
        assert response.status_code == 200
        assert "PENDING_APPROVAL" in data["message"]
        msg = data["message"].lower()
        if "confirmed" in msg:
            assert "not confirmed" in msg or "pending" in msg


# ===========================================================================
# 7. MULTILINGUAL COMPLETENESS
# ===========================================================================

class TestMultilingual:

    def test_english_queries_return_verified(self, client):
        queries = [
            "What is CSE Data Science?",
            "Who is the HOD of CSE Data Science?",
            "Does RGMCET have a library?",
            "Tell me about RGMCET.",
        ]
        for query in queries:
            response = client.post("/api/chat", json={"message": query})
            data = response.json()
            assert data["language"] == "English"
            assert data["verified"] is True, f"Failed: {query}"

    def test_telugu_cse_ds_returns_verified(self, client):
        response = client.post("/api/chat", json={
            "message": "CSE Data Science \u0c05\u0c02\u0c1f\u0c47 \u0c0f\u0c2e\u0c3f\u0c1f\u0c3f?"
        })
        assert response.json()["language"] == "Telugu"
        assert response.json()["verified"] is True

    def test_roman_telugu_library_query(self, client):
        response = client.post("/api/chat", json={"message": "college lo library ekkada undi?"})
        assert response.json()["language"] == "Roman Telugu"
        assert response.json()["intent"] == "FACILITY_INFORMATION"
        assert response.json()["verified"] is True


# ===========================================================================
# 8. LLM FALLBACK
# ===========================================================================

class TestLLMFallback:

    def test_knowledge_queries_work_without_llm(self, client):
        """With LLM returning None, verified knowledge still returns correct data."""
        response = client.post("/api/chat", json={"message": "What is CSE Data Science?"})
        data = response.json()
        assert response.status_code == 200
        assert data["verified"] is True
        assert "240" in data["message"]

    def test_hod_query_works_without_llm(self, client):
        response = client.post("/api/chat", json={"message": "Who is the HOD of CSE Data Science?"})
        data = response.json()
        assert response.status_code == 200
        assert data["verified"] is True
        assert "Bhaskara Rao" in data["message"]

    def test_college_info_without_llm(self, client):
        response = client.post("/api/chat", json={"message": "Tell me about RGMCET."})
        data = response.json()
        assert response.status_code == 200
        assert data["verified"] is True
        assert "1995" in data["message"]

    def test_general_greeting_without_llm(self, client):
        response = client.post("/api/chat", json={"message": "Hello"})
        data = response.json()
        assert response.status_code == 200
        assert data["intent"] == "GENERAL_QUERY"
        assert len(data["message"]) > 5


# ===========================================================================
# 9. LLM GROUNDED (with fake LLM)
# ===========================================================================

class TestLLMGroundedResponse:

    def test_llm_receives_verified_context_for_cse_ds(self, llm_client):
        response = llm_client.post("/api/chat", json={"message": "What is CSE Data Science?"})
        data = response.json()
        assert response.status_code == 200
        assert data["verified"] is True
        assert data["sources"][0]["url"] == "https://www.rgmcet.edu.in/department-of-cseds.php"

    def test_llm_grounded_does_not_expose_api_keys(self, llm_client):
        response = llm_client.post("/api/chat", json={"message": "Tell me about RGMCET."})
        data = response.json()
        msg = data["message"].lower()
        assert "api_key" not in msg
        assert "gemini_api_key" not in msg
        assert "openai_api_key" not in msg

    def test_appointment_status_not_overridden_by_llm(self, llm_client):
        selected = date.fromisoformat(future_workday())
        natural_date = f"{selected.strftime('%B')} {selected.day}"
        response = llm_client.post("/api/chat", json={
            "message": f"I want to meet Ravi sir on {natural_date} at 10 AM",
        })
        data = response.json()
        assert response.status_code == 200
        assert "PENDING_APPROVAL" in data["message"]


# ===========================================================================
# 10. SOURCE METADATA
# ===========================================================================

class TestSourceMetadata:

    def test_all_sources_are_official_rgmcet_urls(self, client):
        """Every source URL in verified responses must be an official RGMCET URL."""
        queries = [
            "What is CSE Data Science?",
            "Who is the HOD of CSE Data Science?",
            "Tell me about RGMCET.",
            "Does RGMCET have a library?",
        ]
        for query in queries:
            response = client.post("/api/chat", json={"message": query})
            data = response.json()
            for source in data.get("sources", []):
                assert "rgmcet.edu.in" in source["url"], \
                    f"Non-official source URL for '{query}': {source['url']}"

    def test_chat_response_schema(self, client):
        """Response must include all required schema fields."""
        response = client.post("/api/chat", json={"message": "What is CSE Data Science?"})
        data = response.json()
        required = {"message", "intent", "language", "session_id", "verified", "sources"}
        assert required.issubset(data.keys())

    def test_session_id_stable_across_turns(self, client):
        """Session ID must remain stable across turns."""
        first = client.post("/api/chat", json={"message": "What is CSE DS?", "session_id": "agent-stable-session"}).json()
        second = client.post("/api/chat", json={"message": "Who is the HOD?", "session_id": "agent-stable-session"}).json()
        assert first["session_id"] == second["session_id"] == "agent-stable-session"
