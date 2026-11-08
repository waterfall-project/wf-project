# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the tables of the planning, the history and the imports forbid (EP-06).

The constraints of the eight tables of US-1380/L1, one refusal each, as
``test_database_constraints_projects.py`` tries those of EP-04; then the cascades the design decides
inside a current revision, and the renumbering of siblings in one statement. Every row is written
around the services of the modules, by the service (WF-DAT-0090). Each list of values the tables
and the migration copy from an enumeration of the contract is compared with it, so that a value the
contract adds is never refused by the database in silence.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, TypeAliasType, get_args
from uuid import UUID, uuid4

import psycopg
import pytest
from planning_support import insert_link, insert_task, link_row, node_row, task_row
from project_rows import AT, STAMP, insert_revision, insert_structure, projects_with_partitions
from sqlalchemy import Engine, delete, func, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from support import raw_account

from waterfall.api.contract import models
from waterfall.core.exchanges.interface import ExchangeKind, ExportKind
from waterfall.core.exchanges.tables import EXCHANGE_KINDS, IMPORT_STATUSES, ImportReport
from waterfall.core.history.interface import UndoneKind
from waterfall.core.history.tables import NODE_COLUMNS, UNDONE_KINDS, PastePlan, UndoEntry
from waterfall.core.planning.tables import (
    DURATION_UNITS,
    LAG_UNITS,
    LINK_TYPES,
    NODE_KINDS,
    PROGRESSES,
    SCHEDULING_MODES,
    Node,
    Task,
    TaskLink,
    Timeline,
    TrackingEntry,
)
from waterfall.core.projects.tables import OrderItem, WorkPackage
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Base, Database

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.sql import Executable

pytestmark = pytest.mark.requirement("WF-DAT-0090-A")

# The eight tables of US-1380/L1.
TABLES: tuple[type[Base], ...] = (
    Node,
    Task,
    TaskLink,
    Timeline,
    TrackingEntry,
    ImportReport,
    UndoEntry,
    PastePlan,
)

type Refusal = tuple[type[Base], dict[str, object], str]


@dataclass(frozen=True)
class Parents:
    """What a row of a test names: a project with its current revision and its main structure.

    The structure holds two root tasks, ``node`` and ``other``; the project a work package with an
    order item, and a timeline; an account writes the history.
    """

    project: UUID
    revision: UUID
    structure: UUID
    node: UUID
    other: UUID
    account: UUID
    work_package: UUID
    order_item: UUID
    timeline: UUID


@pytest.fixture
def parents(database: Database, owner: Engine) -> Iterator[Parents]:
    """Write the parents of the rows a test tries, around the service."""
    with projects_with_partitions(owner) as (project,):
        revision, structure, account, work_package, order_item, timeline = (
            uuid4() for _ in range(6)
        )
        with database.engine.begin() as connection:
            connection.execute(insert(UserAccount).values(**raw_account(id=account)))
            connection.execute(insert_revision(project, id=revision))
            connection.execute(insert_structure(project, revision, id=structure))
            node = insert_task(connection, project, revision, structure)
            other = insert_task(connection, project, revision, structure, rank=2)
            element = {"project_id": project, "position": 0, **STAMP}
            connection.execute(insert(WorkPackage).values(id=work_package, label="Lot", **element))
            connection.execute(
                insert(OrderItem).values(
                    id=order_item, work_package_id=work_package, label="Poste", **element
                )
            )
            connection.execute(
                insert(Timeline).values(id=timeline, project_id=project, label="Jalons", **STAMP)
            )
        yield Parents(
            project, revision, structure, node, other, account, work_package, order_item, timeline
        )


