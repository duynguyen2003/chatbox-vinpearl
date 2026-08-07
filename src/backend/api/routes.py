from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ..agents.graph import agent_graph
from ..models.chat import ChatRequest, ChatResponse, SourceItem
from ..services.memory import MemoryService

router = APIRouter(prefix="/api/v1", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # Tin nhắn đầu tiên: tự tạo session_id.
    # Tin nhắn sau: frontend gửi lại session_id cũ.
    session_id = request.session_id or f"SES-{uuid4().hex}"

    try:
        state = agent_graph.invoke(
            {
                "user_message": request.message,
                "session_id": session_id,
                "user_id": request.user_id,
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    sources = []

    for item in state.get("retrieved_documents", []):
        metadata = item.get("metadata", {})

        sources.append(
            SourceItem(
                source_file=metadata.get("source_file", "unknown"),
                category=metadata.get("category"),
                path=metadata.get("path"),
                score=item.get("score"),
            )
        )

    return ChatResponse(
        answer=state.get("answer", ""),
        session_id=state.get("session_id") or session_id,
        language=state.get("original_language", "unknown"),
        route=state.get("route", "unknown"),
        ticket_id=state.get("ticket_id"),
        sources=sources,
    )


@router.delete("/chat/{session_id}/history")
def clear_chat_history(session_id: str) -> dict[str, int | str]:
    deleted = MemoryService().clear(session_id)

    return {
        "session_id": session_id,
        "deleted_turns": deleted,
    }