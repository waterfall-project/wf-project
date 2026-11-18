# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The amendments and the risks (§4.4.1; EP-08, "Tables et migrations").

``cost_structure`` admits the kinds ``amendment`` and ``risk``, and receives ``risk_id``, the risk
whose own estimate the structure is: there if and only if the kind is ``risk``, a key to the risk
with its project, one own estimate at most by risk and by revision (a partial unique index). The
uniqueness of the main structure is unchanged. What an evaluation names is unique: its own estimate
with its revision and its risk (``cost_structure``), its provision line with its revision
(``node``) — so that it names a structure of kind risk, of its risk, and a line of its revision.
``node.origin_risk_id`` (``0022``) receives its key to the risk, with an index of the nodes that
name one, what the key reads when a risk is deleted.
Added to the partitioned tables, the column, the checks, the keys and the indexes go to each
partition; the column is born null, every existing row a main structure.

``risk``, of the regime "project", not partitioned: the identity of a risk, its counter and its
audit. Three revised tables, partitioned by project as ``cost_structure``: ``risk_evaluation``, one
row by risk and by revision that bears it; ``risk_review``, one row by review, of the revision it
was made in; ``risk_reference_share``, one row by risk and by reference revision, the provision the
risk bears in it. ``create_project_partitions`` reads the revised tables in the catalogue since
``0026``: it is not replaced, and creates the partitions of the three for each new project, given
their functions ``<table>_refuse_truncate``. The partitions the projects that exist lack are created
here as it creates them — the table alone, then attached —, each with the trigger that refuses its
truncation; ``risk``, which their keys bind, enters the tables the function locks.

An evaluation and a review of a marked revision are never written, owner included: a guard of the
form of ``cost_structure``'s locks the revision of the row ``FOR KEY SHARE`` whatever its status,
then reads it, and refuses (#2104). A share is written once its revision is marked — a reference is
— and deleted when a designation is corrected: it has no such guard.

Every key refuses (``RESTRICT``). No row is to take up: no revision has a structure but its main
one, nor a risk. The service may read, insert, change and delete a risk and an evaluation; read,
insert and delete a review — the abandonment and the undoing take them away — and a share.
"""

from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The kinds of a structure before and after; the states of a risk (``RiskState``).
FORMER_KINDS = ("main",)
KINDS = ("main", "amendment", "risk")
STATES = ("identified", "occurred", "dismissed")
# The revised tables of the risks, the guarded first; the clause of their partitioning.
GUARDED = ("risk_evaluation", "risk_review")
REVISED = (*GUARDED, "risk_reference_share")
BY_PROJECT = "LIST (project_id)"
# What the service may do on each table the migration creates.
RIGHTS = {
    "risk": "SELECT, INSERT, UPDATE, DELETE",
    "risk_evaluation": "SELECT, INSERT, UPDATE, DELETE",
    "risk_review": "SELECT, INSERT, DELETE",
    "risk_reference_share": "SELECT, INSERT, DELETE",
}


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def grant(rights: str, table: str) -> str:
    """Give the grant of rights on a table to the role of the service of this database."""
    return f"""
DO $$
BEGIN
    EXECUTE format('GRANT {rights} ON {table} TO %I', current_database() || '_service');
END
$$
"""


# The guard of a marked revision on a revised table ``<table>``, of the form of ``0032``'s: the
# revision of the row locked whatever its status, then judged (#2104).
GUARD = """
CREATE FUNCTION <table>_refuse_marked_change() RETURNS trigger
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
CREATE TRIGGER <table>_refuse_marked_change BEFORE INSERT OR UPDATE OR DELETE
ON <table> FOR EACH ROW EXECUTE FUNCTION <table>_refuse_marked_change();
"""


# The refusal of the truncation of a revised table ``<table>``, which its partitions take up.
REFUSE_TRUNCATE = """
CREATE FUNCTION <table>_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'the rows of the risks of a revision are never truncated'
        USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER <table>_refuse_truncate BEFORE TRUNCATE ON <table>
FOR EACH STATEMENT EXECUTE FUNCTION <table>_refuse_truncate();
"""


# The partitions of a table ``<table>`` the projects that exist lack, as the function of ``0026``
# creates them: alone, then attached, with the trigger that refuses their truncation.
EXISTING = """
DO $$
DECLARE
    project uuid;
    partition text;
BEGIN
    FOR project IN SELECT id FROM public.project LOOP
        partition := '<table>_p_' || replace(project::text, '-', '');
        EXECUTE format(
            'CREATE TABLE public.%I (LIKE public.<table> INCLUDING DEFAULTS '
            'INCLUDING CONSTRAINTS INCLUDING STORAGE INCLUDING COMPRESSION)',
            partition
        );
        EXECUTE format(
            'ALTER TABLE public.<table> ATTACH PARTITION public.%I FOR VALUES IN (%L)',
            partition,
            project
        );
        EXECUTE format(
            'CREATE TRIGGER <table>_refuse_truncate BEFORE TRUNCATE ON public.%I '
            'FOR EACH STATEMENT EXECUTE FUNCTION public.<table>_refuse_truncate()',
            partition
        );
    END LOOP;
END
$$
"""


def created() -> list[sa.Column[Any]]:
    """Give the columns of the creation of a row: its instant and its author, an account or null."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
    ]


