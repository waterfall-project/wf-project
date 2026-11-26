# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A revision is read in the partition of its project, on the schema and on the real readings.

``test_partitions`` holds it for ``cost_structure`` (EP-04, US-0910); here it is held for every
table the catalog says is revised, those the EPICs created since included, found in the catalog
rather than in a list: a revised table added later without its partition, or partitioned on
another key, fails the first two tests, naming it. The second explains, for each, the shape of a
reading of a revision (its project, and its revision when the table names one): it holds the schema
and that shape.

The third holds the statements of the code (issue #5076): the functions of the core that serve the
operations that read a revision are played on a platform of three projects, each with its data, and
the statements they send to a table of a revision are explained, with their parameters; a plan that
reads more than one partition of a table — a reading that filters on the revision without its
project, say — fails and names the statement and the partitions.
"""

import re
from contextlib import contextmanager
from dataclasses import replace
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from nodes_support import Tree, mark, opened
from project_rows import insert_revision, projects_with_partitions
from projects_support import MANAGING, Scene, create
from projects_support import scene as make_scene
from sqlalchemy import (
    ARRAY,
    String,
    bindparam,
    column,
    event,
    literal_column,
    select,
    table,
    text,
)
from test_comparison import follow

from waterfall.api.nodes import node_body
from waterfall.core.estimate.interface import (
    ComparisonAsked,
    compare_revisions,
    kept_reference,
    rate_update_proposal,
)
from waterfall.core.planning.interface import NodeFilters, Place
from waterfall.core.planning.reading import list_records, read_structure
from waterfall.core.projects.interface import Viewer
from waterfall.core.revisions.interface import list_cost_structures, read_revision

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection
    from sqlalchemy.orm import Session
    from support import ContractClient

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
    assert revised >= PARTITIONED_REVISED, (
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


def days(count: str) -> dict[str, Any]:
    """Give the facet of a task of so many days."""
    return {"duration": {"value": count, "unit": "d"}}


def with_data(api: ContractClient, stage: Scene) -> tuple[UUID, UUID, UUID]:
    """Give a project data in each table a reading of its revisions reads, and two revisions.

    An offer of tasks, one following another, marked: it keeps the images and the rates of the
    reference; then an amendment, the current revision, which a comparison reads against it.
    Give the offer, the amendment and the main structure of the offer.
    """
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    studies = tree.made("Études")
    design = tree.made("Conception", parent_id=studies["node_id"], task=days("2"))
    follow(tree, tree.made("Plans", parent_id=studies["node_id"], task=days("1")), design)
    tree.made("Recette", task=days("1"))
    mark(stage, offer, "v1.0")
    amendment = opened(api, stage)
    return UUID(offer["revision_id"]), UUID(amendment["revision_id"]), UUID(tree.structure_id)


@contextmanager
def statements_of(engine: Engine) -> Generator[list[tuple[str, Any]]]:
    """Collect the statements an engine sends, with their parameters, as the driver takes them."""
    sent: list[tuple[str, Any]] = []

    def collect(*heard: Any) -> None:
        # The event gives the connection, the cursor, the statement, its parameters, and two more.
        sent.append((heard[2], heard[3]))

    event.listen(engine, "before_cursor_execute", collect)
    try:
        yield sent
    finally:
        event.remove(engine, "before_cursor_execute", collect)


def partitions_read(connection: Connection, statement: str, parameters: Any) -> dict[str, set[str]]:
    """Give the partitions a statement's plan reads, by revised table, with its parameters."""
    explained = connection.exec_driver_sql(f"EXPLAIN (FORMAT JSON) {statement}", parameters)
    read: dict[str, set[str]] = {}
    for name in relations(explained.scalar_one()[0]["Plan"]):
        found = PARTITION_NAME.fullmatch(name)
        if found:
            read.setdefault(found["parent"], set()).add(name)
    return read


def test_the_plans_of_the_real_readings_of_a_revision_read_one_partition_of_each_table(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # « Le plan d'exécution d'une lecture de révision ne parcourt que la partition du projet. »
    # The functions of the core the operations that read a revision serve — getRevision,
    # listCostStructures, listNodes, a structure read, compareRevisions, getRateUpdateProposal —
    # are played on a platform of three projects, each with its data: a plan that read the
    # partitions of the other two would show. The statements they send to a revised table are
    # explained, with their parameters; each reads at most one partition of each table.
    stage = make_scene(api, owner, database, realm)
    projects = [stage]
    projects += [replace(stage, project=create(api, stage.manager, label=n)) for n in ("B", "C")]
    revisions = [with_data(api, each) for each in projects]
    project_id = UUID(stage.project["project_id"])
    offer, amendment, structure_id = revisions[0]
    viewer = Viewer(stage.manager.user_id, MANAGING)
    place = Place(project_id, offer, structure_id)
    asked = ComparisonAsked(offer, amendment, NodeFilters())
    readings: dict[str, Callable[[Session], object]] = {
        "getRevision": lambda each: read_revision(each, project_id, offer, viewer),
        "getRevision (what it keeps)": lambda each: kept_reference(each, project_id, offer),
        "listCostStructures": lambda each: list_cost_structures(each, project_id, offer, viewer),
        "listNodes": lambda each: list_records(each, place, NodeFilters()),
        "listNodes (tasks)": lambda each: list_records(each, place, NodeFilters(kinds=("task",))),
        "readStructure": lambda each: read_structure(each, place, NodeFilters()),
        "compareRevisions": lambda each: compare_revisions(each, project_id, asked, node_body),
        "getRateUpdateProposal": lambda each: rate_update_proposal(each, project_id, amendment),
    }
    explained: dict[str, list[tuple[str, dict[str, set[str]]]]] = {}
    for name, read in readings.items():
        with statements_of(database.engine) as sent, database.transaction() as session:
            read(session)
        with owner.connect() as connection:
            parents = partitioned_by_project(connection)
            explained[name] = [
                (statement, partitions_read(connection, statement, parameters))
                for statement, parameters in sent
                if re.match(r"\s*(SELECT|WITH)", statement)
                and re.search(rf"\b(?:FROM|JOIN)\s+(?:{'|'.join(parents)})\b", statement)
            ]
    assert all(explained.values()), [name for name, found in explained.items() if not found]
    wide = [
        f"{name}: { ({parent: sorted(each) for parent, each in found.items() if len(each) > 1}) }"
        f"\n{statement}"
        for name, statements in explained.items()
        for statement, found in statements
        if any(len(each) > 1 for each in found.values())
    ]
    assert not wide, "\n\n".join(wide)
