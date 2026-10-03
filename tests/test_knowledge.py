import pytest
import asyncio
from app.web_mvp.knowledge import retrieve_verified
from scripts.update_rgmcet_knowledge import approved_url, normalize_html

@pytest.mark.asyncio
async def test_official_cse_data_science_and_hod_retrieval():
    department = await retrieve_verified(
        "What is CSE Data Science?",
        "DEPARTMENT_INFORMATION",
        "Computer Science and Engineering (Data Science)",
    )
    assert len(department) >= 1
    # Check that one of the returned docs matches CSE Data Science
    assert any("Computer Science and Engineering (Data Science)" in doc.get("title", "") or "Computer Science and Engineering (Data Science)" in doc.get("name", "") or "Computer Science and Engineering (Data Science)" in doc.get("department", "") for doc in department)
@pytest.mark.asyncio
async def test_faculty_retrieval_rag():
    faculty = await retrieve_verified(
        "Who is the HOD of CSE Data Science?",
        "FACULTY_INFORMATION",
        "Computer Science and Engineering (Data Science)",
    )
    assert len(faculty) >= 1
    # Dr. B.Bhaskara Rao should be included
    assert any("Dr. B.Bhaskara Rao" in doc.get("name", "") for doc in faculty)

def test_ingestion_script_rejects_unapproved_urls_and_strips_scripts():
    assert approved_url("cseds") == "https://www.rgmcet.edu.in/department-of-cseds.php"
    with pytest.raises(ValueError):
        approved_url("https://example.com/facts")
    with pytest.raises(ValueError):
        approved_url("unknown-page-id")
    content = normalize_html("<main><h1>RGMCET</h1><script>secret()</script><p>Official page</p></main>")
    assert "RGMCET" in content and "Official page" in content
    assert "secret" not in content