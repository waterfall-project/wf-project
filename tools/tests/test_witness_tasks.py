# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the tasks of the witness written for the loader of the tasks (US-1480/L1)."""

import json
import re
from collections import Counter
from datetime import date
from typing import TYPE_CHECKING, Any

from wftools import (
    REPOSITORY,
    mockchronology,
    mockdata,
    mockhistory,
    mockstructure,
    mockwitness,
    paths,
)
from wftools import mockwitnesstasks as module

if TYPE_CHECKING:
    from wftools.mockwitness import Task

FILE = REPOSITORY / "fixtures" / "api" / module.NAME

KEYS = {
    "revision",
    "node_id",
    "lineage_id",
    "parent_lineage_id",
    "position",
    "label",
    "description",
    "is_summary",
    "is_milestone",
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "order_item_id",
    "work_package_id",
    "predecessors",
    "progress",
    "started_on",
    "completed_on",
    "inscriptions",
}

LINK_TYPES = {"finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish"}
UNITS = {"min", "h", "d", "w", "mo", "emin", "eh", "ed", "ew", "emo"}
REVISIONS = (mockchronology.OFFER, mockchronology.REFERENCE, mockchronology.CURRENT)


def _value() -> dict[str, Any]:
    return json.loads(FILE.read_text(encoding="utf-8"))["value"]


def _tasks(revision: int) -> list[dict[str, Any]]:
    return [task for task in _value()["tasks"] if task["revision"] == revision]


def test_the_tasks_are_held_by_the_check_of_make_mock_data_up_to_date() -> None:
    # WF-QUA-0040-A: the engendering yields the data announced; the file is held by the check.
    assert module.NAME in mockdata.named()
    assert module.NAME in mockdata.declared_names()
    assert FILE.read_text(encoding="utf-8") == mockdata.render(mockdata.named()[module.NAME])
    assert not [problem for problem in mockdata.check(FILE.parent) if module.NAME in problem]


def test_the_tasks_are_declared_generated_by_make_mock_data() -> None:
    # WF-QUA-0040-A: a file written by the generator is declared so, and left out of a lot's size.
    declared = [
        entry for entry in paths.read().generated if f"fixtures/api/{module.NAME}" in entry.paths
    ]
    assert [entry.by for entry in declared] == ["make mock-data"]


def test_two_engenderings_give_the_same_bytes() -> None:
    # WF-QUA-0040-A: two engenderings give identifying data that are identical.
    first = mockdata.render(module.examples()[module.NAME])
    second = mockdata.render(module.examples()[module.NAME])
    assert first == second


def test_the_revisions_are_those_of_the_chronology_with_the_planning_start() -> None:
    # WF-QUA-0040-A: the revisions 100, 101 and 102 of PRJ-001, the planning start of the structure.
    revisions = _value()["revisions"]
    assert [entry["revision"] for entry in revisions] == [
        mockchronology.OFFER,
        mockchronology.REFERENCE,
        mockchronology.CURRENT,
    ]
    assert {entry["planning_start_on"] for entry in revisions} == {
        mockwitness.PLANNING_START.isoformat()
    }
    assert [entry["task_count"] for entry in revisions] == [
        len(_tasks(entry["revision"])) for entry in revisions
    ]


def test_the_revision_in_progress_holds_the_thousand_tasks() -> None:
    # WF-QUA-0040-A: the thousand tasks of the main structure of the revision in progress.
    assert len(_tasks(mockchronology.CURRENT)) == mockstructure.TASK_COUNT
    assert len(_tasks(mockchronology.REFERENCE)) < mockstructure.TASK_COUNT
    assert len(_tasks(mockchronology.OFFER)) < mockstructure.TASK_COUNT


