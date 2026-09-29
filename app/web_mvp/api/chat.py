from fastapi import APIRouter, HTTPException

from app.web_mvp import store
from app.web_mvp.schemas import ChatRequest, ChatResponse
from app.web_mvp.services import answer_chat

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not store.store_ready():
        raise HTTPException(status_code=503, detail="Campus data store is unavailable")
    reply, intent, language, session_id, verified, sources = await answer_chat(
        request.message.strip(), request.session_id, request.student_id
    )
    return ChatResponse(
        message=reply,
        intent=intent,
        language=language,
        session_id=session_id,
        verified=verified,
        sources=sources,
    )