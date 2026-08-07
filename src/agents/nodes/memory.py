from src.agents.state import AgentState
from src.services.memory import MemoryService


def load_conversation_memory(state: AgentState) -> AgentState:
    memory = MemoryService()
    turns = memory.load_recent(state.get("session_id"))
    return {
        "conversation_turns": turns,
        "conversation_history": memory.format_for_prompt(turns),
    }


def save_conversation_memory(state: AgentState) -> AgentState:
    MemoryService().append_turn(
        session_id=state.get("session_id"),
        user_id=state.get("user_id"),
        user_message=state.get("user_message", ""),
        assistant_answer=state.get("answer", ""),
        language=state.get("original_language", "unknown"),
        route=state.get("route", "unknown"),
        rag_query=state.get("rag_query"),
        ticket_id=state.get("ticket_id"),
    )
    return {}
