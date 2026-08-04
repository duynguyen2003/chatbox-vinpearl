from src.agents.state import AgentState
from src.config import get_settings
from src.services.llm import LLMService
from src.services.rag import RAGService


def retrieve_context(state: AgentState) -> AgentState:
    rag = RAGService()
    documents = rag.search(state["rag_query"])
    return {
        "retrieved_documents": documents,
        "context": rag.build_context(documents),
    }


def assess_information(state: AgentState) -> AgentState:
    documents = state.get("retrieved_documents", [])
    settings = get_settings()

    if not documents:
        return {"enough_information": False}

    best_score = max(float(item.get("score", 0)) for item in documents)
    if best_score < settings.min_relevance_score:
        return {"enough_information": False}

    llm = LLMService()
    result = llm.json(
        system_prompt=(
            "Judge whether the retrieved Vinpearl/VinWonders context contains enough "
            "reliable information to answer the user's question. Do not use outside "
            "knowledge. If key details are missing, ambiguous, dynamic, or require a "
            "human action, mark false."
        ),
        user_prompt=f"""
Question:
{state["user_message"]}

Retrieved context:
{state.get("context", "")}

Return:
{{"enough": true, "reason": "brief reason"}}
""",
    )
    return {"enough_information": bool(result.get("enough", False))}