def constraint_of(engine: Engine, error: IntegrityError) -> str:
    """Give the constraint of the table a refusal comes from, that of its partition named so.

    A partition clones the constraints and the indexes of its table, under a name of its own for a
    unique index or for a key that names a partitioned table: each is read up to the table's.
    """
    cause = error.orig
    assert isinstance(cause, psycopg.Error)
    name = cause.diag.constraint_name or ""
    with engine.connect() as connection:
        constraint = connection.scalar(
            text(
                "WITH RECURSIVE up(oid, parent, name) AS (SELECT oid, conparentid, conname "
                "FROM pg_constraint WHERE conname = :name UNION SELECT c.oid, c.conparentid, "
                "c.conname FROM pg_constraint AS c JOIN up ON c.oid = up.parent) "
                "SELECT name FROM up WHERE parent = 0 LIMIT 1"
            ),
            {"name": name},
        )
        index = connection.scalar(
            text(
                "WITH RECURSIVE up(oid) AS (SELECT to_regclass(:name)::oid UNION "
                "SELECT inhparent FROM pg_inherits JOIN up ON inhrelid = up.oid) "
                "SELECT relname FROM pg_class JOIN up ON pg_class.oid = up.oid "
                "WHERE NOT EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid = up.oid)"
            ),
            {"name": name},
        )
    return constraint or index or name


def refusal(engine: Engine, statement: Executable) -> str:
    """Run a statement the database must refuse, and give the constraint that refused it."""
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        connection.execute(statement)
    return constraint_of(engine, raised.value)


def valid(table: type[Base], parents: Parents) -> dict[str, object]:
    """Give the columns of a valid row of a table, under the parents of the test."""
    project, revision, structure = parents.project, parents.revision, parents.structure
    node = node_row(project, revision, structure, rank=3)
    rows: dict[type[Base], dict[str, object]] = {
        Node: node,
        Task: task_row(project, parents.node, structure),
        TaskLink: link_row(project, revision, structure, parents.node, parents.other),
        Timeline: {"id": uuid4(), "project_id": project, "label": "Revues", **STAMP},
        TrackingEntry: {
            "id": uuid4(),
            "project_id": project,
            "lineage_id": parents.node,
            "kind": "timeline",
            "timeline_id": parents.timeline,
            **STAMP,
        },
        ImportReport: {
            "id": uuid4(),
            "project_id": project,
            "kind": "ms_project_schedule",
            "filename": "planning.xml",
            "upload_id": uuid4(),
            "object_key": f"uploads/{uuid4()}",
            "status": "analysing",
            "created_at": AT,
        },
        UndoEntry: {
            "id": uuid4(),
            "project_id": project,
            "revision_id": revision,
            "user_account_id": parents.account,
            "session_id": "sid",
            "rank": 1,
            "kind": "cell",
            "node_ids": [parents.node],
            "before": [],
            "after": [],
            "undone": False,
            "created_at": AT,
        },
        PastePlan: {
            "id": uuid4(),
            "project_id": project,
            "revision_id": revision,
            "structure_id": structure,
            "user_account_id": parents.account,
            "target_node_id": parents.node,
            "target_column": "label",
            "rows": [["Conception"]],
            "structure_lock_version": 0,
            "created_at": AT,
            "expires_at": AT,
        },
    }
    return rows[table]


def row(table: type[Base], parents: Parents, **overrides: object) -> Executable:
    """Give the insertion of a row of a table, valid but for the changes a test asks for."""
    return insert(table).values(**{**valid(table, parents), **overrides})


def bounds(table: type[Base], column: str, longest: int) -> list[Refusal]:
    """Give the three refusals of a bounded text: empty, too long, blank."""
    name = table.__tablename__
    return [
        (table, {column: ""}, f"ck_{name}_{column}_length"),
        (table, {column: "x" * (longest + 1)}, f"ck_{name}_{column}_length"),
        (table, {column: " \t"}, f"ck_{name}_{column}_not_blank"),
    ]


def stamped(table: type[Base]) -> list[Refusal]:
    """Give the refusals of the authors of a row, accounts that do not exist."""
    name = table.__tablename__
    return [
        (table, {"created_by": uuid4()}, f"fk_{name}_created_by_user_account"),
        (table, {"updated_by": uuid4()}, f"fk_{name}_updated_by_user_account"),
    ]


