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

    # If authenticated student, override student_id from token
    if token and token.get("role") in {"student", "admin"}:
        request = request.model_copy(update={
            "student_id": token["sub"],
            "student_name": token.get("name", request.student_name),
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
# Professor decisions — approve / reject (professor only, own queue)
# ---------------------------------------------------------------------------

async def _assert_professor_owns_appointment(appointment_id: str, token: dict[str, Any]) -> dict:
    """Raise 403/404 if the professor does not own this appointment."""
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    professor_id = token.get("professor_id")
    if professor_id and appt.get("professor_id") != professor_id:
        raise HTTPException(status_code=403, detail="You can only manage your own appointments")
    return appt


@router.post("/appointments/{appointment_id}/approve")
async def approve(
    appointment_id: str,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    if token and token.get("role") == "student":
        raise HTTPException(status_code=403, detail="Students cannot approve appointments")
    if token and token.get("role") == "professor":
        await _assert_professor_owns_appointment(appointment_id, token)
    return await change_appointment_status(appointment_id, "APPROVED")


@router.post("/appointments/{appointment_id}/reject")
async def reject(
    appointment_id: str,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    if token and token.get("role") == "student":
        raise HTTPException(status_code=403, detail="Students cannot reject appointments")
    if token and token.get("role") == "professor":
        await _assert_professor_owns_appointment(appointment_id, token)
    return await change_appointment_status(appointment_id, "REJECTED")


@router.post("/appointments/{appointment_id}/cancel")
async def cancel(
    appointment_id: str,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    # Student can only cancel their own
    if token and token.get("role") == "student" and appt.get("student_id") != token["sub"]:
        raise HTTPException(status_code=403, detail="You can only cancel your own appointments")
    return await change_appointment_status(appointment_id, "CANCELLED")


@router.patch("/appointments/{appointment_id}/reschedule")
async def reschedule(
    appointment_id: str,
    request: dict,
    token: dict[str, Any] | None = Depends(_optional_user),
):
    from app.web_mvp.schemas import RescheduleRequest
    try:
        req = RescheduleRequest(**request)
    except Exception as e:
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
            prof_id = token.get("professor_id")
            if prof_id and appt.get("professor_id") != prof_id:
                raise HTTPException(status_code=403, detail="You can only reschedule your own appointments")
                
    from app.web_mvp.services import reschedule_appointment
    return await reschedule_appointment(appointment_id, req.date, req.start_time)


# ---------------------------------------------------------------------------
# Professor-specific endpoints
# ---------------------------------------------------------------------------

@router.get("/professor/appointments")
async def professor_appointments(
    appt_status: str | None = Query(None, alias="status"),
    token: dict[str, Any] = Depends(require_professor),
):
    """Professor's own appointment queue (requires professor auth)."""
    professor_id = token.get("professor_id")
    if not professor_id:
        raise HTTPException(
            status_code=400,
            detail="Your account is not linked to a professor profile. Please contact an admin.",
        )
    query: dict = {"professor_id": professor_id}
    if appt_status:
        query["status"] = appt_status
    return await store.find_many("appointments", query)