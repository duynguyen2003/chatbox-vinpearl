from typing import Any, Literal, TypedDict


RouteName = Literal["greeting", "out_of_scope", "rag"]


class AgentState(TypedDict, total=False):
    user_message: str
    session_id: str | None
    user_id: str | None

    conversation_turns: list[dict[str, Any]]
    conversation_history: str
    recent_destinations: list[dict[str, str]]
    recent_destination_summary: str

    original_language: str
    rag_query: str
    route: RouteName

    retrieved_documents: list[dict[str, Any]]
    context: str

    # Hybrid retrieval diagnostics.
    retrieval_mode: str
    detected_destination: str | None
    detected_destination_name: str | None
    detected_destinations: list[dict[str, Any]]
    detected_destination_ids: list[str]
    detected_destination_names: list[str]
    detected_intent: str | None
    keyword_candidate_count: int
    missing_destination_ids: list[str]

    enough_information: bool
    assessment_reason: str
    best_relevance_score: float

    answer: str

    # Post-generation grounding diagnostics.
    grounding_passed: bool
    grounding_reason: str
    unsupported_claims: list[str]

    ticket_id: str | None
