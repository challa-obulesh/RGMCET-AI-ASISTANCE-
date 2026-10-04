"""Tool registry and execution definitions for the AI Agent."""
import logging
from typing import Any, Callable, Coroutine
from datetime import date

from pydantic import BaseModel, ValidationError

from app.web_mvp import store, services
from app.web_mvp.schemas import AppointmentRequest

logger = logging.getLogger(__name__)

class ToolResult(BaseModel):
    success: bool
    tool: str
    data: dict | list | None = None
    sources: list[dict] = []
    error: dict | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict
    required: list[str] = []


_TOOL_REGISTRY: dict[str, dict] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict,
    required: list[str],
):
    """Decorator to register a tool with its schema."""
    def decorator(func: Callable):
        _TOOL_REGISTRY[name] = {
            "definition": ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                required=required,
            ),
            "execute": func,
        }
        return func
    return decorator


def get_all_tool_definitions() -> list[dict]:
    return [t["definition"].model_dump() for t in _TOOL_REGISTRY.values()]


async def execute_tool(name: str, kwargs: dict, student_id: str) -> ToolResult:
    if name not in _TOOL_REGISTRY:
        return ToolResult(
            success=False,
            tool=name,
            error={"code": "TOOL_NOT_FOUND", "message": f"Tool '{name}' is not registered."}
        )
    
    try:
        # Pass student_id if the tool explicitly asks for it in its signature,
        # but realistically we just pass kwargs and let the tool pop what it needs.
        kwargs["student_id"] = student_id
        result = await _TOOL_REGISTRY[name]["execute"](**kwargs)
        if isinstance(result, ToolResult):
            return result
        return ToolResult(success=True, tool=name, data=result)
    except ValidationError as e:
        return ToolResult(
            success=False,
            tool=name,
            error={"code": "VALIDATION_ERROR", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return ToolResult(
            success=False,
            tool=name,
            error={"code": "INTERNAL_ERROR", "message": str(e)}
        )


@register_tool(
    name="search_knowledge",
    description="Search verified RGMCET knowledge. Use for factual questions about departments, facilities, or general campus info.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The question or topic to search for."},
            "category": {"type": "string", "enum": ["CAMPUS_INFORMATION", "DEPARTMENT_INFORMATION", "FACILITY_INFORMATION", "FACULTY_INFORMATION"]}
        }
    },
    required=["query", "category"]
)
async def tool_search_knowledge(query: str, category: str, student_id: str) -> ToolResult:
    from app.web_mvp.knowledge import retrieve_verified
    records = await retrieve_verified(query, category)
    if not records:
        return ToolResult(
            success=False, 
            tool="search_knowledge", 
            error={"code": "NOT_FOUND", "message": "No verified records found."}
        )
    
    # Extract sources
    sources = []
    unique = set()
    for record in records:
        url = record.get("source")
        if url and url not in unique:
            unique.add(url)
            title = record.get("title") or record.get("name") or "RGMCET Official Website"
            sources.append({"title": title, "url": url})
            
    return ToolResult(
        success=True,
        tool="search_knowledge",
        data={"records": records},
        sources=sources
    )


@register_tool(
    name="search_professor",
    description="Look up a professor's details (department, office, ID).",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the professor (e.g. B. Bhaskara Rao)"}
        }
    },
    required=["name"]
)
async def tool_search_professor(name: str, student_id: str) -> ToolResult:
    prof = await services.find_professor(name)
    if not prof:
        return ToolResult(
            success=False,
            tool="search_professor",
            error={"code": "NOT_FOUND", "message": f"Professor '{name}' not found in the verified database."}
        )
    return ToolResult(success=True, tool="search_professor", data=prof)


