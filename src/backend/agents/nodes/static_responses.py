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