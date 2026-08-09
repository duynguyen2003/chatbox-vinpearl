import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ..agents.graph import agent_graph
from ..models.chat import ChatRequest, ChatResponse, SourceItem
from ..services.memory import MemoryService
from ..services.query_parser import load_destination_catalog, normalize_text
from ..services.source_reranker import get_source_reranker

router = APIRouter(prefix="/api/v1", tags=["agent"])

URL_KEYS = (
    "source_url",
    "canonical_url",
    "page_url",
    "detail_url",
    "booking_url",
    "terms_url",
    "room_page_url",
    "dining_page_url",
    "map_url",
    "target_url",
    "to_url",
    "path",
)


def _phrase_in_text(text: str, phrase: str) -> bool:
    if not text or not phrase:
        return False
    return f" {phrase} " in f" {text} "


def _document_matches_destination_ids(item: dict, destination_ids: set[str]) -> bool:
    if not destination_ids:
        return True

    metadata = item.get("metadata", {}) or {}
    matched_id = str(item.get("matched_destination_id") or "").strip()
    if matched_id and matched_id in destination_ids:
        return True

    metadata_destination = str(metadata.get("destination_id") or "").strip()
    if metadata_destination and metadata_destination in destination_ids:
        return True

    searchable = normalize_text(
        " ".join(
            [
                str(metadata.get("entity_name") or ""),
                str(metadata.get("source_file") or ""),
                str(item.get("text") or ""),
            ]
        )
    )
    catalog = load_destination_catalog()
    for destination_id in destination_ids:
        destination = catalog.get(destination_id) or {}
        aliases = destination.get("normalized_aliases", [])
        if any(_phrase_in_text(searchable, alias) for alias in aliases):
            return True
    return False


def _url_destination_ids(url: str | None) -> set[str]:
    """Return known destinations explicitly encoded in a URL/path."""
    normalized = normalize_text(url or "")
    if not normalized:
        return set()

    found: set[str] = set()
    for destination_id, destination in load_destination_catalog().items():
        for alias in destination.get("normalized_aliases", []):
            # Ignore very short aliases in URLs to reduce accidental matches.
            if len(alias) < 4:
                continue
            if _phrase_in_text(normalized, alias):
                found.add(str(destination_id))
                break
    return found


def _url_conflicts(url: str | None, target_destination_ids: set[str]) -> bool:
    if not url or not target_destination_ids:
        return False
    url_destinations = _url_destination_ids(url)
    # Generic URLs such as /grand-world/ encode no destination and are allowed.
    if not url_destinations:
        return False
    return url_destinations.isdisjoint(target_destination_ids)


def _candidate_urls(item: dict) -> list[str]:
    metadata = item.get("metadata", {}) or {}
    urls: list[str] = []
    for key in URL_KEYS:
        value = str(metadata.get(key) or "").strip()
        if value and value not in urls:
            urls.append(value)

    # Sometimes the row text contains a more specific entity URL than the first
    # metadata URL selected at ingest time. Prefer a non-conflicting URL if found.
    for value in re.findall(r"https?://[^\s<>\]\)\}]+", str(item.get("text") or "")):
        cleaned = value.rstrip(".,;:")
        if cleaned and cleaned not in urls:
            urls.append(cleaned)
    return urls


def _best_source_path(item: dict, target_destination_ids: set[str]) -> str | None:
    candidates = _candidate_urls(item)
    if not candidates:
        return None
    for url in candidates:
        if not _url_conflicts(url, target_destination_ids):
            return url
    # Every URL points to a different known destination: suppress the link rather
    # than displaying a misleading citation.
    return None


def _source_item_from_document(
    item: dict,
    target_destination_ids: set[str],
) -> SourceItem:
    metadata = item.get("metadata", {}) or {}
    source_file = (
        metadata.get("entity_name")
        or metadata.get("source_file")
        or metadata.get("entity_type")
        or metadata.get("source_table")
        or "unknown"
    )
    category = (
        metadata.get("entity_type")
        or metadata.get("category")
        or metadata.get("source_table")
    )
    path = item.get("best_source_url") or _best_source_path(item, target_destination_ids)

    return SourceItem(
        source_file=str(source_file),
        category=str(category) if category is not None else None,
        path=path,
        score=item.get("score"),
    )


def _build_sources(state: dict) -> list[SourceItem]:
    destination_ids = {
        str(value)
        for value in state.get("detected_destination_ids", [])
        if str(value).strip()
    }
    retrieved_documents = state.get("retrieved_documents", []) or []
    answer = str(state.get("answer") or "")

    # Citation selection happens AFTER answer generation. The answer may mention
    # only a subset of the retrieved context (e.g. Grand World Hanoi), so showing
    # retrieved_documents[:5] can expose semantically related but misleading URLs.
    # Re-rank sources against the final answer and resolve the best direct URL for
    # each entity actually named in that answer.
    try:
        documents = get_source_reranker().rerank(
            answer=answer,
            retrieved_documents=retrieved_documents,
            destination_ids=destination_ids,
            max_sources=5,
        )
    except Exception as exc:
        print(f"[SOURCE RERANK] fallback because of error: {exc}")
        documents = list(retrieved_documents)

    # Safety guard: even a reranked source must not contradict the hard
    # destination. If reranking found fewer than five trustworthy sources, return
    # fewer sources instead of padding with unrelated pages.
    if destination_ids:
        documents = [
            item
            for item in documents
            if _document_matches_destination_ids(item, destination_ids)
        ]

    sources: list[SourceItem] = []
    seen_urls: set[str] = set()
    seen_entities: set[str] = set()
    for item in documents:
        source = _source_item_from_document(item, destination_ids)

        # A missing URL must never suppress valid evidence. The frontend can render
        # this source as plain text (path=None) while the answer still uses the data.
        normalized_entity = normalize_text(source.source_file)
        if source.path and source.path in seen_urls:
            continue
        if normalized_entity and normalized_entity in seen_entities:
            continue

        if source.path:
            seen_urls.add(source.path)
        if normalized_entity:
            seen_entities.add(normalized_entity)
        sources.append(source)
        if len(sources) >= 5:
            break

    return sources


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
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

    sources = _build_sources(state)

    return ChatResponse(
        answer=state.get("answer", ""),
        session_id=state.get("session_id") or session_id,
        language=state.get("original_language", "unknown"),
        route=state.get("route", "unknown"),
        ticket_id=state.get("ticket_id"),
        sources=sources,
        debug={
            "enough_information": state.get("enough_information"),
            "assessment_reason": state.get("assessment_reason"),
            "best_relevance_score": state.get("best_relevance_score"),
            "retrieved_count": len(state.get("retrieved_documents", [])),
            "source_count": len(sources),
            "sources_without_url": sum(1 for item in sources if not item.path),
            "retrieval_mode": state.get("retrieval_mode"),
            "detected_destinations": state.get("detected_destination_names", []),
            "recent_destinations": state.get("recent_destination_summary"),
        },
    )


@router.delete("/chat/{session_id}/history")
def clear_chat_history(session_id: str) -> dict[str, int | str]:
    deleted = MemoryService().clear(session_id)
    return {"session_id": session_id, "deleted_turns": deleted}
