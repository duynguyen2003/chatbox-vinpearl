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

from src.backend.config import get_settings


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
        ("tiện nghi (từ điển)", "SELECT count(*) FROM amenity", 50),
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
# Ba bảng đã gộp — khoá lại kết quả
# --------------------------------------------------------------------------


def test_merged_tables_are_gone(db) -> None:
    """promotion_step, golf_course_map, attraction_itinerary_day đã gộp đi."""
    assert count(
        db,
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='core' "
        "AND table_name IN ('promotion_step','golf_course_map','attraction_itinerary_day')",
    ) == 0


def test_redemption_steps_moved_into_promotion_term(db) -> None:
    """78 bước đổi thưởng giờ nằm trong promotion_term với kind='step'."""
    assert count(db, "SELECT count(*) FROM promotion_term WHERE kind = 'step'") == 78
    assert count(db, "SELECT count(*) FROM promotion_term") == 188


def test_term_ord_counts_within_each_kind(db) -> None:
    """'bước 3' phải độc lập với 'điều khoản thứ 3' — mỗi kind đếm ord riêng."""
    assert count(
        db,
        "SELECT count(*) FROM (SELECT promotion_id, kind, ord FROM promotion_term "
        "GROUP BY 1,2,3 HAVING count(*) > 1) d",
    ) == 0


def test_course_maps_moved_into_golf_feature(db) -> None:
    """6 bản đồ sân giờ là golf_feature với kind='map', giữ variant."""
    assert count(db, "SELECT count(*) FROM golf_feature WHERE kind = 'map'") == 6
    assert count(db, "SELECT count(*) FROM golf_feature") == 67
    assert count(db, "SELECT count(*) FROM golf_feature WHERE variant IS NOT NULL") == 6


def test_itinerary_moved_into_attraction_jsonb(db) -> None:
    """7 ngày hành trình của 3 topic giờ nằm trong cột JSONB."""
    assert count(db, "SELECT count(*) FROM attraction WHERE itinerary IS NOT NULL") == 3
    assert count(
        db, "SELECT sum(jsonb_array_length(itinerary)) FROM attraction "
            "WHERE itinerary IS NOT NULL"
    ) == 7


def test_jsonb_none_is_sql_null_not_json_null(db) -> None:
    """None của Python phải thành SQL NULL.

    Mặc định SQLAlchemy biến nó thành JSON 'null' — một scalar — khiến
    jsonb_array_length() báo 'cannot get array length of a scalar'.
    """
    assert count(db, "SELECT count(*) FROM attraction WHERE itinerary::text = 'null'") == 0


# --------------------------------------------------------------------------
# Bốn bảng nối đã gộp thành cột — 45 bảng còn 41
# --------------------------------------------------------------------------


def test_column_merges_removed_their_link_tables(db) -> None:
    assert count(
        db,
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='core' "
        "AND table_name IN ('room_amenity','promotion_tag')",
    ) == 0


def test_amenity_links_survived_the_move_into_an_array(db) -> None:
    """1.796 cạnh của bảng nối cũ phải còn nguyên trong room.amenity_ids."""
    assert count(db, "SELECT sum(cardinality(amenity_ids)) FROM room") == 1796
    assert count(db, "SELECT count(*) FROM room WHERE amenity_ids IS NOT NULL") == 111


def test_no_amenity_id_points_at_nothing(db) -> None:
    """Thay cho khoá ngoại đã mất: Postgres không kiểm tra phần tử mảng được."""
    assert count(
        db,
        "SELECT count(*) FROM (SELECT unnest(amenity_ids) a FROM room) u "
        "WHERE NOT EXISTS (SELECT 1 FROM amenity WHERE id = u.a)",
    ) == 0


def test_promotion_tags_survived_the_move_into_jsonb(db) -> None:
    assert count(
        db,
        "SELECT sum((SELECT count(*) FROM jsonb_each(tags) e, "
        "jsonb_array_elements_text(e.value))) FROM promotion",
    ) == 561
    assert count(db, "SELECT count(*) FROM promotion WHERE tags IS NOT NULL") == 38


def test_tag_dimension_names_stay_inside_the_five_allowed(db) -> None:
    """Thay cho CHECK đã mất khi promotion_tag thành cột JSONB."""
    assert count(
        db,
        "SELECT count(*) FROM promotion p, jsonb_object_keys(p.tags) k "
        "WHERE k NOT IN ('promotion_type','service','channel','customer_group',"
        "'member_tier')",
    ) == 0


def test_section_and_block_tables_stayed_separate(db) -> None:
    """Đã thử gộp thành content_section/content_block rồi tách lại.

    Đa hình đổi 2 khoá ngoại lấy 1 bảng — chỉ đáng khi có nhiều loại chủ sở hữu.
    media có 8 nên hợp lý; chỗ này chỉ có 2.
    """
    assert count(
        db,
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='core' "
        "AND table_name IN ('content_section','content_block')",
    ) == 0
    assert count(db, "SELECT count(*) FROM promotion_section") == 164
    assert count(db, "SELECT count(*) FROM policy_section") == 36
    assert count(db, "SELECT count(*) FROM promotion_block") == 507
    assert count(db, "SELECT count(*) FROM policy_block") == 15


def test_the_four_tables_have_real_foreign_keys(db) -> None:
    """Cái lấy lại được khi tách: khoá ngoại thật + ON DELETE CASCADE."""
    for table in ("promotion_section", "promotion_block",
                  "policy_section", "policy_block"):
        assert count(
            db,
            "SELECT count(*) FROM pg_constraint "
            f"WHERE conrelid = 'core.{table}'::regclass "  # noqa: S608
            "AND contype = 'f' AND confdeltype = 'c'",
        ) == 1, table


def test_both_block_tables_speak_the_same_vocabulary(db) -> None:
    """'bullet_list' đã đổi thành 'list' — giữ lại từ lần gộp."""
    assert count(
        db, "SELECT count(*) FROM promotion_block WHERE block_type='bullet_list'"
    ) == 0
    assert count(db, "SELECT count(*) FROM promotion_block WHERE block_type='list'") > 0
    assert count(db, "SELECT count(*) FROM policy_block WHERE block_type='list'") > 0


def test_batch_insert_keeps_columns_only_some_rows_have(db) -> None:
    """insert().values([...]) lấy khoá của dòng ĐẦU làm khuôn cho cả câu lệnh.

    Thẻ giới thiệu (không có duration) luôn được thêm trước trang chi tiết, nên
    trước khi sửa, duration_days và itinerary bị bỏ lặng lẽ ở toàn bộ 78 dòng.
    """
    assert count(db, "SELECT count(*) FROM attraction WHERE duration_days IS NOT NULL") == 2


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
