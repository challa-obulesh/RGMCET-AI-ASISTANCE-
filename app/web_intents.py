"""Structured intent detection for the web MVP.

This deterministic first-pass parser keeps the web flow usable without an LLM.
An LLM provider can later enrich these fields, while services remain the
authority for all facts and actions.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel


Intent = Literal[
    "CAMPUS_INFORMATION",
    "DEPARTMENT_INFORMATION",
    "FACULTY_INFORMATION",
    "FACILITY_INFORMATION",
    "PROFESSOR_INFORMATION",
    "PROFESSOR_SCHEDULE",
    "PROFESSOR_APPOINTMENT",
    "APPOINTMENT_CANCELLATION",
    "APPOINTMENT_STATUS",
    "GENERAL_QUERY",
    "UNKNOWN",
]


class ParsedIntent(BaseModel):
    intent: Intent
    entity: str | None = None
    professor: str | None = None
    date: str | None = None
    time: str | None = None
    language: Literal["English", "Telugu", "Roman Telugu"] = "English"


def _department_entity(text: str) -> str | None:
    lowered = text.casefold()
    department_names = (
        (r"\b(cse\s*(?:\(\s*)?data\s*science|cse\s*ds|computer\s+science\s*(?:and|&)\s+engineering\s*\(\s*data\s+science\s*\))", "Computer Science and Engineering (Data Science)"),
        (r"\b(cse\s*(?:ai\s*(?:and|&)\s*ml|aiml)|artificial\s+intelligence\s+(?:and|&)\s+machine\s+learning)\b", "Computer Science and Engineering (Artificial Intelligence and Machine Learning)"),
        (r"\b(cse\s*(?:cyber\s*security)|cyber\s*security)\b", "Computer Science and Engineering (Cyber Security)"),
        (r"\b(cse\s*(?:and|&)\s*(?:business\s+)?systems|csbs|business\s+systems)\b", "Computer Science and Engineering and Business Systems"),
    )
    for pattern, canonical_name in department_names:
        if re.search(pattern, lowered, re.I):
            return canonical_name
    simple_names = (
        (r"\bcomputer\s+science\s+(?:and|&)\s+engineering\b|\bcse\b", "Computer Science and Engineering"),
        (r"\binformation\s+technology\b|\bit\s+department\b", "Information Technology"),
        (r"\belectronics\s+(?:and|&)\s+communication(?:s)?\s+engineering\b|\bece\b", "Electronics and Communication Engineering"),
        (r"\belectrical\s+(?:and|&)\s+electronics\s+engineering\b|\beee\b", "Electrical and Electronics Engineering"),
        (r"\bcivil\s+engineering\b|\bce\b", "Civil Engineering"),
        (r"\bmechanical\s+engineering\b|\bme\b", "Mechanical Engineering"),
        (r"\bmba\b|\bmanagement\s+studies\b", "Master of Business Administration"),
        (r"\bmca\b|\bmaster\s+of\s+computer\s+applications\b", "Master of Computer Applications"),
    )
    for pattern, canonical_name in simple_names:
        if re.search(pattern, lowered, re.I):
            return canonical_name
    return None


def _language(text: str) -> Literal["English", "Telugu", "Roman Telugu"]:
    if re.search(r"[\u0c00-\u0c7f]", text):
        return "Telugu"
    if re.search(r"\b(ekkada|enti|unnara|kalavacha|repu|ivala|naaku|undi|unnayi|unnay|gurinchi)\b", text, re.I):
        return "Roman Telugu"
    if re.search(r"\b(?:college|campus)\s+lo\b", text, re.I):
        return "Roman Telugu"
    return "English"


def _date(text: str) -> str | None:
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    normalized = text.lower()
    if any(term in normalized for term in ("tomorrow", "repu", "రేపు")):
        return (today + timedelta(days=1)).isoformat()
    if any(term in normalized for term in ("today", "ivala", "eeroju", "ఈరోజు")):
        return today.isoformat()
    weekdays = {
        "monday": 0, "mon": 0, "somavaram": 0, "సోమవారం": 0,
        "tuesday": 1, "tue": 1, "mangalavaram": 1, "మంగళవారం": 1,
        "wednesday": 2, "wed": 2, "budhavaram": 2, "బుధవారం": 2,
        "thursday": 3, "thu": 3, "guruvaram": 3, "గురువారం": 3,
        "friday": 4, "fri": 4, "shukravaram": 4, "శుక్రవారం": 4,
        "saturday": 5, "sat": 5, "shanivaram": 5, "శనివారం": 5,
        "sunday": 6, "sun": 6, "adivaram": 6, "ఆదివారం": 6,
    }
    for day_name, target_weekday in weekdays.items():
        if re.search(r"\b" + day_name + r"\b", normalized, re.I):
            days_ahead = (target_weekday - today.weekday()) % 7
            if days_ahead == 0 and "next" in normalized:
                days_ahead = 7
            elif days_ahead == 0:
                return today.isoformat()
            return (today + timedelta(days=days_ahead)).isoformat()
    named_date = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b",
        normalized,
        re.I,
    )
    if named_date:
        try:
            month = datetime.strptime(named_date.group(1)[:3].title(), "%b").month
            day = int(named_date.group(2))
            year = int(named_date.group(3)) if named_date.group(3) else today.year
            parsed = date(year, month, day)
            if not named_date.group(3) and parsed < today:
                parsed = date(year + 1, month, day)
            return parsed.isoformat()
        except ValueError:
            return None
    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", normalized)
    if not match:
        return None
    day, month = int(match.group(1)), int(match.group(2))
    year = int(match.group(3)) if match.group(3) else today.year
    if year < 100:
        year += 2000
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _time(text: str) -> str | None:
    normalized = text.lower()
    # Check 24-hour format e.g. 14:00, 09:30, 14:00 hrs
    match_24 = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", normalized)
    if match_24 and not re.search(r"(am|pm)", normalized):
        h, m = int(match_24.group(1)), int(match_24.group(2))
        return f"{h:02d}:{m:02d}"
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", normalized)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2) or 0)
        meridiem = match.group(3).lower()
        if 1 <= hour <= 12 and 0 <= minute <= 59:
            hour = hour % 12 + (12 if meridiem == "pm" else 0)
            return f"{hour:02d}:{minute:02d}"
    # Match Roman Telugu / informal e.g. "2 PM ki", "2pm ki", "2 ki"
    match_ki = re.search(r"\b(\d{1,2})\s*(?:pm|am)?\s*(?:ki|gantalaku|o'clock)\b", normalized)
    if match_ki:
        h = int(match_ki.group(1))
        if 1 <= h <= 12:
            if "pm" in normalized or (1 <= h <= 7):
                h = h % 12 + 12
            return f"{h:02d}:00"
    return None


def detect_web_intent(message: str) -> ParsedIntent:
    text = (message or "").strip()
    lowered = text.lower()
    language = _language(text)
    professor = None
    if re.search(r"\b(cse\s*(?:ds|data\s*science)\s*hod|hod\s*of\s*cse\s*(?:ds|data\s*science))\b", lowered):
        professor = "Dr. B. Bhaskara Rao"
    else:
        professor_match = re.search(
            r"\b((?:prof(?:essor)?\.?|dr\.?\s*)?[a-z][a-z.'-]*(?:\s+[a-z][a-z.'-]*){0,2}\s+(?:sir|madam))\b|\b(?:prof(?:essor)?\.?|dr\.)\s+[a-z][a-z.'-]*(?:\s+[a-z][a-z.'-]*)?",
            text,
            re.I,
        )
        professor = professor_match.group(0).strip() if professor_match else None
        if professor is None:
            bare_professor = re.search(
                r"\b(?:is|show|find|what\s+is)\s+(?!(?:the|a|an)\b)([A-Z][a-z]+)(?:['’]s)?\b",
                text,
                re.I,
            )
            if bare_professor:
                professor = bare_professor.group(1)
    if professor:
        professor = re.sub(
            r"^(?:(?:what|is|are|the|who|tell|me|about|can|could|may|i|we|want|to|book|schedule|meet|see|with)\s+)+",
            "",
            professor,
            flags=re.I,
        )

    department_entity = _department_entity(text)
    asks_faculty = bool(re.search(r"\b(hod|faculty|faculties|who\s+teaches|professors?)\b", lowered))

    if any(term in lowered for term in ("cancel", "రద్దు")) and any(
        term in lowered or term in text for term in ("appointment", "booking", "meeting", "అపాయింట్", "సమావేశ")
    ):
        intent: Intent = "APPOINTMENT_CANCELLATION"
    elif any(term in lowered for term in ("my appointment", "appointments", "appointment status", "show my")):
        intent: Intent = "APPOINTMENT_STATUS"
    elif any(term in lowered for term in ("schedule", "available", "availability", "timings enti")) and professor:
        intent = "PROFESSOR_SCHEDULE"
    elif any(term in lowered for term in ("meet", "appointment", "book", "kalavacha", "kalavali")):
        intent = "PROFESSOR_APPOINTMENT"
    elif asks_faculty:
        intent = "FACULTY_INFORMATION"
    elif professor and any(term in lowered for term in ("details", "who is", "about")):
        intent = "PROFESSOR_INFORMATION"
    elif re.search(r"\b(?:library|libraries|lab|labs|laboratory|laboratories|hostel|hostels|facility|facilities)\b", lowered) or re.search(
        r"(లైబ్రరీ|గ్రంథాలయం|ల్యాబ్|ప్రయోగశాల|హాస్టల్)", text
    ):
        intent = "FACILITY_INFORMATION"
        if re.search(r"\bcentral\s+library\b|\blibrary\b", lowered) or "లైబ్రరీ" in text or "గ్రంథాలయం" in text:
            entity = "Central Library"
        elif re.search(r"\bdata\s+science\b", lowered):
            entity = "Data Science Laboratory"
        else:
            entity = None
        return ParsedIntent(intent=intent, entity=entity, professor=professor, language=language)
    elif re.search(r"\b(departments?|branches?|courses?|programs?|b\.tech|m\.tech|cse|ece|eee|mechanical|civil|it\s+department)\b", lowered) or re.search(
        r"(విభాగం|విభాగాలు|శాఖ|శాఖలు)", text
    ):
        intent = "DEPARTMENT_INFORMATION"
    elif any(term in lowered for term in ("college", "rgmcet", "timings", "college timings", "address", "contact", "phone", "email", "founded", "established", "official website")):
        intent = "CAMPUS_INFORMATION"
    elif text:
        intent = "GENERAL_QUERY"
    else:
        intent = "UNKNOWN"

    return ParsedIntent(
        intent=intent,
        entity=department_entity,
        professor=professor,
        date=_date(text),
        time=_time(text),
        language=language,
    )