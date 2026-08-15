"""split public into core and app schemas

41 tables stop living flat in `public`:

    core.*  34 tables - business data plus the two ingest bookkeeping tables
    app.*    7 tables - chat sessions, messages, tickets, event log

Nothing about the rows changes. ALTER TABLE ... SET SCHEMA moves the table
together with its indexes, constraints, sequences and foreign keys, so this is
a catalog-only operation.

Two details that matter:

1. `alembic_version` deliberately stays in `public`. Alembic looks it up on the
   default search_path, and pinning it to a managed schema would mean a broken
   migration could strand the version marker inside a schema it just dropped.

2. The database default search_path becomes `public, core, app`, so unqualified
   SQL ("SELECT * FROM room") keeps working - tests, psql sessions and DataGrip
   consoles all rely on that. It only applies to connections opened after this
   migration commits.

   `public` must stay FIRST even though it now holds only alembic_version.
   current_schema() returns the head of search_path, and SQLAlchemy takes that
   as the connection's default schema; whatever sits there is the schema whose
   tables get reported with schema=None on reflection. Put `core` first and
   every core table reflects as unqualified, stops matching the metadata that
   declares schema='core', and `alembic check` reports all 34 as missing.

Revision ID: 27b9683b75a6
Revises: 9b9c2a68204e
Create Date: 2026-08-09 22:14:03.118742

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '27b9683b75a6'
down_revision: Union[str, Sequence[str], None] = '9b9c2a68204e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APP_TABLES = (
    "app_user",
    "session",
    "message",
    "message_citation",
    "message_feedback",
    "ticket",
    "event_log",
)

# Everything else that this project owns. Listed explicitly rather than swept
# from the catalog so that an unrelated table someone leaves in `public` is not
# silently dragged along.
CORE_TABLES = (
    "amenity",
    "attraction",
    "brand",
    "complex",
    "content_block",
    "content_section",
    "data_quality_issue",
    "destination",
    "destination_alias",
    "destination_highlight",
    "dining_service",
    "entity_source",
    "faq",
    "golf_course",
    "golf_feature",
    "ingest_run",
    "media",
    "mice_room",
    "mice_room_capacity",
    "mice_venue",
    "org_highlight",
    "org_info",
    "page_link",
    "policy_document",
    "promotion",
    "promotion_benefit",
    "promotion_code",
    "promotion_destination",
    "promotion_property_raw",
    "promotion_relation",
    "promotion_term",
    "property",
    "room",
    "source",
)

# promotion_active is a view built by an earlier migration; it moves too.
CORE_VIEWS = ("promotion_active",)


def _move(names: tuple[str, ...], schema: str, kind: str = "TABLE") -> None:
    for name in names:
        op.execute(f'ALTER {kind} IF EXISTS "{name}" SET SCHEMA {schema}')


def _set_search_path(value: str) -> None:
    """ALTER DATABASE takes a literal name, so build the statement dynamically.

    Hardcoding "vinpearl" would break any deployment that names the database
    something else.
    """
    op.execute(
        "DO $$ BEGIN EXECUTE format("
        f"'ALTER DATABASE %I SET search_path TO {value}', current_database()"
        "); END $$"
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    # Order is free here: Postgres records view dependencies by OID, not by
    # name, so moving a table does not invalidate a view that reads it.
    _move(CORE_VIEWS, "core", kind="VIEW")
    _move(CORE_TABLES, "core")
    _move(APP_TABLES, "app")

    # Unqualified SQL keeps resolving. Takes effect on new connections only.
    _set_search_path("public, core, app")


def downgrade() -> None:
    _set_search_path("public")

    for name in APP_TABLES:
        op.execute(f'ALTER TABLE IF EXISTS app."{name}" SET SCHEMA public')
    for name in CORE_TABLES:
        op.execute(f'ALTER TABLE IF EXISTS core."{name}" SET SCHEMA public')
    for name in CORE_VIEWS:
        op.execute(f'ALTER VIEW IF EXISTS core."{name}" SET SCHEMA public')

    op.execute("DROP SCHEMA IF EXISTS app")
    op.execute("DROP SCHEMA IF EXISTS core")
