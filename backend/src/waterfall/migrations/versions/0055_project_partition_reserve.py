# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve of sets of partitions, made by the worker, that a creation takes (US-2830/L4, #4801).

A creation of a project made its partitions itself (``create_project_partitions``, ``0026``), which
locks ``SHARE ROW EXCLUSIVE`` every table a key of a partition binds: a marking, or the application
of an import, that writes one of them held the creation until it committed, or refused it (#4735).
The worker now makes sets in advance, for identifiers of projects it draws itself, by that very
function and under its very locks, and inscribes each in ``project_partition_reserve``: the worker
waits for a marking, never a request. A creation takes a set with no DDL, in its own transaction:
it deletes a row of the reserve, skipping those another creation holds (``FOR UPDATE SKIP
LOCKED``), and the project receives its identifier. A set is taken only whole — a partition in
every table partitioned by the identifier of a project, read in the catalogue as the creation
reads them —: a table a later migration partitions, which would give its partitions to the
projects and forget the reserve, makes no project that lacks one, the creation then making its
own as before.

``project_partition_set_whole(set)`` says whether a set has its partition in every table
partitioned by the identifier of a project: the one criterion of the taking, of the filling and of
the count that schedules it.

``reserve_project_partitions(project, size)`` first makes whole the sets that are not (a table a
later migration partitioned, whose partition the sets lack): it makes the partitions they lack as
``create_project_partitions`` makes them, under its very locks, all taken at once without waiting,
again and again for ten seconds (``lock_not_available`` past them). It never detaches nor drops a
partition, which would ask ``ACCESS EXCLUSIVE`` of a parent: queued behind a marking, that demand
would hold every reading of the table, and a writer that locks the tables in another order would
deadlock with it. It makes then the set of ``project`` and inscribes it while the reserve holds
fewer than ``size`` sets, and says whether it did. It takes first the advisory lock of the
partitions (``4100010``, ``PARTITIONS_LOCK`` of ``core/revisions/interface/revisions.py``; a
migration does not import the application, a test compares the two), which
``create_project_partitions`` takes too, so that two fillings count one after the other; its
holder gives up after its own ten seconds. ``take_project_partitions()`` gives
the identifier of a set taken, or null when none is free. These two run as the owner of the tables
(``SECURITY DEFINER``), their search path their own; the role of the service may execute them and
read the reserve, nothing more.

``background_task.kind`` admits ``partition_reserve``, the filling, after the kinds of the
schedule. A set in reserve is no project: no row of ``project`` names it, and nothing that counts
or lists the projects sees it. The reserve is in ``public``: a backup takes it with the partitions
it names, and a restoration gives both back. The projects that exist are not touched.

The descent drops the partitions of the sets left in reserve, the table, the three functions and the
tasks of the filling, which the former constraint refuses.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "project_partition_reserve"
TASKS = "background_task"
KINDS_BEFORE = (
    "import_analysis",
    "import_apply",
    "revision_mark",
    "structure_merge",
    "risk_occurrence",
    "export",
    "backup",
    "restore",
    "identity_sync",
    "purge",
    "backup_copy",
    "restore_test",
)
FILLING = "partition_reserve"
KINDS = (*KINDS_BEFORE, FILLING)

# The tables partitioned by list on the identifier of a project, as ``create_project_partitions``
# reads them (0026).
PARENTS = """
    SELECT partitioned.partrelid
    FROM pg_partitioned_table AS partitioned
    JOIN pg_class AS parent ON parent.oid = partitioned.partrelid
    JOIN pg_attribute AS key
        ON key.attrelid = partitioned.partrelid AND key.attnum = partitioned.partattrs[0]
    WHERE parent.relnamespace = 'public'::regnamespace AND NOT parent.relispartition
        AND partitioned.partstrat = 'l' AND partitioned.partnatts = 1
        AND key.attname = 'project_id'
"""

FUNCTIONS = """
CREATE FUNCTION project_partition_set_whole(candidate uuid) RETURNS boolean
LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $$
    SELECT NOT EXISTS (
        SELECT FROM (<parents>) AS listed (partrelid)
        JOIN pg_class AS named ON named.oid = listed.partrelid
        WHERE NOT EXISTS (
            SELECT FROM pg_inherits JOIN pg_class AS partition ON partition.oid = inhrelid
            WHERE inhparent = listed.partrelid
                AND partition.relname = named.relname || '_p_' || replace(candidate::text, '-', '')
        )
    )
$$;
REVOKE ALL ON FUNCTION project_partition_set_whole(uuid) FROM PUBLIC;
CREATE FUNCTION reserve_project_partitions(project uuid, size integer) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    deadline timestamptz;
    parents oid[];
    related oid[];
    bound text;
    updated text;
    incomplete uuid;
    suffix text;
    revised text;
BEGIN
    IF size IS NULL OR size < 0 THEN
        RAISE EXCEPTION 'the size of the reserve is a number of sets, at least nought'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;
    -- PARTITIONS_LOCK (core/revisions/interface/revisions.py): the migration does not import the
    -- application, a test compares the two. Its holder is a creation or a filling, which gives up
    -- after its ten seconds of locks held: the wait is bounded by theirs.
    PERFORM pg_advisory_xact_lock(4100010);
    -- A set that is not whole is never taken: the partitions it lacks are made, as
    -- create_project_partitions makes them (0026) — the same locks, all taken at once without
    -- waiting, again and again for ten seconds, then alone and attached. No partition is detached
    -- nor dropped: no lock ACCESS EXCLUSIVE is asked of a table a request reads or writes.
    IF EXISTS (
        SELECT FROM public.project_partition_reserve
        WHERE NOT public.project_partition_set_whole(id)
    ) THEN
        deadline := clock_timestamp() + interval '10 seconds';
        SELECT array_agg(listed.partrelid) INTO parents FROM (<parents>) AS listed (partrelid);
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
        FOR incomplete IN
            SELECT id FROM public.project_partition_reserve
            WHERE NOT public.project_partition_set_whole(id) ORDER BY id
        LOOP
            suffix := '_p_' || replace(incomplete::text, '-', '');
            FOR revised IN
                SELECT named.relname FROM pg_class AS named
                WHERE named.oid = ANY (parents)
                    AND NOT EXISTS (
                        SELECT FROM pg_inherits
                        JOIN pg_class AS partition ON partition.oid = inhrelid
                        WHERE inhparent = named.oid
                            AND partition.relname = named.relname || suffix
                    )
                ORDER BY named.relname
            LOOP
                EXECUTE format(
                    'CREATE TABLE public.%I (LIKE public.%I INCLUDING DEFAULTS '
                    'INCLUDING CONSTRAINTS INCLUDING STORAGE INCLUDING COMPRESSION)',
                    revised || suffix,
                    revised
                );
                EXECUTE format(
                    'ALTER TABLE public.%I ATTACH PARTITION public.%I FOR VALUES IN (%L)',
                    revised,
                    revised || suffix,
                    incomplete
                );
                EXECUTE format(
                    'CREATE TRIGGER %I BEFORE TRUNCATE ON public.%I '
                    'FOR EACH STATEMENT EXECUTE FUNCTION public.%I()',
                    revised || '_refuse_truncate',
                    revised || suffix,
                    revised || '_refuse_truncate'
                );
            END LOOP;
        END LOOP;
    END IF;
    -- Every set of the reserve is now whole.
    IF (SELECT count(*) FROM public.project_partition_reserve) >= size THEN
        RETURN false;
    END IF;
    PERFORM public.create_project_partitions(project);
    INSERT INTO public.project_partition_reserve (id) VALUES (project);
    RETURN true;
END
$$;
REVOKE ALL ON FUNCTION reserve_project_partitions(uuid, integer) FROM PUBLIC;
CREATE FUNCTION take_project_partitions() RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    candidate uuid;
BEGIN
    -- One row read and locked, the first whole and free: a loop over the reserve would lock every
    -- row it fetched ahead, and another creation would find none free.
    SELECT reserved.id INTO candidate FROM public.project_partition_reserve AS reserved
    WHERE public.project_partition_set_whole(reserved.id)
    ORDER BY reserved.reserved_at, reserved.id
    LIMIT 1
    FOR UPDATE OF reserved SKIP LOCKED;
    IF candidate IS NOT NULL THEN
        DELETE FROM public.project_partition_reserve WHERE id = candidate;
    END IF;
    RETURN candidate;
END
$$;
REVOKE ALL ON FUNCTION take_project_partitions() FROM PUBLIC;
""".replace("<parents>", PARENTS)

GRANT = """
DO $$
DECLARE
    service text := current_database() || '_service';
BEGIN
    EXECUTE format('GRANT SELECT ON project_partition_reserve TO %I', service);
    EXECUTE format(
        'GRANT EXECUTE ON FUNCTION reserve_project_partitions(uuid, integer) TO %I', service
    );
    EXECUTE format('GRANT EXECUTE ON FUNCTION take_project_partitions() TO %I', service);
    EXECUTE format('GRANT EXECUTE ON FUNCTION project_partition_set_whole(uuid) TO %I', service);
END
$$
"""

# The partitions of the sets left in reserve, which no project names, empty: each detached first —
# a partition a key names is dropped only once detached —, then dropped.
RESERVED_PARTITIONS = """
DO $$
DECLARE
    parent_name text;
    partition_name text;
BEGIN
    FOR parent_name, partition_name IN
        SELECT parent.relname, partition.relname
        FROM public.project_partition_reserve AS reserved
        JOIN pg_inherits ON true
        JOIN pg_class AS parent ON parent.oid = inhparent
        JOIN pg_class AS partition ON partition.oid = inhrelid
            AND partition.relname = parent.relname || '_p_' || replace(reserved.id::text, '-', '')
        WHERE parent.relnamespace = 'public'::regnamespace AND NOT parent.relispartition
        ORDER BY partition.relname
    LOOP
        EXECUTE format(
            'ALTER TABLE public.%I DETACH PARTITION public.%I', parent_name, partition_name
        );
        EXECUTE format('DROP TABLE public.%I', partition_name);
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Create the reserve, its two functions and their rights; admit the task of the filling."""
    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "reserved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(FUNCTIONS)
    op.execute(GRANT)
    _replace_kinds(KINDS)


def downgrade() -> None:
    """Drop the partitions of the sets in reserve, the reserve, its functions and its tasks."""
    kind = sa.column("kind", sa.Text())
    op.execute(sa.table(TASKS, kind).delete().where(kind == FILLING))
    _replace_kinds(KINDS_BEFORE)
    op.execute(RESERVED_PARTITIONS)
    op.execute("DROP FUNCTION take_project_partitions()")
    op.execute("DROP FUNCTION reserve_project_partitions(uuid, integer)")
    op.execute("DROP FUNCTION project_partition_set_whole(uuid)")
    op.drop_table(TABLE)


def _replace_kinds(kinds: tuple[str, ...]) -> None:
    constraint = op.f(f"ck_{TASKS}_kind_known")
    op.drop_constraint(constraint, TASKS, type_="check")
    listed = ", ".join(repr(each) for each in kinds)
    op.create_check_constraint(constraint, TASKS, f"kind IN ({listed})")
