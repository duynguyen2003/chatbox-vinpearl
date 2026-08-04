from langgraph.graph import END, START, StateGraph

from src.agents.nodes.answer import generate_answer
from src.agents.nodes.classify import classify_input
from src.agents.nodes.language import detect_language_and_translate
from src.agents.nodes.retrieval import assess_information, retrieve_context
from src.agents.nodes.static_responses import greeting_response, out_of_scope_response
from src.agents.nodes.ticket import create_ticket
from src.agents.state import AgentState


def route_after_classification(state: AgentState) -> str:
    return state["route"]


def route_after_assessment(state: AgentState) -> str:
    return "answer" if state.get("enough_information") else "ticket"


builder = StateGraph(AgentState)

builder.add_node("language", detect_language_and_translate)
builder.add_node("classify", classify_input)
builder.add_node("greeting", greeting_response)
builder.add_node("out_of_scope", out_of_scope_response)
builder.add_node("retrieve", retrieve_context)
builder.add_node("assess", assess_information)
builder.add_node("answer", generate_answer)
builder.add_node("ticket", create_ticket)

builder.add_edge(START, "language")
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

builder.add_edge("greeting", END)
builder.add_edge("out_of_scope", END)
builder.add_edge("answer", END)
builder.add_edge("ticket", END)

agent_graph = builder.compile()
