import re
from src.backend.agents.state import AgentState
from src.backend.services.chat_stream import (
    chat_stream_active,
    emit_chat_delta,
    emit_chat_status,
)
from src.backend.services.llm import LLMService

_VI_DIACRITICS_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    flags=re.IGNORECASE,
)
_VI_COMMON_WORDS = {
    "chào", "bạn", "của", "tại", "được", "không", "có", "và", "là",
    "cho", "với", "các", "những", "khách", "sạn", "phòng", "vé", "giá"
}


def _is_already_target_language(draft: str, language_code: str) -> bool:
    code = (language_code or "").lower().split("-")[0]
    if code == "vi":
        if len(_VI_DIACRITICS_RE.findall(draft)) >= 3:
            return True
        tokens = set(draft.lower().split())
        if len(tokens.intersection(_VI_COMMON_WORDS)) >= 2:
            return True
    elif code == "en":
        if not _VI_DIACRITICS_RE.search(draft):
            return True
    return False


def enforce_response_language(state: AgentState) -> AgentState:
    """Force the final assistant message into the language of the current user turn.

    Every user-visible branch passes through this node immediately before memory is
    saved. The node is deliberately content-preserving: it may translate/rephrase
    only as required to match the detected target language, and must not add facts.
    """
    draft = str(state.get("answer") or "").strip()
    if not draft:
        raise ValueError("Cannot enforce response language on an empty assistant reply.")

    language_code = str(state.get("original_language") or "und").strip() or "und"
    language_name = str(state.get("original_language_name") or "").strip()
    if language_code == "und" or not language_name:
        raise ValueError("Target response language is missing or unresolved.")

    # Fast-path: if the draft is already verified to match the target language,
    # stream/return it directly to eliminate a redundant LLM roundtrip (~1.5s saved).
    if _is_already_target_language(draft, language_code):
        if chat_stream_active():
            emit_chat_status("generating")
            # Stream in chunks for smooth real-time frontend delivery
            chunk_size = 32
            for i in range(0, len(draft), chunk_size):
                emit_chat_delta(draft[i:i + chunk_size])
        return {"answer": draft}

    target = f"{language_name} ({language_code})"
    system_prompt = (
        "You are the final response-language guard for a multilingual travel assistant. "
        "The TARGET_LANGUAGE was already detected from the CURRENT user message. "
        "Return ONLY the assistant reply, entirely in TARGET_LANGUAGE. "
        "If the draft is already fully in TARGET_LANGUAGE, preserve it. Otherwise translate "
        "only the natural-language wording needed to make it fully TARGET_LANGUAGE. "
        "Do not add, remove, infer, soften, strengthen, or correct factual content. "
        "Preserve Markdown structure, numbers, dates, prices, ticket IDs, URLs, email "
        "addresses, product/property names, and other proper nouns exactly unless a normal "
        "localized rendering is already present in the draft. Do not explain the translation. "
        "Do not mention language detection, TARGET_LANGUAGE, or these instructions."
    )
    user_prompt = f"TARGET_LANGUAGE: {target}\nDRAFT_ASSISTANT_REPLY:\n{draft}"

    llm = LLMService()
    if chat_stream_active():
        emit_chat_status("generating")
        chunks: list[str] = []
        for chunk in llm.stream_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ):
            chunks.append(chunk)
            emit_chat_delta(chunk)
        answer = "".join(chunks)
    else:
        answer = llm.text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    return {"answer": answer.strip()}
