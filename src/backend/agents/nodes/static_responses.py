from src.backend.agents.state import AgentState
from src.backend.services.llm import LLMService


def _get_language(state: AgentState) -> str:
    """
    Lấy mã ngôn ngữ đã được node language phát hiện.

    Ví dụ:
    - vi
    - en
    - ko
    - ja
    - zh
    - en-US
    """
    language = state.get("original_language", "en")

    if not isinstance(language, str) or not language.strip():
        return "en"

    return language.strip()


def greeting_response(state: AgentState) -> AgentState:
    """
    Trả lời khi người dùng chỉ chào hỏi.

    Câu trả lời phải sử dụng đúng ngôn ngữ đầu vào đã được phát hiện.
    """
    llm = LLMService()
    language = _get_language(state)
    user_message = state.get("user_message", "")

    answer = llm.text(
        system_prompt=(
            "You are a friendly Vinpearl/VinWonders travel assistant. "
            "The user's detected language will be provided explicitly. "
            "You must reply only in that detected language. "
            "Do not switch to Vietnamese unless the detected language is vi. "
            "Keep the response brief and friendly. "
            "Introduce that you can help with Vinpearl/VinWonders destinations, "
            "hotels, rooms, entertainment, promotions, policies, events, golf, "
            "and payment guidance."
        ),
        user_prompt=f"""
Detected language: {language}

User message:
{user_message}

Reply only in the detected language.
""",
    )

    return {
        "answer": answer,
    }


def out_of_scope_response(state: AgentState) -> AgentState:
    """
    Trả lời khi câu hỏi nằm ngoài phạm vi Vinpearl/VinWonders.

    Không trả lời nội dung ngoài phạm vi.
    Câu trả lời phải sử dụng đúng ngôn ngữ đầu vào.
    """
    llm = LLMService()
    language = _get_language(state)
    user_message = state.get("user_message", "")

    answer = llm.text(
        system_prompt=(
            "You are a Vinpearl/VinWonders travel support assistant. "
            "The user's detected language will be provided explicitly. "
            "You must reply only in that detected language. "
            "Do not switch to Vietnamese unless the detected language is vi. "
            "Politely explain that you can only support Vinpearl/VinWonders "
            "travel services and payment guidance. "
            "Do not answer the user's out-of-scope question. "
            "Do not provide unrelated facts, opinions, or explanations. "
            "Keep the response brief."
        ),
        user_prompt=f"""
Detected language: {language}

Out-of-scope user message:
{user_message}

Politely refuse and reply only in the detected language.
""",
    )

    return {
        "answer": answer,
    }

def conversation_context_response(state: AgentState) -> AgentState:
    """Answer a meta question such as 'what place did I mean by here?' from memory only."""
    llm = LLMService()
    language = _get_language(state)
    recent = state.get("recent_destinations", []) or []

    if not recent:
        answer = llm.text(
            system_prompt=(
                "Reply only in the detected language. The user is asking what destination "
                "a conversational reference points to, but structured session memory contains "
                "no destination. Say briefly that you cannot determine the referenced destination "
                "from the current conversation memory. Do not use outside knowledge and do not "
                "create or mention a support ticket."
            ),
            user_prompt=f"""
Detected language: {language}
Current message: {state.get('user_message', '')}
""",
        )
        return {"answer": answer}

    active = recent[0]
    destination_name = str(active.get("name") or active.get("id") or "").strip()
    destination_id = str(active.get("id") or "").strip()

    answer = llm.text(
        system_prompt=(
            "You answer a conversation-reference clarification for a Vinpearl/VinWonders assistant. "
            "Use ONLY the STRUCTURED_MEMORY_REFERENCE supplied below. It is conversation memory, "
            "not external factual knowledge. Tell the user which destination 'here/there/that place' "
            "refers to. Do not add attractions, services, facts, URLs, or details not supplied. "
            "Do not call RAG and do not mention or create a support ticket. Reply only in the detected "
            "language and keep it brief."
        ),
        user_prompt=f"""
Detected language: {language}
Current message: {state.get('user_message', '')}

STRUCTURED_MEMORY_REFERENCE:
Destination name: {destination_name}
Destination id: {destination_id}
""",
    )
    return {"answer": answer}


def no_data_response(state: AgentState) -> AgentState:
    """Return a safe knowledge-base absence answer without creating a ticket."""
    llm = LLMService()
    language = _get_language(state)
    destinations = state.get("detected_destination_names", []) or []
    if not destinations:
        destinations = [item.get("name") for item in state.get("recent_destinations", []) if item.get("name")]

    answer = llm.text(
        system_prompt=(
            "You are a strictly grounded Vinpearl/VinWonders assistant. The retrieval system found "
            "no sufficiently grounded knowledge-base evidence for the user's yes/no catalog/existence "
            "question. Reply only in the detected language. Do NOT claim that the thing does not exist "
            "in the real world. Say only that the CURRENT KNOWLEDGE BASE does not record or does not "
            "contain enough information to confirm it for the referenced destination. Do not use outside "
            "knowledge, do not invent facts, and do not create or mention a support ticket. If a resolved "
            "destination is supplied, mention it so the user can see the conversational reference was understood."
        ),
        user_prompt=f"""
Detected language: {language}
Current question: {state.get('user_message', '')}
Resolved destination(s): {', '.join(str(x) for x in destinations) or '(none)'}
Assessment reason: {state.get('assessment_reason', '')}
""",
    )
    return {"answer": answer, "ticket_id": None}
