from __future__ import annotations

from typing import Literal

from src.backend.agents.state import AgentState
from src.backend.services.llm import LLMService
from src.backend.services.query_parser import normalize_text


RequestMode = Literal["information", "support_action"]
ResolutionMode = Literal["information_only", "self_serve", "human_required"]


def _heuristic_fallback(message: str) -> tuple[RequestMode, ResolutionMode, str, float]:
    """Conservative fallback used only when the semantic classifier fails.

    Keywords are signals, not the primary ticket trigger. A human-required result
    needs either a clearly case-specific transaction/booking problem or a personal
    action request that the chatbot cannot perform itself.
    """
    text = normalize_text(message)

    personal_markers = (
        "toi ", "cua toi", "cho toi", "giao dich cua", "booking cua",
        "my ", "me ", "i was", "i have", "i did",
    )
    operational_markers = (
        "kiem tra giao dich", "check my transaction", "kiem tra booking", "check my booking",
        "hoan tien cho toi", "refund my", "huy booking", "cancel my booking",
        "doi booking", "change my booking", "xac minh", "verify my",
        "toi de quen do", "i lost", "khong nhan duoc xac nhan", "did not receive confirmation",
    )
    transaction_problem_markers = (
        "bi tru tien 2 lan", "bi tru tien hai lan", "charged twice", "double charged",
        "tien da bi tru", "money was charged",
    )
    has_personal = any(marker in f"{text} " for marker in personal_markers)
    has_operational = any(marker in text for marker in operational_markers)
    has_transaction_problem = any(marker in text for marker in transaction_problem_markers)
    if has_operational or (has_personal and has_transaction_problem):
        return (
            "support_action",
            "human_required",
            "Fallback detected a personal case requiring record access, verification, or an operational action.",
            0.90,
        )

    problem_markers = (
        "bi loi",
        "khong dung duoc",
        "khong su dung duoc",
        "khong thanh toan duoc",
        "loi thanh toan",
        "error",
        "failed",
        "not working",
        "cannot use",
        "can t use",
        "khong nhan duoc",
        "problem",
        "su co",
    )
    guidance_markers = (
        "lam sao",
        "cach xu ly",
        "huong dan",
        "how to",
        "what should i do",
        "help me troubleshoot",
    )
    if any(marker in text for marker in problem_markers):
        return (
            "support_action",
            "self_serve",
            "Fallback detected a troubleshooting/support request that may be solvable with grounded guidance.",
            0.70,
        )

    if any(marker in text for marker in guidance_markers):
        return (
            "support_action",
            "self_serve",
            "Fallback detected a request for procedural guidance.",
            0.65,
        )

    return (
        "information",
        "information_only",
        "Fallback classified the message as an informational request.",
        0.60,
    )


def analyze_support_request(state: AgentState) -> AgentState:
    """Classify whether this turn is information, self-service support, or human action.

    This node deliberately does NOT create tickets. It only provides semantic
    decision metadata. The assessment/router later combines this result with RAG
    sufficiency so that:
      - information + no data => safe no-data answer
      - self-serve + grounded guidance => answer
      - self-serve + insufficient guidance => ticket
      - human-required => ticket even if a general policy exists in RAG
    """
    message = state.get("user_message", "")
    llm = LLMService()

    try:
        result = llm.json(
            system_prompt=(
                "You are a support-triage classifier for a Vinpearl/VinWonders RAG assistant. "
                "Classify the CURRENT user message semantically; do not trigger on keywords alone. "
                "Return request_mode and resolution_mode. request_mode=information when the user only "
                "asks for facts, availability, policy, prices, locations, or general explanations. "
                "request_mode=support_action when the user reports a problem or asks for help resolving it. "
                "resolution_mode=information_only for factual questions. resolution_mode=self_serve when "
                "the user has a problem but grounded instructions from the knowledge base could reasonably "
                "solve it without accessing or changing a personal record. resolution_mode=human_required "
                "ONLY when the user asks for or clearly needs case-specific investigation, verification, "
                "account/transaction/booking access, cancellation/change/refund execution, lost-property "
                "handling, complaint handling, or another operational action the chatbot cannot perform. "
                "A phrase like 'help me' by itself is NOT enough for human_required. A known policy or guide "
                "does not remove the need for human support when the requested action is case-specific. "
                "Examples: 'What is the refund policy?' => information/information_only. "
                "'Payment fails, how do I fix it?' => support_action/self_serve. "
                "'I was charged twice; check my transaction' => support_action/human_required. "
                "'My booking was not confirmed; please check it' => support_action/human_required. "
                "Use conversation history only to resolve references, never to inherit an old support mode. "
                "Return valid JSON only with request_mode, resolution_mode, reason, confidence."
            ),
            user_prompt=f"""
Current message:
{message}

Standalone retrieval query:
{state.get('rag_query', '')}

Detected destination(s):
{', '.join(state.get('detected_destination_names', [])) or 'none'}

Detected intent(s):
{', '.join(state.get('detected_intents', [])) or state.get('detected_intent') or 'none'}

Return exactly:
{{
  "request_mode": "information|support_action",
  "resolution_mode": "information_only|self_serve|human_required",
  "reason": "brief semantic reason",
  "confidence": 0.0
}}
""",
        )

        request_mode = str(result.get("request_mode") or "").strip()
        resolution_mode = str(result.get("resolution_mode") or "").strip()
        reason = str(result.get("reason") or "").strip()
        try:
            confidence = float(result.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0

        if request_mode not in {"information", "support_action"}:
            raise ValueError(f"invalid request_mode={request_mode!r}")
        if resolution_mode not in {"information_only", "self_serve", "human_required"}:
            raise ValueError(f"invalid resolution_mode={resolution_mode!r}")

        # Keep the pair logically consistent.
        if request_mode == "information":
            resolution_mode = "information_only"
        elif resolution_mode == "information_only":
            resolution_mode = "self_serve"

        # Narrow deterministic safety override: only a strong PERSONAL operational
        # signal may upgrade to human_required. Generic words such as "help",
        # "error", or "refund" never create a ticket by themselves.
        fallback_request, fallback_resolution, fallback_reason, fallback_confidence = _heuristic_fallback(message)
        if fallback_resolution == "human_required" and resolution_mode != "human_required":
            request_mode = fallback_request
            resolution_mode = fallback_resolution
            reason = f"{reason} Safety override: {fallback_reason}".strip()
            confidence = max(confidence, fallback_confidence)

        confidence = max(0.0, min(1.0, confidence))
        if not reason:
            reason = "Semantic support triage completed."

    except Exception as exc:
        request_mode, resolution_mode, reason, confidence = _heuristic_fallback(message)
        reason = f"{reason} Classifier fallback reason: {exc}"

    print("\n===== SUPPORT TRIAGE =====")
    print(f"Question: {message}")
    print(f"Request mode: {request_mode}")
    print(f"Resolution mode: {resolution_mode}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Reason: {reason}")
    print("==========================\n")

    return {
        "request_mode": request_mode,
        "resolution_mode": resolution_mode,
        "support_triage_reason": reason,
        "support_triage_confidence": confidence,
    }
