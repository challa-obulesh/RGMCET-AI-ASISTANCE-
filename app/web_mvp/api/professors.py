from datetime import date

from fastapi import APIRouter, HTTPException, Query, Depends

from app.web_mvp.auth import get_current_user
from app.web_mvp.services import get_availability, get_professor, get_schedule, list_professors

router = APIRouter(prefix="/api/professors", tags=["professors"])


@router.get("")
async def professors(q: str | None = None):
    return await list_professors(q)


@router.get("/search")
async def search_professors(q: str = Query(min_length=1)):
    return await list_professors(q)


@router.get("/{professor_id}")
async def professor_detail(professor_id: str):
    return await get_professor(professor_id)


@router.get("/{professor_id}/schedule")
async def professor_schedule(professor_id: str, on_date: date | None = None):
    return await get_schedule(professor_id, on_date)


@router.get("/{professor_id}/availability")
async def professor_availability(professor_id: str, on_date: date = Query(alias="date")):
    return await get_availability(professor_id, on_date)


@router.put("/{professor_id}/schedule")
async def update_schedule(
    professor_id: str,
    request: dict,
    token: dict = Depends(get_current_user)
):
    if token.get("role") != "professor" or token.get("professor_id") != professor_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this schedule")
    from app.web_mvp.schemas import ScheduleUpdateRequest
    # validate using Pydantic
    try:
        validated = ScheduleUpdateRequest(**request)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    
    # check for conflicting or invalid slots
    slots = validated.model_dump()["slots"]
    from datetime import datetime
    for slot in slots:
        start = datetime.strptime(slot["start_time"], "%H:%M")
        end = datetime.strptime(slot["end_time"], "%H:%M")
        if start >= end:
            raise HTTPException(status_code=422, detail="End time must be after start time")

    from app.web_mvp.services import update_professor_schedule
    return await update_professor_schedule(professor_id, slots)