# A value a row already written holds (``held``, below), the facet of the second task, and a node
# of a line, which never bears the facet of a task.
TAKEN = "TAKEN"
OTHER = "OTHER"
LINE = "LINE"
LINE_NODE = uuid4()

REFUSALS: list[Refusal] = [
    (Node, {"kind": "milestone"}, "ck_node_kind_known"),
    (Node, {"rank": 0}, "ck_node_rank_positive"),
    (Node, {"lock_version": -1}, "ck_node_lock_version_not_negative"),
    (Node, {"revision_id": uuid4()}, "fk_node_project_id_cost_structure"),
    (Node, {"parent_id": uuid4()}, "fk_node_project_id_node"),
    (Node, {"rank": 1}, "uq_node_structure_id"),
    *stamped(Node),
    (Task, {"node_id": LINE}, "fk_task_project_id_node"),
    (Task, {"structure_id": uuid4()}, "fk_task_node_id_node"),
    (Task, {"kind": "estimate_line"}, "ck_task_kind_task"),
    *bounds(Task, "label", 300),
    (Task, {"scheduling_mode": "fixed"}, "ck_task_scheduling_mode_known"),
    (Task, {"duration_unit": "y"}, "ck_task_duration_unit_known"),
    (Task, {"duration_value": Decimal(-1)}, "ck_task_duration_value_not_negative"),
    (Task, {"start_hours": Decimal(-1)}, "ck_task_start_hours_of_a_day"),
    (Task, {"finish_hours": Decimal(25)}, "ck_task_finish_hours_of_a_day"),
    (Task, {"progress": "suspended"}, "ck_task_progress_known"),
    (Task, {"progress": "started"}, "ck_task_started_on_when_started"),
    (
        Task,
        {"progress": "completed", "started_on": date(2026, 11, 2)},
        "ck_task_completed_on_when_completed",
    ),
    (Task, {"completed_on": date(2026, 11, 2)}, "ck_task_completed_on_when_completed"),
    (Task, {"external_id": "x" * 201}, "ck_task_external_id_length"),
    (Task, {"order_item_id": TAKEN, "work_package_id": TAKEN}, "ck_task_one_work_breakdown_item"),
    (Task, {"order_item_id": uuid4()}, "fk_task_order_item_id_order_item"),
    (Task, {"work_package_id": uuid4()}, "fk_task_work_package_id_work_package"),
    (Task, {"node_id": OTHER, "order_item_id": TAKEN}, "uq_task_order_item"),
    (Task, {"node_id": OTHER, "work_package_id": TAKEN}, "uq_task_work_package"),
    (TaskLink, {"revision_id": uuid4()}, "fk_task_link_project_id_cost_structure"),
    (TaskLink, {"predecessor_id": uuid4()}, "fk_task_link_predecessor_id_node"),
    (TaskLink, {"successor_id": uuid4()}, "fk_task_link_successor_id_node"),
    (TaskLink, {"successor_id": TAKEN}, "ck_task_link_predecessor_not_successor"),
    (TaskLink, {"link_type": "overlap"}, "ck_task_link_link_type_known"),
    (TaskLink, {"lag_unit": "y"}, "ck_task_link_lag_unit_known"),
    (TaskLink, {"in_conflict": True}, "uq_task_link_structure_id"),
    *bounds(Timeline, "label", 200),
    (Timeline, {"project_id": uuid4()}, "fk_timeline_project_id_project"),
    *stamped(Timeline),
    (TrackingEntry, {"kind": "budget"}, "ck_tracking_entry_kind_known"),
    (TrackingEntry, {"timeline_id": None}, "ck_tracking_entry_timeline_when_timeline"),
    (TrackingEntry, {"kind": "milestone_tracking"}, "ck_tracking_entry_timeline_when_timeline"),
    (
        TrackingEntry,
        {"kind": "milestone_tracking", "timeline_id": None},
        "uq_tracking_entry_lineage_id",
    ),
    (TrackingEntry, {"project_id": uuid4()}, "fk_tracking_entry_project_id_project"),
    (TrackingEntry, {"timeline_id": uuid4()}, "fk_tracking_entry_timeline_id_timeline"),
    *stamped(TrackingEntry),
    (ImportReport, {"kind": "budget"}, "ck_import_report_kind_known"),
    (ImportReport, {"status": "waiting"}, "ck_import_report_status_known"),
    (ImportReport, {"status": "analysed"}, "ck_import_report_expires_at_when_analysed"),
    (ImportReport, {"expires_at": AT}, "ck_import_report_expires_at_when_analysed"),
    (ImportReport, {"report": []}, "ck_import_report_report_object"),
    (ImportReport, {"filename": ""}, "ck_import_report_filename_length"),
    (ImportReport, {"filename": "x" * 256}, "ck_import_report_filename_length"),
    (ImportReport, {"upload_id": TAKEN}, "uq_import_report_upload_id"),
    (ImportReport, {"project_id": uuid4()}, "fk_import_report_project_id_project"),
    (ImportReport, {"requested_by": uuid4()}, "fk_import_report_requested_by_user_account"),
    (UndoEntry, {"kind": "rename"}, "ck_undo_entry_kind_known"),
    (UndoEntry, {"rank": TAKEN}, "uq_undo_entry_revision_id"),
    (UndoEntry, {"revision_id": uuid4()}, "fk_undo_entry_project_id_revision"),
    (UndoEntry, {"user_account_id": uuid4()}, "fk_undo_entry_user_account_id_user_account"),
    (PastePlan, {"target_column": "amount"}, "ck_paste_plan_target_column_known"),
    (
        PastePlan,
        {"structure_lock_version": -1},
        "ck_paste_plan_structure_lock_version_not_negative",
    ),
    (PastePlan, {"revision_id": uuid4()}, "fk_paste_plan_project_id_revision"),
    (PastePlan, {"user_account_id": uuid4()}, "fk_paste_plan_user_account_id_user_account"),
]
# The constraints a key holds already, never broken without it: what a facet and a task name.
UNBROKEN = {"uq_node_project_id", "uq_node_id"}
UPLOAD = uuid4()


