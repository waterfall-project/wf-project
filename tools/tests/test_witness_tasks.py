# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the tasks of the witness written for the loader of the tasks (US-1480/L1)."""

import json
import re
from collections import Counter
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
    assert all(set(task) == KEYS for task in _value()["tasks"])


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
    for task in _value()["tasks"]:
        assert task["progress"] in {"not_started", "started", "completed"}
        assert (task["completed_on"] is not None) == (task["progress"] == "completed")
        if task["progress"] == "not_started" and not task["is_milestone"]:
            assert task["started_on"] is None
    states = Counter(task["progress"] for task in _tasks(mockchronology.CURRENT))
    assert set(states) == {"not_started", "started", "completed"}


def test_the_inscriptions_name_the_timelines_of_the_witness() -> None:
    # WF-QUA-0040-A: the inscriptions of the current revision are those of the witness.
    timelines = {identifier for identifier, _ in mockwitness.TIMELINES}
    inscribed = [entry for task in _tasks(mockchronology.CURRENT) for entry in task["inscriptions"]]
    assert {entry["timeline_id"] for entry in inscribed if entry["kind"] == "timeline"} == (
        timelines
    )
    assert [entry for entry in inscribed if entry["kind"] == "milestone_tracking"]
    assert {entry["timeline_id"] for entry in inscribed if entry["kind"] != "timeline"} == {None}


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
