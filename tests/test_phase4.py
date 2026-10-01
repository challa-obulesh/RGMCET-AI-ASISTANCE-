"""
Phase 4 Automated Test Suite for RGMCET AI Campus Assistant.

Tests:
1. Multi-turn conversation context (professor, date, time preservation across turns)
2. User context isolation (Student A vs Student B context separation)
3. Missing information handling (prompts for professor name, date, time)
4. Ambiguous context handling ("him/her" without professor context)
5. CSE Data Science HOD entity resolution -> Dr. B. Bhaskara Rao
6. Knowledge grounding and zero hallucination on unknown questions
7. Multilingual context handling (English, Telugu, Roman Telugu)
8. LLM fallback / resilience under provider failure
"""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.web_mvp.main import app
from app.web_mvp.services import get_session_context, clear_session_context, answer_chat
from tests.test_web_api import future_workday
from app.web_mvp import store


from app.web_mvp import services

@pytest.fixture
def client(monkeypatch):
    async def no_live_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(services.llm, "complete", no_live_llm)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_store():
    store.reset_demo_data()
    yield


class TestMultiTurnContext:
    def test_multi_turn_appointment_flow(self, client):
        session_id = "session_phase4_1"
        student_id = "STU_P4_001"
        clear_session_context(session_id, student_id)

        # Turn 1: Specify professor only
        resp1 = client.post("/api/chat", json={
            "message": "I want to meet Dr. B. Bhaskara Rao.",
            "session_id": session_id,
            "student_id": student_id,
        })
        assert resp1.status_code == 200
        msg1 = resp1.json()["message"]
        assert "Bhaskara Rao" in msg1

        ctx1 = get_session_context(session_id, student_id)
        assert "Bhaskara" in ctx1.get("professor", "")

        # Turn 2: Provide date and time ("Tomorrow at 2 PM")
        target_date = future_workday()
        formatted_date = date.fromisoformat(target_date).strftime("%d-%m-%Y")
        resp2 = client.post("/api/chat", json={
            "message": f"{formatted_date} at 2 PM",
            "session_id": session_id,
            "student_id": student_id,
        })
        assert resp2.status_code == 200
        msg2 = resp2.json()["message"]
        assert "Bhaskara Rao" in msg2
        assert "PENDING_APPROVAL" in msg2 or "request" in msg2.lower()

    def test_user_context_isolation(self, client):
        session_a = "session_user_a"
        student_a = "STU_USER_A"
        session_b = "session_user_b"
        student_b = "STU_USER_B"

        clear_session_context(session_a, student_a)
        clear_session_context(session_b, student_b)

        # User A sets professor context
        client.post("/api/chat", json={
            "message": "I want to meet Dr. B. Bhaskara Rao.",
            "session_id": session_a,
            "student_id": student_a,
        })

        ctx_a = get_session_context(session_a, student_a)
        ctx_b = get_session_context(session_b, student_b)

        assert "Bhaskara" in ctx_a.get("professor", "")
        assert ctx_b.get("professor") is None

    def test_missing_professor_prompts_for_name(self, client):
        resp = client.post("/api/chat", json={
            "message": "I want to meet a professor.",
            "session_id": "session_missing_prof",
            "student_id": "STU_P4_002",
        })
        assert resp.status_code == 200
        msg = resp.json()["message"]
        assert "Which professor" in msg

    def test_ambiguous_pronoun_prompts_for_clarification(self, client):
        resp = client.post("/api/chat", json={
            "message": f"I want to meet him on {future_workday()} at 2 PM.",
            "session_id": "session_ambiguous",
            "student_id": "STU_P4_003",
        })
        assert resp.status_code == 200
        msg = resp.json()["message"]
        assert "Which professor" in msg or "couldn't find" in msg.lower() or "check the professor name" in msg.lower()


class TestKnowledgeAndEntities:
    def test_cse_ds_hod_resolution(self, client):
        resp = client.post("/api/chat", json={
            "message": "Who is the HOD of CSE Data Science?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Bhaskara Rao" in data["message"]
        assert data["verified"] is True
        assert len(data["sources"]) > 0

    def test_unknown_question_no_hallucination(self, client):
        resp = client.post("/api/chat", json={
            "message": "What is the exact monthly salary of Professor X?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "couldn't find a verified answer" in data["message"].lower() or "verified" in data["message"].lower()
        assert data["verified"] is False

    def test_roman_telugu_library_query(self, client):
        resp = client.post("/api/chat", json={
            "message": "Library ekkada undi?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "Central Library" in data["message"] or "library" in data["message"].lower()
        assert data["verified"] is True


class TestMultilingualAndLLMFallback:
    def test_roman_telugu_multi_turn_appointment(self, client):
        session_id = "session_roman_telugu"
        student_id = "STU_P4_TELUGU"
        clear_session_context(session_id, student_id)

        resp1 = client.post("/api/chat", json={
            "message": "Professor ni kalavali.",
            "session_id": session_id,
            "student_id": student_id,
        })
        assert resp1.status_code == 200
        assert "professor" in resp1.json()["message"].lower()

        target_date = future_workday()
        formatted_date = date.fromisoformat(target_date).strftime("%d-%m-%Y")
        resp2 = client.post("/api/chat", json={
            "message": f"Dr. B. Bhaskara Rao sir ni {formatted_date} 2 PM ki kalavacha?",
            "session_id": session_id,
            "student_id": student_id,
        })
        assert resp2.status_code == 200
        msg2 = resp2.json()["message"]
        assert "Bhaskara Rao" in msg2

    @pytest.mark.asyncio
    async def test_llm_failure_does_not_crash_app(self):
        with patch("app.web_mvp.services.llm.complete", new=AsyncMock(side_effect=Exception("LLM Timeout"))):
            reply, intent, lang, session_id, verified, sources = await answer_chat(
                message="Hello, I need help",
                session_id="session_fallback",
                student_id="STU_FALLBACK",
            )
            assert isinstance(reply, str)
            assert len(reply) > 0
            assert "RGMCET" in reply or "help" in reply.lower() or "Assistant" in reply
