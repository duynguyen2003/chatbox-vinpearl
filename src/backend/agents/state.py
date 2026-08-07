from typing import Any, Literal, TypedDict


RouteName = Literal["greeting", "out_of_scope", "rag"]


class AgentState(TypedDict, total=False):
    user_message: str
    session_id: str | None
    user_id: str | None

    conversation_turns: list[dict[str, Any]]
    conversation_history: str

    original_language: str
    rag_query: str
    route: RouteName

    retrieved_documents: list[dict[str, Any]]
    context: str
    enough_information: bool

    answer: str
    ticket_id: str | None
