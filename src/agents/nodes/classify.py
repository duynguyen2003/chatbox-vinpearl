from src.agents.state import AgentState
from src.services.llm import LLMService


def classify_input(state: AgentState) -> AgentState:
    llm = LLMService()
    result = llm.json(
        system_prompt=(
            "Classify a user message for a Vinpearl/VinWonders travel support agent. "
            "The allowed routes are: greeting, rag, out_of_scope. "
            "Use greeting only for pure greeting/small talk without a substantive request. "
            "Use rag for Vinpearl, VinWonders, destinations, hotels, rooms, dining, "
            "entertainment, golf, meetings/events, promotions, policies, FAQs, and "
            "payment guidance. The agent only guides payment; it does not process payment. "
            "Everything else is out_of_scope."
        ),
        user_prompt=f"""
Original message:
{state["user_message"]}

English retrieval version:
{state.get("rag_query", "")}

Return:
{{"route": "greeting|rag|out_of_scope"}}
""",
    )
    route = str(result.get("route", "out_of_scope"))
    if route not in {"greeting", "rag", "out_of_scope"}:
        route = "out_of_scope"
    return {"route": route}