def resolved(parents: Parents, overrides: dict[str, object]) -> dict[str, object]:
    """Give the values a refusal tries, the ones a row already written holds put in."""
    named = {
        "order_item_id": parents.order_item,
        "work_package_id": parents.work_package,
        "successor_id": parents.node,
        "upload_id": UPLOAD,
        "rank": 1,
    }
    found = {
        column: named[column] if value == TAKEN else value for column, value in overrides.items()
    }
    if found.get("node_id") == OTHER:
        found["node_id"] = parents.other
    if found.get("node_id") == LINE:
        found["node_id"] = LINE_NODE
    return found


def held_by_a_node(parents: Parents, overrides: dict[str, object]) -> Executable:
    """Give the row a facet tried collides with: the node of a line, or the facet of a task."""
    if overrides.get("node_id") == LINE:
        line = node_row(parents.project, parents.revision, parents.structure, id=LINE_NODE)
        return insert(Node).values({**line, "kind": "estimate_line"})
    column = next(column for column in overrides if column != "node_id")
    return row(Task, parents, **resolved(parents, {column: TAKEN}))


def held(table: type[Base], parents: Parents, overrides: dict[str, object]) -> Executable | None:
    """Give the row already written that a refusal collides with, if it needs one."""
    if table is Task and overrides.get("node_id") in {LINE, OTHER}:
        return held_by_a_node(parents, overrides)
    if table is TaskLink and "in_conflict" in overrides:
        return row(TaskLink, parents)
    if table is TrackingEntry and overrides.get("timeline_id", TAKEN) is None:
        return row(TrackingEntry, parents, **overrides) if "kind" in overrides else None
    if table is ImportReport and overrides.get("upload_id") == TAKEN:
        return row(ImportReport, parents, upload_id=UPLOAD)
    if table is UndoEntry and overrides.get("rank") == TAKEN:
        return row(UndoEntry, parents)
    return None


