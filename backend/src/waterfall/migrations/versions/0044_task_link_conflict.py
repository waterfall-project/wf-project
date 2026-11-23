# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in manual mode a link in conflict cannot satisfy (EP-32, "Tables et migrations").

Regime "revised", partitioned by project as ``task_link`` (WF-DAT-0050): ``task_link_conflict``, one
row by link in conflict and by task in manual mode it cannot satisfy — its successor, or a
subordinate in manual mode of a summary successor (#3984, US-3300) —, keyed by the project, the link
and the task. A row names its revision and its structure together, by the key towards the structure
that names its revision too, as every revised row of the planning does (``0022``); its link by its
key, and its task by a key that names its structure too. Every key cascades: the row follows the
deletion of its link, of its task or of its structure inside a current revision (§4.4.1), and goes
with them at the abandonment of its revision (WF-DAT-0010). ``task_link.in_conflict`` stays, the
engine writing both together.

``create_project_partitions`` reads the revised tables in the catalogue since ``0026``: it is not
replaced, and creates the partition of the table for each new project, given the function
``task_link_conflict_refuse_truncate``. The partitions the projects that exist lack are created here
as it creates them — the table alone, then attached —, each with the trigger that refuses its
truncation.

The table is filled before its guard is created, marked revisions included: for each link in
conflict whose successor is a task in manual mode without a subtask, that successor, which is what
the engine could say until now. No engine is replayed — a migration of the schema does not call the
core —: the conflicts of a link toward a summary are born at the first replay of its structure,
and a marked revision keeps those it froze (WF-REF-0130). Then the guard, of the form of
``task_link``'s, refuses any write of a row of a marked revision, owner included: it locks the
revision of the row ``FOR KEY SHARE`` whatever its status, then reads it (#2104). The service may
read, insert, change and delete a row, as a link. The descent drops the table, its partitions and
its functions: the links keep ``in_conflict``.
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

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON task_link_conflict TO %I',
        current_database() || '_service'
    );
END
$$
"""

# The refusal of the truncation, which the partitions of every project receive.
REFUSE_TRUNCATE = """
CREATE FUNCTION task_link_conflict_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'the task_link_conflict is never truncated'
        USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER task_link_conflict_refuse_truncate BEFORE TRUNCATE ON task_link_conflict
FOR EACH STATEMENT EXECUTE FUNCTION task_link_conflict_refuse_truncate();
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
        partition := 'task_link_conflict_p_' || replace(project::text, '-', '');
        EXECUTE format(
            'CREATE TABLE public.%I (LIKE public.task_link_conflict INCLUDING DEFAULTS '
            'INCLUDING CONSTRAINTS INCLUDING STORAGE INCLUDING COMPRESSION)',
            partition
        );
        EXECUTE format(
            'ALTER TABLE public.task_link_conflict ATTACH PARTITION public.%I FOR VALUES IN (%L)',
            partition,
            project
        );
        EXECUTE format(
            'CREATE TRIGGER task_link_conflict_refuse_truncate BEFORE TRUNCATE ON public.%I '
            'FOR EACH STATEMENT EXECUTE FUNCTION public.task_link_conflict_refuse_truncate()',
            partition
        );
    END LOOP;
END
$$
"""

# What the engine could say of a link in conflict until now: its successor, a task in manual mode
# without a subtask. Marked revisions included, before the guard exists.
FILL = """
INSERT INTO task_link_conflict (project_id, link_id, node_id, revision_id, structure_id)
SELECT link.project_id, link.id, link.successor_id, link.revision_id, link.structure_id
FROM task_link AS link
JOIN task ON task.project_id = link.project_id AND task.node_id = link.successor_id
WHERE link.in_conflict AND task.scheduling_mode = 'manual'
    AND NOT EXISTS (
        SELECT FROM node AS child
        WHERE child.project_id = link.project_id AND child.parent_id = link.successor_id
            AND child.kind = 'task'
    )
"""

# The guard of a marked revision, of the form of ``task_link``'s (migration 0022): the revision of
# the row locked whatever its status, then judged (#2104).
GUARD = """
CREATE FUNCTION task_link_conflict_refuse_marked_change() RETURNS trigger
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
CREATE TRIGGER task_link_conflict_refuse_marked_change BEFORE INSERT OR UPDATE OR DELETE
ON task_link_conflict FOR EACH ROW EXECUTE FUNCTION task_link_conflict_refuse_marked_change();
"""


def upgrade() -> None:
    """Create the table and the partitions of the projects, fill it, then guard it; grant it."""
    op.create_table(
        "task_link_conflict",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("link_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "link_id", "node_id"),
        sa.ForeignKeyConstraint(
            ["project_id", "structure_id", "revision_id"],
            ["cost_structure.project_id", "cost_structure.id", "cost_structure.revision_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "link_id"], ["task_link.project_id", "task_link.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["node_id", "project_id", "structure_id"],
            ["node.id", "node.project_id", "node.structure_id"],
            ondelete="CASCADE",
        ),
        postgresql_partition_by="LIST (project_id)",
    )
    op.create_index(None, "task_link_conflict", ["node_id"])
    op.execute(REFUSE_TRUNCATE)
    op.execute(EXISTING)
    op.execute(FILL)
    op.execute(GUARD)
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table, its partitions and its functions: the links keep ``in_conflict``."""
    op.drop_table("task_link_conflict")
    op.execute("DROP FUNCTION task_link_conflict_refuse_marked_change()")
    op.execute("DROP FUNCTION task_link_conflict_refuse_truncate()")
