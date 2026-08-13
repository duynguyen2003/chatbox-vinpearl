"""add api schema with aggregate read views

One rule to remember: `core.*` is the real table, `api.*` is the same thing
already joined and folded into JSON. Swap the schema prefix to switch between
them. Reading code touches 11 views instead of 34 tables; nothing about the
storage layer changes, so every foreign key and CHECK stays where it is.

Names are deliberately reused (`core.room` the table, `api.room` the view).
search_path lists `core` before `api`, so an unqualified `room` always means the
table - the view only answers to `api.room`.

These are plain views, not materialised ones: the data is small (largest is 768
rows) and a materialised view would need refreshing after every ingest run.

Revision ID: e94fc771da30
Revises: 27b9683b75a6
Create Date: 2026-08-09 22:31:47.905112

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e94fc771da30'
down_revision: Union[str, Sequence[str], None] = '27b9683b75a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The shape core.promotion_active had before the merge migration added `tags`.
# Only downgrade() needs it; see the note there.
PROMOTION_COLUMNS_BEFORE_TAGS = (
    "id", "slug", "title", "summary", "is_nationwide",
    "booking_from", "booking_to", "booking_raw",
    "stay_from", "stay_to", "stay_raw",
    "validity_from", "validity_to", "validity_raw",
    "purchase_from", "purchase_to", "purchase_raw",
    "redemption_from", "redemption_to", "redemption_raw",
    "excluded_dates", "recurring_schedule", "date_confidence",
    "status_at_crawl", "status_reason_raw", "status_calculated_at",
    "quality_score", "needs_review", "brand_id",
    "booking_url", "app_url", "terms_url", "content_language",
    "discount_text", "full_text", "word_count", "crawl_method",
    "published_at", "source_updated_at", "first_seen_at", "last_seen_at",
    "content_hash", "is_active", "source_id", "ingest_run_id",
    "created_at", "updated_at",
)

VIEWS: dict[str, str] = {}

# --------------------------------------------------------------------------
# promotion_active - moved out of core and rebuilt.
#
# The original was written as SELECT *, which Postgres expands at creation
# time, so it never picked up the `tags` column added by the merge migration.
# --------------------------------------------------------------------------
VIEWS["promotion_active"] = """
SELECT *
FROM core.promotion
WHERE is_active
  AND (booking_to  IS NULL OR booking_to  >= CURRENT_DATE)
  AND (validity_to IS NULL OR validity_to >= CURRENT_DATE)
"""

VIEWS["hotel"] = """
SELECT
    p.id,
    p.name,
    p.kind,
    p.address,
    p.url,
    p.destination_id,
    coalesce(d.name_vi, d.name_en)  AS destination,
    c.name                          AS complex,
    b.name                          AS brand,
    (SELECT count(*) FROM core.room r
      WHERE r.property_id = p.id AND r.is_active)                 AS room_count,
    (SELECT min(r.price_from_amount) FROM core.room r
      WHERE r.property_id = p.id AND r.is_active)                 AS price_from_min,
    (SELECT jsonb_agg(jsonb_build_object(
                'id',         r.id,
                'name',       r.name,
                'guests',     r.guest_count,
                'area_sqm',   r.area_sqm,
                'price_from', r.price_from_amount,
                'currency',   r.price_from_currency)
              ORDER BY r.room_index)
       FROM core.room r
      WHERE r.property_id = p.id AND r.is_active)                 AS rooms,
    (SELECT jsonb_agg(jsonb_build_object(
                'name',        ds.name,
                'description', ds.description,
                'hours',       ds.hours_display)
              ORDER BY ds.service_index)
       FROM core.dining_service ds
      WHERE ds.property_id = p.id AND ds.is_active)               AS dining,
    s.url                           AS source_url
FROM core.property p
JOIN core.destination d ON d.id = p.destination_id
LEFT JOIN core.complex c ON c.id = p.complex_id
LEFT JOIN core.brand   b ON b.id = p.brand_id
LEFT JOIN core.source  s ON s.id = p.source_id
WHERE p.is_active
"""

# amenity_ids lost its foreign key when room_amenity was folded into an array;
# resolving the names here means callers never touch the raw ids.
VIEWS["room"] = """
SELECT
    r.id,
    r.name,
    r.property_id,
    p.name                          AS property,
    p.destination_id,
    coalesce(d.name_vi, d.name_en)  AS destination,
    r.room_index,
    r.guest_count,
    r.area_sqm,
    r.price_from_amount,
    r.price_from_currency,
    r.is_rate_suspect,
    r.bed_types,
    r.has_wifi,
    r.image_url,
    (SELECT array_agg(coalesce(a.name_vi, a.name_en) ORDER BY a.name_en)
       FROM core.amenity a
      WHERE a.id = ANY (r.amenity_ids))                           AS amenities
