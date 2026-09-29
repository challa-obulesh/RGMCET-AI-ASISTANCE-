import pytest

from app.web_intents import detect_web_intent
from app.web_mvp import services


def test_library_queries_in_english_roman_telugu_and_telugu():
    assert detect_web_intent("Where is the library?").intent == "FACILITY_INFORMATION"
    roman = detect_web_intent("Library ekkada undi?")
    assert roman.intent == "FACILITY_INFORMATION"
    assert roman.language == "Roman Telugu"
    telugu = detect_web_intent("లైబ్రరీ ఎక్కడ ఉంది?")
    assert telugu.intent == "FACILITY_INFORMATION"
    assert telugu.language == "Telugu"


def test_professor_schedule_and_appointment_extract_entities():
    schedule = detect_web_intent("Ravi sir schedule enti?")
    assert schedule.intent == "PROFESSOR_SCHEDULE"
    assert schedule.professor.lower() == "ravi sir"

    request = detect_web_intent("Can I meet Ravi sir tomorrow at 2 PM?")
    assert request.intent == "PROFESSOR_APPOINTMENT"
    assert request.professor.lower() == "ravi sir"
    assert request.time == "14:00"
    named_date = detect_web_intent("Can I meet Ravi sir on October 1st at 2 PM?")
    assert named_date.date.endswith("-10-01")


def test_blank_and_unknown_query_intents():
    assert detect_web_intent("").intent == "UNKNOWN"
    assert detect_web_intent("Tell me a joke").intent == "GENERAL_QUERY"
    assert detect_web_intent("Show my appointments").intent == "APPOINTMENT_STATUS"
    incomplete = detect_web_intent("Ravi sir ni kalavacha?")
    assert incomplete.intent == "PROFESSOR_APPOINTMENT"
    assert incomplete.date is None and incomplete.time is None


def test_professor_schedule_question_does_not_capture_question_prefix():
    parsed = detect_web_intent("What is Ravi sir's schedule?")
    assert parsed.intent == "PROFESSOR_SCHEDULE"
    assert parsed.professor.lower() == "ravi sir"


def test_department_name_is_a_department_intent():
    assert detect_web_intent("Tell me about CSE").intent == "DEPARTMENT_INFORMATION"


def test_current_phase_one_enquiry_and_bare_professor_prompts():
    english_departments = detect_web_intent("What departments are available?")
    assert english_departments.intent == "DEPARTMENT_INFORMATION"

    telugu_departments = detect_web_intent("కళాశాలలో ఏ విభాగాలు ఉన్నాయి?")
    assert telugu_departments.intent == "DEPARTMENT_INFORMATION"
    assert telugu_departments.language == "Telugu"

    roman_departments = detect_web_intent("college lo ye departments unnayi?")
    assert roman_departments.intent == "DEPARTMENT_INFORMATION"
    assert roman_departments.language == "Roman Telugu"

    for prompt in ("Show Ravi's schedule", "Is Ravi available?", "Show Ravi's available slots"):
        parsed = detect_web_intent(prompt)
        assert parsed.intent == "PROFESSOR_SCHEDULE"
        assert parsed.professor == "Ravi"


def test_data_science_laboratory_is_unknown_facility_not_a_claim():
    parsed = detect_web_intent("Where is the Data Science Laboratory?")
    assert parsed.intent == "FACILITY_INFORMATION"
    assert parsed.entity == "Data Science Laboratory"

def test_cse_data_science_and_faculty_intents_extract_department():
    department = detect_web_intent("What is CSE Data Science?")
    assert department.intent == "DEPARTMENT_INFORMATION"
    assert department.entity == "Computer Science and Engineering (Data Science)"

    hod = detect_web_intent("Who is the HOD of CSE Data Science?")
    assert hod.intent == "FACULTY_INFORMATION"
    assert hod.entity == "Computer Science and Engineering (Data Science)"

    faculty = detect_web_intent("Show CSE DS faculty.")
    assert faculty.intent == "FACULTY_INFORMATION"
    assert faculty.entity == "Computer Science and Engineering (Data Science)"

    roman = detect_web_intent("CSE DS ante enti?")
    assert roman.intent == "DEPARTMENT_INFORMATION"
    assert roman.language == "Roman Telugu"


def test_appointment_cancellation_intent():
    parsed = detect_web_intent("Cancel my appointment")
    assert parsed.intent == "APPOINTMENT_CANCELLATION"


@pytest.mark.parametrize(
    ("message", "intent", "language", "professor", "entity", "date", "time"),
    [
        ("Where is the library?", "FACILITY_INFORMATION", "English", None, "Central Library", None, None),
        ("Library ekkada undi?", "FACILITY_INFORMATION", "Roman Telugu", None, "Central Library", None, None),
        ("లైబ్రరీ ఎక్కడ ఉంది?", "FACILITY_INFORMATION", "Telugu", None, "Central Library", None, None),
        ("Ravi sir details", "PROFESSOR_INFORMATION", "English", "Ravi sir", None, None, None),
        ("Ravi sir schedule enti?", "PROFESSOR_SCHEDULE", "Roman Telugu", "Ravi sir", None, None, None),
        ("Ravi sir available unnara?", "PROFESSOR_SCHEDULE", "Roman Telugu", "Ravi sir", None, None, None),
        ("Can I meet Ravi sir?", "PROFESSOR_APPOINTMENT", "English", "Ravi sir", None, None, None),
        ("Ravi sir ni October 1st 2 PM ki kalavacha?", "PROFESSOR_APPOINTMENT", "Roman Telugu", "Ravi sir", None, "2026-10-01", "14:00"),
        ("College timings enti?", "CAMPUS_INFORMATION", "Roman Telugu", None, None, None, None),
        ("Hello", "GENERAL_QUERY", "English", None, None, None, None),
        ("What is Ravi sir's schedule?", "PROFESSOR_SCHEDULE", "English", "Ravi sir", None, None, None),
        ("Ravi sir ni repu 2 PM ki kalavacha?", "PROFESSOR_APPOINTMENT", "Roman Telugu", "Ravi sir", None, None, "14:00"),
        ("Tell me about CSE", "DEPARTMENT_INFORMATION", "English", None, "Computer Science and Engineering", None, None),
        ("What facilities are available?", "FACILITY_INFORMATION", "English", None, None, None, None),
    ],
)
def test_required_prompt_matrix(message, intent, language, professor, entity, date, time):
    parsed = detect_web_intent(message)
    assert parsed.intent == intent
    assert parsed.language == language
    assert parsed.professor == professor
    assert parsed.entity == entity
    if date is not None:
        assert parsed.date.endswith(date[-6:])
    if time is not None:
        assert parsed.time == time


@pytest.mark.asyncio
async def test_hosted_classifier_cannot_override_confident_local_telugu_intent(monkeypatch):
    async def fake_complete(*args, **kwargs):
        return '{"intent":"GENERAL_QUERY","language":"English"}'

    monkeypatch.setattr(services.llm, "complete", fake_complete)
    parsed = await services.classify("లైబ్రరీ ఎక్కడ ఉంది?")
    assert parsed.intent == "FACILITY_INFORMATION"
    assert parsed.language == "Telugu"


@pytest.mark.asyncio
async def test_classifier_falls_back_to_local_parser_when_hosted_llm_fails(monkeypatch):
    async def failed_complete(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(services.llm, "complete", failed_complete)
    parsed = await services.classify("Ravi sir schedule enti?")
    assert parsed.intent == "PROFESSOR_SCHEDULE"
    assert parsed.professor == "Ravi sir"
    assert parsed.language == "Roman Telugu"