import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.config import get_settings


class TicketService:
    def __init__(self) -> None:
        self.path: Path = get_settings().ticket_file
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        message: str,
        language: str,
        session_id: str | None,
        user_id: str | None,
        reason: str,
    ) -> str:
        ticket_id = f"VP-{uuid4().hex[:10].upper()}"
        record = {
            "ticket_id": ticket_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "message": message,
            "language": language,
            "session_id": session_id,
            "user_id": user_id,
            "reason": reason,
        }

        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        return ticket_id
