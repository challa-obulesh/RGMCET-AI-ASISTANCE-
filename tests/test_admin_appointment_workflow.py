"""Tests for Admin and Professor Appointment Approval Workflow & Professor Account Approval."""

import pytest
from starlette.testclient import TestClient
from app.web_mvp.main import app
from app.web_mvp import store


from datetime import date, timedelta


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


def test_professor_account_approval_lifecycle(client):
    # 1. Register a new professor account
    prof_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. Sarah Connor",
            "email": "sarah.connor@rgmcet.edu.in",
            "password": "Password123!",
            "role": "professor",
            "department": "Computer Science and Engineering",
        },
    )
    assert prof_reg.status_code == 201
    prof_data = prof_reg.json()
    prof_user_id = prof_data["user_id"]
    assert prof_data["approval_status"] == "PENDING"

    # 2. Attempt login while PENDING -> should be rejected with 403 Forbidden
    login_res = client.post(
        "/api/auth/login",
        json={"email": "sarah.connor@rgmcet.edu.in", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "pending" in login_res.json()["detail"].lower()

    # 3. Register admin account
    admin_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Admin Officer",
            "email": "admin.officer@rgmcet.edu.in",
            "password": "AdminPassword123!",
            "role": "admin",
        },
    )
    assert admin_reg.status_code == 201
    admin_token = admin_reg.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Admin views users -> sees professor in PENDING status
    users_res = client.get("/api/admin/users?role=professor", headers=admin_headers)
    assert users_res.status_code == 200
    users = users_res.json()
    prof_user = next((u for u in users if u["user_id"] == prof_user_id), None)
    assert prof_user is not None
    assert prof_user["approval_status"] == "PENDING"
    assert "password_hash" not in prof_user

    # 5. Admin approves professor account
    approve_res = client.post(f"/api/admin/users/{prof_user_id}/approve", headers=admin_headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 6. Approved professor can now log in successfully
    login_ok = client.post(
        "/api/auth/login",
        json={"email": "sarah.connor@rgmcet.edu.in", "password": "Password123!"},
    )
    assert login_ok.status_code == 200
    prof_token = login_ok.json()["access_token"]
    assert login_ok.json()["approval_status"] == "APPROVED"

    # 7. Admin suspends professor
    suspend_res = client.post(f"/api/admin/users/{prof_user_id}/suspend", headers=admin_headers)
    assert suspend_res.status_code == 200
    assert suspend_res.json()["status"] == "SUSPENDED"

    # Suspended professor login rejected
    login_susp = client.post(
        "/api/auth/login",
        json={"email": "sarah.connor@rgmcet.edu.in", "password": "Password123!"},
    )
    assert login_susp.status_code == 403
    assert "suspended" in login_susp.json()["detail"].lower()

    # 8. Admin reactivates professor
    react_res = client.post(f"/api/admin/users/{prof_user_id}/reactivate", headers=admin_headers)
    assert react_res.status_code == 200
    assert react_res.json()["status"] == "APPROVED"

    # 9. Verify Audit Logs contain all approval actions
    audit_res = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    actions = [l["action"] for l in logs]
    assert "APPROVE_PROFESSOR" in actions
    assert "SUSPEND_PROFESSOR" in actions
    assert "REACTIVATE_PROFESSOR" in actions


def test_appointment_approval_and_rejection_workflow(client):
    # Setup Admin
    admin_res = client.post(
        "/api/auth/register",
        json={"name": "Admin", "email": "admin@rgmcet.edu.in", "password": "Pass@123Admin", "role": "admin"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_res.json()['access_token']}"}

    # Setup Professor (pre-approved in demo data or registered and approved)
    prof_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Dr. K. Subba Rao",
            "email": "ksubbarao@rgmcet.edu.in",
            "password": "ProfPassword123!",
            "role": "professor",
        },
    )
    prof_user_id = prof_reg.json()["user_id"]
    # Admin approves professor
    client.post(f"/api/admin/users/{prof_user_id}/approve", headers=admin_headers)
    prof_login = client.post(
        "/api/auth/login",
        json={"email": "ksubbarao@rgmcet.edu.in", "password": "ProfPassword123!"},
    )
    prof_headers = {"Authorization": f"Bearer {prof_login.json()['access_token']}"}

    # Setup Student
    student_res = client.post(
        "/api/auth/register",
        json={"name": "Alice Student", "email": "alice@rgmcet.edu.in", "password": "StudentPass123!", "role": "student"},
    )
    student_headers = {"Authorization": f"Bearer {student_res.json()['access_token']}"}

    # 1. Student creates an appointment
    appt_date = future_workday()
    appt_create = client.post(
        "/api/appointments",
        headers=student_headers,
        json={
            "student_id": "alice-id",
            "student_name": "Alice Student",
            "professor_id": "PROF-DEMO-001",
            "date": appt_date,
            "start_time": "10:00",
            "end_time": "10:30",
            "reason": "Project Guidance Discussion",
        },
    )
    assert appt_create.status_code == 201
    appt_data = appt_create.json()
    appt_id = appt_data["appointment_id"]
    assert appt_data["status"] == "PENDING_APPROVAL"

    # 2. Student cannot approve own appointment
    stu_appr = client.post(f"/api/appointments/{appt_id}/approve", headers=student_headers)
    assert stu_appr.status_code == 403

    # 3. Professor approves appointment
    prof_appr = client.post(f"/api/appointments/{appt_id}/approve", headers=prof_headers)
    assert prof_appr.status_code == 200
    assert prof_appr.json()["status"] == "APPROVED"

    # 4. Admin views appointments list
    admin_appts = client.get(f"/api/admin/appointments?status=APPROVED", headers=admin_headers)
    assert admin_appts.status_code == 200
    appts = admin_appts.json()
    assert any(a["appointment_id"] == appt_id for a in appts)

    # 5. Create a second appointment to test rejection
    appt_create2 = client.post(
        "/api/appointments",
        headers=student_headers,
        json={
            "student_id": "alice-id",
            "student_name": "Alice Student",
            "professor_id": "PROF-DEMO-001",
            "date": appt_date,
            "start_time": "11:00",
            "end_time": "11:30",
            "reason": "Lab Doubt Session",
        },
    )
    assert appt_create2.status_code == 201
    appt_id2 = appt_create2.json()["appointment_id"]

    # Professor rejects second appointment
    prof_rej = client.post(f"/api/appointments/{appt_id2}/reject", headers=prof_headers)
    assert prof_rej.status_code == 200
    assert prof_rej.json()["status"] == "REJECTED"

    # 6. Admin override capability
    admin_override = client.patch(
        f"/api/admin/appointments/{appt_id2}/override",
        headers=admin_headers,
        json={"status": "APPROVED", "reason": "Department Head approved exception"},
    )
    assert admin_override.status_code == 200
    assert admin_override.json()["status"] == "APPROVED"

    # 7. Student can cancel an approved appointment
    cancel_res = client.post(f"/api/appointments/{appt_id}/cancel", headers=student_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # 8. Check Audit Logs in Admin API
    audit_res = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    actions = [l["action"] for l in audit_res.json()]
    assert "APPROVE_APPOINTMENT" in actions
    assert "REJECT_APPOINTMENT" in actions
    assert "ADMIN_OVERRIDE_APPOINTMENT" in actions
    assert "CANCEL_APPOINTMENT" in actions


def test_authorization_security_boundaries(client):
    # Register student
    student_res = client.post(
        "/api/auth/register",
        json={"name": "Bob Student", "email": "bob@rgmcet.edu.in", "password": "Password123!", "role": "student"},
    )
    student_headers = {"Authorization": f"Bearer {student_res.json()['access_token']}"}

    # Student cannot access admin overview
    assert client.get("/api/admin/overview", headers=student_headers).status_code == 403
    # Student cannot access admin users
    assert client.get("/api/admin/users", headers=student_headers).status_code == 403
    # Student cannot access admin audit logs
    assert client.get("/api/admin/audit-logs", headers=student_headers).status_code == 403
    # Student cannot access admin appointments
    assert client.get("/api/admin/appointments", headers=student_headers).status_code == 403
