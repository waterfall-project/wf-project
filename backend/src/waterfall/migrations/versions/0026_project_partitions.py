# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The partitions of a project created without waiting while a lock is held (#2603, #2667).

``create_project_partitions`` is replaced (``CREATE OR REPLACE``, its owner and its grants kept);
no row and no right changes. The function of ``0025`` created each partition by ``CREATE TABLE …
PARTITION OF``, which locks the parent ``ACCESS EXCLUSIVE``, nine parents one after the other, and
took besides, to clone the keys, ``SHARE ROW EXCLUSIVE`` on every table they bind, in both
directions: a reading or a write that held one of these tables and asked for another deadlocked
with the creation that held the other (EP-07, "Décisions de l'utilisateur du 2026-11-09").

This one takes first the advisory lock of the transaction ``4100010`` (``PARTITIONS_LOCK`` of the
revisions), which puts the creations one after the other. It reads then in the catalogue the tables
partitioned by list on ``project_id`` and the tables their keys bind, both ways, and takes all their
locks at once without waiting — ``SHARE ROW EXCLUSIVE`` on the tables bound, ``SHARE UPDATE
EXCLUSIVE`` on the other parents —, each table alone (``ONLY``), without the partitions of every
project. The attachment locks besides the partitions of a partitioned table a key names (``node``,
``cost_structure``), but a writer locks the parent before its partition, and the parent held keeps
it out: the creation waits for none of them, unless a DDL of the owner holds one. A lock missing
undoes the block that took the others, and the attempt is made again after a short pause, at
random, for about ten seconds; past them ``lock_not_available`` is raised, a 500 the service logs.
Each partition is then created alone (``CREATE TABLE … (LIKE <parent> …)``) and attached
(``ATTACH PARTITION``), which takes no more than ``SHARE UPDATE EXCLUSIVE`` on its parent: readings
and writes go on. The partition has the trigger that refuses its truncation, as before; what the
attachment gives it — its constraints, indexes, row triggers and keys — is what ``PARTITION OF``
gave, but for the names the server numbers.

The tables are read at each call: a revised table, or a key, that a later epic adds enters the
creation and the locks by itself, and no later migration replaces the function again. The descent
puts back the function of ``0025``.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The function that creates the partitions of a project in every table partitioned by its
# identifier, without ever waiting for a lock while it holds one.
PARTITIONS = """
CREATE OR REPLACE FUNCTION create_project_partitions(project uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    suffix text := '_p_' || replace(project::text, '-', '');
    deadline timestamptz := clock_timestamp() + interval '10 seconds';
    parents oid[];
    related oid[];
    bound text;
    updated text;
    revised text;
BEGIN
    IF project IS NULL THEN
        RAISE EXCEPTION 'the partitions of a project need its identifier'
            USING ERRCODE = 'null_value_not_allowed';
    END IF;
    PERFORM pg_advisory_xact_lock(4100010);
    SELECT array_agg(partitioned.partrelid) INTO parents
    FROM pg_partitioned_table AS partitioned
    JOIN pg_class AS parent ON parent.oid = partitioned.partrelid
    JOIN pg_attribute AS key
        ON key.attrelid = partitioned.partrelid AND key.attnum = partitioned.partattrs[0]
    WHERE parent.relnamespace = 'public'::regnamespace AND NOT parent.relispartition
        AND partitioned.partstrat = 'l' AND partitioned.partnatts = 1
        AND key.attname = 'project_id';
    IF EXISTS (
        SELECT FROM pg_class AS parent JOIN pg_class AS partition
            ON partition.relname = parent.relname || suffix
            AND partition.relnamespace = parent.relnamespace
        WHERE parent.oid = ANY (parents)
    ) THEN
        RAISE EXCEPTION 'the project % has its partitions already', project
            USING ERRCODE = 'duplicate_table';
    END IF;
    SELECT array_agg(other) INTO related
    FROM (
        SELECT confrelid FROM pg_constraint
        WHERE contype = 'f' AND conparentid = 0 AND conrelid = ANY (parents)
        UNION
        SELECT conrelid FROM pg_constraint
        WHERE contype = 'f' AND conparentid = 0 AND confrelid = ANY (parents)
    ) AS keyed (other);
    SELECT string_agg('ONLY ' || other::regclass::text, ', ' ORDER BY other) INTO bound
    FROM unnest(related) AS other;
    SELECT string_agg('ONLY ' || parent::regclass::text, ', ' ORDER BY parent) INTO updated
    FROM unnest(parents) AS parent
    WHERE parent <> ALL (coalesce(related, '{}'));
    LOOP
        BEGIN
            IF bound IS NOT NULL THEN
                EXECUTE 'LOCK TABLE ' || bound || ' IN SHARE ROW EXCLUSIVE MODE NOWAIT';
            END IF;
            IF updated IS NOT NULL THEN
                EXECUTE 'LOCK TABLE ' || updated || ' IN SHARE UPDATE EXCLUSIVE MODE NOWAIT';
            END IF;
            EXIT;
        EXCEPTION WHEN lock_not_available THEN
            IF clock_timestamp() >= deadline THEN
                RAISE;
            END IF;
        END;
        PERFORM pg_sleep(0.01 + random() * 0.04);
    END LOOP;
    FOR revised IN SELECT relname FROM pg_class WHERE oid = ANY (parents) ORDER BY relname LOOP
        EXECUTE format(
            'CREATE TABLE public.%I (LIKE public.%I INCLUDING DEFAULTS INCLUDING CONSTRAINTS '
            'INCLUDING STORAGE INCLUDING COMPRESSION)',
            revised || suffix,
            revised
        );
        EXECUTE format(
            'ALTER TABLE public.%I ATTACH PARTITION public.%I FOR VALUES IN (%L)',
            revised,
            revised || suffix,
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

# The function of 0025, which the descent puts back: each partition by ``PARTITION OF``, in the nine
# revised tables it names.
FORMER_REVISED = (
    "cost_structure",
    "node",
    "task",
    "task_link",
    "estimate_line",
    "revision_rate",
    "revision_role",
    "revision_calendar",
    "revision_category",
)
FORMER_PARTITIONS = """
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
""".replace("<tables>", ", ".join(f"'{table}'" for table in FORMER_REVISED))


def upgrade() -> None:
    """Replace the function by the one that never waits for a lock while it holds one."""
    op.execute(PARTITIONS)


def downgrade() -> None:
    """Put back the function of 0025, which creates each partition by ``PARTITION OF``."""
    op.execute(FORMER_PARTITIONS)
