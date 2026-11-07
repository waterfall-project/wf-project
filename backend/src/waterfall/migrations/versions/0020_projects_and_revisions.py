# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the projects and of the revisions (§4.4.1; EP-04, "Tables et migrations").

Regime "project": the project, the history of its states, its contributors, its subprojects, its
work packages, order items and deliverables, its revisions. Regime "revised": the cost structures,
the first table partitioned by list on ``project_id`` (WF-DAT-0050), one partition per project,
created in the transaction of the creation of the project by ``create_project_partitions`` — a
function of the owner of the tables (``SECURITY DEFINER``), which the role of the service alone may
execute: it gains no right of DDL. The function takes the identifier alone, reads nothing else, and
refuses a project that has its partitions already; each epic that adds a revised table replaces it
(``CREATE OR REPLACE``) and creates the partitions of the projects that exist.

Two triggers of the module of the revisions refuse, owner included, what a marked revision forbids
(WF-REV-0020): on ``revision``, going back from ``marked``, any change of a marked revision but its
designation as reference, its counter and its audit, and its deletion; on ``cost_structure``, any
write of a row whose revision is marked — the revision locked ``FOR KEY SHARE`` whatever its
status, then read: the marking, which locks it ``FOR UPDATE``, waits for the writer, and a writer
that comes after the marking waits for it and reads the revision marked (#2104). Their search path
is their own and the table they read is named in ``public``: a temporary table of the session never
shadows it. A project is never deleted, nor a transition (``INSERT`` and ``SELECT`` alone); the
rest is deleted by the service, row by row. Every key refuses (``RESTRICT``).
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.schema import SchemaItem

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATES = "('created', 'pricing', 'in_progress', 'completed', 'lost', 'abandoned')"
# The rights of the role of the service: a project and a transition are never deleted.
DELETED = "contributor, subproject, work_package, order_item, deliverable, revision, cost_structure"
GRANT = f"""
DO $$
DECLARE
    service text := current_database() || '_service';
BEGIN
    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON project TO %I', service);
    EXECUTE format('GRANT SELECT, INSERT ON project_state_transition TO %I', service);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON {DELETED} TO %I', service);
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION create_project_partitions(uuid) TO %I', service
    );
END
$$
"""

PARTITIONS = """
CREATE FUNCTION create_project_partitions(project uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    name text := 'cost_structure_p_' || replace(project::text, '-', '');
BEGIN
    IF project IS NULL THEN
        RAISE EXCEPTION 'the partitions of a project need its identifier'
            USING ERRCODE = 'null_value_not_allowed';
    END IF;
    IF to_regclass('public.' || name) IS NOT NULL THEN
        RAISE EXCEPTION 'the project % has its partitions already', project
            USING ERRCODE = 'duplicate_table';
    END IF;
    EXECUTE format(
        'CREATE TABLE public.%I PARTITION OF public.cost_structure FOR VALUES IN (%L)',
        name,
        project
    );
    -- A statement trigger of the parent is not cloned on a partition, which TRUNCATE aims at alone.
    EXECUTE format(
        'CREATE TRIGGER cost_structure_refuse_truncate BEFORE TRUNCATE ON public.%I '
        'FOR EACH STATEMENT EXECUTE FUNCTION public.cost_structure_refuse_truncate()',
        name
    );
END
$$;
REVOKE ALL ON FUNCTION create_project_partitions(uuid) FROM PUBLIC;
"""

# What a marked revision may still change: its designation as reference, which the same transaction
# writes on its project, its counter and its audit.
REVISION_GUARD = """
CREATE FUNCTION revision_refuse_marked_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    kept text[] := ARRAY['is_reference', 'lock_version', 'updated_at', 'updated_by'];
BEGIN
    IF OLD.status = 'marked' AND (
        TG_OP = 'DELETE' OR to_jsonb(NEW) - kept IS DISTINCT FROM to_jsonb(OLD) - kept
    ) THEN
        RAISE EXCEPTION 'a marked revision changes in its designation as reference alone: %',
            TG_OP USING ERRCODE = 'restrict_violation';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER revision_refuse_marked_change BEFORE UPDATE OR DELETE ON revision
FOR EACH ROW EXECUTE FUNCTION revision_refuse_marked_change();
CREATE FUNCTION revision_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'a revision is never truncated' USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER revision_refuse_truncate BEFORE TRUNCATE ON revision
FOR EACH STATEMENT EXECUTE FUNCTION revision_refuse_truncate();
"""

# The revision of the row is locked whatever its status, then judged: a draft one, locked so, waits
# for the marking that holds it ``FOR UPDATE``, and is read marked once it has committed (#2104).
STRUCTURE_GUARD = """
CREATE FUNCTION cost_structure_refuse_marked_change() RETURNS trigger
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
CREATE TRIGGER cost_structure_refuse_marked_change BEFORE INSERT OR UPDATE OR DELETE
ON cost_structure FOR EACH ROW EXECUTE FUNCTION cost_structure_refuse_marked_change();
CREATE FUNCTION cost_structure_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'the cost structure is never truncated' USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER cost_structure_refuse_truncate BEFORE TRUNCATE ON cost_structure
FOR EACH STATEMENT EXECUTE FUNCTION cost_structure_refuse_truncate();
"""


def stamped() -> list[SchemaItem]:
    """Give the columns of audit of a row that changes."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
    ]


def audited() -> list[SchemaItem]:
    """Give the counter of the writes and the columns of audit of a row written on its own."""
    return [
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        *stamped(),
        sa.CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
    ]


def bounded(column: str, longest: int) -> list[SchemaItem]:
    """Bound a text from 1 to ``longest`` characters, and refuse it blank."""
    return [
        sa.CheckConstraint(
            f"char_length({column}) BETWEEN 1 AND {longest}", name=f"{column}_length"
        ),
        sa.CheckConstraint(f"{column} ~ '\\S'", name=f"{column}_not_blank"),
    ]


def sorted_text(name: str, *, nullable: bool = False) -> sa.Column[str]:
    """Give a text column a table sorts, in the order of the code points."""
    return sa.Column(name, sa.Text(collation="C"), nullable=nullable)


def upgrade() -> None:
    """Create the nine tables, the partitions' function and the guards; grant the service."""
    _projects()
    _work_breakdown()
    _revisions()
    op.execute(PARTITIONS)
    op.execute(REVISION_GUARD)
    op.execute(STRUCTURE_GUARD)
    op.execute(GRANT)


def _projects() -> None:
    op.create_table(
        "project",
        sa.Column("id", sa.Uuid(), nullable=False),
        sorted_text("label"),
        sorted_text("code", nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sorted_text("client", nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("inflation_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("win_probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("order_received_on", sa.Date(), nullable=True),
        sa.Column("reference_revision_id", sa.Uuid(), nullable=True),
        sa.Column("current_revision_id", sa.Uuid(), nullable=True),
        sa.Column("contributors_lock_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("work_breakdown_lock_version", sa.Integer(), server_default="0", nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        *bounded("label", 300),
        *bounded("code", 50),
        sa.CheckConstraint("code !~ '/'", name="code_without_slash"),
        *bounded("client", 300),
        sa.CheckConstraint(f"state IN {STATES}", name="state_known"),
        sa.CheckConstraint(
            "inflation_rate BETWEEN 0 AND 1", name="inflation_rate_between_zero_and_one"
        ),
        sa.CheckConstraint(
            "win_probability BETWEEN 0 AND 1", name="win_probability_between_zero_and_one"
        ),
        sa.CheckConstraint(
            "contributors_lock_version >= 0", name="contributors_lock_version_not_negative"
        ),
        sa.CheckConstraint(
            "work_breakdown_lock_version >= 0", name="work_breakdown_lock_version_not_negative"
        ),
    )
    op.create_index(None, "project", ["reference_revision_id"])
    op.create_index(None, "project", ["current_revision_id"])
    op.create_table(
        "project_state_transition",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=True),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(f"from_state IN {STATES}", name="from_state_known"),
        sa.CheckConstraint(f"to_state IN {STATES}", name="to_state_known"),
    )
    op.create_index(None, "project_state_transition", ["project_id", "occurred_at"])
    op.create_table(
        "contributor",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_account_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "user_account_id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_account_id"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("kind IN ('project_manager', 'contributor')", name="kind_known"),
    )
    op.create_index(None, "contributor", ["user_account_id"])
    op.create_table(
        "subproject",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sorted_text("code"),
        sorted_text("label"),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("project_id", "code"),
        *bounded("code", 31),
        sa.CheckConstraint("code !~ '[:\\\\/?*\\[\\]]'", name="code_form"),
        *bounded("label", 300),
    )


def _work_breakdown() -> None:
    parents = (
        ("work_package", "project_id", "project"),
        ("order_item", "work_package_id", "work_package"),
        ("deliverable", "order_item_id", "order_item"),
    )
    for table, parent, parent_table in parents:
        marked = table != "deliverable"
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("project_id", sa.Uuid(), nullable=False),
            *([sa.Column(parent, sa.Uuid(), nullable=False)] if parent != "project_id" else []),
            sorted_text("label"),
            sa.Column("position", sa.Integer(), nullable=False),
            *([sa.Column("deleted_at", sa.DateTime(timezone=True))] if marked else []),
            *stamped(),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
            *(
                [sa.ForeignKeyConstraint([parent], [f"{parent_table}.id"], ondelete="RESTRICT")]
                if parent != "project_id"
                else []
            ),
            *bounded("label", 300),
            sa.CheckConstraint("position >= 0", name="position_not_negative"),
        )
        op.create_index(
            f"uq_{table}_position",
            table,
            [parent, "position"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL") if marked else None,
        )
        if parent != "project_id":
            op.create_index(None, table, ["project_id"])


def _revisions() -> None:
    op.create_table(
        "revision",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sorted_text("version_name", nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_year", sa.SmallInteger(), nullable=False),
        sa.Column("is_reference", sa.Boolean(), nullable=False),
        sa.Column("lineage_id", sa.Uuid(), nullable=False),
        sa.Column("source_revision_id", sa.Uuid(), nullable=True),
        *audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("project_id", "id"),
        # The source is a revision of the same project, and never the revision itself.
        sa.ForeignKeyConstraint(
            ["project_id", "source_revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("source_revision_id <> id", name="source_not_self"),
        sa.CheckConstraint("status IN ('draft', 'marked')", name="status_known"),
        *bounded("version_name", 100),
        sa.CheckConstraint(
            "status <> 'marked' OR version_name IS NOT NULL", name="version_name_when_marked"
        ),
        sa.CheckConstraint(
            "(marked_at IS NOT NULL) = (status = 'marked')", name="marked_at_when_marked"
        ),
        sa.CheckConstraint("reference_year BETWEEN 2000 AND 2100", name="reference_year_bound"),
    )
    partial = {
        "uq_revision_draft": (["project_id"], "status = 'draft'"),
        "uq_revision_version_name": (["project_id", "version_name"], "status = 'marked'"),
        "uq_revision_reference": (["project_id"], "is_reference"),
    }
    for name, (columns, where) in partial.items():
        op.create_index(name, "revision", columns, unique=True, postgresql_where=sa.text(where))
    for column in ("reference_revision_id", "current_revision_id"):
        op.create_foreign_key(None, "project", "revision", [column], ["id"], ondelete="RESTRICT")
    op.create_table(
        "cost_structure",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sorted_text("label"),
        sa.Column("is_merged", sa.Boolean(), nullable=False),
        sa.Column("lineage_id", sa.Uuid(), nullable=False),
        *audited(),
        sa.PrimaryKeyConstraint("project_id", "id"),
        sa.ForeignKeyConstraint(
            ["project_id", "revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("kind IN ('main')", name="kind_known"),
        *bounded("label", 300),
        postgresql_partition_by="LIST (project_id)",
    )
    op.create_index(None, "cost_structure", ["project_id", "revision_id"])
    op.create_index(
        "uq_cost_structure_main",
        "cost_structure",
        ["project_id", "revision_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'main'"),
    )


def downgrade() -> None:
    """Drop the nine tables, their partitions, the guards and the function: their rows are lost."""
    for column in ("current_revision_id", "reference_revision_id"):
        op.drop_constraint(f"fk_project_{column}_revision", "project", type_="foreignkey")
    for table in (
        "cost_structure",
        "revision",
        "deliverable",
        "order_item",
        "work_package",
        "subproject",
        "contributor",
        "project_state_transition",
        "project",
    ):
        op.drop_table(table)
    for function in (
        "cost_structure_refuse_truncate()",
        "revision_refuse_truncate()",
        "cost_structure_refuse_marked_change()",
        "revision_refuse_marked_change()",
        "create_project_partitions(uuid)",
    ):
        op.execute(f"DROP FUNCTION {function}")
