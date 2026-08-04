from fastapi import APIRouter, HTTPException

from src.agents.graph import agent_graph
from src.models.chat import ChatRequest, ChatResponse, SourceItem

router = APIRouter(prefix="/api/v1", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        state = agent_graph.invoke(
            {
                "user_message": request.message,
                "session_id": request.session_id,
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
        language=state.get("original_language", "unknown"),
        route=state.get("route", "unknown"),
        ticket_id=state.get("ticket_id"),
        sources=sources,
    )
