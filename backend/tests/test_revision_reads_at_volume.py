# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A revision is read in the partition of its project, at one project or six hundred (US-2970/L1).

``test_partitions`` holds it for ``cost_structure`` (EP-04, US-0910); here it is held for every
table the catalog says is revised, those the EPICs created since included, found in the catalog
rather than in a list: a revised table added later without its partition, or partitioned on
another key, fails the first two tests, naming it.

The duration of a reading is not read on a clock, which a loaded runner moves by more than the
effect looked for. A reading's work is the pages it touches (``EXPLAIN (ANALYZE, BUFFERS)``: hits
and reads together, whatever the cache holds), which depend on the partition it reads alone: the
same reading of the same project touches the same pages on a platform of one project and on one of
six hundred, or it reads what it should not. The six hundred projects are written around the
service, by the owner, as ``test_partitions`` writes its own: the full set of ``load-reference
--projects 600`` takes some ten minutes, beyond the delay of a test (``pyproject.toml``).
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from planning_support import node_row
from project_rows import (
    insert_project,
    insert_revision,
    insert_structure,
    projects_with_partitions,
)
from sqlalchemy import String, bindparam, column, func, insert, literal_column, select, table, text

from waterfall.core.planning.tables import Node
from waterfall.migrations.runner import upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-DAT-0050-A")

PROJECTS = 600
# The nodes of the revision of each project: what the pages of a reading are counted on.
NODES = 100
# The tables that name a revision and hold no revised data, so no partition: the revision and the
# project, which hold the key itself; the history of a session, the plan of a paste kept an hour and
# the report of an import, which are working state, read by their own key (EP-06, EP-09). A table
# added later is partitioned, or named here with its reason.
NOT_PARTITIONED = frozenset({"revision", "project", "undo_entry", "paste_plan", "import_report"})

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
    "AND confrelid = 'revision'::regclass)) ORDER BY 1"
)


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
    """Give the root of the plan of a statement, executed, with the pages it touched."""
    explained = connection.execute(
        text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}"), values
    ).scalar_one()
    plan: dict[str, Any] = explained[0]["Plan"]
    return plan


def relations(plan: dict[str, Any]) -> set[str]:
    """Give the relations a plan reads, in its whole tree."""
    found: set[str] = {plan["Relation Name"]} if "Relation Name" in plan else set()
    for child in plan.get("Plans", []):
        found |= relations(child)
    return found


def pages(plan: dict[str, Any]) -> int:
    """Give the pages a plan touched, those the cache held and those it read."""
    return int(plan["Shared Hit Blocks"]) + int(plan["Shared Read Blocks"])


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
    assert revised - NOT_PARTITIONED <= partitioned, (
        f"partition by project the tables {sorted(revised - NOT_PARTITIONED - partitioned)}"
    )
    assert "cost_structure" in partitioned
    assert len(partitioned) >= 15


def test_the_plan_of_a_reading_of_a_revised_table_reads_the_partition_of_its_project_alone(
    database: Database, owner: Engine
) -> None:
    # « Le plan d'exécution d'une lecture de révision ne parcourt que la partition du projet. »
    # For each partitioned table the catalog lists, three projects holding their partitions: the
    # plan of the reading of the first reads the partition of the first and none of the others, and
    # the partition is there, which a table the function does not partition for the project is
    # not.
    del database
    with projects_with_partitions(owner, 3) as projects, owner.connect() as connection:
        first = projects[0]
        for name in partitioned_by_project(connection):
            reading = str(
                select(literal_column("*", String))
                .select_from(table(name))
                .where(column("project_id") == bindparam("project"))
            )
            plan = plan_tree(connection, reading, project=first)
            assert relations(plan) == {f"{name}_p_{first.hex}"}, name


def written(connection: Connection, project_id: UUID) -> UUID:
    """Write a revision of a project, its structure and its nodes, and give the revision."""
    revision = uuid4()
    connection.execute(insert_revision(project_id, id=revision))
    structure = uuid4()
    connection.execute(insert_structure(project_id, revision, id=structure))
    connection.execute(
        insert(Node),
        [
            node_row(project_id, revision, structure, rank=rank, lineage_id=uuid4())
            for rank in range(1, NODES + 1)
        ],
    )
    return revision


@pytest.mark.timeout(1800)
def test_the_reading_of_a_revision_touches_as_many_pages_at_six_hundred_projects_as_at_one(
    empty_engine: Engine,
) -> None:
    # « La durée de lecture d'une révision est la même sur une plateforme d'un projet et sur une
    # plateforme de six cents projets. » The same reading of the same revision, on a platform of
    # that project alone and on one of six hundred: the nodes of the revision, which the nodes of
    # the others must not make longer to read, are read in the same pages, and the plan reads the
    # partition of the project alone. On a database of its own, dropped whole: the partitions of
    # six hundred projects take minutes to drop one by one, more than the test takes to write.
    owner = empty_engine
    upgrade(owner)
    project_id = uuid4()
    reading = str(
        select(Node.id).where(
            Node.project_id == bindparam("project"), Node.revision_id == bindparam("revision")
        )
    )
    with owner.begin() as connection:
        connection.execute(insert_project(id=project_id))
        connection.execute(select(func.create_project_partitions(project_id)))
        revision = written(connection, project_id)
    with owner.connect() as connection:
        connection.execute(text("ANALYZE node"))
        alone = plan_tree(connection, reading, project=project_id, revision=revision)
    for _ in range(PROJECTS - 1):
        with owner.begin() as connection:
            other = uuid4()
            connection.execute(insert_project(id=other))
            connection.execute(select(func.create_project_partitions(other)))
            written(connection, other)
    with owner.connect() as connection:
        connection.execute(text("ANALYZE node"))
        crowded = plan_tree(connection, reading, project=project_id, revision=revision)
        count = connection.scalar(text("SELECT count(*) FROM project"))
    assert count == PROJECTS
    assert alone["Actual Rows"] == crowded["Actual Rows"] == NODES
    assert relations(alone) == {f"node_p_{project_id.hex}"}
    assert relations(crowded) == relations(alone)
    assert pages(alone) > 0
    assert pages(crowded) == pages(alone)