def test_a_task_has_exactly_the_keys_the_loader_reads() -> None:
    # WF-QUA-0040-A: a strict model of the back reads the file without importing wftools.
    for task in _value()["tasks"]:
        assert set(task) == KEYS
        assert task["scheduling_mode"] in {"automatic", "manual"}
        for amount in (task["duration"], *(link["lag"] for link in task["predecessors"])):
            assert set(amount) == {"value", "unit"}
            assert amount["unit"] in UNITS
        for moment in (task["start"], task["finish"]):
            assert set(moment) == {"date", "hours"}
            assert isinstance(moment["hours"], str)
            assert isinstance(date.fromisoformat(moment["date"]), date)
        for link in task["predecessors"]:
            assert set(link) == {"predecessor_lineage_id", "link_type", "lag"}
            assert link["link_type"] in LINK_TYPES
        for entry in task["inscriptions"]:
            assert set(entry) == {"kind", "timeline_id"}
            assert entry["kind"] in {"timeline", "milestone_tracking"}
        for key in ("started_on", "completed_on"):
            assert task[key] is None or isinstance(date.fromisoformat(task[key]), date)


def test_the_lineages_are_unique_by_revision_and_shared_by_the_revisions() -> None:
    # WF-QUA-0040-A: a lineage is what the revisions share; the offer's are the current's.
    lineages = {
        revision: [task["lineage_id"] for task in _tasks(revision)]
        for revision in (mockchronology.OFFER, mockchronology.REFERENCE, mockchronology.CURRENT)
    }
    assert all(len(found) == len(set(found)) for found in lineages.values())
    current = set(lineages[mockchronology.CURRENT])
    # The preliminary trials on site, which the amendment 1 removed, are the offer's alone.
    assert set(lineages[mockchronology.OFFER]) - current == {
        mockwitness.lineage_id(mockwitness.N.SITE_TRIALS)
    }
    assert set(lineages[mockchronology.REFERENCE]) <= current


def test_a_parent_comes_before_its_children_and_the_ranks_are_ordered() -> None:
    # WF-QUA-0040-A: the tasks are in the order of the plan, the parent by its lineage.
    for revision in (mockchronology.OFFER, mockchronology.REFERENCE, mockchronology.CURRENT):
        seen: set[str] = set()
        ranks: dict[str | None, list[int]] = {}
        for task in _tasks(revision):
            assert task["parent_lineage_id"] is None or task["parent_lineage_id"] in seen
            seen.add(task["lineage_id"])
            ranks.setdefault(task["parent_lineage_id"], []).append(task["position"])
        assert all(found == sorted(set(found)) for found in ranks.values())


def test_the_links_name_a_predecessor_of_the_same_revision() -> None:
    # WF-QUA-0040-A: the links, by the lineage of their predecessor.
    for revision in (mockchronology.OFFER, mockchronology.REFERENCE, mockchronology.CURRENT):
        tasks = _tasks(revision)
        lineages = {task["lineage_id"] for task in tasks}
        links = [link for task in tasks for link in task["predecessors"]]
        assert links
        assert all(link["predecessor_lineage_id"] in lineages for link in links)
        assert {link["link_type"] for link in links} >= {"finish_to_start"}


def test_the_states_and_their_dates_agree() -> None:
    # WF-QUA-0040-A: a completed task says when it completed, a task not started, neither.
    read_on = {entry["revision"]: entry["read_on"] for entry in _value()["revisions"]}
    for task in _value()["tasks"]:
        assert task["progress"] in {"not_started", "started", "completed"}
        assert (task["completed_on"] is not None) == (task["progress"] == "completed")
        if task["progress"] == "not_started" and not task["is_milestone"]:
            assert task["started_on"] is None
        if task["progress"] in {"started", "completed"}:
            assert task["started_on"] is not None
        if task["completed_on"] is not None:
            assert task["started_on"] <= task["completed_on"]
        for key in ("started_on", "completed_on"):
            # ISO dates compare as text; none is after the day its revision is read at.
            assert task[key] is None or task[key] <= read_on[task["revision"]]
    states = Counter(task["progress"] for task in _tasks(mockchronology.CURRENT))
    assert set(states) == {"not_started", "started", "completed"}


