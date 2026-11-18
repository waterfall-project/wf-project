# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators a revision keeps at its marking (§4.4.1, WF-DAT-0040; EP-10, US-1660/L1).

Regime "revised", partitioned by project as ``cost_structure`` (WF-DAT-0050):
``revision_indicator``, one JSON document by revision, kind and scope — the answer of the contract
of its kind for its scope as the marking computed it, the zones excluded —, unique on the four. A
kind EP-11 adds needs no new column nor table: the check of the kinds alone widens.

``create_project_partitions`` reads the revised tables in the catalogue since ``0026``: it is not
replaced, and creates the partition of the table for each new project, given the function
``revision_indicator_refuse_truncate``. The partitions the projects that exist lack are created here
as it creates them — the table alone, then attached —, each with the trigger that refuses its
truncation.

A row is never changed nor deleted: written by the marking, then held by the immutability of its
revision (WF-DAT-0020). Two triggers say it, owner included. The guard, of the form of
``cost_structure``'s, locks the revision of the row ``FOR KEY SHARE`` whatever its status, then
reads it, and refuses any write of a row of a marked revision: a writer that comes during a marking,
which holds the revision ``FOR UPDATE``, waits for it and is refused (#2104). The second refuses a
row written outside the marking of its revision: a constraint trigger, deferred to the end of the
transaction that wrote the row, which then finds its revision marked, at the instant the row was
computed at (``marked_at`` = ``computed_at``). A row is thus written while its revision, locked by
its marking, is still ``draft``, and by the very transaction that marks it; a current revision has
none, and its abandonment has nothing to take with it. The service may read and insert, never update
nor delete. No row is to take up.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The kinds of document a marking keeps (EP-10, "Tables et migrations"), and the longest scope: an
# identifier of a subproject in text, as the contract writes it.
KINDS = (
    "estimate",
    "remaining",
    "project",
    "cost_curve",
    "cost_curve_payment_delays",
    "earned_value_curves",
)
SCOPE_LENGTH = 36

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT ON revision_indicator TO %I', current_database() || '_service'
    );
END
$$
"""

# The partitions the projects that exist lack, created as ``create_project_partitions`` creates
# them since ``0026``: alone, then attached, with the trigger that refuses their truncation.
EXISTING = """
DO $$
DECLARE
    project uuid;
    partition text;
BEGIN
    FOR project IN SELECT id FROM public.project LOOP
        partition := 'revision_indicator_p_' || replace(project::text, '-', '');
        EXECUTE format(
            'CREATE TABLE public.%I (LIKE public.revision_indicator INCLUDING DEFAULTS '
            'INCLUDING CONSTRAINTS INCLUDING STORAGE INCLUDING COMPRESSION)',
            partition
        );
        EXECUTE format(
            'ALTER TABLE public.revision_indicator ATTACH PARTITION public.%I FOR VALUES IN (%L)',
            partition,
            project
        );
        EXECUTE format(
            'CREATE TRIGGER revision_indicator_refuse_truncate BEFORE TRUNCATE ON public.%I '
            'FOR EACH STATEMENT EXECUTE FUNCTION public.revision_indicator_refuse_truncate()',
            partition
        );
    END LOOP;
END
$$
"""

# The guard of a marked revision, of the form of the cost structures' (migration 0020): the revision
# of the row locked whatever its status, then judged (#2104); and the refusal of the truncation.
GUARD = """
CREATE FUNCTION revision_indicator_refuse_marked_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    status text;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        SELECT revision.status INTO status FROM public.revision
        WHERE revision.id = OLD.revision_id FOR KEY SHARE;
        IF status = 'marked' THEN
            RAISE EXCEPTION 'a row of a marked revision is never written: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END IF;
    END IF;
    IF TG_OP <> 'DELETE' THEN
        SELECT revision.status INTO status FROM public.revision
        WHERE revision.id = NEW.revision_id FOR KEY SHARE;
        IF status = 'marked' THEN
            RAISE EXCEPTION 'a row of a marked revision is never written: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END
$$;
CREATE TRIGGER revision_indicator_refuse_marked_change BEFORE INSERT OR UPDATE OR DELETE
ON revision_indicator FOR EACH ROW EXECUTE FUNCTION revision_indicator_refuse_marked_change();
CREATE FUNCTION revision_indicator_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'the indicators of the revisions are never truncated'
        USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER revision_indicator_refuse_truncate BEFORE TRUNCATE ON revision_indicator
FOR EACH STATEMENT EXECUTE FUNCTION revision_indicator_refuse_truncate();
"""

# The refusal of a row written outside the marking of its revision, judged when the transaction that
# wrote it ends: its revision must then be marked, at the instant the row was computed at.
MARKING_ONLY = """
CREATE FUNCTION revision_indicator_refuse_outside_marking() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    status text;
    marked_at timestamptz;
BEGIN
    SELECT revision.status, revision.marked_at INTO status, marked_at FROM public.revision
    WHERE revision.id = NEW.revision_id;
    IF status IS DISTINCT FROM 'marked' OR marked_at IS DISTINCT FROM NEW.computed_at THEN
        RAISE EXCEPTION 'the indicators of a revision are written by its marking alone: % refused',
            TG_OP USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NULL;
END
$$;
CREATE CONSTRAINT TRIGGER revision_indicator_refuse_outside_marking AFTER INSERT OR UPDATE
ON revision_indicator DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION revision_indicator_refuse_outside_marking();
"""


def upgrade() -> None:
    """Create the table, its triggers and the partitions of the projects; grant it."""
    op.create_table(
        "revision_indicator",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(collation="C"), nullable=False),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("project_id", "id"),
        sa.ForeignKeyConstraint(
            ["project_id", "revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            f"kind IN ({', '.join(repr(kind) for kind in KINDS)})", name="kind_known"
        ),
        sa.CheckConstraint(f"char_length(scope) BETWEEN 1 AND {SCOPE_LENGTH}", name="scope_length"),
        sa.CheckConstraint("scope ~ '\\S'", name="scope_not_blank"),
        sa.CheckConstraint("jsonb_typeof(document) = 'object'", name="document_object"),
        sa.UniqueConstraint("project_id", "revision_id", "kind", "scope"),
        postgresql_partition_by="LIST (project_id)",
    )
    op.execute(GUARD)
    op.execute(MARKING_ONLY)
    op.execute(EXISTING)
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table, its partitions and its triggers: the indicators kept are lost."""
    op.drop_table("revision_indicator")
    op.execute("DROP FUNCTION revision_indicator_refuse_outside_marking()")
    op.execute("DROP FUNCTION revision_indicator_refuse_truncate()")
    op.execute("DROP FUNCTION revision_indicator_refuse_marked_change()")
