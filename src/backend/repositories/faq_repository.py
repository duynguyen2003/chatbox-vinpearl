"""Repository đọc FAQ từ PostgreSQL.

Hỗ trợ search text, filter theo category/destination, pagination,
và trả category count phản ánh filter hiện tại.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select, text

from src.backend.services.db import open_session
from src.data_postgre.db.core import Faq


def _base_filter(
    *,
    q: str | None,
    category: str | None,
    destination: str | None,
):
    """Trả danh sách SQLAlchemy filter conditions dùng chung cho items và count."""
    conditions = []

    if q:
        term = f"%{q}%"
        conditions.append(
            or_(
                Faq.question.ilike(term),
                Faq.answer.ilike(term),
            )
        )

    if category:
        conditions.append(Faq.category == category)

    if destination:
        conditions.append(Faq.destination_id == destination)

    return conditions


def list_faqs(
    *,
    q: str | None = None,
    category: str | None = None,
    destination: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Trả FAQ với search/filter/pagination và category counts.

    Loại duplicate question bằng DISTINCT ON (question) trên PostgreSQL.
    """
    with open_session() as session:
        filters = _base_filter(q=q, category=category, destination=destination)

        # ── Distinct subquery để loại duplicate question ──────────────
        distinct_subq = (
            select(
                func.min(Faq.id).label("id"),
                Faq.question,
            )
            .group_by(Faq.question)
            .subquery("distinct_q")
        )

        # ── Base query join distinct ────────────────────────────────
        base = (
            select(Faq)
            .join(distinct_subq, Faq.id == distinct_subq.c.id)
        )

        for cond in filters:
            base = base.where(cond)

        # ── Total count ─────────────────────────────────────────────
        count_stmt = select(func.count()).select_from(base.subquery())
        total = session.execute(count_stmt).scalar() or 0

        # ── Category counts (phản ánh search + destination, KHÔNG filter category) ──
        cat_filters = _base_filter(q=q, category=None, destination=destination)
        cat_base = (
            select(Faq.category, func.count(func.distinct(Faq.question)).label("cnt"))
            .join(distinct_subq, Faq.id == distinct_subq.c.id)
        )
        for cond in cat_filters:
            cat_base = cat_base.where(cond)
        cat_base = cat_base.group_by(Faq.category).order_by(Faq.category)

        cat_rows = session.execute(cat_base).all()
        categories = [{"name": name, "count": cnt} for name, cnt in cat_rows]

        # ── Items với pagination ────────────────────────────────────
        items_stmt = (
            base
            .order_by(
                Faq.sort_order.asc().nullslast(),
                Faq.question.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        rows = session.execute(items_stmt).scalars().all()

        items = [
            {
                "id": row.id,
                "category": row.category,
                "subcategory": row.subcategory,
                "question": row.question,
                "answer": row.answer,
                "destination_id": row.destination_id,
                "content_language": row.content_language,
                "sort_order": row.sort_order,
            }
            for row in rows
        ]

        return {
            "items": items,
            "categories": categories,
            "total": total,
        }
