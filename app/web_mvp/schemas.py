from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    student_id: str = "demo-student"

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


class ChatResponse(BaseModel):
    message: str
    intent: str
    language: str
    session_id: str
    verified: bool = False
    sources: list["ChatSource"] = Field(default_factory=list)


class ChatSource(BaseModel):
    title: str
    url: str


class AppointmentRequest(BaseModel):
    professor_id: str
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    reason: str = Field(min_length=2, max_length=500)
    student_id: str = "demo-student"
    student_name: str = "Demo Student"


class AppointmentStatusUpdate(BaseModel):
    status: Literal["APPROVED", "REJECTED", "CANCELLED"]