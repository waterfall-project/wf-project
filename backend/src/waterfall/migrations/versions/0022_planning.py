# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the planning, of the history and of the imports (§4.4.1; EP-06, "Tables").

Regime "revised", partitioned by project as ``cost_structure`` (WF-DAT-0050): ``node``, its facet
``task`` and ``task_link``. Regime "project": ``timeline``, ``tracking_entry`` and
``import_report``. Technical rows: ``undo_entry`` and ``paste_plan``. ``cost_structure`` receives
the date its planning starts on and the instant its dates were computed, null until the migration
``0023`` fills them (#2170), the code reading a null as the value it derived.

``create_project_partitions`` is replaced (``CREATE OR REPLACE``, its owner and its grants kept): it
creates the partitions of the four revised tables of a project, each with the trigger that refuses
its truncation, which a partition does not inherit; the partitions of the projects that exist are
created here. Each revised table of the planning has its guard, a trigger of the module of the
planning that refuses, owner included, any write of a row whose revision is marked, the revision
locked ``FOR KEY SHARE`` whatever its status, then read, as the guard of the cost structures does
(#2104); the facet task reads its revision through its node. A row names its revision and its
structure together, by a key towards the structure that names its revision too, and the nodes a row
names — its parent, the tasks of a link, the node of a facet — by a key that names its structure
too: no row binds a revision in progress to a structure, a parent or a task of a marked one, which
the guards, judging the revision of the row alone, would let pass. Every key refuses (``RESTRICT``),
but inside a current revision, where the deletion cascades: the facet with its node, a link with
either of its tasks or its structure, a node with its structure or its parent, an inscription with
its timeline. The service may read, insert, change and delete the rows of the eight tables: the
content of a current revision, a timeline, an inscription, a plan and an entry of the history are
deleted for good, a report at its expiry or its abandonment (§4.4.1).
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.schema import SchemaItem

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "node",
    "task",
    "task_link",
    "timeline",
    "tracking_entry",
    "import_report",
    "undo_entry",
    "paste_plan",
)
GRANT = f"""
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON {", ".join(TABLES)} TO %I',
        current_database() || '_service'
    );
END
$$
"""

# The partitions of a project in each revised table, each with the trigger that refuses its
# truncation: a statement trigger of the parent is not cloned on a partition.
PARTITIONS = """
CREATE OR REPLACE FUNCTION create_project_partitions(project uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    suffix text := '_p_' || replace(project::text, '-', '');
    revised text;
BEGIN
    IF project IS NULL THEN
        RAISE EXCEPTION 'the partitions of a project need its identifier'
            USING ERRCODE = 'null_value_not_allowed';
    END IF;
    IF to_regclass('public.cost_structure' || suffix) IS NOT NULL THEN
        RAISE EXCEPTION 'the project % has its partitions already', project
            USING ERRCODE = 'duplicate_table';
    END IF;
    FOREACH revised IN ARRAY ARRAY['cost_structure', 'node', 'task', 'task_link'] LOOP
        EXECUTE format(
            'CREATE TABLE public.%I PARTITION OF public.%I FOR VALUES IN (%L)',
            revised || suffix,
            revised,
            project
        );
        EXECUTE format(
            'CREATE TRIGGER %I BEFORE TRUNCATE ON public.%I '
            'FOR EACH STATEMENT EXECUTE FUNCTION public.%I()',
            revised || '_refuse_truncate',
            revised || suffix,
            revised || '_refuse_truncate'
        );
    END LOOP;
END
$$;
"""

# The partitions the projects that exist lack, in the three tables of the planning.
EXISTING = """
DO $$
DECLARE
    project uuid;
    revised text;
BEGIN
    FOR project IN SELECT id FROM public.project LOOP
        FOREACH revised IN ARRAY ARRAY['node', 'task', 'task_link'] LOOP
            EXECUTE format(
                'CREATE TABLE public.%I PARTITION OF public.%I FOR VALUES IN (%L)',
                revised || '_p_' || replace(project::text, '-', ''),
                revised,
                project
            );
            EXECUTE format(
                'CREATE TRIGGER %I BEFORE TRUNCATE ON public.%I '
                'FOR EACH STATEMENT EXECUTE FUNCTION public.%I()',
                revised || '_refuse_truncate',
                revised || '_p_' || replace(project::text, '-', ''),
                revised || '_refuse_truncate'
            );
        END LOOP;
    END LOOP;
END
$$
"""

# The function of 0020, which the descent puts back.
FORMER_PARTITIONS = """
CREATE OR REPLACE FUNCTION create_project_partitions(project uuid) RETURNS void
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
"""

# The status of the revision of the row, locked whatever it is, then judged (#2104): by the row's
# own ``revision_id`` for a node and a link, through its node for a task. A task deleted by the
# cascade of its node finds the node gone, which its own guard judged already. The template names
# the table ``<table>``, the row ``<row>`` and the reading of its revision ``<revision of …>``.
REVISION_OF = {
    "node": "FROM public.revision WHERE revision.id = <row>.revision_id FOR KEY SHARE",
    "task_link": "FROM public.revision WHERE revision.id = <row>.revision_id FOR KEY SHARE",
    "task": (
        "FROM public.node JOIN public.revision ON revision.id = node.revision_id "
        "WHERE node.project_id = <row>.project_id AND node.id = <row>.node_id "
        "FOR KEY SHARE OF revision"
    ),
}
GUARD = """
CREATE FUNCTION <table>_refuse_marked_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    status text;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        SELECT revision.status INTO status <revision of OLD>;
        IF status = 'marked' THEN
            RAISE EXCEPTION 'a row of a marked revision is never written: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END IF;
    END IF;
    IF TG_OP <> 'DELETE' THEN
        SELECT revision.status INTO status <revision of NEW>;
        IF status = 'marked' THEN
            RAISE EXCEPTION 'a row of a marked revision is never written: % refused', TG_OP
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END
$$;
CREATE TRIGGER <table>_refuse_marked_change BEFORE INSERT OR UPDATE OR DELETE
ON <table> FOR EACH ROW EXECUTE FUNCTION <table>_refuse_marked_change();
CREATE FUNCTION <table>_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'the <table> is never truncated' USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER <table>_refuse_truncate BEFORE TRUNCATE ON <table>
FOR EACH STATEMENT EXECUTE FUNCTION <table>_refuse_truncate();
"""


def guard(table: str) -> str:
    """Give the guard of a revised table of the planning, and the refusal of its truncation."""
    reading = REVISION_OF[table]
    return (
        GUARD.replace("<revision of OLD>", reading.replace("<row>", "OLD"))
        .replace("<revision of NEW>", reading.replace("<row>", "NEW"))
        .replace("<table>", table)
    )


def stamped() -> list[SchemaItem]:
    """Give the columns of audit of a row."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
    ]


def bounded(column: str, longest: int) -> list[SchemaItem]:
    """Bound a text from 1 to ``longest`` characters, and refuse it blank."""
    return [
        sa.CheckConstraint(
            f"char_length({column}) BETWEEN 1 AND {longest}", name=f"{column}_length"
        ),
        sa.CheckConstraint(f"{column} ~ '\\S'", name=f"{column}_not_blank"),
    ]


def known(column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    """Keep a text among the values the contract enumerates."""
    listed = ", ".join(f"'{value}'" for value in values)
    return sa.CheckConstraint(f"{column} IN ({listed})", name=f"{column}_known")


def of_revision() -> sa.ForeignKeyConstraint:
    """Give the key of a technical row towards its revision, which refuses."""
    return sa.ForeignKeyConstraint(
        ["project_id", "revision_id"], ["revision.project_id", "revision.id"], ondelete="RESTRICT"
    )


def in_revision() -> sa.ForeignKeyConstraint:
    """Give the key of a revised row towards its structure, named with its revision; it cascades.

    The structure names its revision in turn, which refuses: the row is of one revision, and of a
    structure of that revision.
    """
    return sa.ForeignKeyConstraint(
        ["project_id", "structure_id", "revision_id"],
        ["cost_structure.project_id", "cost_structure.id", "cost_structure.revision_id"],
        ondelete="CASCADE",
    )


def of_structure(column: str, *, first: bool = False) -> sa.ForeignKeyConstraint:
    """Give the key of a node a row names, in the structure of the row, which cascades.

    ``first`` puts the project first, so that the key is named after the project, not the column.
    """
    columns = ["project_id", column] if first else [column, "project_id"]
    referred = ["node.project_id", "node.id"] if first else ["node.id", "node.project_id"]
    return sa.ForeignKeyConstraint(
        [*columns, "structure_id"], [*referred, "node.structure_id"], ondelete="CASCADE"
    )


DURATION_UNITS = ("min", "h", "d", "w", "mo", "emin", "eh", "ed", "ew", "emo")


def upgrade() -> None:
    """Create the eight tables, the two columns, the partitions and the guards; grant them."""
    op.add_column("cost_structure", sa.Column("planning_start_on", sa.Date(), nullable=True))
    op.add_column(
        "cost_structure", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True)
    )
    # What a revised row names: a structure with its revision.
    op.create_unique_constraint(
        "uq_cost_structure_project_id", "cost_structure", ["project_id", "id", "revision_id"]
    )
    _revised()
    _planning()
    _history()
    _imports()
    for table in ("node", "task", "task_link"):
        op.execute(guard(table))
    op.execute(PARTITIONS)
    op.execute(EXISTING)
    op.execute(GRANT)


def _revised() -> None:
    op.create_table(
        "node",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("lineage_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("origin_risk_id", sa.Uuid(), nullable=True),
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        *stamped(),
        sa.PrimaryKeyConstraint("project_id", "id"),
        in_revision(),
        of_structure("parent_id", first=True),
        known("kind", ("task", "estimate_line")),
        sa.CheckConstraint("rank >= 1", name="rank_positive"),
        sa.UniqueConstraint("project_id", "id", "kind"),
        sa.UniqueConstraint("id", "project_id", "structure_id"),
        sa.UniqueConstraint(
            "structure_id",
            "parent_id",
            "kind",
            "rank",
            "project_id",
            postgresql_nulls_not_distinct=True,
            deferrable=True,
            initially="IMMEDIATE",
        ),
        sa.CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
        postgresql_partition_by="LIST (project_id)",
    )
    op.create_index(None, "node", ["revision_id"])
    op.create_index(None, "node", ["parent_id"])
    op.create_table(
        "task",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(collation="C"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheduling_mode", sa.Text(), nullable=False),
        sa.Column("duration_value", sa.Numeric(), nullable=False),
        sa.Column("duration_unit", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("start_hours", sa.Numeric(), nullable=False),
        sa.Column("finish_date", sa.Date(), nullable=False),
        sa.Column("finish_hours", sa.Numeric(), nullable=False),
        sa.Column("progress", sa.Text(), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("order_item_id", sa.Uuid(), nullable=True),
        sa.Column("work_package_id", sa.Uuid(), nullable=True),
        sa.Column("total_float_days", sa.Numeric(), nullable=True),
        sa.Column("is_critical", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "node_id"),
        sa.ForeignKeyConstraint(
            ["project_id", "node_id", "kind"],
            ["node.project_id", "node.id", "node.kind"],
            ondelete="CASCADE",
        ),
        of_structure("node_id"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_package_id"], ["work_package.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("kind = 'task'", name="kind_task"),
        *bounded("label", 300),
        known("scheduling_mode", ("automatic", "manual")),
        known("duration_unit", DURATION_UNITS),
        sa.CheckConstraint("duration_value >= 0", name="duration_value_not_negative"),
        sa.CheckConstraint("start_hours BETWEEN 0 AND 24", name="start_hours_of_a_day"),
        sa.CheckConstraint("finish_hours BETWEEN 0 AND 24", name="finish_hours_of_a_day"),
        known("progress", ("not_started", "started", "completed")),
        sa.CheckConstraint(
            "progress = 'not_started' OR started_on IS NOT NULL", name="started_on_when_started"
        ),
        sa.CheckConstraint(
            "(completed_on IS NOT NULL) = (progress = 'completed')",
            name="completed_on_when_completed",
        ),
        sa.CheckConstraint("char_length(external_id) <= 200", name="external_id_length"),
        sa.CheckConstraint(
            "order_item_id IS NULL OR work_package_id IS NULL", name="one_work_breakdown_item"
        ),
        postgresql_partition_by="LIST (project_id)",
    )
    for item in ("order_item", "work_package"):
        op.create_index(
            f"uq_task_{item}",
            "task",
            ["project_id", "structure_id", f"{item}_id"],
            unique=True,
            postgresql_where=sa.text(f"{item}_id IS NOT NULL"),
        )
        op.create_index(None, "task", [f"{item}_id"])
    op.create_table(
        "task_link",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("predecessor_id", sa.Uuid(), nullable=False),
        sa.Column("successor_id", sa.Uuid(), nullable=False),
        sa.Column("link_type", sa.Text(), nullable=False),
        sa.Column("lag_value", sa.Numeric(), nullable=False),
        sa.Column("lag_unit", sa.Text(), nullable=False),
        sa.Column("in_conflict", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "id"),
        in_revision(),
        of_structure("predecessor_id"),
        of_structure("successor_id"),
        sa.CheckConstraint("predecessor_id <> successor_id", name="predecessor_not_successor"),
        known(
            "link_type",
            ("finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish"),
        ),
        known("lag_unit", (*DURATION_UNITS, "percent")),
        sa.UniqueConstraint("structure_id", "predecessor_id", "successor_id", "project_id"),
        postgresql_partition_by="LIST (project_id)",
    )
    op.create_index(None, "task_link", ["predecessor_id"])
    op.create_index(None, "task_link", ["successor_id"])


def _planning() -> None:
    op.create_table(
        "timeline",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(collation="C"), nullable=False),
        *stamped(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        *bounded("label", 200),
    )
    op.create_index(None, "timeline", ["project_id"])
    op.create_table(
        "tracking_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("lineage_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("timeline_id", sa.Uuid(), nullable=True),
        *stamped(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["timeline_id"], ["timeline.id"], ondelete="CASCADE"),
        known("kind", ("timeline", "milestone_tracking")),
        sa.CheckConstraint(
            "(timeline_id IS NOT NULL) = (kind = 'timeline')", name="timeline_when_timeline"
        ),
        sa.UniqueConstraint(
            "lineage_id", "kind", "timeline_id", postgresql_nulls_not_distinct=True
        ),
    )
    op.create_index(None, "tracking_entry", ["project_id"])
    op.create_index(None, "tracking_entry", ["timeline_id"])


UNDONE_KINDS = (
    "cell",
    "node_create",
    "node_delete",
    "node_move",
    "paste",
    "link",
    "progress",
    "remaining",
    "tracking",
    "structure_update",
    "risk_create",
    "risk_update",
    "risk_review",
    "risk_delete",
)
NODE_COLUMNS = (
    "label",
    "description",
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "physical_progress",
    "total_float",
    "is_critical",
    "started_on",
    "completed_on",
    "predecessors",
    "work_breakdown",
    "cost_category",
    "resource_role",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject",
    "payment_delay_days",
    "consumption_year",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)


def _history() -> None:
    op.create_table(
        "undo_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("user_account_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("node_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=False),
        sa.Column("after", postgresql.JSONB(), nullable=False),
        sa.Column("undone", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        of_revision(),
        sa.ForeignKeyConstraint(["user_account_id"], ["user_account.id"], ondelete="RESTRICT"),
        known("kind", UNDONE_KINDS),
        sa.UniqueConstraint("revision_id", "user_account_id", "session_id", "rank"),
    )
    op.create_table(
        "paste_plan",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("user_account_id", sa.Uuid(), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), nullable=False),
        sa.Column("target_column", sa.Text(), nullable=False),
        sa.Column("rows", postgresql.JSONB(), nullable=False),
        sa.Column("structure_lock_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        of_revision(),
        sa.ForeignKeyConstraint(["user_account_id"], ["user_account.id"], ondelete="RESTRICT"),
        known("target_column", NODE_COLUMNS),
        sa.CheckConstraint(
            "structure_lock_version >= 0", name="structure_lock_version_not_negative"
        ),
    )


def _imports() -> None:
    expiring = "'analysed', 'applying', 'applied', 'abandoned', 'expired'"
    op.create_table(
        "import_report",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=True),
        sa.Column("revision_id", sa.Uuid(), nullable=True),
        sa.Column("period_from", sa.Date(), nullable=True),
        sa.Column("period_to", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("report", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["user_account.id"], ondelete="RESTRICT"),
        known("kind", ("ms_project_schedule", "estimate", "remaining", "actual_costs")),
        known(
            "status",
            (
                "analysing",
                "analysed",
                "applying",
                "applied",
                "abandoned",
                "expired",
                "failed",
                "refused",
            ),
        ),
        sa.CheckConstraint(
            f"(expires_at IS NOT NULL) = (status IN ({expiring}))",
            name="expires_at_when_analysed",
        ),
        sa.CheckConstraint(
            "report IS NULL OR jsonb_typeof(report) = 'object'", name="report_object"
        ),
        sa.CheckConstraint("char_length(filename) BETWEEN 1 AND 255", name="filename_length"),
        sa.UniqueConstraint("upload_id"),
    )
    op.create_index(None, "import_report", ["project_id"])


def downgrade() -> None:
    """Drop the eight tables, their partitions, guards and columns: their rows are lost."""
    op.execute(FORMER_PARTITIONS)
    for table in (
        "import_report",
        "paste_plan",
        "undo_entry",
        "tracking_entry",
        "timeline",
        "task_link",
        "task",
        "node",
    ):
        op.drop_table(table)
    for table in ("task_link", "task", "node"):
        op.execute(f"DROP FUNCTION {table}_refuse_truncate()")
        op.execute(f"DROP FUNCTION {table}_refuse_marked_change()")
    op.drop_constraint("uq_cost_structure_project_id", "cost_structure", type_="unique")
    op.drop_column("cost_structure", "scheduled_at")
    op.drop_column("cost_structure", "planning_start_on")
