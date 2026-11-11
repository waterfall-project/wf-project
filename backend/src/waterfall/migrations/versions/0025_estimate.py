# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the estimate (§4.4.1; EP-07, "Tables et migrations").

Regime "revised", partitioned by project as ``node`` (WF-DAT-0050): ``estimate_line``, the facet of
a node of kind ``estimate_line``, and what a revision keeps of the reference — ``revision_rate``,
the rates it is priced at, and the images of the roles, the calendars and the categories it
employs at its marking: ``revision_role``, ``revision_calendar``, ``revision_category``.
``revision`` receives the rate of inflation and the probability of winning kept at its marking,
null until then; no row is to take up, nothing existing before.

``create_project_partitions`` is replaced (``CREATE OR REPLACE``, its owner and its grants kept): it
creates the partitions of the nine revised tables of a project, each with the trigger that refuses
its truncation; the partitions the projects that exist lack are created here. Each table has its
guard, a trigger of the module of the estimate that refuses, owner included, any write of a row
whose revision is marked, the revision locked ``FOR KEY SHARE`` whatever its status, then read, as
the guard of the tasks does (#2104): a line reads its revision through its node, a rate and an
image by their own ``revision_id``. The line follows its node (``CASCADE``, WF-DAT-0090); every
other key refuses. A subproject is named with its project, which a new unique key of
``subproject`` allows. The service may read, insert, change and delete a line and a rate of a
current revision; an image it writes once, at the marking, and never deletes.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.schema import SchemaItem

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IMAGES = ("revision_role", "revision_calendar", "revision_category")
TABLES = ("estimate_line", "revision_rate", *IMAGES)


def grant(rights: str, tables: Sequence[str]) -> str:
    """Give the grant of rights on tables to the role of the service of this database."""
    return f"""
DO $$
BEGIN
    EXECUTE format(
        'GRANT {rights} ON {", ".join(tables)} TO %I', current_database() || '_service'
    );
END
$$
"""


# The function that creates the partitions of a project in the revised tables ``<tables>`` names,
# each with the trigger that refuses its truncation: a statement trigger of the parent is not cloned
# on a partition.
PARTITIONS_OF = """
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
    FOREACH revised IN ARRAY ARRAY[<tables>] LOOP
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


def listed(tables: Sequence[str]) -> str:
    """Give the tables named as the elements of an array of texts."""
    return ", ".join(f"'{table}'" for table in tables)


# The function of 0022, which the descent puts back; this one creates the partitions of the estimate
# besides.
PLANNING = ("cost_structure", "node", "task", "task_link")
FORMER_PARTITIONS = PARTITIONS_OF.replace("<tables>", listed(PLANNING))
PARTITIONS = PARTITIONS_OF.replace("<tables>", listed((*PLANNING, *TABLES)))

# The partitions the projects that exist lack, in the five tables of the estimate.
EXISTING = """
DO $$
DECLARE
    project uuid;
    revised text;
BEGIN
    FOR project IN SELECT id FROM public.project LOOP
        FOREACH revised IN ARRAY ARRAY[<tables>] LOOP
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
""".replace("<tables>", listed(TABLES))

# The status of the revision of the row, locked whatever it is, then judged (#2104): through its
# node for a line, as for a task, which a line deleted by the cascade of its node finds gone; by
# the row's own ``revision_id`` for a rate and an image.
BY_NODE = (
    "FROM public.node JOIN public.revision ON revision.id = node.revision_id "
    "WHERE node.project_id = <row>.project_id AND node.id = <row>.node_id "
    "FOR KEY SHARE OF revision"
)
BY_REVISION = "FROM public.revision WHERE revision.id = <row>.revision_id FOR KEY SHARE"
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
    """Give the guard of a revised table of the estimate, and the refusal of its truncation."""
    reading = BY_NODE if table == "estimate_line" else BY_REVISION
    return (
        GUARD.replace("<revision of OLD>", reading.replace("<row>", "OLD"))
        .replace("<revision of NEW>", reading.replace("<row>", "NEW"))
        .replace("<table>", table)
    )


def of_revision() -> sa.ForeignKeyConstraint:
    """Give the key of a row towards its revision, named with its project; it refuses."""
    return sa.ForeignKeyConstraint(
        ["project_id", "revision_id"], ["revision.project_id", "revision.id"], ondelete="RESTRICT"
    )


def not_negative(column: str) -> sa.CheckConstraint:
    """Refuse a negative value of a column."""
    return sa.CheckConstraint(f"{column} >= 0", name=f"{column}_not_negative")


def counted() -> sa.CheckConstraint:
    """Refuse a negative counter of the writes."""
    return not_negative("lock_version")


def image(table: str, *columns: SchemaItem) -> None:
    """Create the image of an object of the reference a revision keeps, with its own columns.

    Its audit and its counter are the object's at the marking, its authors copied, not keys.
    """
    op.create_table(
        table,
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        *columns,
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "id"),
        of_revision(),
        counted(),
        postgresql_partition_by="LIST (project_id)",
    )


def text(column: str) -> sa.Column[str]:
    """Give a text of an image, in the order of the code points, as its object keeps it."""
    return sa.Column(column, sa.Text(collation="C"), nullable=False)


def uuid(column: str) -> sa.Column[object]:
    """Give an identifier an image keeps."""
    return sa.Column(column, sa.Uuid(), nullable=False)


DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def upgrade() -> None:
    """Create the five tables, the two columns, the partitions and the guards; grant them."""
    op.add_column("revision", sa.Column("inflation_rate", sa.Numeric(5, 4), nullable=True))
    op.add_column("revision", sa.Column("win_probability", sa.Numeric(5, 4), nullable=True))
    # What a line names: a subproject with its project.
    op.create_unique_constraint("uq_subproject_id", "subproject", ["id", "project_id"])
    _lines()
    op.create_table(
        "revision_rate",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("cost_category_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "id"),
        of_revision(),
        sa.CheckConstraint("origin IN ('reference', 'projected')", name="origin_known"),
        sa.CheckConstraint("amount >= 0.01", name="amount_positive"),
        sa.UniqueConstraint("revision_id", "cost_category_id", "project_id"),
        postgresql_partition_by="LIST (project_id)",
    )
    _images()
    for table in TABLES:
        op.execute(guard(table))
    op.execute(PARTITIONS)
    op.execute(EXISTING)
    op.execute(grant("SELECT, INSERT, UPDATE, DELETE", ("estimate_line", "revision_rate")))
    op.execute(grant("SELECT, INSERT", IMAGES))


def _lines() -> None:
    op.create_table(
        "estimate_line",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(collation="C"), nullable=False),
        sa.Column("cost_category_id", sa.Uuid(), nullable=False),
        sa.Column("resource_role_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("unit_disbursement", sa.Numeric(14, 2), nullable=True),
        sa.Column("payment_delay_days", sa.Integer(), nullable=False),
        sa.Column("subproject_id", sa.Uuid(), nullable=True),
        sa.Column("reference_quantity", sa.Numeric(14, 4), nullable=True),
        sa.Column("reference_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("reference_unit_disbursement", sa.Numeric(14, 2), nullable=True),
        sa.Column("base_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("budgeted_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("reestimated_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("consumption_year", sa.SmallInteger(), nullable=False),
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("project_id", "node_id"),
        sa.ForeignKeyConstraint(
            ["project_id", "node_id", "kind"],
            ["node.project_id", "node.id", "node.kind"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "subproject_id"],
            ["subproject.project_id", "subproject.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["cost_category_id"], ["cost_category.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resource_role_id"], ["resource_role.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("kind = 'estimate_line'", name="kind_estimate_line"),
        sa.CheckConstraint("char_length(label) BETWEEN 1 AND 300", name="label_length"),
        sa.CheckConstraint("label ~ '\\S'", name="label_not_blank"),
        not_negative("quantity"),
        not_negative("hours"),
        not_negative("unit_disbursement"),
        not_negative("payment_delay_days"),
        sa.CheckConstraint("(resource_role_id IS NULL) = (hours IS NULL)", name="hours_of_a_role"),
        sa.CheckConstraint(
            "(resource_role_id IS NULL) = (unit_disbursement IS NOT NULL)",
            name="unit_disbursement_without_role",
        ),
        sa.CheckConstraint("consumption_year BETWEEN 2000 AND 2100", name="consumption_year_bound"),
        counted(),
        postgresql_partition_by="LIST (project_id)",
    )
    for column in ("cost_category_id", "resource_role_id", "subproject_id"):
        op.create_index(None, "estimate_line", [column])


def _images() -> None:
    image(
        "revision_role",
        uuid("resource_role_id"),
        text("code"),
        text("label"),
        uuid("org_node_id"),
        text("org_node_label"),
        uuid("cost_category_id"),
        text("cost_category_label"),
        uuid("calendar_id"),
        text("calendar_label"),
        sa.Column("monthly_hours", sa.Numeric(), nullable=False),
        sa.Column("headcount", sa.Numeric(), nullable=False),
        sa.UniqueConstraint("revision_id", "resource_role_id", "project_id"),
    )
    image(
        "revision_calendar",
        uuid("calendar_id"),
        text("label"),
        *(sa.Column(day, sa.Numeric(4, 2), nullable=False) for day in DAYS),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("revision_id", "calendar_id", "project_id"),
    )
    image(
        "revision_category",
        uuid("cost_category_id"),
        text("code"),
        text("label"),
        uuid("cost_type_id"),
        text("cost_type_label"),
        sa.Column("cost_type_kind", sa.Text(), nullable=False),
        sa.Column("cost_type_is_active", sa.Boolean(), nullable=False),
        text("accounting_code"),
        sa.CheckConstraint(
            "cost_type_kind IN ('labor', 'non_labor', 'provision')", name="cost_type_kind_known"
        ),
        sa.UniqueConstraint("revision_id", "cost_category_id", "project_id"),
    )


def downgrade() -> None:
    """Drop the five tables, their partitions, guards and columns: their rows are lost."""
    op.execute(FORMER_PARTITIONS)
    for table in reversed(TABLES):
        op.drop_table(table)
        op.execute(f"DROP FUNCTION {table}_refuse_truncate()")
        op.execute(f"DROP FUNCTION {table}_refuse_marked_change()")
    op.drop_constraint("uq_subproject_id", "subproject", type_="unique")
    op.drop_column("revision", "win_probability")
    op.drop_column("revision", "inflation_rate")
