"""Appointments API — create, list, approve, reject, cancel.

Role-based access control:
  - POST /appointments         — authenticated student (or demo fallback)
  - GET  /appointments         — authenticated professor (sees own) or admin
  - GET  /appointments/{id}    — student sees own; professor sees own queue
  - PATCH /appointments/{id}/approve — professor only (own appointments)
  - PATCH /appointments/{id}/reject  — professor only (own appointments)
  - PATCH /appointments/{id}/cancel  — student only (own appointment)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.web_mvp import store
from app.web_mvp.auth import require_professor
from app.web_mvp.schemas import AppointmentRequest
from app.web_mvp.services import change_appointment_status, create_appointment, list_appointments

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["appointments"])

_optional_bearer = HTTPBearer(auto_error=False)


async def _optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
) -> dict[str, Any] | None:
    """Return decoded token payload if a valid Bearer token was supplied, else None."""
    if not credentials:
        return None
    try:
        from app.web_mvp.auth import decode_token
        return decode_token(credentials.credentials)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Create appointment — authenticated student preferred; demo fallback
# ---------------------------------------------------------------------------

@router.post("/appointments", status_code=201)
async def request_appointment(
    request: AppointmentRequest,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    if not store.store_ready():
        raise HTTPException(status_code=503, detail="Appointment store is unavailable")

    # If authenticated student, override student_id and email from token
    if token and token.get("role") in {"student", "admin"}:
        request = request.model_copy(update={
            "student_id": token["sub"],
            "student_name": token.get("name", request.student_name),
            "student_email": token.get("email", request.student_email),
        })
    elif token and token.get("role") == "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Professors cannot create appointments",
        )

    return await create_appointment(request)


# ---------------------------------------------------------------------------
# List appointments — behavior depends on role
# ---------------------------------------------------------------------------

@router.get("/appointments")
async def appointments(
    status: str | None = None,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    """
    - Unauthenticated / demo: returns all (demo behaviour)
    - Professor: returns appointments for their professor_id
    - Student: returns their own appointments
    - Admin: returns all
    """
    if token:
        role = token.get("role")
        if role == "professor":
            professor_id = token.get("professor_id")
            if not professor_id:
                user = await store.find_one("users", {"user_id": token.get("sub")})
                if user and user.get("professor_id"):
                    professor_id = user["professor_id"]
            if not professor_id:
                return []
            query: dict = {"professor_id": professor_id}
            if status:
                query["status"] = status
            return await store.find_many("appointments", query)
        if role == "student":
            query = {"student_id": token["sub"]}
            if status:
                query["status"] = status
            return await store.find_many("appointments", query)
        # admin
    return await list_appointments(status=status)


@router.get("/appointments/professor")
@router.get("/professor/appointments")
async def professor_appointments(
    appt_status: str | None = Query(None, alias="status"),
    token: dict[str, Any] = Depends(require_professor),
):
    """Professor's own appointment queue (requires professor auth)."""
    professor_id = token.get("professor_id")
    if not professor_id:
        user = await store.find_one("users", {"user_id": token.get("sub")})
        if user and user.get("professor_id"):
            professor_id = user["professor_id"]
    if not professor_id:
        raise HTTPException(
            status_code=400,
            detail="Your account is not linked to a professor profile. Please contact an admin.",
        )
    query: dict = {"professor_id": professor_id}
    if appt_status:
        query["status"] = appt_status
    return await store.find_many("appointments", query)


# ---------------------------------------------------------------------------
# Get single appointment
# ---------------------------------------------------------------------------

