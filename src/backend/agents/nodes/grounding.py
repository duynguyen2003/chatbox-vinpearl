from src.backend.agents.state import AgentState
from src.backend.services.llm import LLMService


def validate_grounding(state: AgentState) -> AgentState:
    """Validate the drafted answer against RAG context and repair it once if needed."""
    draft = str(state.get("answer") or "").strip()
    context = str(state.get("context") or "").strip()

    if not draft or not context:
        return {
            "grounding_passed": False,
            "grounding_reason": "Answer or retrieved context is empty.",
        }

    llm = LLMService()
    result = llm.json(
        system_prompt=(
            "You are a strict grounding validator for a RAG system. "
            "Judge ONLY whether the DRAFT_ANSWER is supported by RETRIEVED_CONTEXT. "
            "Do not use your own knowledge to validate a claim. "
            "A claim is supported only when the retrieved context explicitly contains the fact "
            "or directly supports the paraphrase. "
            "Named entities not present in the retrieved context are unsupported. "
            "URLs must appear exactly in the retrieved context to be supported. "
            "Missing URL metadata does not invalidate other supported facts. "
            "If unsupported content exists, return a corrected answer that removes all unsupported "
            "claims and introduces NO new facts. Preserve the user's language. "
            "Return JSON with exactly these keys: grounded, reason, unsupported_claims, corrected_answer."
        ),
        user_prompt=f"""
USER_QUESTION:
{state.get("user_message", "")}

RETRIEVED_CONTEXT:
{context}

DRAFT_ANSWER:
{draft}

Return exactly this JSON shape:
{{
  "grounded": true,
  "reason": "brief reason",
  "unsupported_claims": [],
  "corrected_answer": ""
}}
""",
    )

    grounded = bool(result.get("grounded", False))
    reason = str(result.get("reason") or "No grounding reason returned.").strip()
    unsupported = result.get("unsupported_claims") or []
    if not isinstance(unsupported, list):
        unsupported = [str(unsupported)]

    if grounded:
        final_answer = draft
    else:
        corrected = str(result.get("corrected_answer") or "").strip()
        final_answer = corrected or (
            "The current knowledge base does not contain enough grounded information "
            "to answer this request safely."
        )

    print("\n===== GROUNDING VALIDATION =====")
    print(f"Grounded: {grounded}")
    print(f"Reason: {reason}")
    if unsupported:
        print("Unsupported claims:")
        for claim in unsupported:
            print(f"- {claim}")
    print("================================\n")

    return {
        "answer": final_answer,
        "grounding_passed": grounded,
        "grounding_reason": reason,
        "unsupported_claims": [str(item) for item in unsupported],
    }
