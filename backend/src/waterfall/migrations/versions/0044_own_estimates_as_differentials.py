# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own estimate of a risk prepared as a differential (EP-30, "Tables et migrations").

``cost_structure``: the counter of the main structure a differential keeps (``main_lock_version``,
``0038``) is kept by the own estimate of a risk too — there if and only if the kind is ``amendment``
or ``risk`` —; and ``pruned_revision_id`` names, for an own estimate pruned by a marking, the marked
revision against whose main structure its differences are exact: there for that kind alone, a key
to the revision with its project. The base of an own estimate names it as the base of a
differential names its differential: the key of ``0038`` holds for both.

``own_estimate_abandonment``, revised, partitioned by project as ``cost_structure``: what an own
estimate pruned abandons, a node by its lineage or a link by the lineages of its two tasks, of its
structure with its revision. ``create_project_partitions`` creates its partition for each new
project, given its function ``own_estimate_abandonment_refuse_truncate``; the partitions the
projects that exist lack are created here as it creates them. A row of a marked revision is never
written, owner included: a guard of the form of ``0035``'s. The service may read, insert and delete
it.

``risk_evaluation``: the severity recorded (``severity``), signed, null until it is written; the
cost at occurrence becomes signed; ``occurrence_frozen_cost`` and ``occurrence_earned_value``, what
an occurrence froze, signed, null out of the state occurred. ``risk_review``: the severity retained
becomes signed.

No data is taken up: no base the service keeps holds an own estimate of EP-08 (the decision of the
author of 2026-11-21). The migration refuses to apply, saying it, while a structure of the kind
``risk`` exists: the databases of development are made again, the witness loaded again. The descent
refuses likewise, and loses the abandonments, the severities and the figures of the occurrences.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STRUCTURES = "cost_structure"
ABANDONMENTS = "own_estimate_abandonment"
EVALUATIONS = "risk_evaluation"
REVIEWS = "risk_review"
AMOUNT = sa.Numeric(14, 2)
# The kinds that keep the counter of the main structure, before and after.
FORMER_COUNTED = "kind = 'amendment'"
COUNTED = "kind IN ('amendment', 'risk')"

# The refusal of the ascent over an own estimate of EP-08, which no data of this migration takes up.
REFUSE_ASCENT = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.cost_structure WHERE kind = 'risk') THEN
        RAISE EXCEPTION 'an own estimate of a risk exists: no base that holds one is migrated, '
            'make the database again (EP-30)'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;
END
$$
"""
# The refusal of the descent over an own estimate of EP-30, which the tables of 0043 cannot hold.
REFUSE_DESCENT = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.cost_structure WHERE kind = 'risk') THEN
        RAISE EXCEPTION 'an own estimate of a risk exists: no base that holds one is taken back '
            'to 0043, make the database again (EP-30)'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;
END
$$
"""

# The guard of a marked revision on the abandonments, of the form of ``0035``'s (#2104).
GUARD = """
CREATE FUNCTION own_estimate_abandonment_refuse_marked_change() RETURNS trigger
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
CREATE TRIGGER own_estimate_abandonment_refuse_marked_change BEFORE INSERT OR UPDATE OR DELETE
ON own_estimate_abandonment FOR EACH ROW
EXECUTE FUNCTION own_estimate_abandonment_refuse_marked_change();
"""

# The refusal of the truncation of the abandonments, which their partitions take up.
REFUSE_TRUNCATE = """
CREATE FUNCTION own_estimate_abandonment_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'the abandonments of the own estimates of a revision are never truncated'
        USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER own_estimate_abandonment_refuse_truncate BEFORE TRUNCATE
ON own_estimate_abandonment
FOR EACH STATEMENT EXECUTE FUNCTION own_estimate_abandonment_refuse_truncate();
"""

# The partitions the projects that exist lack, as the function of ``0026`` creates them.
EXISTING = """
DO $$
DECLARE
    project uuid;
    partition text;
BEGIN
    FOR project IN SELECT id FROM public.project LOOP
        partition := 'own_estimate_abandonment_p_' || replace(project::text, '-', '');
        EXECUTE format(
            'CREATE TABLE public.%I (LIKE public.own_estimate_abandonment INCLUDING DEFAULTS '
            'INCLUDING CONSTRAINTS INCLUDING STORAGE INCLUDING COMPRESSION)',
            partition
        );
        EXECUTE format(
            'ALTER TABLE public.own_estimate_abandonment ATTACH PARTITION public.%I '
            'FOR VALUES IN (%L)',
            partition,
            project
        );
        EXECUTE format(
            'CREATE TRIGGER own_estimate_abandonment_refuse_truncate BEFORE TRUNCATE '
            'ON public.%I FOR EACH STATEMENT '
            'EXECUTE FUNCTION public.own_estimate_abandonment_refuse_truncate()',
            partition
        );
    END LOOP;
END
$$
"""

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT, DELETE ON own_estimate_abandonment TO %I',
        current_database() || '_service'
    );
