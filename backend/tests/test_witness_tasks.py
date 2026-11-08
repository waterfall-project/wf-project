# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the tasks of the witness (US-1480/L2; WF-QUA-0040): loaded, reconciled and read.

``load-witness`` fills each revision of PRJ-001 once the slice of the revisions has opened it and
before it is marked (``witness.tasks``): the tasks the copy gave it reconciled by lineage with those
``witness_tasks.json`` describes — deleted, created, their links, their states, their inscriptions,
the planning start of the structure —, at the identifiers and the instants the witness imposes.

What the service reads of the loaded witness is compared with the examples of the contract
(``nodes_planning``, ``nodes_summaries``, ``nodes_timeline``, ``nodes_milestone`` and
``volume/nodes_thousand``), but for what the slice does not reach, listed here (``UNREACHED``):
each entry names the EPIC that lifts it. The dates the engine computes are the expected; those of
the file and of the volume example differ where the calendar of a task comes from the lines
EP-07 loads, and the tests say which tasks (``test_the_dates_differ_only_...``).
"""

import json
from collections import defaultdict
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from installed_reference import install
from projects_support import PROJECTS
from sqlalchemy import select
from test_witness import load, wipe
from test_witness_projects import (
    PRJ_001,
    REVISION_100,
    REVISION_101,
    REVISION_102,
    example,
    instant,
    read,
)

from waterfall.core.planning.interface import (
    LinkLoad,
    Place,
    TaskLoad,
    TasksLoad,
    WorkInstant,
    load_tasks,
)
from waterfall.core.planning.scheduling import Duration
from waterfall.core.planning.tables import Node, Task, TaskLink, TrackingEntry
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient, Logs

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

REVISIONS = {100: REVISION_100, 101: REVISION_101, 102: REVISION_102}
# The events that open the revisions in the chronology (sequence numbers), and the planning start.
OPENED = {100: 3, 101: 5, 102: 9}
PLANNING_START = date(2026, 3, 2)
CORE = "01926f3a-7c00-7000-8000-000000000521"
POPULAR_TIMELINE = "01926f3a-7c00-7000-8000-000000001000"
# What the service reads of a task that the slice does not reach, and the EPIC that lifts it.
UNREACHED = {
    "amounts": "the amounts, the budget and the physical progress come from the lines (EP-07)",
    "lines": "the row numbers count the lines of the examples (EP-07)",
    "calendar_id": "the example names no calendar for a task on the default one",
    "reading_date": "finish_overdue is read at the day of the reading: the example's, 3 June 2026",
    "lock_version": "a state laid counts one write of the task (US-1410)",
    "empties": "the examples omit an empty list of predecessors or of inscriptions",
    "risk": "the origin risk of a provision task is posed by EP-08",
}
AMOUNTS = {"base_amount", "budgeted_amount", "reestimated_amount", "physical_progress"}
# The float is measured to the end of the project, which the calendars of the lines move (EP-07).
FLOAT = {"total_float"}
# What an example of the service answers beside the tasks, by the lines or the reading.
BESIDE = {"origin_risk_id", "row_number", "lock_version"}
# The tasks the calendar of a line reaches: dates, durations and floats the engine computes on the
# default calendar (EP-07 lifts it with the lines).
CALENDAR = {"start", "finish", "duration", "total_float", "calendar_hours", "is_critical"}


def described() -> dict[str, Any]:
    """Read the value of ``witness_tasks.json``."""
    return example("witness_tasks")


def file_tasks(revision: int) -> list[dict[str, Any]]:
    """Give the tasks the file describes for a revision, in the order of the plan."""
    return [task for task in described()["tasks"] if task["revision"] == revision]


def structure_of(session: Session, revision: UUID) -> UUID:
    """Give the main structure of a revision."""
    found = session.scalar(
        select(CostStructure.id).where(
            CostStructure.revision_id == revision, CostStructure.kind == "main"
        )
    )
    assert found is not None
    return found


def rows(session: Session, revision: UUID) -> dict[UUID, tuple[Node, Task]]:
    """Give the lineage of each node of a revision with its node and its task."""
    found = session.execute(
        select(Node, Task)
        .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
        .where(Node.revision_id == revision)
    ).all()
    return {node.lineage_id: (node, task) for node, task in found}


def instants(value: dict[str, Any]) -> tuple[date, Decimal]:
    """Give a start or a finish of the file as a day and the hours elapsed."""
    return date.fromisoformat(value["date"]), Decimal(value["hours"])


def lineage_of_facets(session: Session, revision: UUID) -> dict[UUID, dict[str, object]]:
    """Give what the identifying data of a revision are: identifiers, lineages, place, dates."""
    parents = {node.id: node.lineage_id for node, _ in rows(session, revision).values()}
    return {
        lineage: {
            "id": node.id,
            "parent": parents.get(node.parent_id) if node.parent_id else None,
            "rank": node.rank,
            "label": task.label,
            "mode": task.scheduling_mode,
            "start": (task.start_date, task.start_hours),
            "finish": (task.finish_date, task.finish_hours),
            "progress": (task.progress, task.started_on, task.completed_on),
            "created_at": node.created_at,
        }
        for lineage, (node, task) in rows(session, revision).items()
    }


def test_each_revision_holds_the_tasks_the_file_describes_under_their_lineages(
    witness: Database,
) -> None:
    # The thousand tasks of the revision in progress, the offer's and the reference's before it:
    # the same lineages, in the places and with the facets the file gives them.
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            held = rows(session, revision)
            expected = file_tasks(number)
            assert {str(lineage) for lineage in held} == {task["lineage_id"] for task in expected}
            by_lineage = {str(lineage): pair for lineage, pair in held.items()}
            siblings: dict[str | None, list[tuple[int, str]]] = defaultdict(list)
            for task in expected:
                node, facet = by_lineage[task["lineage_id"]]
                parent = task["parent_lineage_id"]
                assert node.parent_id == (None if parent is None else by_lineage[parent][0].id), (
                    task["label"]
                )
                assert (facet.label, facet.description) == (task["label"], task["description"])
                assert facet.scheduling_mode == task["scheduling_mode"]
                assert (facet.duration_value, facet.duration_unit) == (
                    Decimal(task["duration"]["value"]),
                    task["duration"]["unit"],
                ) or task["is_summary"]
                assert str(facet.work_package_id or "") == (task["work_package_id"] or "")
                assert str(facet.order_item_id or "") == (task["order_item_id"] or "")
                siblings[parent].append((task["position"], task["lineage_id"]))
            for found in siblings.values():
                ranks = [by_lineage[lineage][0].rank for _, lineage in sorted(found)]
                assert ranks == list(range(1, len(found) + 1))
    assert [len(file_tasks(number)) for number in REVISIONS] == [997, 997, 1000]


def test_the_revision_in_progress_holds_the_identifiers_of_the_examples_and_the_marked_ones_theirs(
    witness: Database,
) -> None:
    # A node belongs to one revision: the examples read the identifiers of the revision in progress;
    # a marked one holds the same lineages under identifiers derived from them, the same on every
    # platform, none shared.
    with witness.transaction() as session:
        identifiers = {
            number: {node.id for node, _ in rows(session, revision).values()}
            for number, revision in REVISIONS.items()
        }
        in_progress = {task["node_id"] for task in file_tasks(102)}
    assert {str(each) for each in identifiers[102]} == in_progress
    assert not identifiers[100] & identifiers[102]
    assert not identifiers[101] & identifiers[102]
    assert not identifiers[100] & identifiers[101]
    assert [len(identifiers[number]) for number in REVISIONS] == [997, 997, 1000]


def test_the_copy_of_the_offer_is_reconciled_deleted_and_created_by_lineage(
    witness: Database,
) -> None:
    # The preliminary trials on site, removed by the amendment 1, are the offer's alone; the
    # reference and the revision in progress hold the lineages the file says, none more.
    with witness.transaction() as session:
        lineages = {
            number: {str(lineage) for lineage in rows(session, revision)}
            for number, revision in REVISIONS.items()
        }
    trials = lineages[100] - lineages[102]
    assert len(trials) == 1
    assert not trials & lineages[101]
    assert lineages[101] <= lineages[102]
    assert len(lineages[102] - lineages[101]) == 3


def test_the_links_are_those_of_the_file_by_the_lineage_of_their_predecessor(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            held = rows(session, revision)
            by_id = {node.id: lineage for lineage, (node, _) in held.items()}
            found = {
                (
                    str(by_id[link.successor_id]),
                    str(by_id[link.predecessor_id]),
                    link.link_type,
                    link.lag_value,
                    link.lag_unit,
                )
                for link in session.scalars(
                    select(TaskLink).where(TaskLink.revision_id == revision)
                )
            }
            expected = {
                (
                    task["lineage_id"],
                    link["predecessor_lineage_id"],
                    link["link_type"],
                    Decimal(link["lag"]["value"]),
                    link["lag"]["unit"],
                )
                for task in file_tasks(number)
                for link in task["predecessors"]
            }
            assert found == expected
            assert len(expected) > 1000


def test_the_states_and_their_dates_are_those_of_the_file_on_every_leaf(
    witness: Database,
) -> None:
    # A summary has none of its own: its state is derived from its subordinates (US-1410).
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            held = rows(session, revision)
            expected = file_tasks(number)
            summaries = {task["parent_lineage_id"] for task in expected}
            started = 0
            for task in expected:
                if task["lineage_id"] in summaries:
                    continue
                facet = held[UUID(task["lineage_id"])][1]
                state = (task["progress"], task["started_on"], task["completed_on"])
                assert (
                    facet.progress,
                    None if facet.started_on is None else facet.started_on.isoformat(),
                    None if facet.completed_on is None else facet.completed_on.isoformat(),
                ) == state, task["label"]
                started += task["progress"] != "not_started"
            assert (started > 0) == (number == 102)


def test_the_planning_start_of_each_structure_is_that_of_the_file_and_its_dates_are_the_opening(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            structure = session.get(CostStructure, (PRJ_001, structure_of(session, revision)))
            assert structure is not None
            expected = next(e for e in described()["revisions"] if e["revision"] == number)
            assert structure.planning_start_on == date.fromisoformat(expected["planning_start_on"])
            assert structure.planning_start_on == PLANNING_START
            # The engine replayed at the instant of the event that opens the revision.
            assert structure.scheduled_at == instant(OPENED[number])


def test_the_inscriptions_follow_each_lineage_as_the_file_says_for_the_revision_in_progress(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        found: dict[str, set[tuple[str, str | None]]] = defaultdict(set)
        for entry in session.scalars(select(TrackingEntry)):
            found[str(entry.lineage_id)].add(
                (entry.kind, entry.timeline_id and str(entry.timeline_id))
            )
    for task in file_tasks(102):
        assert found[task["lineage_id"]] == {
            (entry["kind"], entry["timeline_id"]) for entry in task["inscriptions"]
        }, task["label"]


def test_every_row_is_written_by_the_platform_at_the_instant_of_the_event_of_its_revision(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            opened = instant(OPENED[number])
            for node, _ in rows(session, revision).values():
                assert (node.created_at, node.created_by) == (opened, None)
                assert node.updated_by is None
                assert node.updated_at == opened


def closure(volume: list[dict[str, Any]]) -> set[str]:
    """Give the tasks the calendar of a line reaches.

    The tasks on a calendar of ten hours, their successors and their summaries.
    """
    items = {item["node_id"]: item for item in volume if item["kind"] == "task"}
    reached = {k for k, v in items.items() if v["task"]["calendar_hours"]["monday"] == "10"}
    pending = list(reached)
    successors: dict[str, list[str]] = defaultdict(list)
    for node_id, item in items.items():
        links: list[dict[str, Any]] = item.get("predecessors") or []
        for link in links:
            successors[link["predecessor_node_id"]].append(node_id)
    while pending:
        current = pending.pop()
        above = items[current]["parent_id"]
        for found in (*successors[current], *([above] if above else [])):
            if found not in reached:
                reached.add(found)
                pending.append(found)
    return reached


def test_the_dates_differ_from_the_file_only_for_the_tasks_a_calendar_of_a_line_reaches(
    witness: Database, logs: Logs
) -> None:
    # The computed is the expected: on the three revisions, the engine dates every task as the file
    # does but those the 4x10 calendars of the lines reach (EP-07), their successors and their
    # summaries; the core of the examples is not among them.
    volume = example("volume/nodes_thousand")["items"]
    reached = closure(volume)
    node_of_lineage = {
        item["lineage_id"]: item["node_id"] for item in volume if item["kind"] == "task"
    }
    differing_counts: dict[int, int] = {}
    with witness.transaction() as session:
        for number, revision in REVISIONS.items():
            held = rows(session, revision)
            differing: list[str | None] = []
            for task in file_tasks(number):
                facet = held[UUID(task["lineage_id"])][1]
                computed = (
                    (facet.start_date, facet.start_hours),
                    (facet.finish_date, facet.finish_hours),
                )
                if computed != (instants(task["start"]), instants(task["finish"])):
                    differing.append(node_of_lineage.get(task["lineage_id"]))
            assert set(differing) <= reached
            assert not set(differing) & {each["node_id"] for each in core_items()}
            differing_counts[number] = len(differing)
    assert all(differing_counts.values())
    # The loader notes how many, revision after revision.
    noted = {r["revision"]: r["tasks"] for r in logs.named("witness.tasks_dated_by_the_engine")}
    assert noted in ({}, differing_counts)


def core_items() -> list[dict[str, Any]]:
    """Give the nodes of the examples of the core: the planning, the timeline, the milestone."""
    return [
        item
        for name in ("nodes_planning", "nodes_timeline", "nodes_milestone")
        for item in example(name)["items"]
    ]


def test_the_loading_notes_for_each_revision_how_many_tasks_the_engine_dated_otherwise(
    logs: Logs, witness_loaded: Database
) -> None:
    del witness_loaded
    noted = logs.named("witness.tasks_dated_by_the_engine")
    assert sorted(record["revision"] for record in noted) == [100, 101, 102]
    assert all(record["tasks"] > 0 for record in noted)


READS = {
    "nodes_planning": f"?subtree_of={CORE}&kinds=task",
    "nodes_summaries": "?kinds=task&summaries_only=true&max_level=2",
    "nodes_timeline": f"?kinds=task&timeline_id={POPULAR_TIMELINE}",
    "nodes_milestone": "?search=R%C3%A9ception%20usine",
    "volume/nodes_thousand": "?kinds=task",
}
# The group the example "nodes_summaries" rearranges (a variant with the lot under the
# installation): its place and what derives from it are not the loaded witness's.
VARIANT = "01926f3a-7c00-7000-8000-000000000561"
VARIANT_KEYS = {"parent_id", "position", "level"}


def normal(entries: list[dict[str, Any]] | None, dropped: str = "") -> list[str]:
    """Give a list of the reading as a set of texts: an absent list is an empty one."""
    return sorted(
        json.dumps({k: v for k, v in each.items() if k != dropped}, sort_keys=True)
        for each in entries or []
    )


def difference(read_node: dict[str, Any], expected: dict[str, Any], *, calendar: bool) -> list[str]:
    """Name what a node read differs in from the example, but for what the slice does not reach."""
    found: list[str] = []
    for key in set(read_node) | set(expected):
        if key in BESIDE | {"task", "predecessors"}:
            continue
        if read_node.get(key) != expected.get(key):
            found.append(key)
    ours, theirs = read_node["task"], expected["task"]
    for key in set(ours) | set(theirs):
        if key in AMOUNTS | FLOAT | {"calendar_id", "finish_overdue", "tracking", "origin_risk_id"}:
            continue
        if key in CALENDAR and calendar:
            continue
        if ours.get(key) != theirs.get(key):
            found.append(f"task.{key}")
    # The inscriptions and the links as sets, without the row numbers of the lines of the example.
    if normal(ours.get("tracking")) != normal(theirs.get("tracking")):
        found.append("task.tracking")
    if normal(read_node.get("predecessors"), "predecessor_row_number") != normal(
        expected.get("predecessors"), "predecessor_row_number"
    ):
        found.append("predecessors")
    return found


@pytest.mark.parametrize("name", list(READS))
def test_the_readings_of_the_loaded_witness_are_the_examples_but_for_what_it_does_not_reach(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
    url = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_102}/structures/{structure}/nodes{READS[name]}"
    body = read(api, witness, realm, url)
    expected = example(name)
    wanted = {item["node_id"]: item for item in expected["items"] if item["kind"] == "task"}
    got = {item["node_id"]: item for item in body["items"]}
    reached = closure(example("volume/nodes_thousand")["items"])
    if name == "nodes_summaries":
        # The reading answers the three summaries and every one the filter keeps of the tree.
        assert wanted.keys() <= got.keys()
        got = {key: value for key, value in got.items() if key in wanted}
    assert got.keys() == wanted.keys()
    assert len(got) == len(wanted)
    for node_id, item in wanted.items():
        found = difference(got[node_id], item, calendar=node_id in reached)
        if name == "nodes_summaries":
            found = [each for each in found if each not in VARIANT_KEYS]
            if node_id == VARIANT:
                found = []
        assert not found, (name, item["task"]["label"], found)
    # The order of the plan and the meta the reading answers, but for the amounts (EP-07) and the
    # instant of the engine: the opening of the revision in progress, not the example's.
    if name != "nodes_summaries":
        assert list(got) == list(wanted)
    assert body["meta"]["scheduled_at"] == instant(OPENED[102]).isoformat().replace("+00:00", "Z")
    if name in {"nodes_planning", "nodes_timeline", "volume/nodes_thousand"}:
        assert body["totals"]["task_count"] == expected["totals"]["task_count"]
    if name == "volume/nodes_thousand":
        # Only the origin risk, the calendar and what they move differ: three provision tasks bear
        # a risk (EP-08), a hundred and three a calendar of ten hours (EP-07).
        risky = [i for i in expected["items"] if i["kind"] == "task" and i["origin_risk_id"]]
        assert len(risky) == 3
        assert all(i["origin_risk_id"] is None for i in body["items"])
        ten = [i for i in wanted.values() if i["task"]["calendar_hours"]["monday"] == "10"]
        assert len(ten) == 103


def test_two_platforms_loaded_with_the_witness_hold_the_same_tasks(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    # Identifiers, lineages, places, dates and states: the platform draws none of them.
    def identifying() -> dict[int, dict[UUID, dict[str, object]]]:
        with witness.transaction() as session:
            return {
                number: lineage_of_facets(session, revision)
                for number, revision in REVISIONS.items()
            }

    def links() -> list[tuple[object, ...]]:
        with witness.transaction() as session:
            return sorted(
                (each.id, each.revision_id, each.predecessor_id, each.successor_id, each.lag_value)
                for each in session.scalars(select(TaskLink))
            )

    first, first_links = identifying(), links()
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    assert identifying() == first
    assert links() == first_links
    assert [len(each) for each in first.values()] == [997, 997, 1000]


def test_a_second_loading_finds_the_tasks_there_and_writes_nothing(
    witness: Database, service_database_url: str
) -> None:
    def counts() -> tuple[int, int, int]:
        with witness.transaction() as session:
            return (
                len(session.scalars(select(Node.id)).all()),
                len(session.scalars(select(TaskLink.id)).all()),
                len(session.scalars(select(TrackingEntry.id)).all()),
            )

    before = counts()
    assert load(service_database_url) == 0
    assert counts() == before
    assert before[0] == 997 + 997 + 1000


def loaded_tasks(number: int, current: int = 102) -> tuple[TaskLoad, ...]:
    """Give the tasks of a revision as the planning loads them, at the identifiers of the file."""
    del current
    return tuple(
        TaskLoad(
            node_id=UUID(task["node_id"]),
            lineage_id=UUID(task["lineage_id"]),
            parent_lineage_id=None
            if task["parent_lineage_id"] is None
            else UUID(task["parent_lineage_id"]),
            position=task["position"],
            label=task["label"],
            description=task["description"],
            scheduling_mode=task["scheduling_mode"],
            duration=Duration(Decimal(task["duration"]["value"]), task["duration"]["unit"]),
            start=WorkInstant(*instants(task["start"])),
            finish=WorkInstant(*instants(task["finish"])),
            work_package_id=None
            if task["work_package_id"] is None
            else UUID(task["work_package_id"]),
            order_item_id=None if task["order_item_id"] is None else UUID(task["order_item_id"]),
            links=tuple(
                LinkLoad(
                    UUID(link["predecessor_lineage_id"]),
                    link["link_type"],
                    Decimal(link["lag"]["value"]),
                    link["lag"]["unit"],
                )
                for link in task["predecessors"]
            ),
            progress=task["progress"],
            started_on=None
            if task["started_on"] is None
            else date.fromisoformat(task["started_on"]),
            completed_on=None
            if task["completed_on"] is None
            else date.fromisoformat(task["completed_on"]),
        )
        for task in file_tasks(number)
    )


def test_a_task_the_revision_holds_under_its_identifier_is_changed_in_place_and_the_rest_reconciled(
    witness: Database,
) -> None:
    # The revision in progress is a draft: described again with a task relabelled, one removed with
    # its subtree and one created, the others keep their rows, their identifiers and their lineage.
    tasks = loaded_tasks(102)
    leaves = [each for each in tasks if each.lineage_id not in {t.parent_lineage_id for t in tasks}]
    predecessors = {link.predecessor_lineage_id for each in tasks for link in each.links}
    relabelled = leaves[0]
    removed = next(each for each in leaves[1:] if each.lineage_id not in predecessors)
    created = replace(
        leaves[2],
        node_id=UUID("01926f3a-7c00-7000-8000-00000000f001"),
        lineage_id=UUID("01926f3a-7c00-7000-8000-00000000f101"),
        label="Tâche créée",
        position=900,
        links=(),
    )
    changed = tuple(
        replace(each, label="Libellé modifié") if each is relabelled else each
        for each in tasks
        if each is not removed
    )
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        before = {node.id: node for node, _ in rows(session, REVISION_102).values()}
        act = Act(author=None, at=instant(OPENED[102]))
        load_tasks(session, place, TasksLoad(PLANNING_START, (*changed, created)), act)
        after = rows(session, REVISION_102)
        assert len(after) == 1000
        node, facet = after[relabelled.lineage_id]
        assert (node.id, facet.label) == (relabelled.node_id, "Libellé modifié")
        assert node.id in before
        assert removed.lineage_id not in after
        assert after[created.lineage_id][0].id == created.node_id
        assert after[created.lineage_id][1].label == "Tâche créée"
        # Every other node keeps its row, which is not written again but for its counter.
        assert {n.id for n, _ in after.values()} - {created.node_id} <= set(before)


def test_a_copy_under_other_identifiers_is_written_again_under_the_ones_of_the_file(
    witness: Database,
) -> None:
    # The reference 101 is the copy of the offer 100, whose identifiers are not its own: each task
    # is written again under the identifier of the file, its lineage kept (WF-DAT-0030).
    with witness.transaction() as session:
        offer = {lineage: node.id for lineage, (node, _) in rows(session, REVISION_100).items()}
        reference = {lineage: node.id for lineage, (node, _) in rows(session, REVISION_101).items()}
    common = offer.keys() & reference.keys()
    assert len(common) == 996
    assert all(offer[each] != reference[each] for each in common)