FROM core.room r
JOIN core.property p    ON p.id = r.property_id
JOIN core.destination d ON d.id = p.destination_id
WHERE r.is_active
"""

VIEWS["promotion"] = """
SELECT
    pr.id,
    pr.slug,
    pr.title,
    pr.summary,
    pr.is_nationwide,
    pr.validity_from,
    pr.validity_to,
    pr.booking_from,
    pr.booking_to,
    pr.discount_text,
    pr.tags,
    b.name                          AS brand,
    pr.booking_url,
    (SELECT array_agg(pd.destination_id ORDER BY pd.destination_id)
       FROM core.promotion_destination pd
      WHERE pd.promotion_id = pr.id)                              AS destination_ids,
    (SELECT jsonb_agg(jsonb_build_object(
                'type',        pb.benefit_type,
                'value',       pb.value,
                'unit',        pb.unit,
                'description', pb.description)
              ORDER BY pb.sort_order)
       FROM core.promotion_benefit pb
      WHERE pb.promotion_id = pr.id)                              AS benefits,
    (SELECT array_agg(pc.code ORDER BY pc.code)
       FROM core.promotion_code pc
      WHERE pc.promotion_id = pr.id AND NOT pc.is_suspect)        AS codes,
    (SELECT jsonb_object_agg(t.kind, t.texts)
       FROM (SELECT pt.kind, jsonb_agg(pt.text ORDER BY pt.ord) AS texts
               FROM core.promotion_term pt
              WHERE pt.promotion_id = pr.id
              GROUP BY pt.kind) t)                                AS terms,
    (pr.validity_to IS NULL OR pr.validity_to >= CURRENT_DATE)    AS is_current
FROM core.promotion pr
LEFT JOIN core.brand b ON b.id = pr.brand_id
WHERE pr.is_active
"""

VIEWS["attraction"] = """
SELECT
    a.id,
    a.kind,
    a.title,
    a.summary,
    a.description,
    a.location_text,
    a.destination_id,
    coalesce(d.name_vi, d.name_en)  AS destination,
    c.name                          AS complex,
    parent.title                    AS parent_title,
    a.duration_days,
    a.duration_label,
    a.itinerary,
    a.detail_url,
    a.image_url
FROM core.attraction a
JOIN core.destination d      ON d.id = a.destination_id
LEFT JOIN core.complex c     ON c.id = a.complex_id
LEFT JOIN core.attraction parent ON parent.id = a.parent_id
WHERE a.is_active
"""

VIEWS["golf_course"] = """
SELECT
    g.id,
    g.name,
    g.destination_id,
    coalesce(d.name_vi, d.name_en)  AS destination,
    c.name                          AS complex,
    g.designer,
    g.holes,
    g.par,
    g.course_length_raw,
    g.full_address,
    g.page_url,
    (SELECT jsonb_object_agg(f.kind, f.items)
       FROM (SELECT gf.kind,
                    jsonb_agg(jsonb_build_object(
                        'title',       gf.title,
                        'description', gf.description,
                        'variant',     gf.variant)
                      ORDER BY gf.sort_order) AS items
               FROM core.golf_feature gf
              WHERE gf.course_id = g.id AND gf.is_active
              GROUP BY gf.kind) f)                                AS features
FROM core.golf_course g
JOIN core.destination d  ON d.id = g.destination_id
LEFT JOIN core.complex c ON c.id = g.complex_id
WHERE g.is_active
"""

VIEWS["mice_venue"] = """
SELECT
    v.id,
    v.name,
    v.destination_id,
    coalesce(d.name_vi, d.name_en)  AS destination,
    v.address,
    v.phone,
    v.summary,
    p.name                          AS property,
    (SELECT jsonb_agg(jsonb_build_object(
                'name',      mr.name,
                'area_sqm',  mr.area_sqm,
                'length_m',  mr.length_m,
                'width_m',   mr.width_m,
                'capacity',  (SELECT jsonb_object_agg(cap.layout, cap.pax)
                                FROM core.mice_room_capacity cap
                               WHERE cap.room_id = mr.id))
              ORDER BY mr.sort_order)
       FROM core.mice_room mr
      WHERE mr.venue_id = v.id AND mr.is_active)                  AS rooms,
    (SELECT max(cap.pax)
       FROM core.mice_room mr
       JOIN core.mice_room_capacity cap ON cap.room_id = mr.id
      WHERE mr.venue_id = v.id AND mr.is_active)                  AS max_pax