@register_tool(
    name="check_availability",
    description="Check a professor's available schedule slots for a specific date.",
    parameters={
        "type": "object",
        "properties": {
            "professor_id": {"type": "string", "description": "The ID of the professor."},
            "date": {"type": "string", "description": "The date to check in YYYY-MM-DD format."}
        }
    },
    required=["professor_id", "date"]
)
async def tool_check_availability(professor_id: str, date: str, student_id: str) -> ToolResult:
    try:
        check_date = __import__("datetime").date.fromisoformat(date)
    except ValueError:
        return ToolResult(success=False, tool="check_availability", error={"code": "INVALID_DATE", "message": "Date must be YYYY-MM-DD"})
        
    slots = await services.get_availability(professor_id, check_date)
    return ToolResult(success=True, tool="check_availability", data={"slots": slots})


@register_tool(
    name="search_appointments",
    description="Fetch the authenticated user's current appointments.",
    parameters={
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Filter by status (PENDING_APPROVAL, APPROVED, REJECTED, CANCELLED)"}
        }
    },
    required=[]
)
async def tool_search_appointments(student_id: str, status: str = None, **kwargs) -> ToolResult:
    items = await services.list_appointments(student_id=student_id, status=status)
    return ToolResult(success=True, tool="search_appointments", data={"appointments": items})


@register_tool(
    name="create_appointment",
    description="Create an appointment. WARNING: Only use this if the user has explicitly confirmed the professor, date, and time.",
    parameters={
        "type": "object",
        "properties": {
            "professor_id": {"type": "string"},
            "date": {"type": "string", "description": "YYYY-MM-DD format"},
            "start_time": {"type": "string", "description": "HH:MM format"},
            "reason": {"type": "string"}
        }
    },
    required=["professor_id", "date", "start_time"]
)
async def tool_create_appointment(professor_id: str, date: str, start_time: str, student_id: str, reason: str = "Requested via chat") -> ToolResult:
    try:
        req = AppointmentRequest(
            professor_id=professor_id,
            date=date,
            start_time=start_time,
            reason=reason,
            student_id=student_id
        )
        appointment = await services.create_appointment(req)
        return ToolResult(success=True, tool="create_appointment", data=appointment)
    except Exception as e:
        return ToolResult(success=False, tool="create_appointment", error={"code": "CREATION_FAILED", "message": str(e)})


@register_tool(
    name="reschedule_appointment",
    description="Reschedule an existing appointment. Requires user confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "appointment_id": {"type": "string"},
            "new_date": {"type": "string", "description": "YYYY-MM-DD"},
            "new_time": {"type": "string", "description": "HH:MM"}
        }
    },
    required=["appointment_id", "new_date", "new_time"]
)
async def tool_reschedule_appointment(appointment_id: str, new_date: str, new_time: str, student_id: str) -> ToolResult:
    # Auth check
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        return ToolResult(success=False, tool="reschedule_appointment", error={"code": "NOT_FOUND", "message": "Appointment not found."})
    if appt.get("student_id") != student_id:
        return ToolResult(success=False, tool="reschedule_appointment", error={"code": "UNAUTHORIZED", "message": "Can only reschedule own appointments."})
        
    try:
        updated = await services.reschedule_appointment(appointment_id, new_date, new_time)
        return ToolResult(success=True, tool="reschedule_appointment", data=updated)
    except Exception as e:
        return ToolResult(success=False, tool="reschedule_appointment", error={"code": "UPDATE_FAILED", "message": str(e)})


@register_tool(
    name="cancel_appointment",
    description="Cancel an existing appointment. Requires user confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "appointment_id": {"type": "string"}
        }
    },
    required=["appointment_id"]
)
async def tool_cancel_appointment(appointment_id: str, student_id: str) -> ToolResult:
    appt = await store.find_one("appointments", {"appointment_id": appointment_id})
    if not appt:
        return ToolResult(success=False, tool="cancel_appointment", error={"code": "NOT_FOUND", "message": "Appointment not found."})
    if appt.get("student_id") != student_id:
        return ToolResult(success=False, tool="cancel_appointment", error={"code": "UNAUTHORIZED", "message": "Can only cancel own appointments."})
        
    try:
        updated = await services.change_appointment_status(appointment_id, "CANCELLED")
        return ToolResult(success=True, tool="cancel_appointment", data=updated)
    except Exception as e:
        return ToolResult(success=False, tool="cancel_appointment", error={"code": "UPDATE_FAILED", "message": str(e)})
