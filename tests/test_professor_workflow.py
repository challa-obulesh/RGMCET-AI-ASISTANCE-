"""Comprehensive tests for Professor Authentication, Personal Identity,
Dashboard Routing, Schedules, and Student Appointment Approval Workflow.
Covering all 14 mandatory security and workflow verification test scenarios.
"""

from datetime import date, timedelta
import pytest
from starlette.testclient import TestClient

from app.web_mvp import store
from app.web_mvp.main import app
from app.web_mvp.auth import create_access_token


@pytest.fixture
def client():
    store.reset_demo_data()
    with TestClient(app) as test_client:
        yield test_client


def future_workday():
    candidate = date.today() + timedelta(days=1)
    while candidate.weekday() == 6:  # Skip Sunday
        candidate += timedelta(days=1)
    return candidate.isoformat()


def register_and_approve_professor(client, name, email, password, prof_id, department):
    """Helper to register a professor, create admin, and approve the professor."""
    # 1. Register professor
    p_reg = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "role": "professor",
            "department": department,
            "professor_id": prof_id,
        },
    )
    assert p_reg.status_code == 201, p_reg.text
    prof_user_id = p_reg.json()["user_id"]

    # 2. Register admin (or use existing)
    client.post(
        "/api/auth/register",
        json={
            "name": "Super Admin",
            "email": "admin.master@rgmcet.edu.in",
            "password": "AdminMasterPass123!",
            "role": "admin",
        },
    )
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin.master@rgmcet.edu.in", "password": "AdminMasterPass123!"},
    )
    admin_token = admin_login.json()["access_token"]

    # 3. Admin approves professor
    appr_res = client.patch(
        f"/api/admin/professors/{prof_user_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "APPROVED"},
    )
    assert appr_res.status_code == 200, appr_res.text

    # 4. Login as professor and return token + profile
    prof_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert prof_login.status_code == 200, prof_login.text
    return prof_login.json()["access_token"], prof_user_id, prof_login.json()


def register_student(client, name="Rahul Kumar", email="rahul.student@rgmcet.edu.in"):
    s_reg = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "StudentPassword123!",
            "role": "student",
            "department": "Computer Science and Engineering",
        },
    )
    assert s_reg.status_code == 201, s_reg.text
    s_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "StudentPassword123!"},
    )
    assert s_login.status_code == 200, s_login.text
    return s_login.json()["access_token"], s_login.json()