def stamped() -> list[sa.Column[Any]]:
    """Give the columns of audit of a row that changes: its creation, then its last change."""
    return [
        *created(),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    ]


def authors(*, changed: bool) -> list[sa.ForeignKeyConstraint]:
    """Give the keys of the authors of a row to the accounts, which refuse."""
    columns = ("created_by", "updated_by") if changed else ("created_by",)
    return [
        sa.ForeignKeyConstraint([column], ["user_account.id"], ondelete="RESTRICT")
        for column in columns
    ]


def of_revision_and_risk() -> list[sa.ForeignKeyConstraint]:
    """Give the keys of a revised row to its revision and to its risk, each with its project."""
    return [
        sa.ForeignKeyConstraint(
            ["project_id", "revision_id"],
            ["revision.project_id", "revision.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "risk_id"], ["risk.project_id", "risk.id"], ondelete="RESTRICT"
        ),
    ]


def probability() -> sa.CheckConstraint:
    """Bound a probability from 0 to 1, a ratio."""
    return sa.CheckConstraint("probability BETWEEN 0 AND 1", name="probability_ratio")


def _risk() -> None:
    op.create_table(
        "risk",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(collation="C"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mitigation_notes", sa.Text(), nullable=True),
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        *stamped(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="RESTRICT"),
        *authors(changed=True),
        sa.UniqueConstraint("project_id", "id"),
        sa.CheckConstraint("char_length(label) BETWEEN 1 AND 300", name="label_length"),
        sa.CheckConstraint("label ~ '\\S'", name="label_not_blank"),
        sa.CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
    )


def _structures() -> None:
    op.add_column("cost_structure", sa.Column("risk_id", sa.Uuid(), nullable=True))
    kind = op.f("ck_cost_structure_kind_known")
    op.drop_constraint(kind, "cost_structure", type_="check")
    op.create_check_constraint(kind, "cost_structure", _in("kind", KINDS))
    op.create_check_constraint(
        "risk_of_its_kind", "cost_structure", "(risk_id IS NOT NULL) = (kind = 'risk')"
    )
    op.create_foreign_key(
        None,
        "cost_structure",
        "risk",
        ["project_id", "risk_id"],
        ["project_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_cost_structure_risk",
        "cost_structure",
        ["project_id", "revision_id", "risk_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'risk'"),
    )
    op.create_unique_constraint(
        None, "cost_structure", ["risk_id", "id", "revision_id", "project_id"]
    )
    op.create_unique_constraint(None, "node", ["revision_id", "id", "project_id"])
    op.create_foreign_key(
        None,
        "node",
        "risk",
        ["project_id", "origin_risk_id"],
        ["project_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        None, "node", ["origin_risk_id"], postgresql_where=sa.text("origin_risk_id IS NOT NULL")
    )


def _evaluations() -> None:
    op.create_table(
        "risk_evaluation",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("risk_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("provision_node_id", sa.Uuid(), nullable=True),
        sa.Column("provision_cost_category_id", sa.Uuid(), nullable=False),
        sa.Column("provision_subproject_id", sa.Uuid(), nullable=True),
        sa.Column("provision_task_lineage_id", sa.Uuid(), nullable=True),
        sa.Column("occurrence_cost", sa.Numeric(14, 2), nullable=True),
        *stamped(),
        sa.PrimaryKeyConstraint("project_id", "risk_id", "revision_id"),
        sa.ForeignKeyConstraint(
            ["project_id", "structure_id", "revision_id", "risk_id"],
            [
                "cost_structure.project_id",
                "cost_structure.id",
                "cost_structure.revision_id",
                "cost_structure.risk_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "provision_node_id", "revision_id"],
            ["node.project_id", "node.id", "node.revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["provision_cost_category_id"], ["cost_category.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "provision_subproject_id"],
            ["subproject.project_id", "subproject.id"],
            ondelete="RESTRICT",
        ),
        *authors(changed=True),
        probability(),
        sa.CheckConstraint(_in("state", STATES), name="state_known"),
        sa.CheckConstraint(
            "(provision_node_id IS NOT NULL) = (state = 'identified')",
            name="provision_when_identified",
        ),
        sa.CheckConstraint(
            "(occurrence_cost IS NOT NULL) = (state = 'occurred')", name="cost_when_occurred"
        ),
        sa.CheckConstraint("occurrence_cost >= 0", name="occurrence_cost_not_negative"),
        sa.UniqueConstraint("structure_id", "project_id"),
        sa.UniqueConstraint("provision_node_id", "project_id"),
        postgresql_partition_by=BY_PROJECT,
    )
    for column in (
        "provision_cost_category_id",
        "provision_subproject_id",
        "risk_id",
        "revision_id",
    ):
        op.create_index(None, "risk_evaluation", [column])


def _reviews() -> None:
    op.create_table(
        "risk_review",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("risk_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_on", sa.Date(), nullable=False),
        sa.Column("probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("severity", sa.Numeric(14, 2), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        *created(),
        sa.PrimaryKeyConstraint("project_id", "id"),
        *of_revision_and_risk(),
        *authors(changed=False),
        probability(),
        sa.CheckConstraint("severity >= 0", name="severity_not_negative"),
        sa.CheckConstraint(_in("state", STATES), name="state_known"),
        postgresql_partition_by=BY_PROJECT,
    )
    for column in ("risk_id", "revision_id"):
        op.create_index(None, "risk_review", [column])


def _shares() -> None:
    op.create_table(
        "risk_reference_share",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("risk_id", sa.Uuid(), nullable=False),
        sa.Column("provision_amount", sa.Numeric(14, 2), nullable=False),
        *created(),
        sa.PrimaryKeyConstraint("project_id", "revision_id", "risk_id"),
        *of_revision_and_risk(),
        *authors(changed=False),
        sa.CheckConstraint("provision_amount >= 0", name="provision_amount_not_negative"),
        postgresql_partition_by=BY_PROJECT,
    )
    op.create_index(None, "risk_reference_share", ["risk_id"])


def upgrade() -> None:
    """Create the risk, widen the structures, create the three revised tables; grant them."""
    _risk()
    _structures()
    _evaluations()
    _reviews()
    _shares()
    for table in GUARDED:
        op.execute(GUARD.replace("<table>", table))
    for table in REVISED:
        op.execute(REFUSE_TRUNCATE.replace("<table>", table))
        op.execute(EXISTING.replace("<table>", table))
    for table, rights in RIGHTS.items():
        op.execute(grant(rights, table))


def downgrade() -> None:
    """Drop the tables of the risks and narrow the structures again: the risks are lost.

    Refused while a structure of another kind than the main one is left: its kind is no longer
    known.
    """
    for table in REVISED:
        op.drop_table(table)
        op.execute(f"DROP FUNCTION {table}_refuse_truncate()")
    for table in GUARDED:
        op.execute(f"DROP FUNCTION {table}_refuse_marked_change()")
    op.drop_constraint(op.f("uq_node_revision_id"), "node", type_="unique")
    op.drop_index(op.f("ix_node_origin_risk_id"), table_name="node")
    op.drop_constraint(op.f("fk_node_project_id_risk"), "node", type_="foreignkey")
    op.drop_constraint(op.f("uq_cost_structure_risk_id"), "cost_structure", type_="unique")
    op.drop_index("uq_cost_structure_risk", table_name="cost_structure")
    op.drop_constraint(op.f("fk_cost_structure_project_id_risk"), "cost_structure", "foreignkey")
    op.drop_constraint(op.f("ck_cost_structure_risk_of_its_kind"), "cost_structure", "check")
    kind = op.f("ck_cost_structure_kind_known")
    op.drop_constraint(kind, "cost_structure", type_="check")
    op.create_check_constraint(kind, "cost_structure", _in("kind", FORMER_KINDS))
    op.drop_column("cost_structure", "risk_id")
    op.drop_table("risk")
