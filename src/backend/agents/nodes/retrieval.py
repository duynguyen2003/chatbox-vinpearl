from src.backend.agents.state import AgentState
from src.backend.config import get_settings
from src.backend.services.llm import LLMService
from src.backend.services.rag import RAGService


def retrieve_context(state: AgentState) -> AgentState:
    rag = RAGService()
    documents, diagnostics = rag.hybrid_search(
        query=state["rag_query"],
        user_message=state.get("user_message", ""),
    )
    return {
        "retrieved_documents": documents,
        "context": rag.build_context(documents),
        "retrieval_mode": diagnostics.get("mode"),
        "detected_destination": diagnostics.get("destination_id"),
        "detected_destination_name": diagnostics.get("destination_name"),
        "detected_destinations": diagnostics.get("destinations", []),
        "detected_destination_ids": diagnostics.get("destination_ids", []),
        "detected_destination_names": diagnostics.get("destination_names", []),
        "detected_intent": diagnostics.get("intent"),
        "keyword_candidate_count": int(diagnostics.get("keyword_candidate_count") or 0),
        "missing_destination_ids": diagnostics.get("missing_destination_ids", []),
    }


def assess_information(state: AgentState) -> AgentState:
    documents = state.get("retrieved_documents", [])
    settings = get_settings()

    if not documents:
        return {
            "enough_information": False,
            "assessment_reason": "No matching documents were retrieved for the requested destination(s).",
            "best_relevance_score": 0.0,
        }

    scores = [float(item.get("score", 0.0) or 0.0) for item in documents]
    best_score = max(scores, default=0.0)

    if best_score < settings.min_relevance_score:
        return {
            "enough_information": False,
            "assessment_reason": (
                f"Best relevance score {best_score:.4f} is below the configured "
                f"minimum {settings.min_relevance_score:.4f}."
            ),
            "best_relevance_score": best_score,
        }

    context = state.get("context", "").strip()
    if not context:
        return {
            "enough_information": False,
            "assessment_reason": "Retrieved documents exist but the assembled context is empty.",
            "best_relevance_score": best_score,
        }

    missing = state.get("missing_destination_ids", [])
    detected_ids = state.get("detected_destination_ids", [])
    if len(detected_ids) > 1 and missing:
        return {
            "enough_information": False,
            "assessment_reason": (
                "Comparison requested across multiple destinations but the knowledge base "
                f"has no matching retrieval candidates for: {', '.join(missing)}."
            ),
            "best_relevance_score": best_score,
        }

    llm = LLMService()
    result = llm.json(
        system_prompt=(
            "You are an evidence sufficiency judge for a Vinpearl/VinWonders RAG assistant. "
            "Decide only whether the supplied retrieved context contains enough information "
            "to give a useful, grounded answer to the user's current question. Do not use "
            "outside knowledge. For comparison questions, verify that the context includes "
            "useful evidence for every destination named in the standalone retrieval query. "
            "Mark enough=true when the context directly contains the requested facts or enough "
            "information for a useful partial answer. Do not mark false merely because every "
            "possible detail is absent. Mark enough=false only when key facts are genuinely "
            "missing, contradictory, require real-time data not present, or require a human action. "
            "Return valid JSON only with keys enough and reason."
        ),
        user_prompt=f"""
Question:
{state["user_message"]}

Standalone retrieval query:
{state.get("rag_query", "")}

Recently discussed destinations:
{state.get("recent_destination_summary", "(none)")}

Detected destinations:
{', '.join(state.get("detected_destination_names", [])) or 'none'}

Detected intent:
{state.get("detected_intent") or "none"}

Retrieval mode:
{state.get("retrieval_mode", "unknown")}

Best retrieval score:
{best_score:.4f}

Retrieved context:
{context}

Return exactly:
{{"enough": true, "reason": "brief evidence-based reason"}}
""",
    )

    enough = bool(result.get("enough", False))
    reason = str(result.get("reason") or "LLM judge returned no reason.").strip()

    print("\n===== RAG ASSESSMENT =====")
    print(f"Question: {state.get('user_message', '')}")
    print(f"RAG query: {state.get('rag_query', '')}")
    print(f"Retrieval mode: {state.get('retrieval_mode', 'unknown')}")
    print(f"Recent memory destinations: {state.get('recent_destination_summary', '(none)')}")
    print(
        "Detected: "
        f"destinations={state.get('detected_destination_names', [])} "
        f"intent={state.get('detected_intent')} "
        f"keyword_candidates={state.get('keyword_candidate_count', 0)}"
    )
    print(f"Best score: {best_score:.4f}")
    for index, item in enumerate(documents, start=1):
        metadata = item.get("metadata", {}) or {}
        print(
            f"{index}. score={float(item.get('score', 0.0) or 0.0):.4f} "
            f"semantic={float(item.get('semantic_score', 0.0) or 0.0):.4f} "
            f"keyword={float(item.get('keyword_score', 0.0) or 0.0):.4f} "
            f"dest={item.get('matched_destination_name') or metadata.get('destination_id')} "
            f"type={metadata.get('entity_type') or metadata.get('category') or 'unknown'} "
            f"name={metadata.get('entity_name') or metadata.get('source_file') or 'unknown'}"
        )
    print(f"Enough: {enough}")
    print(f"Reason: {reason}")
    print("==========================\n")

    return {
        "enough_information": enough,
        "assessment_reason": reason,
        "best_relevance_score": best_score,
    }
