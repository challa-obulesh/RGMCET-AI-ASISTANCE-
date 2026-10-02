import asyncio
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.web_mvp.main import app
from app.web_mvp import services
from app.web_mvp.schemas import AppointmentRequest
from app.web_mvp.services import create_appointment


@pytest.fixture
def client(monkeypatch):
    async def no_live_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(services.llm, "complete", no_live_llm)
    with TestClient(app) as test_client:
        yield test_client


def future_workday():
    candidate = date.today() + timedelta(days=1)
    while candidate.weekday() == 6:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def test_chat_returns_verified_library_info_and_intent(client):
    response = client.post("/api/chat", json={"message": "Where is the Central Library?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "FACILITY_INFORMATION"
    assert data["session_id"]
    # Knowledge is populated: should return verified record, not invented location
    assert data["verified"] is True
    # Must not invent a specific room number / building that isn't on the official site
    assert "room" not in data["message"].casefold() or "room number" in data["message"].casefold()


def test_telugu_chat_returns_library_in_telugu(client):
    response = client.post("/api/chat", json={"message": "లైబ్రరీ ఎక్కడ ఉంది?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "FACILITY_INFORMATION"
    assert data["language"] == "Telugu"
    # Knowledge is populated – response should be verified
    assert data["verified"] is True


@pytest.mark.parametrize(
    ("message", "intent", "language"),
    [
        ("What departments are available?", "DEPARTMENT_INFORMATION", "English"),
        ("కళాశాలలో ఏ విభాగాలు ఉన్నాయి?", "DEPARTMENT_INFORMATION", "Telugu"),
        ("college lo ye departments unnayi?", "DEPARTMENT_INFORMATION", "Roman Telugu"),
        ("Tell me about RGMCET.", "CAMPUS_INFORMATION", "English"),
        ("Where is the Data Science Laboratory?", "FACILITY_INFORMATION", "English"),
    ],
)
def test_verified_enquiries_return_real_rgmcet_facts(client, message, intent, language):
    """With knowledge populated, responses must be verified and not invent facts."""
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == intent
    assert data["language"] == language
    # Knowledge base is loaded so all factual intents should return verified=True
    assert data["verified"] is True
    # Must have official source links
    assert len(data["sources"]) > 0
    # Must include rgmcet.edu.in source URLs
    assert all("rgmcet.edu.in" in src["url"] for src in data["sources"])


def test_department_list_responses_are_verified_and_name_departments(client):
    """With knowledge loaded, department list queries return real department names verified=True."""
    roman = client.post("/api/chat", json={"message": "college lo ye departments unnayi?"}).json()
    telugu = client.post("/api/chat", json={"message": "కళాశాలలో ఏ విభాగాలు ఉన్నాయి?"}).json()
    # Both should now be verified with actual department names
    assert roman["verified"] is True
    assert telugu["verified"] is True
    # Should mention at least one known department in the response
    assert any(dept in roman["message"] for dept in ("CSE", "Computer Science", "ECE", "Mechanical", "Civil", "IT", "MBA"))
    assert any(dept in telugu["message"] for dept in ("CSE", "Computer Science", "ECE", "Mechanical", "Civil", "IT", "MBA", "విభాగ"))


def test_chat_returns_verified_cse_data_science_record_and_source(client):
    response = client.post("/api/chat", json={"message": "What is CSE Data Science?"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["intent"] == "DEPARTMENT_INFORMATION"
    assert payload["verified"] is True
    assert payload["sources"][0]["url"] == "https://www.rgmcet.edu.in/department-of-cseds.php"
    assert "B.Tech" in payload["message"]
    assert "240" in payload["message"]
    assert "160" in payload["message"]
    assert "8 semesters" in payload["message"]


def test_hod_query_uses_official_faculty_and_faculty_list_is_separate_from_demo(client):
    hod = client.post("/api/chat", json={"message": "Who is the HOD of CSE Data Science?"}).json()
    assert hod["intent"] == "FACULTY_INFORMATION"
    assert hod["verified"] is True
    assert "Dr. B.Bhaskara Rao" in hod["message"]
    assert hod["sources"][0]["url"] == "https://www.rgmcet.edu.in/cseds_faculty1.php"

    faculty = client.post("/api/chat", json={"message": "Show CSE Data Science faculty."}).json()
    assert faculty["verified"] is True
    assert "Dr. B.Bhaskara Rao" in faculty["message"]
    assert "Ravi Sir (DEMO DATA)" not in faculty["message"]


def test_facility_answers_keep_sources_and_do_not_invent_room_locations(client):
    library = client.post("/api/chat", json={"message": "Does RGMCET have a library?"}).json()
    assert library["verified"] is True
    assert any(source["url"] == "https://www.rgmcet.edu.in/library" for source in library["sources"])

    room = client.post("/api/chat", json={"message": "What is the exact room number of the Data Science laboratory?"}).json()
    assert room["verified"] is True
    assert "verified building/location detail" in room["message"]
    assert "room number" in room["message"]


def test_no_llm_key_uses_deterministic_grounded_fallback(client):
    response = client.post("/api/chat", json={"message": "Tell me about RGMCET."})
    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert response.json()["sources"]
    assert "1995" in response.json()["message"]


def test_hosted_answer_generation_receives_only_retrieved_verified_context(client, monkeypatch):
    calls = []

    async def fake_complete(system_prompt, user_prompt, *, json_mode=False, timeout=12):
        calls.append((system_prompt, user_prompt, json_mode))
        if json_mode:
            return '{"intent":"DEPARTMENT_INFORMATION","entity":"CSE Data Science","language":"English"}'
        return "CSE Data Science is a four-year B.Tech program with 240 intake, 160 credits and eight semesters."

    monkeypatch.setattr(services.llm, "complete", fake_complete)
    response = client.post("/api/chat", json={"message": "What is CSE Data Science?"})
    payload = response.json()
    assert payload["verified"] is True
    assert payload["sources"][0]["url"] == "https://www.rgmcet.edu.in/department-of-cseds.php"
    assert "240 intake" in payload["message"]
    assert len(calls) == 2
    assert "verified RGMCET records" in calls[1][0]
    assert '"verified": true' in calls[1][1]


def test_availability_chat_returns_verified_demo_slots(client, monkeypatch):
    from datetime import datetime as RealDateTime
    from zoneinfo import ZoneInfo

    import app.web_mvp.services as services

    class FrozenDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 30, 9, 0, tzinfo=tz or ZoneInfo("Asia/Kolkata"))

    monkeypatch.setattr(services, "datetime", FrozenDateTime)
    response = client.post("/api/chat", json={"message": "Is Ravi available?"})
    assert response.status_code == 200
    assert response.json()["intent"] == "PROFESSOR_SCHEDULE"
    assert "available demo slots" in response.json()["message"].casefold()
    assert "10:00-10:30" in response.json()["message"]


def test_whitespace_only_message_is_rejected(client):
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 422


def test_long_message_and_unknown_facility_are_handled_safely(client):
    long_message = client.post("/api/chat", json={"message": "x" * 4001})
    assert long_message.status_code == 422
    unknown = client.post("/api/chat", json={"message": "Where is the hostel?"})
    assert unknown.status_code == 200
    assert "verified" in unknown.json()["message"].lower()
    laboratory = client.post("/api/chat", json={"message": "Where is the Data Science Laboratory?"})
    assert laboratory.status_code == 200
    assert "Central Library" not in laboratory.json()["message"]
    assert "verified" in laboratory.json()["message"].lower()


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_malformed_json_and_cors(client, origin):
    malformed = client.post("/api/chat", content="{not json", headers={"Content-Type": "application/json"})
    assert malformed.status_code == 422
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_demo_professor_search_and_schedule(client):
    response = client.get("/api/professors/search", params={"q": "Ravi"})
    assert response.status_code == 200
    professor = response.json()[0]
    assert professor["is_demo"] is True
    schedule = client.get(f"/api/professors/{professor['professor_id']}/schedule")
    assert schedule.status_code == 200
    assert all(item["is_demo"] is True for item in schedule.json())


def test_professor_alias_details_and_availability(client):
    target_date = future_workday()
    target_day = date.fromisoformat(target_date).strftime("%A")
    response = client.get("/api/professors/search", params={"q": "Ravi sir"})
    professor = response.json()[0]
    detail = client.get(f"/api/professors/{professor['professor_id']}").json()
    assert detail["department"] and detail["designation"] and detail["office"] and detail["room"]
    assert "subjects" in detail and detail["is_demo"] is True
    schedule = client.get(f"/api/professors/{professor['professor_id']}/schedule", params={"on_date": target_date}).json()
    assert schedule[0]["day"] == target_day
    assert schedule[0]["start_time"] == "10:00"
    assert schedule[0]["end_time"] == "16:00"
    available = client.get(f"/api/professors/{professor['professor_id']}/availability", params={"date": target_date})
    assert available.status_code == 200
    assert "10:00" in [slot["start_time"] for slot in available.json()]
    assert "16:00" not in [slot["start_time"] for slot in available.json()]
    assert client.get("/api/professors/not-real/availability", params={"date": target_date}).status_code == 404


def test_appointment_conflict_and_approval_flow(client):
    professor = client.get("/api/professors").json()[0]
    payload = {
        "professor_id": professor["professor_id"],
        "date": future_workday(),
        "start_time": "10:00",
        "reason": "Project discussion",
    }
    created = client.post("/api/appointments", json=payload)
    assert created.status_code == 201
    appointment_id = created.json()["appointment_id"]
    assert created.json()["status"] == "PENDING_APPROVAL"
    assert client.post("/api/appointments", json=payload).status_code == 409

    approved = client.post(f"/api/appointments/{appointment_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert len(client.get("/api/students/demo-student/appointments").json()) == 1


def test_unknown_professor_is_not_invented(client):
    response = client.post("/api/chat", json={"message": "Ravi Sir schedule enti?"})
    assert response.status_code == 200
    assert "demo" in response.json()["message"].lower()
    assert response.json()["intent"] == "PROFESSOR_SCHEDULE"


def test_unknown_professor_detail_returns_404(client):
    response = client.get("/api/professors/NOT-A-REAL-PROFESSOR")
    assert response.status_code == 404


def test_complete_chat_appointment_request_creates_pending_record(client):
    selected = date.fromisoformat(future_workday())
    natural_date = f"{selected.strftime('%B')} {selected.day}"
    response = client.post("/api/chat", json={
        "message": f"Can I meet Ravi sir on {natural_date} at 10 AM?",
    })
    assert response.status_code == 200
    assert "Would you like me to request" in response.json()["message"]
    
    session_id = response.json()["session_id"]
    response2 = client.post("/api/chat", json={
        "message": "Yes",
        "session_id": session_id
    })
    
    assert response2.status_code == 200
    assert "PENDING_APPROVAL" in response2.json()["message"]
    assert "not confirmed" in response2.json()["message"]
    pending = client.get("/api/appointments", params={"status": "PENDING_APPROVAL"})
    assert len(pending.json()) == 1


def test_chat_cancellation_uses_appointment_service_and_updates_status(client):
    professor = client.get("/api/professors").json()[0]
    created = client.post("/api/appointments", json={
        "professor_id": professor["professor_id"],
        "date": future_workday(),
        "start_time": "10:00",
        "reason": "Cancel through chat",
    }).json()
    response = client.post("/api/chat", json={
        "message": "Cancel my appointment",
        "student_id": "demo-student",
    })
    assert response.status_code == 200
    assert response.json()["intent"] == "APPOINTMENT_CANCELLATION"
    assert "CANCELLED" in response.json()["message"]
    assert client.get(f"/api/appointments/{created['appointment_id']}").json()["status"] == "CANCELLED"


def test_pending_appointment_can_be_rejected(client):
    professor = client.get("/api/professors").json()[0]
    payload = {
        "professor_id": professor["professor_id"],
        "date": future_workday(),
        "start_time": "10:00",
        "reason": "Course question",
    }
    created = client.post("/api/appointments", json=payload).json()
    rejected = client.post(f"/api/appointments/{created['appointment_id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    rebooked = client.post("/api/appointments", json=payload)
    assert rebooked.status_code == 201
    assert rebooked.json()["status"] == "PENDING_APPROVAL"


def test_past_appointment_date_is_rejected(client):
    professor = client.get("/api/professors").json()[0]
    past_slot = (date.today() - timedelta(days=1)).isoformat()
    response = client.post("/api/appointments", json={
        "professor_id": professor["professor_id"],
        "date": past_slot,
        "start_time": "10:00",
        "reason": "Past appointment",
    })
    assert response.status_code == 422


def test_same_day_past_appointment_time_and_availability_are_rejected(client, monkeypatch):
    from datetime import datetime as RealDateTime

    import app.web_mvp.services as services

    class FrozenDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 1, 14, 45, tzinfo=tz)

    monkeypatch.setattr(services, "datetime", FrozenDateTime)
    past_slot = client.post("/api/appointments", json={
        "professor_id": "PROF-DEMO-001",
        "date": "2026-10-01",
        "start_time": "14:30",
        "reason": "Past today slot",
    })
    assert past_slot.status_code == 422
    available = client.get("/api/professors/PROF-DEMO-001/availability", params={"date": "2026-10-01"})
    assert available.status_code == 200
    starts = [item["start_time"] for item in available.json()]
    assert "14:00" not in starts
    assert "15:00" in starts


def test_invalid_time_and_impossible_date_are_rejected(client):
    professor = client.get("/api/professors").json()[0]
    base_payload = {
        "professor_id": professor["professor_id"],
        "reason": "Invalid value test",
    }
    bad_time = client.post("/api/appointments", json={
        **base_payload,
        "date": future_workday(),
        "start_time": "99:00",
    })
    assert bad_time.status_code == 422
    bad_date = client.post("/api/appointments", json={
        **base_payload,
        "date": "2026-02-31",
        "start_time": "10:00",
    })
    assert bad_date.status_code == 422
    missing_reason = client.post("/api/appointments", json={
        "professor_id": professor["professor_id"],
        "date": future_workday(),
        "start_time": "10:00",
    })
    assert missing_reason.status_code == 422


def test_invalid_professor_and_out_of_schedule_appointment_are_rejected(client):
    invalid_professor = client.post("/api/appointments", json={
        "professor_id": "NOT-REAL",
        "date": future_workday(),
        "start_time": "10:00",
        "reason": "Unknown professor test",
    })
    assert invalid_professor.status_code == 404
    outside_schedule = client.post("/api/appointments", json={
        "professor_id": "PROF-DEMO-001",
        "date": future_workday(),
        "start_time": "16:00",
        "reason": "Outside office hours",
    })
    assert outside_schedule.status_code == 409


def test_chat_session_appends_turns_and_separates_new_sessions(client):
    first = client.post("/api/chat", json={"message": "Ravi sir details", "session_id": "qa-session-one"}).json()
    second = client.post("/api/chat", json={"message": "What is his schedule?", "session_id": "qa-session-one"}).json()
    fresh = client.post("/api/chat", json={"message": "Hello", "session_id": "qa-session-two"}).json()
    assert first["session_id"] == second["session_id"] == "qa-session-one"
    assert fresh["session_id"] == "qa-session-two"
    from app.web_mvp import store
    one = store._memory["chat_sessions"]
    first_session = next(item for item in one if item["session_id"] == "qa-session-one")
    second_session = next(item for item in one if item["session_id"] == "qa-session-two")
    assert len(first_session["turns"]) == 2
    assert len(second_session["turns"]) == 1


def test_appointment_state_machine_and_student_status(client):
    payload = {
        "professor_id": "PROF-DEMO-001",
        "date": future_workday(),
        "start_time": "10:00",
        "reason": "State machine test",
    }
    created = client.post("/api/appointments", json=payload).json()
    appointment_id = created["appointment_id"]
    assert created["status"] == "PENDING_APPROVAL"
    assert client.post(f"/api/appointments/{appointment_id}/approve").json()["status"] == "APPROVED"
    assert client.post(f"/api/appointments/{appointment_id}/reject").status_code == 409
    assert client.post(f"/api/appointments/{appointment_id}/cancel").json()["status"] == "CANCELLED"
    assert client.post(f"/api/appointments/{appointment_id}/approve").status_code == 409
    detail = client.get(f"/api/appointments/{appointment_id}").json()
    student_items = client.get("/api/students/demo-student/appointments").json()
    assert detail["status"] == "CANCELLED"
    assert next(item for item in student_items if item["appointment_id"] == appointment_id)["status"] == "CANCELLED"
    rebooked = client.post("/api/appointments", json=payload)
    assert rebooked.status_code == 201


@pytest.mark.asyncio
async def test_concurrent_same_slot_requests_only_create_one_appointment(client):
    request = AppointmentRequest(
        professor_id="PROF-DEMO-001",
        date=future_workday(),
        start_time="10:00",
        reason="Concurrent reservation test",
    )
    results = await asyncio.gather(
        create_appointment(request),
        create_appointment(request),
        return_exceptions=True,
    )
    created = [result for result in results if not isinstance(result, BaseException)]
    failures = [result for result in results if isinstance(result, HTTPException)]
    assert len(created) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 409