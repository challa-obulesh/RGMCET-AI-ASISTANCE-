"""Intent-scoped retrieval from curated official RGMCET JSON records."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "rgmcet_knowledge"
STOP_WORDS = {
    "where", "what", "when", "which", "who", "how", "does", "do", "is", "are",
    "the", "a", "an", "in", "at", "to", "of", "for", "me", "tell", "about",
    "available", "please", "show", "list", "there", "have", "has", "ante", "enti",
}


def load_verified_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for filename in ("college_info.json", "departments.json", "facilities.json", "timings.json"):
        path = DATA_DIR / filename
        if path.exists():
            records.extend(json.loads(path.read_text(encoding="utf-8")))
    faculty_dir = DATA_DIR / "faculty"
    if faculty_dir.exists():
        for path in sorted(faculty_dir.glob("*.json")):
            faculty_records = json.loads(path.read_text(encoding="utf-8"))
            records.extend({"kind": "faculty", **record} for record in faculty_records)
    return [
        record for record in records
        if record.get("verified") is True
        and record.get("title", record.get("name"))
        and record.get("content", record.get("designation"))
        and record.get("source")
    ]


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[\w\u0c00-\u0c7f]+", text.casefold())
        if len(token) > 1 and token not in STOP_WORDS
    }


def retrieve_verified(
    query: str,
    intent: str,
    entity: str | None = None,
) -> list[dict[str, Any]]:
    records = load_verified_records()
    allowed_kinds = {
        "CAMPUS_INFORMATION": {"college", "contact"},
        "DEPARTMENT_INFORMATION": {"department"},
        "FACILITY_INFORMATION": {"facility"},
        "FACULTY_INFORMATION": {"faculty"},
        "PROFESSOR_INFORMATION": {"faculty"},
    }.get(intent, set())
    candidates = [record for record in records if record.get("kind") in allowed_kinds]
    if not candidates:
        return []

    lowered = query.casefold()
    is_broad_department_list = intent == "DEPARTMENT_INFORMATION" and bool(
        re.search(r"\b(departments?|branches?)\b|విభాగాలు|శాఖలు", lowered)
    ) and entity is None
    is_broad_facility_list = intent == "FACILITY_INFORMATION" and bool(
        re.search(r"\b(facilities|facility)\b|సదుపాయాలు", lowered)
    ) and entity is None
    faculty_list = intent == "FACULTY_INFORMATION" and bool(
        re.search(r"\b(faculty|faculties|staff|members)\b", lowered)
    ) and not re.search(r"\b(hod|head)\b", lowered)

    if is_broad_department_list or is_broad_facility_list or faculty_list:
        return candidates

    query_tokens = _tokens(" ".join(part for part in (query, entity or "") if part))
    if not query_tokens:
        return []
    ranked: list[tuple[int, dict[str, Any]]] = []
    for record in candidates:
        searchable = " ".join([
            record.get("title", ""),
            record.get("content", ""),
            record.get("name", ""),
            record.get("department", ""),
            " ".join(record.get("aliases", [])),
            json.dumps(record.get("facts", {}), ensure_ascii=False),
        ])
        matched = query_tokens & _tokens(searchable)
        score = len(matched)
        if entity and entity.casefold() in searchable.casefold():
            score += len(query_tokens) + 2
        if intent == "FACULTY_INFORMATION" and re.search(r"\b(hod|head)\b", lowered):
            if record.get("is_hod") is True:
                score += 8
            else:
                score -= 4
        if score > 0:
            ranked.append((score, record))
    if not ranked:
        return []
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    best_score = ranked[0][0]
    if intent == "FACULTY_INFORMATION" and re.search(r"\b(hod|head)\b", lowered):
        return [record for score, record in ranked if score == best_score and record.get("is_hod")]
    if intent == "FACULTY_INFORMATION" and entity:
        return [record for score, record in ranked if score >= max(2, best_score - 1)]
    return [ranked[0][1]]