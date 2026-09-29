from fastapi import APIRouter, HTTPException, Query

from app.web_mvp import store
from app.web_mvp.schemas import AppointmentRequest
from app.web_mvp.services import change_appointment_status, create_appointment, list_appointments

router = APIRouter(prefix="/api", tags=["appointments"])


@router.post("/appointments", status_code=201)
async def request_appointment(request: AppointmentRequest):
    if not store.store_ready():
        raise HTTPException(status_code=503, detail="Appointment store is unavailable")
    return await create_appointment(request)


@router.get("/appointments")
async def appointments(status: str | None = None):
    return await list_appointments(status=status)


@router.get("/appointments/{appointment_id}")
async def appointment(appointment_id: str):
    result = await store.find_one("appointments", {"appointment_id": appointment_id})
    if result is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result


@router.get("/students/{student_id}/appointments")
async def student_appointments(student_id: str):
    return await list_appointments(student_id=student_id)


@router.post("/appointments/{appointment_id}/approve")
async def approve(appointment_id: str):
    return await change_appointment_status(appointment_id, "APPROVED")


@router.post("/appointments/{appointment_id}/reject")
async def reject(appointment_id: str):
    return await change_appointment_status(appointment_id, "REJECTED")


@router.post("/appointments/{appointment_id}/cancel")
async def cancel(appointment_id: str):
    return await change_appointment_status(appointment_id, "CANCELLED")