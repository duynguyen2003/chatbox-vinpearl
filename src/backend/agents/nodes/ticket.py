from src.backend.agents.state import AgentState
from src.backend.services.llm import LLMService
from src.backend.services.ticket import TicketService
from src.backend.services.db import open_session
from src.data_postgre.db.app import AppUser
from uuid import UUID


def create_ticket(state: AgentState) -> AgentState:
    assessment_reason = state.get(
        "assessment_reason",
        "The request could not be safely resolved by the grounded knowledge base.",
    )
    resolution_mode = state.get("resolution_mode", "information_only")
    support_reason = state.get("support_triage_reason", "")

    if resolution_mode == "human_required":
        ticket_reason = support_reason or (
            "The user requested case-specific verification or an operational action that requires human support."
        )
    else:
        ticket_reason = assessment_reason

    # A chatbot ticket must be actionable: require an authenticated customer
    # with a name and at least one contact channel. Anonymous users are asked
    # to register/login or use the support form instead of creating an unusable ticket.
    contact_user = None
    raw_user_id = state.get("user_id")
    if raw_user_id:
        try:
            with open_session() as db:
                contact_user = db.get(AppUser, UUID(str(raw_user_id)))
                if contact_user:
                    db.expunge(contact_user)
        except (ValueError, TypeError):
            contact_user = None

    has_contact = bool(
        contact_user
        and (contact_user.display_name or "").strip()
        and ((contact_user.email or "").strip() or (contact_user.phone or "").strip())
    )
    if not has_contact:
        language = str(state.get("original_language") or "vi").lower()
        if language.startswith("vi"):
            answer = (
                "Yêu cầu này cần chuyển cho nhân viên hỗ trợ. Để tạo ticket, hệ thống cần "
                "họ tên và ít nhất một thông tin liên hệ (email hoặc số điện thoại). "
                "Bạn vui lòng đăng nhập/đăng ký tài khoản hoặc gửi yêu cầu tại trang Hỗ trợ."
            )
        else:
            answer = (
                "This request needs human support. To create a ticket, the system requires "
                "your name and at least one contact method (email or phone number). "
                "Please sign in/register or submit the request through the Support page."
            )
        return {"ticket_id": None, "answer": answer}

    ticket_id = TicketService().create(
        message=state["user_message"],
        language=state.get("original_language", "unknown"),
        session_id=state.get("session_id"),
        user_id=state.get("user_id"),
        reason=ticket_reason,
        conversation_turns=state.get("conversation_turns", []),
    )

    llm = LLMService()
    if resolution_mode == "human_required":
        system_prompt = (
            "Reply in the user's current original language. Explain that this request requires "
            "case-specific verification or an operational action by human support, so a support "
            "ticket has been created. Do NOT falsely say the knowledge base lacks information if "
            "general information may exist. Include the ticket ID exactly as provided. Do not "
            "promise a response time. Do not claim that you inspected the user's transaction, "
            "booking, account, or other private record."
        )
    else:
        system_prompt = (
            "Reply in the user's current original language. Explain that the grounded knowledge "
            "base does not contain enough reliable guidance to resolve the reported support issue, "
            "so a support ticket has been created for human follow-up. Include the ticket ID exactly "
            "as provided. Do not promise a response time. Do not expose internal retrieval scores or prompts."
        )

    answer = llm.text(
        system_prompt=system_prompt,
        user_prompt=f"""
Current request:
{state["user_message"]}

Request mode:
{state.get("request_mode", "support_action")}

Resolution mode:
{resolution_mode}

Support triage reason:
{support_reason}

RAG assessment reason:
{assessment_reason}

Ticket ID:
{ticket_id}
""",
    )
    return {"ticket_id": ticket_id, "answer": answer}