def test_1_professor_a_sees_professor_a_dashboard(client):
    """TEST 1: Professor A logs in -> sees Professor A dashboard."""
    token_a, _, user_a = register_and_approve_professor(
        client,
        name="Dr. B. Bhaskara Rao",
        email="bhaskara.rao@rgmcet.edu.in",
        password="ProfPass123!",
        prof_id="PROF-TEST-A",
        department="Computer Science and Engineering",
    )
    assert user_a["role"] == "professor"
    assert user_a["professor_id"] == "PROF-TEST-A"

    res = client.get("/api/professor/dashboard", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    data = res.json()
    assert data["professor"]["professor_id"] == "PROF-TEST-A"
    assert data["professor"]["name"] == "Dr. B. Bhaskara Rao"
    assert data["professor"]["approval_status"] == "APPROVED"
    assert "pending_requests" in data
    assert "schedule" in data


def test_2_professor_b_sees_professor_b_dashboard(client):
    """TEST 2: Professor B logs in -> sees Professor B dashboard."""
    token_b, _, user_b = register_and_approve_professor(
        client,
        name="Dr. K. Subba Rao",
        email="subba.rao@rgmcet.edu.in",
        password="ProfPass123!",
        prof_id="PROF-TEST-B",
        department="Information Technology",
    )
    assert user_b["role"] == "professor"
    assert user_b["professor_id"] == "PROF-TEST-B"

    res = client.get("/api/professor/dashboard", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 200
    data = res.json()
    assert data["professor"]["professor_id"] == "PROF-TEST-B"
    assert data["professor"]["name"] == "Dr. K. Subba Rao"
    assert data["professor"]["approval_status"] == "APPROVED"


def test_3_professor_a_cannot_access_professor_b_appointment(client):
    """TEST 3: Professor A cannot access Professor B's appointment."""
    token_a, _, _ = register_and_approve_professor(
        client,
        name="Dr. Bhaskara A",
        email="prof.a@rgmcet.edu.in",
        password="ProfPasswordA1!",
        prof_id="PROF-A",
        department="CSE",
    )
    token_b, _, _ = register_and_approve_professor(
        client,
        name="Dr. Subba B",
        email="prof.b@rgmcet.edu.in",
        password="ProfPasswordB1!",
        prof_id="PROF-B",
        department="ECE",
    )
    student_token, _ = register_student(client)

    # Student requests appointment with Professor B
    target_date = future_workday()
    booking_res = client.post(
        "/api/appointments",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "professor_id": "PROF-B",
            "professor_name": "Dr. Subba B",
            "date": target_date,
            "start_time": "10:00",
            "end_time": "10:30",
            "reason": "Project guidance with Prof B",
        },
    )
    assert booking_res.status_code == 201
    appt_b_id = booking_res.json()["appointment_id"]

    # Professor A checks dashboard
    dash_a = client.get("/api/professor/dashboard", headers={"Authorization": f"Bearer {token_a}"})
    assert dash_a.status_code == 200
    pending_a = [item["appointment_id"] for item in dash_a.json()["pending_requests"]]
    assert appt_b_id not in pending_a

    # Professor A checks GET /api/appointments/professor
    prof_appts_a = client.get("/api/appointments/professor", headers={"Authorization": f"Bearer {token_a}"})
    assert prof_appts_a.status_code == 200
    appts_a_ids = [item["appointment_id"] for item in prof_appts_a.json()]
    assert appt_b_id not in appts_a_ids


def test_4_professor_b_cannot_approve_professor_a_appointment(client):
    """TEST 4: Professor B cannot approve Professor A's appointment."""
    _, _, _ = register_and_approve_professor(
        client,
        name="Dr. Bhaskara A",
        email="prof.a2@rgmcet.edu.in",
        password="ProfPasswordA1!",
        prof_id="PROF-A2",
        department="CSE",
    )
    token_b, _, _ = register_and_approve_professor(
        client,
        name="Dr. Subba B",
        email="prof.b2@rgmcet.edu.in",
        password="ProfPasswordB1!",
        prof_id="PROF-B2",
        department="ECE",
    )
    student_token, _ = register_student(client)

    # Student requests appointment with Professor A2
    target_date = future_workday()
    booking_res = client.post(
        "/api/appointments",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "professor_id": "PROF-A2",
            "date": target_date,
            "start_time": "11:00",
            "end_time": "11:30",
            "reason": "Thesis discussion",
        },
    )
    assert booking_res.status_code == 201
    appt_a_id = booking_res.json()["appointment_id"]

    # Professor B tries to approve Professor A's appointment -> 403 Forbidden
    approve_res = client.patch(
        f"/api/appointments/{appt_a_id}/approve",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert approve_res.status_code == 403
    assert "not authorized" in approve_res.json()["detail"].lower()


def test_5_professor_a_can_approve_their_own_pending_request(client):
    """TEST 5: Professor A can approve their own pending student request."""
    token_a, _, _ = register_and_approve_professor(
        client,
        name="Dr. Bhaskara A3",
        email="prof.a3@rgmcet.edu.in",
        password="ProfPasswordA1!",
        prof_id="PROF-A3",
        department="CSE",
    )
    student_token, _ = register_student(client)

    target_date = future_workday()
    booking_res = client.post(
        "/api/appointments",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "professor_id": "PROF-A3",
            "date": target_date,
            "start_time": "14:00",
            "end_time": "14:30",
            "reason": "Lab review",
        },
    )
    assert booking_res.status_code == 201
    appt_id = booking_res.json()["appointment_id"]

    # Professor A approves
    approve_res = client.patch(
        f"/api/appointments/{appt_id}/approve",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert approve_res.status_code == 200
    updated_appt = approve_res.json()
    assert updated_appt["status"] == "APPROVED"
    assert updated_appt["approved_by"] == "PROF-A3"


def test_6_student_cannot_approve_appointment(client):
    """TEST 6: Student cannot approve appointment."""
    register_and_approve_professor(
        client,
        name="Dr. Bhaskara A4",
        email="prof.a4@rgmcet.edu.in",
        password="ProfPasswordA1!",
        prof_id="PROF-A4",
        department="CSE",
    )
    student_token, _ = register_student(client)

    target_date = future_workday()
    booking_res = client.post(
        "/api/appointments",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "professor_id": "PROF-A4",
            "date": target_date,
            "start_time": "15:00",
            "end_time": "15:30",
            "reason": "Clarification",
        },
    )
    assert booking_res.status_code == 201
    appt_id = booking_res.json()["appointment_id"]

    # Student attempts to approve -> 403 Forbidden
    approve_res = client.patch(
        f"/api/appointments/{appt_id}/approve",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert approve_res.status_code == 403


def test_7_admin_can_approve_reject_professor_accounts(client):
    """TEST 7: Admin can approve and reject professor accounts."""
    p_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Candidate",
            "email": "prof.candidate@rgmcet.edu.in",
            "password": "Password123!",
            "role": "professor",
            "department": "Mechanical Engineering",
            "professor_id": "PROF-CANDIDATE",
        },
    )
    assert p_reg.status_code == 201
    prof_user_id = p_reg.json()["user_id"]

    # Register admin
    client.post(
        "/api/auth/register",
        json={
            "name": "Head Admin",
            "email": "head.admin@rgmcet.edu.in",
            "password": "HeadAdminPassword123!",
            "role": "admin",
        },
    )
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "head.admin@rgmcet.edu.in", "password": "HeadAdminPassword123!"},
    )
    admin_token = admin_login.json()["access_token"]

    # Admin rejects professor
    reject_res = client.patch(
        f"/api/admin/professors/{prof_user_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "REJECTED"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["approval_status"] == "REJECTED"

    # Admin re-approves professor
    approve_res = client.patch(
        f"/api/admin/professors/{prof_user_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "APPROVED"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["approval_status"] == "APPROVED"


def test_8_pending_professor_cannot_use_professor_dashboard(client):
    """TEST 8: PENDING professor cannot use professor dashboard."""
    p_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Pending Prof",
            "email": "pending.prof@rgmcet.edu.in",
            "password": "Password123!",
            "role": "professor",
            "department": "Civil Engineering",
            "professor_id": "PROF-PENDING",
        },
    )
    assert p_reg.status_code == 201

    # Login rejected with 403
    login_res = client.post(
        "/api/auth/login",
        json={"email": "pending.prof@rgmcet.edu.in", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "pending admin approval" in login_res.json()["detail"].lower()

    # Even if they had an unverified token, require_professor blocks with 403
    token = create_access_token({"sub": p_reg.json()["user_id"], "role": "professor", "professor_id": "PROF-PENDING"})
    dash_res = client.get("/api/professor/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dash_res.status_code == 403
    assert "pending admin approval" in dash_res.json()["detail"].lower()


def test_9_rejected_professor_cannot_use_professor_dashboard(client):
    """TEST 9: REJECTED professor cannot use professor dashboard."""
    p_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Rejected Prof",
            "email": "rejected.prof@rgmcet.edu.in",
            "password": "Password123!",
            "role": "professor",
            "department": "Civil Engineering",
            "professor_id": "PROF-REJECTED",
        },
    )
    prof_user_id = p_reg.json()["user_id"]

    # Register admin and mark professor as REJECTED
    client.post(
        "/api/auth/register",
        json={"name": "Admin", "email": "adm9@rgmcet.edu.in", "password": "AdminPassword123!", "role": "admin"},
    )
    admin_login = client.post("/api/auth/login", json={"email": "adm9@rgmcet.edu.in", "password": "AdminPassword123!"})
    admin_token = admin_login.json()["access_token"]
    client.patch(
        f"/api/admin/professors/{prof_user_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "REJECTED"},
    )

    # Login fails with 403
    login_res = client.post(
        "/api/auth/login",
        json={"email": "rejected.prof@rgmcet.edu.in", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "has not been approved" in login_res.json()["detail"].lower()

    token = create_access_token({"sub": prof_user_id, "role": "professor", "professor_id": "PROF-REJECTED"})
    dash_res = client.get("/api/professor/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dash_res.status_code == 403
    assert "has not been approved" in dash_res.json()["detail"].lower()


def test_10_suspended_professor_cannot_use_professor_dashboard(client):
    """TEST 10: SUSPENDED professor cannot use professor dashboard."""
    p_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Suspended Prof",
            "email": "suspended.prof@rgmcet.edu.in",
            "password": "Password123!",
            "role": "professor",
            "department": "Civil Engineering",
            "professor_id": "PROF-SUSPENDED",
        },
    )
    prof_user_id = p_reg.json()["user_id"]

    # Register admin and mark professor as SUSPENDED
    client.post(
        "/api/auth/register",
        json={"name": "Admin", "email": "adm10@rgmcet.edu.in", "password": "AdminPassword123!", "role": "admin"},
    )
    admin_login = client.post("/api/auth/login", json={"email": "adm10@rgmcet.edu.in", "password": "AdminPassword123!"})
    admin_token = admin_login.json()["access_token"]
    client.patch(
        f"/api/admin/professors/{prof_user_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "SUSPENDED"},
    )

    # Login fails with 403
    login_res = client.post(
        "/api/auth/login",
        json={"email": "suspended.prof@rgmcet.edu.in", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "suspended" in login_res.json()["detail"].lower()

    token = create_access_token({"sub": prof_user_id, "role": "professor", "professor_id": "PROF-SUSPENDED"})
    dash_res = client.get("/api/professor/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dash_res.status_code == 403
    assert "suspended" in dash_res.json()["detail"].lower()


def test_11_approved_professor_can_login(client):
    """TEST 11: Approved professor can login."""
    token, _, user = register_and_approve_professor(
        client,
        name="Dr. Verified Professor",
        email="verified.prof@rgmcet.edu.in",
        password="VerifiedPassword123!",
        prof_id="PROF-VERIFIED",
        department="ECE",
    )
    assert token is not None
    assert user["approval_status"] == "APPROVED"
    assert user["professor_id"] == "PROF-VERIFIED"


def test_12_student_sees_correct_appointment_status_after_approval(client):
    """TEST 12: Student sees correct appointment status after professor approval."""
    token_prof, _, _ = register_and_approve_professor(
        client,
        name="Dr. Subba Rao Faculty",
        email="subba.faculty@rgmcet.edu.in",
        password="Password123!",
        prof_id="PROF-SUBBA-FACULTY",
        department="ECE",
    )
    student_token, _ = register_student(client)

    target_date = future_workday()
    booking_res = client.post(
        "/api/appointments",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "professor_id": "PROF-SUBBA-FACULTY",
            "professor_name": "Dr. Subba Rao Faculty",
            "date": target_date,
            "start_time": "14:00",
            "end_time": "14:30",
            "reason": "Final project evaluation",
        },
    )
    assert booking_res.status_code == 201
    appt_id = booking_res.json()["appointment_id"]

    # Student verifies it starts as PENDING_APPROVAL
    student_appts = client.get("/api/appointments", headers={"Authorization": f"Bearer {student_token}"}).json()
    my_appt = next(a for a in student_appts if a["appointment_id"] == appt_id)
    assert my_appt["status"] == "PENDING_APPROVAL"

    # Professor approves
    client.patch(f"/api/appointments/{appt_id}/approve", headers={"Authorization": f"Bearer {token_prof}"})

    # Student re-checks appointments
    student_appts_updated = client.get("/api/appointments", headers={"Authorization": f"Bearer {student_token}"}).json()
    my_appt_updated = next(a for a in student_appts_updated if a["appointment_id"] == appt_id)
    assert my_appt_updated["status"] == "APPROVED"
    assert my_appt_updated["approved_by"] == "PROF-SUBBA-FACULTY"


def test_13_professor_can_only_modify_their_own_schedule(client):
    """TEST 13: Professor can only modify their own schedule."""
    token_a, _, _ = register_and_approve_professor(
        client,
        name="Dr. Schedule Owner",
        email="sched.owner@rgmcet.edu.in",
        password="Password123!",
        prof_id="PROF-OWNER",
        department="CSE",
    )

    new_schedule = [
        {"day": "Monday", "start_time": "09:00", "end_time": "12:00", "is_available": True},
        {"day": "Wednesday", "start_time": "14:00", "end_time": "17:00", "is_available": True},
    ]

    update_res = client.put(
        "/api/professors/PROF-OWNER/schedule",
        headers={"Authorization": f"Bearer {token_a}"},
        json=new_schedule,
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert len(data["schedule"]) == 2
    assert data["schedule"][0]["day"] == "Monday"


def test_14_professor_cannot_modify_another_professors_schedule(client):
    """TEST 14: Professor cannot modify another professor's schedule by changing IDs in the API request."""
    token_a, _, _ = register_and_approve_professor(
        client,
        name="Dr. Attacker Prof",
        email="attacker.prof@rgmcet.edu.in",
        password="Password123!",
        prof_id="PROF-ATTACKER",
        department="CSE",
    )
    register_and_approve_professor(
        client,
        name="Dr. Victim Prof",
        email="victim.prof@rgmcet.edu.in",
        password="Password123!",
        prof_id="PROF-VICTIM",
        department="ECE",
    )

    malicious_schedule = [
        {"day": "Monday", "start_time": "00:00", "end_time": "23:59", "is_available": False}
    ]

    # Attacker tries to alter Victim's schedule
    attack_res = client.put(
        "/api/professors/PROF-VICTIM/schedule",
        headers={"Authorization": f"Bearer {token_a}"},
        json=malicious_schedule,
    )
    assert attack_res.status_code == 403
    assert "not authorized to update another professor's schedule" in attack_res.json()["detail"].lower()
