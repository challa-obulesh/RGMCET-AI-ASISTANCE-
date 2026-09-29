from datetime import date

from fastapi import APIRouter, HTTPException, Query

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