@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    REFUSALS,
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_row_of_the_planning_that_breaks_a_rule(
    database: Database,
    parents: Parents,
    table: type[Base],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    with database.engine.begin() as connection:
        if table is Task:
            # The tasks of the parents have their facet already: the one tried is written anew.
            connection.execute(delete(Task))
        first = held(table, parents, overrides)
        if first is not None:
            connection.execute(first)
    tried = row(table, parents, **resolved(parents, overrides))
    assert refusal(database.engine, tried) == constraint


def test_every_named_constraint_of_the_planning_has_its_refusal_tried() -> None:
    tables = [Base.metadata.tables[table.__tablename__] for table in TABLES]
    named = {
        str(constraint.name)
        for table in tables
        for constraint in table.constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    } | {str(index.name) for table in tables for index in table.indexes if index.unique}
    tried = {constraint for _, _, constraint in REFUSALS}
    assert named - UNBROKEN == tried


# The cascades the designs decide (sql.md, "Les clés étrangères refusent par défaut").
CASCADES = {
    "fk_node_project_id_cost_structure",
    "fk_node_project_id_node",
    "fk_task_project_id_node",
    "fk_task_node_id_node",
    "fk_task_link_project_id_cost_structure",
    "fk_task_link_predecessor_id_node",
    "fk_task_link_successor_id_node",
    "fk_tracking_entry_timeline_id_timeline",
}


def test_every_foreign_key_of_the_schema_refuses_by_default(database: Database) -> None:
    # Of the whole schema, here since EP-06 brings its first cascades, which
    # ``test_database_constraints.py``, at its bound of lines, could not hold: every key refuses,
    # but the cascades an epic decides in its design, with the rows they take — inside a current
    # revision, the facet with its node, a link with its tasks or its structure, a node with its
    # structure or its parent, an inscription with its timeline (EP-06, "Tables et migrations").
    # A key a partition clones is judged by the key of its table.
    with database.engine.connect() as connection:
        actions = connection.execute(
            text(
                "WITH RECURSIVE up(oid, root, parent) AS (SELECT oid, oid, conparentid "
                "FROM pg_constraint WHERE contype = 'f' UNION ALL SELECT up.oid, parent.oid, "
                "parent.conparentid FROM up JOIN pg_constraint AS parent "
                "ON parent.oid = up.parent) "
                "SELECT root.conname, key.confdeltype, key.confupdtype FROM up "
                "JOIN pg_constraint AS key ON key.oid = up.oid "
                "JOIN pg_constraint AS root ON root.oid = up.root WHERE up.parent = 0"
            )
        ).all()
    assert len(actions) >= 2
    kept = [row for row in actions if row.conname not in CASCADES]
    refusing = {(row.confdeltype, row.confupdtype) for row in kept}
    assert refusing <= {("r", "a"), ("a", "a")}
    assert {row.conname for row in actions if row.confdeltype == "c"} == CASCADES


def count(database: Database, table: type[Base]) -> int:
    """Count the rows of a table."""
    with database.engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(table)).scalar_one()


def test_inside_a_current_revision_a_node_takes_its_facet_its_subtree_and_its_links_with_it(
    database: Database, parents: Parents
) -> None:
    # The cascade the design decides inside a current revision (EP-06, "Tables et migrations"): a
    # task deleted takes its facet, its subordinates and their links; the other task stays.
    with database.engine.begin() as connection:
        child = uuid4()
        row_of_child = node_row(parents.project, parents.revision, parents.structure, id=child)
        connection.execute(insert(Node).values({**row_of_child, "parent_id": parents.node}))
        connection.execute(
            insert(Task).values(**task_row(parents.project, child, parents.structure))
        )
        connection.execute(
            insert_link(parents.project, parents.revision, parents.structure, child, parents.other)
        )
        connection.execute(delete(Node).where(Node.id == parents.node))
    assert (count(database, Node), count(database, Task), count(database, TaskLink)) == (1, 1, 0)


