import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from src.backend.config import get_settings


class MemoryService:
    """Persistent conversation memory backed by JSONL.

    Memory is isolated by ``session_id``. Besides raw turns, each completed RAG
    turn stores structured destination metadata. This makes follow-ups such as
    "there", "that place", or "compare the two destinations" much more stable
    than relying on long free-form chat history alone.
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

    @staticmethod
    def _clip(value: Any, limit: int) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)].rstrip() + "…"

    def format_for_prompt(self, turns: list[dict[str, Any]]) -> str:
        """Build a compact recent history without dropping memory on long turns."""
        if not turns:
            return "(no previous conversation)"

        blocks: list[str] = []
        total_chars = 0

        # A single verbose assistant answer should not erase all previous memory.
        # Clip each turn and retain newest turns first within the global budget.
        for turn in reversed(turns):
            user_text = self._clip(turn.get("user_message", ""), 700)
            assistant_text = self._clip(turn.get("assistant_answer", ""), 1700)
            block = f"User: {user_text}\nAssistant: {assistant_text}"

            remaining = self.max_chars - total_chars
            if remaining <= 120:
                break
            if len(block) > remaining:
                block = block[:remaining].rstrip()

            blocks.append(block)
            total_chars += len(block)

        blocks.reverse()
        return "\n\n".join(blocks) or "(no previous conversation)"

    def extract_recent_destinations(
        self,
        turns: list[dict[str, Any]],
        limit: int = 4,
    ) -> list[dict[str, str]]:
        """Return unique recently discussed destinations, newest first.

        New records already contain structured metadata. For legacy JSONL lines,
        fall back to parsing the stored RAG query so existing history keeps working.
        """
        recent: list[dict[str, str]] = []
        seen: set[str] = set()

        for turn in reversed(turns):
            structured = turn.get("detected_destinations") or []
            if not structured and turn.get("detected_destination"):
                structured = [
                    {
                        "id": turn.get("detected_destination"),
                        "name": turn.get("detected_destination_name"),
                    }
                ]

            if not structured:
                try:
                    from src.backend.services.query_parser import detect_destinations

                    structured = [
                        {
                            "id": item.get("id"),
                            "name": item.get("name_vi") or item.get("name_en") or item.get("id"),
                        }
                        for item in detect_destinations(str(turn.get("rag_query") or ""))
                    ]
                except Exception:
                    structured = []

            # When a comparison contains several destinations, keep their order.
            for item in structured:
                destination_id = str(item.get("id") or "").strip()
                if not destination_id or destination_id in seen:
                    continue
                name = str(
                    item.get("name")
                    or item.get("name_vi")
                    or item.get("name_en")
                    or destination_id
                ).strip()
                recent.append({"id": destination_id, "name": name})
                seen.add(destination_id)
                if len(recent) >= limit:
                    return recent

        return recent

    @staticmethod
    def format_destination_summary(destinations: list[dict[str, str]]) -> str:
        if not destinations:
            return "(none yet)"
        return ", ".join(
            f"{item.get('name') or item.get('id')} [{item.get('id')}]"
            for item in destinations
        )

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
        detected_destinations: list[dict[str, Any]] | None = None,
        detected_intent: str | None = None,
        detected_intents: list[str] | None = None,
        request_mode: str | None = None,
        resolution_mode: str | None = None,
    ) -> None:
        if not self.enabled or not session_id:
            return

        compact_destinations: list[dict[str, str]] = []
        for item in detected_destinations or []:
            destination_id = str(item.get("id") or "").strip()
            if not destination_id:
                continue
            compact_destinations.append(
                {
                    "id": destination_id,
                    "name": str(
                        item.get("name")
                        or item.get("name_vi")
                        or item.get("name_en")
                        or destination_id
                    ),
                }
            )

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
            "detected_destinations": compact_destinations,
            "detected_intent": detected_intent,
            "detected_intents": list(detected_intents or []),
            "request_mode": request_mode,
            "resolution_mode": resolution_mode,
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
