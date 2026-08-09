"""41 bảng CORE — dữ liệu nghiệp vụ đã làm sạch từ data/*.json.

Đặc tả đầy đủ kèm bằng chứng cho từng quan hệ: docs/DATABASE.md
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.data_postgre.db.base import Base, Sourced, Timestamped

# --------------------------------------------------------------------------
# Vận hành
# --------------------------------------------------------------------------


class IngestRun(Base):
    """Mỗi lần chạy scripts/load_core.py là một dòng."""

    __tablename__ = "ingest_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    git_sha: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','success','failed')", name="status_valid"
        ),
    )


class DataQualityIssue(Base):
    """Mọi thứ không parse được. Không bao giờ ``except: pass``."""

    __tablename__ = "data_quality_issue"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ingest_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingest_run.id", ondelete="CASCADE")
    )
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    rule: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[str | None] = mapped_column(Text)
    source_file: Mapped[str | None] = mapped_column(Text)
    json_path: Mapped[str | None] = mapped_column(Text)
    field: Mapped[str | None] = mapped_column(Text)
    raw_value: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('error','warning','info')", name="severity_valid"
        ),
        Index("ix_dqi_rule", "rule"),
        Index("ix_dqi_run_severity", "ingest_run_id", "severity"),
    )


# --------------------------------------------------------------------------
# Trục dùng chung
# --------------------------------------------------------------------------


class Brand(Base, Timestamped):
    __tablename__ = "brand"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    website: Mapped[str | None] = mapped_column(Text)


class Source(Base, Timestamped):
    """Xuất xứ của mọi dòng CORE — nền tảng để bot trích dẫn nguồn."""

    __tablename__ = "source"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text)
    brand_id: Mapped[str | None] = mapped_column(ForeignKey("brand.id"))
    # Suy từ path /vi/ hay /en/ của URL, KHÔNG lấy từ field "language" trong file:
    # nha-trang.json khai language='en' nhưng có 945 URL /vi/ so với 127 URL /en/.
    source_language: Mapped[str | None] = mapped_column(String(2))
    http_status: Mapped[int | None] = mapped_column(Integer)
    is_404: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None] = mapped_column(Text)
    html_filename: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "source_language IS NULL OR source_language IN ('vi','en')",
            name="lang_valid",
        ),
    )


class Destination(Base, Timestamped):
    """Địa danh hành chính. Master data viết tay, KHÔNG sinh từ crawl."""

    __tablename__ = "destination"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    # Không mặc định cứng 'Vietnam': Cape Wickham Golf Links ở Tasmania, Australia.
    country: Mapped[str] = mapped_column(
        Text, server_default=text("'Vietnam'"), nullable=False
    )
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    has_content: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    sort_order: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(
            "region IS NULL OR region IN ('north','central','south')",
            name="region_valid",
        ),
    )


class DestinationAlias(Base, Timestamped):
    """Điểm vào DUY NHẤT để tra địa danh.

    10 cặp tên Việt/Anh đã đếm được trong data: Hanoi/Hà Nội, Phu Quoc/Phú Quốc,
    Nghe An/Nghệ An, Hoi An/Hội An, Hai Phong/Hải Phòng, Ha Tinh/Hà Tĩnh,
    Ha Long/Hạ Long, Ho Chi Minh City/Thành phố Hồ Chí Minh, Hue/Huế, Da Nang/Đà Nẵng.
    """

    __tablename__ = "destination_alias"

    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id", ondelete="CASCADE"), primary_key=True
    )
    alias_normalized: Mapped[str] = mapped_column(Text, primary_key=True)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        # UNIQUE toàn cục, không chỉ trong phạm vi một destination: một bí danh
        # không được phép trỏ về hai địa danh khác nhau.
        UniqueConstraint("alias_normalized", name="uq_alias_normalized"),
        CheckConstraint(
            "origin IS NULL OR origin IN ('crawl','manual')", name="origin_valid"
        ),
    )


class Complex(Base, Sourced):
    """Khu phức hợp — tầng giữa destination và các thực thể sản phẩm.

    Vinpearl bán hàng theo khu chứ không theo khách sạn đơn lẻ. Trong data,
    ``destination.name`` của file entertainment thực chất là TÊN KHU:
    ha_noi.json ghi 'Grand World Ocean City' với city='Hanoi'.
    """

    __tablename__ = "complex"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id"), nullable=False
    )
    kind: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "kind IS NULL OR kind IN ('united_center','park_complex','island')",
            name="kind_valid",
        ),
    )


class Media(Base, Timestamped):
    """Đa hình, cố ý KHÔNG có khoá ngoại (xem docs/DATABASE.md §13)."""

    __tablename__ = "media"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(Text)
    alt: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "url", name="uq_media_entity_url"),
        Index("ix_media_entity", "entity_type", "entity_id"),
        CheckConstraint(
            "role IS NULL OR role IN ('hero','gallery','map','thumbnail')",
            name="role_valid",
        ),
    )


class EntitySource(Base, Timestamped):
    """Quan hệ N–N với nguồn: mỗi sân golf có 2 URL, mỗi mục con lại có URL riêng."""

    __tablename__ = "entity_source"

    entity_type: Mapped[str] = mapped_column(Text, primary_key=True)
    entity_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("source.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "role IS NULL OR role IN ('primary','secondary','detail')",
            name="role_valid",
        ),
    )


class PageLink(Base, Timestamped):
    """Đồ thị điều hướng website — dựng tự động từ 104 đường dẫn lá mang tính liên kết.

    ~500 liên kết trỏ tới /wonderpedia/ có to_source_id = NULL: đã chốt không cào
    ở vòng này, bot được dẫn link nhưng không được tóm tắt nội dung.
    """

    __tablename__ = "page_link"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    from_source_id: Mapped[str] = mapped_column(
        ForeignKey("source.id", ondelete="CASCADE"), nullable=False
    )
    to_url: Mapped[str] = mapped_column(Text, nullable=False)
    to_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("source.id", ondelete="SET NULL")
    )
    anchor_text: Mapped[str | None] = mapped_column(Text)
    is_internal: Mapped[bool | None] = mapped_column(Boolean)
    context: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "context IS NULL OR context IN ('card','body','related','detail','option')",
            name="context_valid",
        ),
        Index("ix_page_link_from", "from_source_id"),
    )


# --------------------------------------------------------------------------
# Lưu trú
# --------------------------------------------------------------------------


class Property(Base, Sourced):
    """15 khách sạn. URL thật: /en/hotels/{slug}."""

    __tablename__ = "property"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str | None] = mapped_column(Text)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id"), nullable=False
    )
    complex_id: Mapped[str | None] = mapped_column(ForeignKey("complex.id"))
    brand_id: Mapped[str | None] = mapped_column(ForeignKey("brand.id"))
    address: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    room_page_url: Mapped[str | None] = mapped_column(Text)
    dining_page_url: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "kind IS NULL OR kind IN ('hotel','resort')", name="kind_valid"
        ),
        Index("ix_property_destination", "destination_id"),
        # Khớp mờ tên khách sạn cho promotion_property_raw: 327 giá trị nguồn
        # phần lớn là chuỗi cụt ('Vinwonders Wave Park &') nên phải so bằng
        # độ tương tự trigram chứ không bằng dấu bằng.
        Index(
            "ix_property_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )


class Room(Base, Sourced):
    """116 phòng.

    Cảnh báo dữ liệu: 69/116 dòng có standard_rate.raw = 'tel:1900232389'
    (crawler bắt nhầm link hotline thành giá) -> is_rate_suspect = true.
    100% dòng có currency = null dù raw ghi rõ USD -> phải suy từ raw.
    """

    __tablename__ = "room"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    property_id: Mapped[str] = mapped_column(
        ForeignKey("property.id", ondelete="CASCADE"), nullable=False
    )
    room_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    guest_count: Mapped[int | None] = mapped_column(Integer)

    area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    area_raw: Mapped[str | None] = mapped_column(Text)

    price_from_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    price_from_currency: Mapped[str | None] = mapped_column(String(3))
    price_is_approximate: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    price_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rate_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    rate_currency: Mapped[str | None] = mapped_column(String(3))
    rate_raw: Mapped[str | None] = mapped_column(Text)
    is_rate_suspect: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    bed_types: Mapped[list[str] | None] = mapped_column(JSONB)
    has_wifi: Mapped[bool | None] = mapped_column(Boolean)
    image_url: Mapped[str | None] = mapped_column(Text)
    page_url: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("property_id", "room_index", name="uq_room_property_index"),
        CheckConstraint(
            "guest_count IS NULL OR guest_count > 0", name="guest_count_positive"
        ),
        Index(
            "ix_room_price",
            "price_from_amount",
            postgresql_where=text("price_from_amount IS NOT NULL"),
        ),
    )


class Amenity(Base, Timestamped):
    """~50 giá trị khác nhau cho 1.796 lần xuất hiện — lặp 36 lần mỗi giá trị."""

    __tablename__ = "amenity"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    name_vi: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "category IS NULL OR category IN "
            "('bathroom','tech','comfort','service','other')",
            name="category_valid",
        ),
    )


class RoomAmenity(Base):
    __tablename__ = "room_amenity"

    room_id: Mapped[str] = mapped_column(
        ForeignKey("room.id", ondelete="CASCADE"), primary_key=True
    )
    amenity_id: Mapped[str] = mapped_column(
        ForeignKey("amenity.id", ondelete="CASCADE"), primary_key=True
    )


class DiningService(Base, Sourced):
    """68 nhà hàng. URL thật: /en/hotels/{slug}/foods."""

    __tablename__ = "dining_service"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    property_id: Mapped[str] = mapped_column(
        ForeignKey("property.id", ondelete="CASCADE"), nullable=False
    )
    service_index: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    opens_at: Mapped[time | None] = mapped_column(Time)
    closes_at: Mapped[time | None] = mapped_column(Time)
    hours_raw: Mapped[str | None] = mapped_column(Text)
    hours_display: Mapped[str | None] = mapped_column(Text)
    contact_raw: Mapped[str | None] = mapped_column(Text)
    contact_display: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------
# Trải nghiệm
# --------------------------------------------------------------------------


class Attraction(Base, Sourced):
    """Chỉ những thứ CÓ THẬT, đi được.

    Nội dung quảng cáo nằm ở destination_highlight. Không có property_id:
    đã kiểm chứng 0/68 giá trị location khớp tên khách sạn — điểm tham quan và
    khách sạn là ANH EM trong cùng một khu phức hợp.
    """

    __tablename__ = "attraction"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id"), nullable=False
    )
    complex_id: Mapped[str | None] = mapped_column(ForeignKey("complex.id"))
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("attraction.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    location_text: Mapped[str | None] = mapped_column(Text)
    section_title: Mapped[str | None] = mapped_column(Text)
    topic_group: Mapped[str | None] = mapped_column(Text)
    detail_url: Mapped[str | None] = mapped_column(Text)
    detail_status: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    content_language: Mapped[str | None] = mapped_column(String(2))
    duration_days: Mapped[int | None] = mapped_column(Integer)
    duration_nights: Mapped[int | None] = mapped_column(Integer)
    duration_label: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('park','show','game','event','experience','journey','itinerary')",
            name="kind_valid",
        ),
        CheckConstraint(
            "detail_status IS NULL OR detail_status IN "
            "('available','missing_url','not_found','not_provided')",
            name="detail_status_valid",
        ),
        Index("ix_attraction_destination_kind", "destination_id", "kind"),
        Index("ix_attraction_parent", "parent_id"),
    )


class DestinationHighlight(Base, Sourced):
    """28 mục nội dung QUẢNG CÁO, tách khỏi attraction.

    Nguồn: 7 section reasons_* và welcome_* trong entertainment/*.json.
    KHÔNG đưa bảng này vào lớp RAG khi trả lời câu hỏi 'có gì chơi ở X'.
    """

    __tablename__ = "destination_highlight"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id"), nullable=False
    )
    complex_id: Mapped[str | None] = mapped_column(ForeignKey("complex.id"))
    section_title: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)


class AttractionItineraryDay(Base, Timestamped):
    """7 ngày hành trình từ 3 topic có journey_data.

    ``activities`` để JSONB chứ không phải bảng con: văn bản tường thuật theo giờ,
    không ai truy vấn riêng một hoạt động, và bản gốc còn có dòng lặp.
    """

    __tablename__ = "attraction_itinerary_day"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    attraction_id: Mapped[str] = mapped_column(
        ForeignKey("attraction.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    text_content: Mapped[str | None] = mapped_column("text", Text)
    activities: Mapped[list[str] | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint("attraction_id", "day_number", name="uq_itinerary_day"),
    )


# --------------------------------------------------------------------------
# Golf & MICE
# --------------------------------------------------------------------------


class GolfCourse(Base, Sourced):
    __tablename__ = "golf_course"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id"), nullable=False
    )
    complex_id: Mapped[str | None] = mapped_column(ForeignKey("complex.id"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    page_url: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    designer: Mapped[str | None] = mapped_column(Text)
    holes: Mapped[int | None] = mapped_column(Integer)
    par: Mapped[int | None] = mapped_column(Integer)
    course_length_raw: Mapped[str | None] = mapped_column(Text)
    total_area: Mapped[str | None] = mapped_column(Text)
    terrain: Mapped[str | None] = mapped_column(Text)
    full_address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    island: Mapped[str | None] = mapped_column(Text)


class GolfFeature(Base, Sourced):
    """Gộp 4 mảng cùng hình dạng {title, description}."""

    __tablename__ = "golf_feature"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("golf_course.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    detail_url: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('feature','award','amenity','experience')", name="kind_valid"
        ),
    )


class GolfCourseMap(Base, Sourced):
    __tablename__ = "golf_course_map"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("golf_course.id", ondelete="CASCADE"), nullable=False
    )
    course_type: Mapped[str | None] = mapped_column(Text)
    map_name: Mapped[str | None] = mapped_column(Text)
    map_url: Mapped[str | None] = mapped_column(Text)


class MiceVenue(Base, Sourced):
    """10 địa điểm hội nghị; chỉ 4 có khối detail nên 6 venue không có phòng."""

    __tablename__ = "mice_venue"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id"), nullable=False
    )
    complex_id: Mapped[str | None] = mapped_column(ForeignKey("complex.id"))
    # 5/10 khớp chính xác tên khách sạn; 5 dòng NULL là Convention Center /
    # Theater / Almaz / VinPalace — công trình độc lập, NULL là đúng nghĩa.
    property_id: Mapped[str | None] = mapped_column(ForeignKey("property.id"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    subtitle: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    overview: Mapped[str | None] = mapped_column(Text)


class MiceRoom(Base, Sourced):
    """36 phòng. Trường area nguồn bẩn: giá trị thật là chuỗi '1250m 2'."""

    __tablename__ = "mice_room"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    venue_id: Mapped[str] = mapped_column(
        ForeignKey("mice_venue.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    area_raw: Mapped[str | None] = mapped_column(Text)
    length_m: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    width_m: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    ceiling_height_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    specifications_raw: Mapped[list[str] | None] = mapped_column(JSONB)
    image_url: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)


class MiceRoomCapacity(Base):
    """Bảng chứ không phải JSONB: câu hỏi thật cần WHERE layout=? AND pax>=?."""

    __tablename__ = "mice_room_capacity"

    room_id: Mapped[str] = mapped_column(
        ForeignKey("mice_room.id", ondelete="CASCADE"), primary_key=True
    )
    layout: Mapped[str] = mapped_column(Text, primary_key=True)
    pax: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "layout IN ('theater','classroom','u_shape','boardroom','banquet','cocktail')",
            name="layout_valid",
        ),
        CheckConstraint("pax > 0", name="pax_positive"),
        Index("ix_mice_capacity_layout_pax", "layout", "pax"),
    )


# --------------------------------------------------------------------------
# Ưu đãi
# --------------------------------------------------------------------------


class Promotion(Base, Sourced):
    """38 thực thể gộp từ 124 dòng trong 9 file.

    Năm cặp cột ngày lấy thẳng từ 5 object có sẵn trong data — KHÔNG parse
    status_reason. status_at_crawl tính lúc 2026-08-01 nên chỉ để tham chiếu;
    trạng thái thật lấy từ view promotion_active theo CURRENT_DATE.
    """

    __tablename__ = "promotion"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    slug: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    is_nationwide: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    booking_from: Mapped[date | None] = mapped_column(Date)
    booking_to: Mapped[date | None] = mapped_column(Date)
    booking_raw: Mapped[str | None] = mapped_column(Text)
    stay_from: Mapped[date | None] = mapped_column(Date)
    stay_to: Mapped[date | None] = mapped_column(Date)
    stay_raw: Mapped[str | None] = mapped_column(Text)
    validity_from: Mapped[date | None] = mapped_column(Date)
    validity_to: Mapped[date | None] = mapped_column(Date)
    validity_raw: Mapped[str | None] = mapped_column(Text)
    purchase_from: Mapped[date | None] = mapped_column(Date)
    purchase_to: Mapped[date | None] = mapped_column(Date)
    purchase_raw: Mapped[str | None] = mapped_column(Text)
    redemption_from: Mapped[date | None] = mapped_column(Date)
    redemption_to: Mapped[date | None] = mapped_column(Date)
    redemption_raw: Mapped[str | None] = mapped_column(Text)
    excluded_dates: Mapped[list[str] | None] = mapped_column(JSONB)
    recurring_schedule: Mapped[str | None] = mapped_column(Text)
    date_confidence: Mapped[str | None] = mapped_column(Text)

    status_at_crawl: Mapped[str | None] = mapped_column(Text)
    status_reason_raw: Mapped[str | None] = mapped_column(Text)
    status_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_score: Mapped[float | None] = mapped_column(Float)
    needs_review: Mapped[bool | None] = mapped_column(Boolean)

    brand_id: Mapped[str | None] = mapped_column(ForeignKey("brand.id"))
    booking_url: Mapped[str | None] = mapped_column(Text)
    app_url: Mapped[str | None] = mapped_column(Text)
    terms_url: Mapped[str | None] = mapped_column(Text)
    content_language: Mapped[str | None] = mapped_column(String(2))

    discount_text: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    crawl_method: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "date_confidence IS NULL OR date_confidence IN "
            "('parsed','partial','unknown')",
            name="date_confidence_valid",
        ),
        CheckConstraint(
            "status_at_crawl IS NULL OR status_at_crawl IN "
            "('active','upcoming','expired','unknown')",
            name="status_at_crawl_valid",
        ),
        Index(
            "ix_promotion_validity",
            "validity_to",
            postgresql_where=text("is_active"),
        ),
    )


class PromotionBenefit(Base, Timestamped):
    """310 dòng. 20 dòng có unit = NULL — không được mặc định thành 'percent'."""

    __tablename__ = "promotion_benefit"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    benefit_type: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    unit: Mapped[str | None] = mapped_column(Text)
    is_maximum: Mapped[bool | None] = mapped_column(Boolean)
    description: Mapped[str | None] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(
            "benefit_type IN ('percentage_discount','voucher','upgrade','hotel_credit',"
            "'multiplier','fixed_amount_discount','gift','free_ticket')",
            name="benefit_type_valid",
        ),
        CheckConstraint(
            "unit IS NULL OR unit IN ('percent','VND','times')", name="unit_valid"
        ),
    )


class PromotionDestination(Base):
    """Lấy HỢP của mọi bản sao xuyên 9 file."""

    __tablename__ = "promotion_destination"

    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), primary_key=True
    )
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destination.id", ondelete="CASCADE"), primary_key=True
    )


class PromotionTag(Base):
    """Gộp 5 chiều phân loại cùng hình dạng mảng chuỗi."""

    __tablename__ = "promotion_tag"

    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), primary_key=True
    )
    tag_type: Mapped[str] = mapped_column(Text, primary_key=True)
    tag_value: Mapped[str] = mapped_column(Text, primary_key=True)

    __table_args__ = (
        CheckConstraint(
            "tag_type IN ('promotion_type','service','channel','customer_group',"
            "'member_tier')",
            name="tag_type_valid",
        ),
        Index("ix_promotion_tag_type_value", "tag_type", "tag_value"),
    )


class PromotionCode(Base, Timestamped):
    __tablename__ = "promotion_code"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    validity: Mapped[str | None] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[list[str] | None] = mapped_column(JSONB)
    is_suspect: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )


class PromotionSection(Base, Timestamped):
    __tablename__ = "promotion_section"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    level: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("promotion_id", "ord", name="uq_promotion_section_ord"),
    )


class PromotionBlock(Base, Timestamped):
    __tablename__ = "promotion_block"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint(
            "block_type IN ('table','bullet_list','heading')", name="block_type_valid"
        ),
    )


class PromotionStep(Base, Timestamped):
    """74 bước đổi thưởng. Cột ord bắt buộc: SQL không giữ thứ tự mảng."""

    __tablename__ = "promotion_step"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column("text", Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("promotion_id", "ord", name="uq_promotion_step_ord"),
    )


class PromotionTerm(Base, Timestamped):
    __tablename__ = "promotion_term"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column("text", Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('term','combination','contact')", name="kind_valid"
        ),
    )


class PromotionRelation(Base, Timestamped):
    __tablename__ = "promotion_relation"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    target_url: Mapped[str | None] = mapped_column(Text)
    target_promotion_id: Mapped[str | None] = mapped_column(
        ForeignKey("promotion.id", ondelete="SET NULL")
    )
    target_brand_id: Mapped[str | None] = mapped_column(ForeignKey("brand.id"))

    __table_args__ = (
        CheckConstraint(
            "kind IN ('related_promotion','related_brand','related_article')",
            name="kind_valid",
        ),
    )


class PromotionPropertyRaw(Base, Timestamped):
    """Bảng kiểm dịch.

    327 giá trị nguồn hầu hết là chuỗi cụt do lỗi parse: 'Vinwonders Wave Park &',
    'Vinwonders Phu Quoc |'. Cố ý KHÔNG ép khoá ngoại bắt buộc vào property.
    """

    __tablename__ = "promotion_property_raw"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    promotion_id: Mapped[str] = mapped_column(
        ForeignKey("promotion.id", ondelete="CASCADE"), nullable=False
    )
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    matched_property_id: Mapped[str | None] = mapped_column(
        ForeignKey("property.id", ondelete="SET NULL")
    )
    match_score: Mapped[float | None] = mapped_column(Float)


# --------------------------------------------------------------------------
# Tri thức
# --------------------------------------------------------------------------


class Faq(Base, Sourced):
    """174 câu hỏi. Chỉ dùng items[], bỏ items_by_category{} vì trùng lặp y hệt."""

    __tablename__ = "faq"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    subcategory: Mapped[str | None] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    destination_id: Mapped[str | None] = mapped_column(ForeignKey("destination.id"))
    content_language: Mapped[str | None] = mapped_column(String(2))
    sort_order: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_faq_category", "category", "subcategory"),)


class PolicyDocument(Base, Sourced):
    """7 văn bản; plain_text dài tới 39.061 ký tự."""

    __tablename__ = "policy_document"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str | None] = mapped_column(Text)
    h1: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    plain_text: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    effective_from: Mapped[date | None] = mapped_column(Date)


class PolicySection(Base, Timestamped):
    __tablename__ = "policy_section"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("policy_document.id", ondelete="CASCADE"), nullable=False
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("document_id", "ord", name="uq_policy_section_ord"),
    )


class PolicyBlock(Base, Timestamped):
    __tablename__ = "policy_block"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("policy_document.id", ondelete="CASCADE"), nullable=False
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        CheckConstraint("block_type IN ('table','list')", name="block_type_valid"),
    )


class OrgInfo(Base, Sourced):
    """Đúng một dòng."""

    __tablename__ = "org_info"

    id: Mapped[int] = mapped_column(
        SmallInteger, primary_key=True, autoincrement=False, server_default=text("1")
    )
    headline: Mapped[str | None] = mapped_column(Text)
    introduction: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    hotline: Mapped[str | None] = mapped_column(Text)
    account_holder: Mapped[str | None] = mapped_column(Text)
    bank_account: Mapped[str | None] = mapped_column(Text)
    bank: Mapped[str | None] = mapped_column(Text)
    business_registration: Mapped[str | None] = mapped_column(Text)
    issued_by: Mapped[str | None] = mapped_column(Text)
    # event/vinpearl_mice_rag_en.json -> page_intro
    mice_intro_title: Mapped[str | None] = mapped_column(Text)
    mice_intro_description: Mapped[str | None] = mapped_column(Text)
    mice_intro_cta: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)


class OrgHighlight(Base, Sourced):
    """9/9 mục hotels_and_resorts khớp chính xác tuyệt đối hotel_name."""

    __tablename__ = "org_highlight"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    destination_id: Mapped[str | None] = mapped_column(ForeignKey("destination.id"))
    property_id: Mapped[str | None] = mapped_column(ForeignKey("property.id"))
    sort_order: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('hotel_resort','package','mice','meeting_event')",
            name="kind_valid",
        ),
    )