def test_inside_a_current_revision_a_structure_takes_its_nodes_and_a_timeline_its_inscriptions(
    database: Database, parents: Parents
) -> None:
    # The abandonment of a full revision deletes its structures, and its nodes with them.
    with database.engine.begin() as connection:
        connection.execute(row(TaskLink, parents))
        connection.execute(row(TrackingEntry, parents))
        connection.execute(delete(CostStructure).where(CostStructure.id == parents.structure))
        connection.execute(delete(Timeline).where(Timeline.id == parents.timeline))
    assert [count(database, table) for table in (Node, Task, TaskLink, TrackingEntry)] == [0] * 4


@pytest.mark.usefixtures("parents")
def test_the_siblings_of_a_node_are_renumbered_in_one_statement(database: Database) -> None:
    # The order among siblings is checked at the end of the statement: every rank moves at once.
    with database.engine.begin() as connection:
        connection.execute(update(Node).values(rank=Node.rank + 1))
        ranks = connection.execute(select(Node.rank).order_by(Node.rank)).scalars().all()
    assert list(ranks) == [2, 3]


# Each list of values a table keeps, by the constraint of its column, and the enumeration of the
# contract it copies (EP-06, "Tables et migrations").
IMPORT_STATUS = models.Import.model_fields["status"].annotation
assert isinstance(IMPORT_STATUS, type)
assert issubclass(IMPORT_STATUS, StrEnum)
ENUMERATIONS: list[tuple[str, str, tuple[str, ...], type[StrEnum]]] = [
    ("node", "kind", NODE_KINDS, models.NodeKind),
    ("task", "scheduling_mode", SCHEDULING_MODES, models.SchedulingMode),
    ("task", "duration_unit", DURATION_UNITS, models.DurationUnit),
    ("task", "progress", PROGRESSES, models.TaskProgress),
    ("task_link", "link_type", LINK_TYPES, models.LinkType),
    ("task_link", "lag_unit", LAG_UNITS, models.LagUnit),
    ("undo_entry", "kind", UNDONE_KINDS, models.UndoneKind),
    ("paste_plan", "target_column", NODE_COLUMNS, models.NodeColumn),
    ("import_report", "kind", EXCHANGE_KINDS, models.ExchangeKind),
    ("import_report", "status", IMPORT_STATUSES, IMPORT_STATUS),
]


@pytest.mark.parametrize(
    ("table", "column", "kept", "enumeration"),
    ENUMERATIONS,
    ids=[f"{table}.{column}" for table, column, _, _ in ENUMERATIONS],
)
def test_each_list_of_values_of_the_tables_is_the_enumeration_of_the_contract(
    database: Database, table: str, column: str, kept: tuple[str, ...], enumeration: type[StrEnum]
) -> None:
    # The code's list, and the one the migration wrote in the constraint, in the contract's order.
    values = [member.value for member in enumeration]
    with database.engine.connect() as connection:
        definition = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = :name AND conrelid = CAST(:table AS regclass)"
            ),
            {"name": f"ck_{table}_{column}_known", "table": table},
        )
    assert list(kept) == values
    assert re.findall(r"'([^']*)'::text", str(definition)) == values


@pytest.mark.parametrize(
    ("declared", "enumeration"),
    [
        (UndoneKind, models.UndoneKind),
        (ExchangeKind, models.ExchangeKind),
        (ExportKind, models.ExportKind),
    ],
    ids=["UndoneKind", "ExchangeKind", "ExportKind"],
)
def test_each_kind_the_interfaces_declare_is_the_enumeration_of_the_contract(
    declared: object, enumeration: type[StrEnum]
) -> None:
    # A kind declared otherwise than by an alias of a type fails here by name, not by its args.
    assert isinstance(declared, TypeAliasType), f"{declared!r} is no alias of a type"
    assert list(get_args(declared.__value__)) == [member.value for member in enumeration]
