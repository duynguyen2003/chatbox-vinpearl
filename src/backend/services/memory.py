import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from src.backend.config import get_settings


class MemoryService:
    """Simple persistent conversation memory backed by JSONL.

    Each line stores one completed user/assistant turn. The frontend must reuse
    the same session_id for subsequent requests in the same conversation.
    """

    _lock = RLock()

    def __init__(self) -> None:
        settings = get_settings()
        self.path: Path = settings.chat_history_file
        self.max_turns = settings.memory_max_turns
        self.max_chars = settings.memory_max_chars
        self.enabled = settings.memory_enabled
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_recent(
        self,
        session_id: str | None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not session_id or not self.path.exists():
            return []

        matched: list[dict[str, Any]] = []
        with self._lock:
            with self.path.open("r", encoding="utf-8") as file:
                for line in file:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if record.get("session_id") == session_id:
                        matched.append(record)

        keep = limit if limit is not None else self.max_turns
        return matched[-max(1, keep):]

    def format_for_prompt(self, turns: list[dict[str, Any]]) -> str:
        if not turns:
            return "(no previous conversation)"

        blocks: list[str] = []
        total_chars = 0

        # Build from newest to oldest so the most relevant context is retained.
        for turn in reversed(turns):
            user_text = str(turn.get("user_message", "")).strip()
            assistant_text = str(turn.get("assistant_answer", "")).strip()
            block = f"User: {user_text}\nAssistant: {assistant_text}"

            if total_chars + len(block) > self.max_chars:
                break

            blocks.append(block)
            total_chars += len(block)

        blocks.reverse()
        return "\n\n".join(blocks) or "(no previous conversation)"

    def append_turn(
        self,
        *,
        session_id: str | None,
        user_id: str | None,
        user_message: str,
        assistant_answer: str,
        language: str,
        route: str,
        rag_query: str | None = None,
        ticket_id: str | None = None,
    ) -> None:
        if not self.enabled or not session_id:
            return

        record = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "user_id": user_id,
            "user_message": user_message,
            "assistant_answer": assistant_answer,
            "language": language,
            "route": route,
            "rag_query": rag_query,
            "ticket_id": ticket_id,
        }

        with self._lock:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def clear(self, session_id: str) -> int:
        """Delete all stored turns for one session and return deleted count."""
        if not self.path.exists():
            return 0

        with self._lock:
            retained: list[str] = []
            deleted = 0

            with self.path.open("r", encoding="utf-8") as file:
                for line in file:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        retained.append(line)
                        continue

                    if record.get("session_id") == session_id:
                        deleted += 1
                    else:
                        retained.append(line)

            temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            with temp_path.open("w", encoding="utf-8") as file:
                file.writelines(retained)
            temp_path.replace(self.path)

        return deleted
