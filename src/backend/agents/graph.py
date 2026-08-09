from langgraph.graph import END, START, StateGraph

from src.backend.agents.nodes.answer import generate_answer
from src.backend.agents.nodes.classify import classify_input
from src.backend.agents.nodes.language import detect_language_and_translate
from src.backend.agents.nodes.grounding import validate_grounding
from src.backend.agents.nodes.memory import (
    load_conversation_memory,
    save_conversation_memory,
)
from src.backend.agents.nodes.retrieval import assess_information, retrieve_context
from src.backend.agents.nodes.static_responses import greeting_response, out_of_scope_response
from src.backend.agents.nodes.ticket import create_ticket
from src.backend.agents.state import AgentState


def route_after_classification(state: AgentState) -> str:
    return state["route"]


def route_after_assessment(state: AgentState) -> str:
    return "answer" if state.get("enough_information") else "ticket"


builder = StateGraph(AgentState)

builder.add_node("load_memory", load_conversation_memory)
builder.add_node("language", detect_language_and_translate)
builder.add_node("classify", classify_input)
builder.add_node("greeting", greeting_response)
builder.add_node("out_of_scope", out_of_scope_response)
builder.add_node("retrieve", retrieve_context)
builder.add_node("assess", assess_information)
builder.add_node("answer", generate_answer)
builder.add_node("grounding", validate_grounding)
builder.add_node("ticket", create_ticket)
builder.add_node("save_memory", save_conversation_memory)

builder.add_edge(START, "load_memory")
builder.add_edge("load_memory", "language")
builder.add_edge("language", "classify")

builder.add_conditional_edges(
    "classify",
    route_after_classification,
    {
        "greeting": "greeting",
        "out_of_scope": "out_of_scope",
        "rag": "retrieve",
    },
)

builder.add_edge("retrieve", "assess")
builder.add_conditional_edges(
    "assess",
    route_after_assessment,
    {
        "answer": "answer",
        "ticket": "ticket",
    },
)

builder.add_edge("greeting", "save_memory")
builder.add_edge("out_of_scope", "save_memory")
builder.add_edge("answer", "grounding")
builder.add_edge("grounding", "save_memory")
builder.add_edge("ticket", "save_memory")
builder.add_edge("save_memory", END)

agent_graph = builder.compile()
