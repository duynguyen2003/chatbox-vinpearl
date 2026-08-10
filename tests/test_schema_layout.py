"""Khoá lại cách lược đồ được chia: hai schema bảng + một schema view.

    core.*  bảng nghiệp vụ và vận hành nạp
    app.*   hội thoại, ticket, nhật ký
    api.*   view đọc, đã gộp sẵn

Tự bỏ qua nếu Postgres chưa chạy.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.backend.config import get_settings
from src.data_postgre.db import APP_TABLES, CORE_TABLES

EXPECTED_VIEWS = {
    "attraction", "data_health", "destination", "faq", "golf_course", "hotel",
    "mice_venue", "policy_document", "promotion", "promotion_active", "room",
}


@pytest.fixture(scope="module")
def db():
    engine = create_engine(get_settings().database_url)
    try:
        with Session(engine) as session:
            session.scalar(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - moi loi ket noi deu bo qua
        pytest.skip(f"Postgres chưa chạy: {exc}")
    return engine


def scalar(db, sql: str):
    with Session(db) as session:
        return session.scalar(text(sql))


def names(db, sql: str) -> set[str]:
    with Session(db) as session:
        return {row[0] for row in session.execute(text(sql))}


# --------------------------------------------------------------------------
# Bảng nằm đúng schema
# --------------------------------------------------------------------------


def test_metadata_declares_two_schemas() -> None:
    """Model phải khai schema, nếu không migration sẽ dựng lại vào public."""
    assert {t.schema for t in CORE_TABLES.values()} == {"core"}
    assert {t.schema for t in APP_TABLES.values()} == {"app"}


def test_lookup_keys_stay_bare_names() -> None:
    """entity_type và Context.rows dùng tên trần — đổi thành 'core.room' là hỏng."""
    assert "room" in CORE_TABLES
    assert CORE_TABLES["room"].fullname == "core.room"
    assert "message" in APP_TABLES


def test_database_matches_the_declared_layout(db) -> None:
    live_core = names(
        db,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='core' AND table_type='BASE TABLE'",
    )
    live_app = names(
        db,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='app' AND table_type='BASE TABLE'",
    )
    assert live_core == set(CORE_TABLES)
    assert live_app == set(APP_TABLES)


def test_public_holds_only_the_alembic_marker(db) -> None:
    """Bảng còn sót trong public nghĩa là ai đó tạo bảng ngoài migration."""
    assert names(
        db,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE'",
    ) == {"alembic_version"}


def test_unqualified_sql_still_resolves(db) -> None:
    """search_path phải giữ được SQL không ghi schema — psql, DataGrip, test cũ."""
    assert scalar(db, "SELECT count(*) FROM room") == 116
    assert scalar(db, "SELECT count(*) FROM message") == 0


def test_public_stays_first_on_search_path(db) -> None:
    """Đặt core lên đầu thì current_schema() thành 'core', SQLAlchemy coi đó là
    schema mặc định, và alembic check báo cả 34 bảng core là thiếu."""
    assert scalar(db, "SELECT current_schema()") == "public"


# --------------------------------------------------------------------------
# View đọc
# --------------------------------------------------------------------------


def test_every_expected_view_exists(db) -> None:
    assert names(
        db, "SELECT table_name FROM information_schema.views WHERE table_schema='api'"
    ) == EXPECTED_VIEWS


def test_bare_name_means_the_table_not_the_view(db) -> None:
    """core đứng trước api trong search_path — 'room' luôn là bảng.

    Bảng room không có cột amenities (chỉ có amenity_ids); view api.room thì có.
    """
    assert scalar(
        db,
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema='core' AND table_name='room' AND column_name='amenities'",
    ) == 0
    assert scalar(
        db,
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema='api' AND table_name='room' AND column_name='amenities'",
    ) == 1


def test_hotel_view_folds_rooms_and_dining(db) -> None:
    assert scalar(db, "SELECT count(*) FROM api.hotel") == 15
    assert scalar(
        db,
        "SELECT count(*) FROM api.hotel WHERE room_count <> "
        "coalesce(jsonb_array_length(rooms), 0)",
    ) == 0
    assert scalar(
        db, "SELECT sum(jsonb_array_length(dining)) FROM api.hotel"
    ) == 68


def test_room_view_resolves_amenity_names(db) -> None:
    """Mảng id đã mất khoá ngoại; view phải tra được tên, không ra NULL."""
    assert scalar(
        db, "SELECT sum(array_length(amenities, 1)) FROM api.room"
    ) == 1796
    assert scalar(
        db,
        "SELECT count(*) FROM api.room "
        "WHERE amenities IS NULL AND id IN "
        "(SELECT id FROM core.room WHERE amenity_ids IS NOT NULL)",
    ) == 0


def test_promotion_view_keeps_all_38(db) -> None:
    assert scalar(db, "SELECT count(*) FROM api.promotion") == 38
    assert scalar(
        db, "SELECT count(*) FROM api.promotion WHERE destination_ids IS NOT NULL"
    ) >= 1


def test_promotion_active_view_now_carries_tags(db) -> None:
    """Bản cũ viết SELECT * nên bị đóng băng trước khi có cột tags."""
    assert scalar(
        db,
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema='api' AND table_name='promotion_active' "
        "AND column_name='tags'",
    ) == 1


def test_destination_view_counts_match_the_tables(db) -> None:
    assert scalar(db, "SELECT sum(hotels) FROM api.destination") == 15
    assert scalar(db, "SELECT sum(attractions) FROM api.destination") == 78
    assert scalar(db, "SELECT sum(golf_courses) FROM api.destination") == 6
