from src.backend.agents.state import AgentState
from src.backend.services.llm import LLMService


def _allowed_entities(state: AgentState) -> str:
    """Build a small entity allow-list from retrieved metadata only."""
    names: list[str] = []
    seen: set[str] = set()

    for item in state.get("retrieved_documents", []):
        metadata = item.get("metadata", {}) or {}
        for key in ("entity_name", "source_file", "title", "name"):
            value = str(metadata.get(key) or "").strip()
            if value and value.lower() not in seen:
                seen.add(value.lower())
                names.append(value)

    return "\n".join(f"- {name}" for name in names[:80]) or "(none)"


def generate_answer(state: AgentState) -> AgentState:
    """Generate a factual answer using retrieved RAG context as the sole evidence source."""
    llm = LLMService()

    answer = llm.text(
        system_prompt=(
            "You are a strictly grounded Vinpearl/VinWonders RAG assistant. "
            "RETRIEVED_CONTEXT is the ONLY factual source of truth for the answer. "
            "Do not use pretrained knowledge, general knowledge, web knowledge, assumptions, "
            "or facts remembered from previous assistant answers. "
            "The user's question and standalone retrieval query may be used only to understand "
            "what is being asked; they are not factual evidence. "
            "Every factual claim and every named attraction, hotel, venue, service, event, "
            "promotion, price, schedule, address, phone number, policy, and URL in the final answer "
            "must be explicitly supported by RETRIEVED_CONTEXT. "
            "If a named entity is not present in RETRIEVED_CONTEXT, do not mention it. "
            "Never fill gaps with your own knowledge. Never fabricate or infer a URL. "
            "A retrieved block remains valid evidence even when its URL is empty or None; "
            "missing URL metadata must never cause supported factual content to be omitted. "
            "If the context is partial, answer only with the supported partial information. "
            "If the context cannot support a useful answer, say that the current knowledge base "
            "does not contain enough information. "
            "For broad destination questions, cover the distinct relevant entities present in the "
            "context before expanding on child events or details. "
            "Reply in the user's current original language. Be clear and concise."
        ),
        user_prompt=f"""
Current user question:
{state["user_message"]}

Standalone retrieval query:
{state.get("rag_query", "")}

Detected destinations:
{', '.join(state.get("detected_destination_names", [])) or 'none'}

Entities explicitly identified in retrieved metadata (supporting hint only):
{_allowed_entities(state)}

RETRIEVED_CONTEXT — the sole factual source of truth:
{state.get("context", "")}

Important: do not use previous assistant answers as evidence. If something is not supported by
RETRIEVED_CONTEXT, omit it.
""",
    )

    return {"answer": answer}
