from src.agents.state import AgentState
from src.services.llm import LLMService
from src.services.ticket import TicketService


def create_ticket(state: AgentState) -> AgentState:
    ticket_id = TicketService().create(
        message=state["user_message"],
        language=state.get("original_language", "unknown"),
        session_id=state.get("session_id"),
        user_id=state.get("user_id"),
        reason="Insufficient information in the Vinpearl knowledge base",
    )

    llm = LLMService()
    answer = llm.text(
        system_prompt=(
            "Reply in the user's original language. Explain that the available knowledge "
            "base does not contain enough reliable information, that a support ticket "
            "has been created, and a human support team will follow up. "
            "Include the ticket ID exactly as provided."
        ),
        user_prompt=f"""
Original request:
{state["user_message"]}

Ticket ID:
{ticket_id}
""",
    )
    return {"ticket_id": ticket_id, "answer": answer}
