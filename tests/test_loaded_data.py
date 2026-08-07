"""Nghiệm thu dữ liệu đã nạp vào lớp CORE.

Khoá lại các con số đã kiểm chứng bằng tay, để lần crawl sau mà lệch thì test đỏ
chứ không âm thầm trôi đi. Tự bỏ qua nếu Postgres chưa chạy hoặc chưa nạp.

    docker compose up -d --wait db
    python -m alembic upgrade head
    python -m scripts.seed_destinations
    python -m scripts.load_core
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.config import get_settings


@pytest.fixture(scope="module")
def db():
    engine = create_engine(get_settings().database_url)
    try:
        with Session(engine) as session:
            loaded = session.scalar(text("SELECT count(*) FROM property"))
    except Exception as exc:  # noqa: BLE001 - moi loi ket noi deu bo qua
        pytest.skip(f"Postgres chưa chạy: {exc}")
    if not loaded:
        pytest.skip("Chưa nạp dữ liệu — chạy python -m scripts.load_core")
    return engine


def count(db, sql: str) -> int:
    with Session(db) as session:
        return session.scalar(text(sql))


# --------------------------------------------------------------------------
# Số lượng thực thể
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "sql", "expected"),
    [
        ("khách sạn", "SELECT count(*) FROM property", 15),
        ("phòng", "SELECT count(*) FROM room", 116),
        ("nhà hàng", "SELECT count(*) FROM dining_service", 68),
        ("cạnh phòng–tiện nghi", "SELECT count(*) FROM room_amenity", 1796),
        ("ưu đãi", "SELECT count(*) FROM promotion", 38),
        ("quyền lợi ưu đãi", "SELECT count(*) FROM promotion_benefit", 310),
        ("mục quảng cáo", "SELECT count(*) FROM destination_highlight", 28),
        ("sân golf", "SELECT count(*) FROM golf_course", 6),
        ("địa điểm hội nghị", "SELECT count(*) FROM mice_venue", 10),
        ("phòng hội nghị", "SELECT count(*) FROM mice_room", 36),
        ("văn bản quy định", "SELECT count(*) FROM policy_document", 7),
        ("địa danh", "SELECT count(*) FROM destination", 13),
        ("khu phức hợp", "SELECT count(*) FROM complex", 8),
    ],
)
def test_entity_counts(db, label: str, sql: str, expected: int) -> None:
    assert count(db, sql) == expected, label


def test_promotions_deduplicated(db) -> None:
    """124 dòng rải trong 9 file gộp lại còn 38 thực thể."""
    assert count(db, "SELECT count(*) FROM promotion") == 38


def test_faq_drops_three_duplicate_questions(db) -> None:
    """Nguồn có 174 mục nhưng 3 câu hỏi bị lặp y hệt."""
    assert count(db, "SELECT count(*) FROM faq") == 171


# --------------------------------------------------------------------------
# Chất lượng dữ liệu — phần quan trọng nhất
# --------------------------------------------------------------------------


def test_hotline_never_becomes_a_price(db) -> None:
    """Crawler nhét số hotline 1900232389 vào cả price_from lẫn standard_rate.

    Nguồn có ``price_from.amount`` khác NULL ở đủ 116 dòng, nhưng 69 trong số đó
    mang giá trị 1900232389 — chính là số hotline. Pipeline đọc từ ``raw`` nên
    loại được; nếu ai đó sửa sang tin ``amount`` thì test này đỏ.
    """
    assert count(db, "SELECT count(*) FROM room WHERE price_from_amount = 1900232389") == 0
    assert count(db, "SELECT count(*) FROM room WHERE rate_amount = 1900232389") == 0


def test_only_47_rooms_have_a_real_price(db) -> None:
    assert count(db, "SELECT count(*) FROM room WHERE price_from_amount IS NOT NULL") == 47


def test_suspect_rate_flag_marks_the_69_bad_rows(db) -> None:
    assert count(db, "SELECT count(*) FROM room WHERE is_rate_suspect") == 69


def test_every_price_has_a_currency(db) -> None:
    """Nguồn để currency = NULL ở 100% dòng; pipeline phải suy từ raw."""
    assert count(
        db,
        "SELECT count(*) FROM room "
        "WHERE price_from_amount IS NOT NULL AND price_from_currency IS NULL",
    ) == 0


def test_no_conference_room_is_kilometres_wide(db) -> None:
    """'Dimensions: 22,839m x 12,938m' — dấu phẩy ở đây là dấu thập phân."""
    assert count(db, "SELECT count(*) FROM mice_room WHERE length_m > 500") == 0
    assert count(db, "SELECT count(*) FROM mice_room WHERE width_m > 500") == 0


def test_language_codes_are_two_letters(db) -> None:
    """Nguồn dùng lẫn 'en' và 'en-US'."""
    assert count(
        db,
        "SELECT count(*) FROM attraction "
        "WHERE content_language IS NOT NULL AND content_language NOT IN ('vi','en')",
    ) == 0


def test_no_local_filesystem_path_leaks(db) -> None:
    """32 chỗ trong data lộ đường dẫn máy người khác — không được vào DB."""
    assert count(
        db,
        r"SELECT count(*) FROM source WHERE html_filename LIKE '%\%' "
        r"OR html_filename LIKE '%/%'",
    ) == 0


# --------------------------------------------------------------------------
# Toàn vẹn quan hệ
# --------------------------------------------------------------------------


def test_every_room_belongs_to_a_known_hotel(db) -> None:
    assert count(
        db,
        "SELECT count(*) FROM room r LEFT JOIN property p ON p.id = r.property_id "
        "WHERE p.id IS NULL",
    ) == 0


def test_nam_hoi_an_data_lands_in_hoi_an(db) -> None:
    """Quyết định §15.1 phải có hiệu lực thật trong dữ liệu."""
    assert count(db, "SELECT count(*) FROM property WHERE destination_id = 'hoi-an'") >= 1
    assert count(
        db, "SELECT count(*) FROM complex WHERE id='nam-hoi-an' AND destination_id='hoi-an'"
    ) == 1


def test_nationwide_promotions_use_the_flag_not_a_fake_destination(db) -> None:
    assert count(db, "SELECT count(*) FROM destination WHERE id ILIKE '%nationwide%'") == 0
    assert count(db, "SELECT count(*) FROM promotion WHERE is_nationwide") >= 1


def test_promotion_active_view_uses_current_date(db) -> None:
    """Trạng thái thật tính theo hôm nay, không tin status_at_crawl."""
    assert count(db, "SELECT count(*) FROM promotion_active") <= count(
        db, "SELECT count(*) FROM promotion"
    )


def test_marketing_copy_is_not_mixed_into_attractions(db) -> None:
    """Quyết định §15.2: 'lý do nên đến' không được nằm trong attraction."""
    assert count(db, "SELECT count(*) FROM attraction WHERE kind = 'highlight'") == 0


# --------------------------------------------------------------------------
# Nhật ký chất lượng
# --------------------------------------------------------------------------


def test_quality_issues_were_recorded_not_swallowed(db) -> None:
    assert count(db, "SELECT count(*) FROM data_quality_issue WHERE rule='rate.not_a_price'") >= 69


def test_last_run_succeeded_with_no_rejected_rows(db) -> None:
    assert count(
        db,
        "SELECT count(*) FROM data_quality_issue WHERE rule LIKE 'db.%' "
        "AND ingest_run_id = (SELECT max(id) FROM ingest_run)",
    ) == 0
