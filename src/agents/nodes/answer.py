from src.agents.state import AgentState
from src.services.llm import LLMService


def generate_answer(state: AgentState) -> AgentState:
    llm = LLMService()
    answer = llm.text(
        system_prompt=(
            "You are a Vinpearl/VinWonders travel support assistant. "
            "Answer only from the supplied retrieved context. "
            "Use the user's original language. "
            "Be useful and concise. Do not invent prices, availability, operating hours, "
            "policies, or payment results. For payment questions, provide guidance only "
            "and never claim to execute a transaction. "
            "When relevant, mention the source destination/property in plain language."
        ),
        user_prompt=f"""
User question:
{state["user_message"]}

Retrieved context:
{state.get("context", "")}
""",
    )
    return {"answer": answer}