FROM core.mice_venue v
JOIN core.destination d  ON d.id = v.destination_id
LEFT JOIN core.property p ON p.id = v.property_id
WHERE v.is_active
"""

VIEWS["policy_document"] = """
SELECT
    pd.id,
    pd.title,
    pd.category,
    pd.word_count,
    pd.effective_from,
    (SELECT jsonb_agg(jsonb_build_object(
                'heading', cs.heading,
                'content', cs.content)
              ORDER BY cs.ord)
       FROM core.content_section cs
      WHERE cs.entity_type = 'policy_document' AND cs.entity_id = pd.id) AS sections,
    (SELECT count(*)
       FROM core.content_block cb
      WHERE cb.entity_type = 'policy_document' AND cb.entity_id = pd.id) AS block_count,
    pd.plain_text
FROM core.policy_document pd
WHERE pd.is_active
"""

VIEWS["faq"] = """
SELECT
    f.id,
    f.category,
    f.subcategory,
    f.question,
    f.answer,
    f.destination_id,
    coalesce(d.name_vi, d.name_en)  AS destination,
    f.content_language,
    f.sort_order
FROM core.faq f
LEFT JOIN core.destination d ON d.id = f.destination_id
WHERE f.is_active
"""

# The one place to answer "what do we actually have for this place?"
VIEWS["destination"] = """
SELECT
    d.id,
    coalesce(d.name_vi, d.name_en)  AS name,
    d.name_en,
    d.name_vi,
    d.province,
    d.region,
    d.lat,
    d.lng,
    (SELECT array_agg(da.alias ORDER BY da.alias)
       FROM core.destination_alias da WHERE da.destination_id = d.id)   AS aliases,
    (SELECT count(*) FROM core.property p
      WHERE p.destination_id = d.id AND p.is_active)                    AS hotels,
    (SELECT count(*) FROM core.attraction a
      WHERE a.destination_id = d.id AND a.is_active)                    AS attractions,
    (SELECT count(*) FROM core.golf_course g
      WHERE g.destination_id = d.id AND g.is_active)                    AS golf_courses,
    (SELECT count(*) FROM core.mice_venue v
      WHERE v.destination_id = d.id AND v.is_active)                    AS mice_venues,
    (SELECT count(*) FROM core.promotion_destination pd
      WHERE pd.destination_id = d.id)                                   AS promotions
FROM core.destination d
"""

# Ingest health without joining two tables by hand every time.
VIEWS["data_health"] = """
SELECT
    ir.id           AS run_id,
    ir.started_at,
    ir.finished_at,
    ir.status,
    ir.git_sha,
    q.severity,
    q.rule,
    count(q.id)     AS issues
FROM core.ingest_run ir
LEFT JOIN core.data_quality_issue q ON q.ingest_run_id = ir.id
GROUP BY ir.id, ir.started_at, ir.finished_at, ir.status, ir.git_sha,
         q.severity, q.rule
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS api")

    # Rebuilt below with the tags column, so drop rather than move.
    op.execute("DROP VIEW IF EXISTS core.promotion_active")

    for name, body in VIEWS.items():
        op.execute(f"CREATE VIEW api.{name} AS{body}")

    op.execute(
        "DO $$ BEGIN EXECUTE format("
        "'ALTER DATABASE %I SET search_path TO public, core, app, api',"
        " current_database()); END $$"
    )


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN EXECUTE format("
        "'ALTER DATABASE %I SET search_path TO public, core, app',"
        " current_database()); END $$"
    )

    for name in reversed(list(VIEWS)):
        op.execute(f"DROP VIEW IF EXISTS api.{name}")

    op.execute("DROP SCHEMA IF EXISTS api")

    # Columns listed one by one on purpose. SELECT * would bind the rebuilt view
    # to `tags` as well, and the migration below this one drops that column -
    # Postgres then refuses with "cannot drop column tags ... view depends on it"
    # and downgrading past this point becomes impossible.
    op.execute(f"""
        CREATE VIEW core.promotion_active AS
        SELECT {", ".join(PROMOTION_COLUMNS_BEFORE_TAGS)}
        FROM core.promotion
        WHERE is_active
          AND (booking_to  IS NULL OR booking_to  >= CURRENT_DATE)
          AND (validity_to IS NULL OR validity_to >= CURRENT_DATE)
    """)