END
$$
"""


def _counted(clause: str) -> None:
    constraint = op.f(f"ck_{STRUCTURES}_main_counter_of_its_kind")
    op.drop_constraint(constraint, STRUCTURES, type_="check")
    op.create_check_constraint(
        constraint, STRUCTURES, f"(main_lock_version IS NOT NULL) = ({clause})"
    )


def _structures() -> None:
    _counted(COUNTED)
    op.add_column(STRUCTURES, sa.Column("pruned_revision_id", sa.Uuid(), nullable=True))
    op.create_check_constraint(
        "pruned_of_its_kind", STRUCTURES, "pruned_revision_id IS NULL OR kind = 'risk'"
    )
    op.create_foreign_key(
        None,
        STRUCTURES,
        "revision",
        ["pruned_revision_id", "project_id"],
        ["id", "project_id"],
        ondelete="RESTRICT",
    )


def _abandonments() -> None:
    op.create_table(
        ABANDONMENTS,
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("node_lineage_id", sa.Uuid(), nullable=True),
        sa.Column("predecessor_lineage_id", sa.Uuid(), nullable=True),
        sa.Column("successor_lineage_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("project_id", "id"),
        sa.ForeignKeyConstraint(
            ["project_id", "structure_id", "revision_id"],
            [f"{STRUCTURES}.project_id", f"{STRUCTURES}.id", f"{STRUCTURES}.revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(node_lineage_id IS NULL) = (predecessor_lineage_id IS NOT NULL) "
            "AND (predecessor_lineage_id IS NULL) = (successor_lineage_id IS NULL)",
            name="node_or_link",
        ),
        sa.UniqueConstraint("node_lineage_id", "structure_id", "project_id"),
        sa.UniqueConstraint(
            "predecessor_lineage_id", "successor_lineage_id", "structure_id", "project_id"
        ),
        postgresql_partition_by="LIST (project_id)",
    )
    op.create_index(None, ABANDONMENTS, ["revision_id"])
    op.execute(GUARD)
    op.execute(REFUSE_TRUNCATE)
    op.execute(EXISTING)
    op.execute(GRANT)


def _risks() -> None:
    for column in ("severity", "occurrence_frozen_cost", "occurrence_earned_value"):
        op.add_column(EVALUATIONS, sa.Column(column, AMOUNT, nullable=True))
    op.drop_constraint(
        op.f(f"ck_{EVALUATIONS}_occurrence_cost_not_negative"), EVALUATIONS, type_="check"
    )
    op.create_check_constraint(
        "frozen_cost_when_occurred",
        EVALUATIONS,
        "state = 'occurred' OR occurrence_frozen_cost IS NULL",
    )
    op.create_check_constraint(
        "earned_value_when_occurred",
        EVALUATIONS,
        "state = 'occurred' OR occurrence_earned_value IS NULL",
    )
    op.drop_constraint(op.f(f"ck_{REVIEWS}_severity_not_negative"), REVIEWS, type_="check")


def upgrade() -> None:
    """Prepare the own estimates as differentials; refused while one of EP-08 exists."""
    op.execute(REFUSE_ASCENT)
    _structures()
    _abandonments()
    _risks()


def downgrade() -> None:
    """Put back the own estimates of EP-08; refused while an own estimate exists.

    The abandonments, the severities recorded and the figures of the occurrences are lost.
    """
    op.execute(REFUSE_DESCENT)
    op.create_check_constraint("severity_not_negative", REVIEWS, "severity >= 0")
    op.drop_constraint(op.f(f"ck_{EVALUATIONS}_earned_value_when_occurred"), EVALUATIONS, "check")
    op.drop_constraint(op.f(f"ck_{EVALUATIONS}_frozen_cost_when_occurred"), EVALUATIONS, "check")
    op.create_check_constraint("occurrence_cost_not_negative", EVALUATIONS, "occurrence_cost >= 0")
    for column in ("occurrence_earned_value", "occurrence_frozen_cost", "severity"):
        op.drop_column(EVALUATIONS, column)
    op.drop_table(ABANDONMENTS)
    op.execute("DROP FUNCTION own_estimate_abandonment_refuse_truncate()")
    op.execute("DROP FUNCTION own_estimate_abandonment_refuse_marked_change()")
    op.drop_constraint(
        op.f(f"fk_{STRUCTURES}_pruned_revision_id_revision"), STRUCTURES, type_="foreignkey"
    )
    op.drop_constraint(op.f(f"ck_{STRUCTURES}_pruned_of_its_kind"), STRUCTURES, type_="check")
    op.drop_column(STRUCTURES, "pruned_revision_id")
    _counted(FORMER_COUNTED)