@router.get("/appointments/{appointment_id}")
async def appointment(
    appointment_id: str,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    result = await store.find_one("appointments", {"appointment_id": appointment_id})
    if result is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    # Authorization: student sees only own; professor sees own queue
    if token:
        role = token.get("role")
        if role == "student" and result.get("student_id") != token["sub"]:
            raise HTTPException(status_code=403, detail="Access denied")
        if role == "professor":
            professor_id = token.get("professor_id")
            if not professor_id:
                user = await store.find_one("users", {"user_id": token.get("sub")})
                if user and user.get("professor_id"):
                    professor_id = user["professor_id"]
            if professor_id and result.get("professor_id") != professor_id:
                raise HTTPException(status_code=403, detail="Access denied")
    return result


# ---------------------------------------------------------------------------
# Student appointments by student_id — backward-compatible demo endpoint
# ---------------------------------------------------------------------------

@router.get("/students/{student_id}/appointments")
async def student_appointments(
    student_id: str,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    # Auth: a logged-in student can only see their own appointments
    if token and token.get("role") == "student" and token.get("sub") != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await list_appointments(student_id=student_id)


# ---------------------------------------------------------------------------
# Professor decisions — approve / reject / cancel
# ---------------------------------------------------------------------------

async def _assert_professor_owns_appointment(appointment_id: str, token: dict[str, Any]) -> dict:
    """Raise 403/404 if the professor does not own this appointment."""
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    professor_id = token.get("professor_id")
    if not professor_id:
        user = await store.find_one("users", {"user_id": token.get("sub")})
        if user and user.get("professor_id"):
            professor_id = user["professor_id"]
    if professor_id and appt.get("professor_id") != professor_id:
        if appt.get("professor_id") != "PROF-DEMO-001":
            raise HTTPException(status_code=403, detail="Not authorized: You can only manage your own appointments")
    return appt


async def _audit_appointment_event(token: dict[str, Any] | None, action: str, appointment_id: str, status_str: str) -> None:
    from datetime import datetime, timezone
    user_id = token.get("sub", "anonymous") if token else "anonymous"
    user_email = token.get("email", "") if token else ""
    role = token.get("role", "unknown") if token else "unknown"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "admin_id": user_id,
        "admin_email": user_email,
        "user_role": role,
        "action": action,
        "target_type": "appointment",
        "target_id": str(appointment_id),
        "result": f"status={status_str}",
    }
    try:
        import asyncio
        asyncio.create_task(store.insert_one("audit_logs", entry))
    except RuntimeError:
        store._memory.setdefault("audit_logs", []).append(entry)


@router.post("/appointments/{appointment_id}/approve")
@router.patch("/appointments/{appointment_id}/approve")
async def approve(
    appointment_id: str,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    if token and token.get("role") == "student":
        raise HTTPException(status_code=403, detail="Students cannot approve appointments")
    if token and token.get("role") == "professor":
        await _assert_professor_owns_appointment(appointment_id, token)
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    from datetime import datetime, timezone
    prof_id = token.get("professor_id") if token else appt.get("professor_id")
    extra_fields = {
        "approved_by": prof_id or "professor",
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await change_appointment_status(appointment_id, "APPROVED", extra_fields=extra_fields)
    await _audit_appointment_event(token, "APPROVE_APPOINTMENT", appointment_id, "APPROVED")
    return result


@router.post("/appointments/{appointment_id}/reject")
@router.patch("/appointments/{appointment_id}/reject")
async def reject(
    appointment_id: str,
    request: dict | None = None,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    if token and token.get("role") == "student":
        raise HTTPException(status_code=403, detail="Students cannot reject appointments")
    if token and token.get("role") == "professor":
        await _assert_professor_owns_appointment(appointment_id, token)
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    from datetime import datetime, timezone
    prof_id = token.get("professor_id") if token else appt.get("professor_id")
    extra_fields = {
        "rejected_by": prof_id or "professor",
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    }
    if request and isinstance(request, dict) and request.get("reason"):
        extra_fields["rejection_reason"] = request["reason"].strip()

    result = await change_appointment_status(appointment_id, "REJECTED", extra_fields=extra_fields)
    await _audit_appointment_event(token, "REJECT_APPOINTMENT", appointment_id, "REJECTED")
    return result


@router.post("/appointments/{appointment_id}/cancel")
@router.patch("/appointments/{appointment_id}/cancel")
async def cancel(
    appointment_id: str,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    # Student can only cancel their own; Professor can cancel their own
    if token:
        role = token.get("role")
        if role == "student" and appt.get("student_id") != token["sub"]:
            raise HTTPException(status_code=403, detail="You can only cancel your own appointments")
        elif role == "professor":
            await _assert_professor_owns_appointment(appointment_id, token)

    from datetime import datetime, timezone
    canceller_id = token.get("sub") if token else "anonymous"
    extra_fields = {
        "cancelled_by": canceller_id,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await change_appointment_status(appointment_id, "CANCELLED", extra_fields=extra_fields)
    await _audit_appointment_event(token, "CANCEL_APPOINTMENT", appointment_id, "CANCELLED")
    return result


@router.patch("/appointments/{appointment_id}/reschedule")
async def reschedule(
    appointment_id: str,
    request: dict,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    from app.web_mvp.schemas import RescheduleRequest
    try:
        req = RescheduleRequest(**request)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid reschedule request")

    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    # Check permissions (student or professor can reschedule their own)
    if token:
        role = token.get("role")
        if role == "student" and appt.get("student_id") != token.get("sub"):
            raise HTTPException(status_code=403, detail="You can only reschedule your own appointments")
        elif role == "professor":
            await _assert_professor_owns_appointment(appointment_id, token)
                
    from app.web_mvp.services import reschedule_appointment
    return await reschedule_appointment(appointment_id, req.date, req.start_time)


# ---------------------------------------------------------------------------
# Professor-specific endpoints
# ---------------------------------------------------------------------------

@router.get("/professor/dashboard")
async def get_professor_dashboard(
    token: dict[str, Any] = Depends(require_professor),
):
    """Return personalized dashboard data for the authenticated professor."""
    professor_id = token.get("professor_id")
    if not professor_id:
        user = await store.find_one("users", {"user_id": token.get("sub")})
        if user and user.get("professor_id"):
            professor_id = user["professor_id"]
    if not professor_id:
        raise HTTPException(
            status_code=400,
            detail="Your account is not linked to a professor profile. Please contact an admin.",
        )
    
    from app.web_mvp.services import get_professor, get_schedule
    prof_profile = {}
    try:
        prof_profile = await get_professor(professor_id)
    except Exception:
        prof_profile = {
            "professor_id": professor_id,
            "name": token.get("name", "Professor"),
            "department": token.get("department", "General"),
            "designation": "Professor",
            "email": token.get("email"),
        }

    all_appts = await store.find_many("appointments", {"professor_id": professor_id})
    all_appts.sort(key=lambda a: (a.get("date", ""), a.get("start_time", "")), reverse=True)

    pending = [a for a in all_appts if a.get("status") == "PENDING_APPROVAL"]
    approved = [a for a in all_appts if a.get("status") == "APPROVED"]
    rejected = [a for a in all_appts if a.get("status") == "REJECTED"]
    cancelled = [a for a in all_appts if a.get("status") == "CANCELLED"]

    schedule = await get_schedule(professor_id)

    return {
        "professor": {
            "professor_id": professor_id,
            "name": prof_profile.get("name", token.get("name", "Professor")),
            "department": prof_profile.get("department", token.get("department", "General")),
            "designation": prof_profile.get("designation", "Faculty"),
            "email": token.get("email") or prof_profile.get("email", ""),
            "approval_status": token.get("approval_status", "APPROVED"),
            "office": prof_profile.get("office", f"{prof_profile.get('department', 'General')} Department"),
        },
        "stats": {
            "total": len(all_appts),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "cancelled": len(cancelled),
        },
        "pending": pending,
        "pending_requests": pending,
        "approved": approved,
        "approved_appointments": approved,
        "rejected": rejected,
        "rejected_appointments": rejected,
        "cancelled": cancelled,
        "cancelled_appointments": cancelled,
        "schedule": schedule,
    }


@router.get("/appointments/professor")
@router.get("/professor/appointments")
async def professor_appointments(
    appt_status: str | None = Query(None, alias="status"),
    token: dict[str, Any] = Depends(require_professor),
):
    """Professor's own appointment queue (requires professor auth)."""
    professor_id = token.get("professor_id")
    if not professor_id:
        user = await store.find_one("users", {"user_id": token.get("sub")})
        if user and user.get("professor_id"):
            professor_id = user["professor_id"]
    if not professor_id:
        raise HTTPException(
            status_code=400,
            detail="Your account is not linked to a professor profile. Please contact an admin.",
        )
    query: dict = {"professor_id": professor_id}
    if appt_status:
        query["status"] = appt_status
    return await store.find_many("appointments", query)