from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text

from src.backend.config import get_settings


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hotel": (
        "hotel", "hotels", "resort", "resorts", "property", "properties",
        "khach san", "khách sạn", "khu nghi duong", "khu nghỉ dưỡng",
        "villa", "villas", "biet thu", "biệt thự", "room", "rooms",
        "phong", "phòng",
    ),
    "service": (
        "service", "services", "amenity", "amenities", "facility", "facilities",
        "dich vu", "dịch vụ", "tien ich", "tiện ích", "spa", "restaurant",
        "restaurants", "nha hang", "nhà hàng", "bar", "pool", "ho boi", "hồ bơi",
    ),
    "promotion": (
        "promotion", "promotions", "offer", "offers", "deal", "deals",
        "khuyen mai", "khuyến mãi", "uu dai", "ưu đãi", "voucher", "code",
    ),
    "attraction": (
        "attraction", "attractions", "vinwonders", "theme park", "water park",
        "khu vui choi", "khu vui chơi", "diem tham quan", "điểm tham quan",
        "hoat dong", "hoạt động", "entertainment", "grand world", "aquafield",
    ),
    "golf": ("golf", "golf course", "san golf", "sân golf"),
    "mice": (
        "mice", "meeting", "meetings", "event", "events", "conference",
        "hoi nghi", "hội nghị", "su kien", "sự kiện", "phong hop", "phòng họp",
    ),
    "policy": (
        "policy", "policies", "regulation", "regulations", "terms", "term",
        "chinh sach", "chính sách", "quy dinh", "quy định", "dieu khoan", "điều khoản",
        "check-in", "check-out", "check in", "check out",
    ),
    "payment": (
        "payment", "payments", "pay", "bank", "account", "swift",
        "thanh toan", "thanh toán", "tai khoan", "tài khoản", "ngan hang", "ngân hàng",
    ),
}

INTENT_ENTITY_TYPES: dict[str, set[str]] = {
    "hotel": {
        "property", "room", "amenity", "dining_service",
        "destination", "destination_highlight", "complex",
    },
    "service": {
        "property", "room", "amenity", "dining_service",
        "destination_highlight", "golf_feature", "mice_venue", "mice_room",
        "attraction", "complex",
    },
    "promotion": {
        "promotion", "promotion_benefit", "content_block", "promotion_code",
        "promotion_destination", "promotion_property_raw", "promotion_relation",
        "content_section", "promotion_term",
    },
    "attraction": {
        "attraction", "destination_highlight", "complex",
    },
    "golf": {"golf_course", "golf_feature"},
    "mice": {"mice_venue", "mice_room", "mice_room_capacity"},
    "policy": {"policy_document", "content_section", "content_block", "faq"},
    "payment": {"policy_document", "content_section", "content_block", "faq"},
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFD", str(value))
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower().replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=1)
def load_destination_catalog() -> dict[str, dict[str, Any]]:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    catalog: dict[str, dict[str, Any]] = {}
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, name_en, name_vi, province FROM destination")
            ).mappings()
            for row in rows:
                destination_id = str(row["id"])
                aliases = {
                    destination_id,
                    str(row.get("name_en") or ""),
                    str(row.get("name_vi") or ""),
                    str(row.get("province") or ""),
                }
                catalog[destination_id] = {
                    "id": destination_id,
                    "name_en": row.get("name_en"),
                    "name_vi": row.get("name_vi"),
                    "aliases": {a for a in aliases if a.strip()},
                }

            alias_rows = conn.execute(
                text("SELECT destination_id, alias, alias_normalized FROM destination_alias")
            ).mappings()
            for row in alias_rows:
                destination_id = str(row["destination_id"])
                if destination_id not in catalog:
                    catalog[destination_id] = {
                        "id": destination_id,
                        "name_en": destination_id,
                        "name_vi": destination_id,
                        "aliases": {destination_id},
                    }
                for field in ("alias", "alias_normalized"):
                    value = str(row.get(field) or "").strip()
                    if value:
                        catalog[destination_id]["aliases"].add(value)
    except Exception as exc:
        print(f"[QueryParser] Could not load destination aliases: {exc}")
        return {}
    finally:
        engine.dispose()

    for item in catalog.values():
        normalized_aliases = {
            normalize_text(alias) for alias in item["aliases"] if normalize_text(alias)
        }
        normalized_aliases.add(normalize_text(item["id"]))
        item["normalized_aliases"] = sorted(
            normalized_aliases,
            key=lambda value: (-len(value), value),
        )

    return catalog


def _contains_phrase(haystack: str, needle: str) -> bool:
    if not haystack or not needle:
        return False
    return re.search(rf"(?:^|\s){re.escape(needle)}(?:$|\s)", haystack) is not None


def detect_destinations(*texts: str | None) -> list[dict[str, Any]]:
    """Detect every distinct destination mentioned, in textual order."""
    combined = normalize_text(" ".join(str(t or "") for t in texts))
    if not combined:
        return []

    matches: list[tuple[int, int, dict[str, Any], str]] = []
    for item in load_destination_catalog().values():
        best_for_item: tuple[int, int, dict[str, Any], str] | None = None
        for alias in item.get("normalized_aliases", []):
            pattern = re.compile(rf"(?:^|\s)({re.escape(alias)})(?:$|\s)")
            match = pattern.search(combined)
            if not match:
                continue
            start = match.start(1)
            candidate = (start, -len(alias), item, alias)
            if best_for_item is None or candidate[:2] < best_for_item[:2]:
                best_for_item = candidate
        if best_for_item is not None:
            matches.append(best_for_item)

    matches.sort(key=lambda value: (value[0], value[1]))
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, _, item, matched_alias in matches:
        destination_id = str(item["id"])
        if destination_id in seen:
            continue
        seen.add(destination_id)
        output.append(
            {
                "id": destination_id,
                "name_en": item.get("name_en"),
                "name_vi": item.get("name_vi"),
                "matched_alias": matched_alias,
                "aliases": list(item.get("normalized_aliases", [])),
            }
        )
    return output


def detect_destination(*texts: str | None) -> dict[str, Any] | None:
    destinations = detect_destinations(*texts)
    return destinations[0] if destinations else None


def detect_intent(*texts: str | None) -> str | None:
    normalized = normalize_text(" ".join(str(t or "") for t in texts))

    best_intent: str | None = None
    best_score = 0
    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)
            if normalized_keyword and _contains_phrase(normalized, normalized_keyword):
                score += max(1, len(normalized_keyword.split()))
        if score > best_score:
            best_intent = intent
            best_score = score

    return best_intent


def parse_retrieval_query(user_message: str, rag_query: str) -> dict[str, Any]:
    # The LLM-created RAG query is the canonical target. This matters for complaint
    # turns such as "why are your links all Phu Quoc?" while the active topic is Hanoi.
    # In that case Phu Quoc appears in the raw message as the WRONG destination and
    # must not override the standalone retrieval query.
    destinations = detect_destinations(rag_query)
    if not destinations:
        destinations = detect_destinations(user_message)

    intent = detect_intent(rag_query, user_message)
    return {
        "destination": destinations[0] if destinations else None,
        "destinations": destinations,
        "intent": intent,
        "preferred_entity_types": sorted(INTENT_ENTITY_TYPES.get(intent or "", set())),
    }
