"""Chat API — accepts both authenticated and demo/anonymous requests."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.web_mvp import store
from app.web_mvp.schemas import ChatRequest, ChatResponse
from app.web_mvp.services import answer_chat

router = APIRouter(prefix="/api", tags=["chat"])

_optional_bearer = HTTPBearer(auto_error=False)


async def _optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
) -> dict[str, Any] | None:
    if not credentials:
        return None
    try:
        from app.web_mvp.auth import decode_token
        return decode_token(credentials.credentials)
    except HTTPException:
        return None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    token: dict[str, Any] | None = Depends(_optional_user),
) -> ChatResponse:
    if not store.store_ready():
        raise HTTPException(status_code=503, detail="Campus data store is unavailable")

    # Use authenticated user's ID if available; otherwise use the demo/anonymous student_id
    student_id = request.student_id
    if token and token.get("role") in {"student", "admin"}:
        student_id = token.get("sub", student_id)

    reply, intent, language, session_id, verified, sources = await answer_chat(
        request.message.strip(), request.session_id, student_id
    )
    return ChatResponse(
        message=reply,
        intent=intent,
        language=language,
        session_id=session_id,
        verified=verified,
        sources=sources,
    )


@router.get("/chat/sessions")
async def get_chat_sessions(token: dict[str, Any] = Depends(_optional_user)):
    if not token or token.get("role") not in {"student", "admin"}:
        raise HTTPException(status_code=401, detail="Only authenticated students can view chat history")
    student_id = token["sub"]
    return await store.list_chat_sessions(student_id)


@router.get("/chat/sessions/{session_id}")
async def get_chat_session_details(session_id: str, token: dict[str, Any] = Depends(_optional_user)):
    if not token or token.get("role") not in {"student", "admin"}:
        raise HTTPException(status_code=401, detail="Only authenticated students can view chat history")
    student_id = token["sub"]
    session = await store.get_chat_session(session_id, student_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session