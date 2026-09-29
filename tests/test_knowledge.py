import pytest

from scripts.update_rgmcet_knowledge import APPROVED_SOURCES, approved_url, normalize_html
from app.web_mvp.knowledge import load_verified_records, retrieve_verified


def test_curated_records_are_verified_and_source_linked():
    records = load_verified_records()
    assert len(records) >= 40
    assert all(record["verified"] is True for record in records)
    assert all(record.get("source", "").startswith("https://www.rgmcet.edu.in/") for record in records)
    assert sum(record.get("kind") == "faculty" for record in records) == 20


def test_official_cse_data_science_and_hod_retrieval():
    department = retrieve_verified(
        "What is CSE Data Science?",
        "DEPARTMENT_INFORMATION",
        "Computer Science and Engineering (Data Science)",
    )
    assert len(department) == 1
    assert department[0]["facts"]["intake"] == 240
    assert department[0]["facts"]["credits"] == 160
    assert department[0]["facts"]["semesters"] == 8

    faculty = retrieve_verified(
        "Who is the HOD of CSE Data Science?",
        "FACULTY_INFORMATION",
        "Computer Science and Engineering (Data Science)",
    )
    assert len(faculty) == 1
    assert faculty[0]["name"] == "Dr. B.Bhaskara Rao"
    assert faculty[0]["is_hod"] is True


def test_ingestion_script_rejects_unapproved_urls_and_strips_scripts():
    assert approved_url("cseds") == "https://www.rgmcet.edu.in/department-of-cseds.php"
    with pytest.raises(ValueError):
        approved_url("https://example.com/facts")
    with pytest.raises(ValueError):
        approved_url("unknown-page-id")
    content = normalize_html("<main><h1>RGMCET</h1><script>secret()</script><p>Official page</p></main>")
    assert "RGMCET" in content and "Official page" in content
    assert "secret" not in content