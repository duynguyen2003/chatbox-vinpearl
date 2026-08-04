from src.agents.state import AgentState
from src.services.llm import LLMService


def detect_language_and_translate(state: AgentState) -> AgentState:
    llm = LLMService()
    result = llm.json(
        system_prompt=(
            "You detect the language of a travel-support message and prepare an "
            "English retrieval query for an English Vinpearl/VinWonders knowledge base."
        ),
        user_prompt=f"""
Message:
{state["user_message"]}

Return:
{{
  "language": "BCP-47-like language code, e.g. vi, en, ko, ja, zh",
  "rag_query": "faithful English translation optimized for retrieval"
}}
""",
    )

    return {
        "original_language": str(result.get("language", "en")),
        "rag_query": str(result.get("rag_query", state["user_message"])),
    }