def test_the_inscriptions_name_the_timelines_of_the_witness() -> None:
    # WF-QUA-0040-A: the inscriptions of every revision name the timelines the loader will read.
    file = json.loads((FILE.parent / "timelines.json").read_text(encoding="utf-8"))
    timelines = {entry["timeline_id"] for entry in file["value"]}
    assert timelines == {identifier for identifier, _ in mockwitness.TIMELINES}
    for revision in REVISIONS:
        inscribed = [entry for task in _tasks(revision) for entry in task["inscriptions"]]
        named = {entry["timeline_id"] for entry in inscribed if entry["kind"] == "timeline"}
        assert named <= timelines
        assert [entry for entry in inscribed if entry["kind"] == "milestone_tracking"]
        assert {entry["timeline_id"] for entry in inscribed if entry["kind"] != "timeline"} == {
            None
        }
    current = [e for t in _tasks(mockchronology.CURRENT) for e in t["inscriptions"]]
    assert {e["timeline_id"] for e in current if e["kind"] == "timeline"} == timelines


def test_the_dates_are_those_of_the_planning_example() -> None:
    # WF-QUA-0040-A: the computed is the expected; the planning example reads the same dates.
    planning = json.loads((FILE.parent / "nodes_planning.json").read_text(encoding="utf-8"))
    nodes = {node["lineage_id"]: node for node in planning["value"]["items"] if "task" in node}
    current = {task["lineage_id"]: task for task in _tasks(mockchronology.CURRENT)}
    assert nodes
    for lineage, node in nodes.items():
        facet = node["task"]
        assert current[lineage]["start"] == facet["start"]
        assert current[lineage]["finish"] == facet["finish"]
        assert current[lineage]["progress"] == facet["progress"]


def _differing(revision: int) -> dict[str, dict[str, Any]]:
    """Give the tasks of a revision whose dates are not the current's, by lineage."""
    current = {task["lineage_id"]: task for task in _tasks(mockchronology.CURRENT)}
    return {
        task["lineage_id"]: task
        for task in _tasks(revision)
        if task["lineage_id"] in current
        and (task["start"], task["finish"])
        != (current[task["lineage_id"]]["start"], current[task["lineage_id"]]["finish"])
    }


def test_the_dates_of_the_reference_are_those_of_the_current() -> None:
    # WF-QUA-0040-A: the dates of 101 come from the history rows, not from the engine; they are held
    # to the revision in progress, which the planning example holds to the engine.
    assert not _differing(mockchronology.REFERENCE)


def test_the_dates_of_the_offer_differ_from_the_current_only_by_the_amendment() -> None:
    # WF-QUA-0040-A: the offer lengthened by the amendment 1: the detailed design file finished on
    # the 13th. The preliminary trials on site the amendment removed are the offer's alone, so
    # the current cannot hold their dates: the loading, where the engine computes them, does
    # (backend `test_witness_tasks.py`).
    current = {task["lineage_id"]: task for task in _tasks(mockchronology.CURRENT)}
    differing = _differing(mockchronology.OFFER)
    assert {task["label"] for task in differing.values()} == {"Dossier de conception"}
    for lineage, task in differing.items():
        assert task["start"] == current[lineage]["start"]
        assert task["finish"] == {"date": "2026-04-13", "hours": "8"}
        assert current[lineage]["finish"] == {"date": "2026-04-15", "hours": "8"}
    alone = [task for task in _tasks(mockchronology.OFFER) if task["lineage_id"] not in current]
    trials = mockwitness.lineage_id(mockwitness.N.SITE_TRIALS)
    assert [task["lineage_id"] for task in alone] == [trials]


def test_no_address_and_no_real_label_figure_in_the_file() -> None:
    # WF-QUA-0040-A: no electronic address, and the labels are those of the witness.
    text = FILE.read_text(encoding="utf-8")
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    labels = {task["label"] for task in _value()["tasks"]}
    assert labels <= _witness_labels()
    assert "Études de détail" in labels


def _witness_labels() -> set[str]:
    found: set[str] = set()

    def gather(task: Task) -> None:
        found.add(task.label)
        for child in task.children:
            gather(child)

    for root in (*mockstructure.described(), mockhistory.SITE_TRIALS):
        gather(root)
    return found
