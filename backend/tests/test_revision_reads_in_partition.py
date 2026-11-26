# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A revision is read in the partition of its project, on the schema.

``test_partitions`` holds it for ``cost_structure`` (EP-04, US-0910); here it is held for every
table the catalog says is revised, those the EPICs created since included, found in the catalog
rather than in a list: a revised table added later without its partition, or partitioned on
another key, fails the first two tests, naming it. The second explains, for each, the shape of a
reading of a revision (its project, and its revision when the table names one): it holds the schema
and that shape, not the statements of the code (issue #5076).

The duration of a reading at six hundred projects is not held here: it is measured on the set of
US-2950 (US-2970/L2).
"""

import re
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from project_rows import insert_revision, projects_with_partitions
from sqlalchemy import (
    ARRAY,
    String,
    bindparam,
    column,
    literal_column,
    select,
    table,
    text,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-DAT-0050-A")

# The tables that name a revision and hold no revised data, so no partition: the revision and the
# project, which hold the key itself; the history of a session, the plan of a paste kept an hour and
# the report of an import, which are working state, read by their own key (EP-06, EP-09). A table
# added later is partitioned, or named here with its reason.
NOT_PARTITIONED = frozenset({"revision", "project", "undo_entry", "paste_plan", "import_report"})

# The revised tables, partitioned by project: the catalog must give exactly these, so that a new one
# is named here, and a table that lost its partitioning is not unnoticed.
PARTITIONED_REVISED = frozenset(
    {
        "cost_structure",
        "estimate_line",
        "node",
        "revision_calendar",
        "revision_category",
        "revision_indicator",
        "revision_rate",
        "revision_role",
        "risk_evaluation",
        "risk_reference_share",
        "risk_review",
        "structure_reading",
        "task",
        "task_link",
        "task_link_conflict",
    }
)

# The name of a partition of a project: its table, then ``_p_`` and the project, in hexadecimal.
PARTITION_NAME = re.compile(r"(?P<parent>[a-z_]+)_p_[0-9a-f]{32}")

PARTITIONED = text(
    "SELECT parent.relname, attribute.attname, partitioned.partstrat, partitioned.partnatts "
    "FROM pg_partitioned_table AS partitioned "
    "JOIN pg_class AS parent ON parent.oid = partitioned.partrelid "
    "LEFT JOIN pg_attribute AS attribute ON attribute.attrelid = parent.oid "
    "AND attribute.attnum = partitioned.partattrs[0] "
    "WHERE parent.relnamespace = 'public'::regnamespace ORDER BY parent.relname"
)
# A table that carries a revision — by a column, or by a key to the revision or to a partitioned
# table — and is not itself a partition.
REVISED = text(
    "SELECT DISTINCT relation.relname FROM pg_class AS relation "
    "WHERE relation.relnamespace = 'public'::regnamespace AND relation.relkind IN ('r', 'p') "
    "AND NOT relation.relispartition AND ("
    "EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = relation.oid "
    "AND attname = 'revision_id' AND NOT attisdropped) "
    "OR EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = relation.oid AND contype = 'f' "
    "AND (confrelid = 'revision'::regclass "
    "OR confrelid IN (SELECT partrelid FROM pg_partitioned_table)))) ORDER BY 1"
)
# The tables, among those given, that carry a column of the revision: those a reading of a revision
# names it on, the others being read by their project alone. A table tied to the revision by a
# single foreign key, with no column ``revision_id`` of its own, is explained by its project alone
# (its key leads to the revision through a partitioned table): the catalog gives none today, and
# such a table would be read here by its project, not by a revision it does not hold.
WITH_REVISION_COLUMN = text(
    "SELECT attrelid::regclass::text FROM pg_attribute WHERE attname = 'revision_id' "
    "AND NOT attisdropped AND attrelid = ANY (SELECT oid FROM pg_class WHERE relname = ANY(:names) "
    "AND relnamespace = 'public'::regnamespace)"
).bindparams(bindparam("names", type_=ARRAY(String)))


def partitioned_by_project(connection: Connection) -> list[str]:
    """Name the partitioned tables, each by list on the identifier of the project alone."""
    found: dict[str, tuple[str | None, str, int]] = {
        name: (column, strategy, count)
        for name, column, strategy, count in connection.execute(PARTITIONED)
    }
    assert found, "no partitioned table: the catalog is not the one of the migrations"
    wrong = {name: kind for name, kind in found.items() if kind != ("project_id", "l", 1)}
    assert not wrong, f"partition each revised table by list on project_id alone, not {wrong}"
    return sorted(found)


def plan_tree(connection: Connection, statement: Any, **values: UUID) -> dict[str, Any]:
    """Give the root of the plan of a statement, with its parameters."""
    explained = connection.execute(text(f"EXPLAIN (FORMAT JSON) {statement}"), values).scalar_one()
    plan: dict[str, Any] = explained[0]["Plan"]
    return plan


def relations(plan: dict[str, Any]) -> set[str]:
    """Give the relations a plan reads, in its whole tree."""
    found: set[str] = {plan["Relation Name"]} if "Relation Name" in plan else set()
    for child in plan.get("Plans", []):
        found |= relations(child)
    return found


def test_every_table_a_revision_names_is_partitioned_by_project_or_is_the_revision(
    database: Database, owner: Engine
) -> None:
    # « Le plan d'exécution d'une lecture de révision ne parcourt que la partition du projet. »
    # The tables found by the catalog: a table that carries a revision and is no partition of
    # the project is a fault, whatever EPIC created it.
    del database
    with owner.connect() as connection:
        partitioned = set(partitioned_by_project(connection))
        revised = set(connection.scalars(REVISED))
        existing = set(
            connection.scalars(text("SELECT relname FROM pg_class WHERE relkind IN ('r', 'p')"))
        )
    assert revised - NOT_PARTITIONED <= partitioned, (
        f"partition by project the tables {sorted(revised - NOT_PARTITIONED - partitioned)}"
    )
    # An exemption of a table gone, or partitioned since, is stale and fails.
    assert existing >= NOT_PARTITIONED, f"drop the exemptions {sorted(NOT_PARTITIONED - existing)}"
    assert not NOT_PARTITIONED & partitioned, (
        f"drop the exemptions of the partitioned {sorted(NOT_PARTITIONED & partitioned)}"
    )
    assert PARTITIONED_REVISED <= revised, (
        f"the tables named here that the catalog no longer finds revised "
        f"{sorted(PARTITIONED_REVISED - revised)}"
    )
    assert partitioned == PARTITIONED_REVISED, (
        f"name the new {sorted(partitioned - PARTITIONED_REVISED)}, "
        f"drop the gone {sorted(PARTITIONED_REVISED - partitioned)}"
    )


def test_the_plan_of_a_reading_of_a_revised_table_reads_the_partition_of_its_project_alone(
    database: Database, owner: Engine
) -> None:
    # « Le plan d'exécution d'une lecture de révision ne parcourt que la partition du projet. »
    # For each partitioned table the catalog lists, three projects holding their partitions: the
    # plan of the reading of the first, by its project and by a revision it holds when the table
    # names one, reads the partition of the first and none of the others, and the partition is
    # there, which a table the function does not partition for the project is not. The test holds
    # the schema and the shape of a reading of a revision; the statements of the code are the
    # next test's.
    del database
    with projects_with_partitions(owner, 3) as projects, owner.begin() as connection:
        first = projects[0]
        revision = uuid4()
        connection.execute(insert_revision(first, id=revision))
        names = partitioned_by_project(connection)
        revised = set(connection.scalars(WITH_REVISION_COLUMN, {"names": names}))
        for name in names:
            reading = select(literal_column("*", String)).select_from(table(name))
            reading = reading.where(column("project_id") == bindparam("project"))
            values = {"project": first}
            if name in revised:
                reading = reading.where(column("revision_id") == bindparam("revision"))
                values["revision"] = revision
            plan = plan_tree(connection, str(reading), **values)
            assert relations(plan) == {f"{name}_p_{first.hex}"}, name
