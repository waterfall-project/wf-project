# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the refusals the service served and the contract did not declare (US-1380/L4, #2519).

Each example ``wftools.mockservedrefusals`` writes is cited by the operation that answers it, and
says what the witness reads: the nodes it names are of the kind its refusal says, the days it
names are those the witness carries, the project the reference names is the witness.
"""

import re
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcore, mockservedrefusals
from wftools.mockwitness import N, fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"


def _operations() -> dict[str, Entry]:
    """Return every operation of the contract, by its operationId."""
    found: dict[str, Entry] = {}
    for path in sorted((API / "paths").glob("*.yaml")):
        for item in cast("dict[str, Entry]", yaml.safe_load(path.read_text("utf-8"))).values():
            for operation in item.values():
                found[operation["operationId"]] = operation
    return found


def _citing(name: str) -> list[tuple[str, str]]:
    """Return the operations and the statuses whose examples cite a file."""
    return [
        (operation, status)
        for operation, entry in _operations().items()
        for status, answer in cast("dict[str, Entry]", entry["responses"]).items()
        for content in cast("dict[str, Entry]", answer.get("content", {})).values()
        for example in cast("dict[str, Entry]", content.get("examples", {})).values()
        if cast("str", example.get("$ref", "")).endswith(f"/{name}")
    ]


CITED = {
    "node_create_parent_unknown.json": ("createNode", "422"),
    "node_create_dates_required.json": ("createNode", "422"),
    "node_create_finish_before_start.json": ("createNode", "422"),
    "node_create_kind_not_accepted.json": ("createNode", "422"),
    "node_create_facet_missing.json": ("createNode", "422"),
    "task_dates_required.json": ("updateTaskFacet", "422"),
    "task_finish_before_start.json": ("updateTaskFacet", "422"),
    "task_update_empty.json": ("updateTaskFacet", "422"),
    "nodes_move_parent_unknown.json": ("moveNodes", "422"),
    "nodes_move_node_cycle.json": ("moveNodes", "422"),
    "predecessors_unknown_task.json": ("setPredecessors", "422"),
    "task_completed_before_start.json": ("setTaskProgress", "422"),
    "import_apply_background_running.json": ("applyImport", "409"),
    "import_apply_may_create_revision.json": ("applyImport", "409"),
    "export_permission_missing.json": ("requestExport", "403"),
    "duration_units_horizon_exceeded.json": ("setDurationUnits", "422"),
    "calendar_update_horizon_exceeded.json": ("updateCalendar", "422"),
    "calendar_default_horizon_exceeded.json": ("setDefaultCalendar", "422"),
    "revision_create_horizon_exceeded.json": ("createRevision", "422"),
    "project_rate_precision.json": ("updateProject", "422"),
}


def test_the_module_writes_each_refusal_declared_and_no_other() -> None:
    assert set(mockservedrefusals.examples()) == set(CITED)


@pytest.mark.parametrize("name", sorted(CITED))
def test_every_example_is_cited_by_the_operation_that_answers_it(name: str) -> None:
    assert _citing(name) == [CITED[name]]


def _rows() -> dict[int, mockcore.Row]:
    return {row.number: row for row in mockcore.current()}


def test_the_nodes_named_where_a_task_is_expected_are_lines_of_the_witness() -> None:
    rows = _rows()
    assert rows[N.BLOCKS].kind == "estimate_line"
    assert rows[N.WIRING_ON_SITE].kind == "estimate_line"
    assert rows[N.WIRING_ON_SITE].parent == N.MOUNTING


def test_the_summary_moved_under_its_own_subordinate_holds_it() -> None:
    assert _rows()[N.WIRING].parent == N.CONTROL_STATION


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_completion_before_the_start_names_the_day_the_wiring_started() -> None:
    # « Une terminaison datée avant le démarrage de la tâche est refusée. »
    task = cast("Entry", _rows()[N.WIRING].node["task"])
    refused = cast("Entry", mockservedrefusals.gestures()["task_completed_before_start.json"])
    [field] = refused["fields"]
    assert task["progress"] == "started"
    assert field["params"]["minimum"] == task["started_on"]
    assert mockservedrefusals.COMPLETED_ON.isoformat() < task["started_on"]


def test_the_finish_entered_for_the_desks_precedes_their_start() -> None:
    task = cast("Entry", _rows()[N.DESKS].node["task"])
    refused = cast("Entry", mockservedrefusals.gestures()["task_finish_before_start.json"])
    [field] = refused["fields"]
    assert task["scheduling_mode"] == "manual"
    assert field["params"]["minimum"] == task["start"]["date"]
    assert mockservedrefusals.DESKS_FINISH.isoformat() < task["start"]["date"]


def test_the_opening_names_the_task_that_finishes_last() -> None:
    last = mockservedrefusals.last_task()
    ends = [
        cast("Entry", row.node["task"])["finish"]["date"]
        for row in mockcore.current()
        if row.kind == "task"
    ]
    assert cast("Entry", last.node["task"])["finish"]["date"] == max(ends)


def test_the_reference_names_the_witness_by_its_label_and_its_code() -> None:
    project = fixture("project")
    for name in (
        "duration_units_horizon_exceeded.json",
        "calendar_update_horizon_exceeded.json",
        "calendar_default_horizon_exceeded.json",
    ):
        refused = cast("Entry", mockservedrefusals.others()[name])
        assert refused["params"]["projects"] == [
            {"project_label": project["label"], "project_code": project["code"]}
        ]


def test_the_rate_refused_breaks_the_pattern_of_a_ratio_and_a_useless_zero_does_not() -> None:
    schemas = yaml.safe_load((API / "components/schemas/projects.yaml").read_text("utf-8"))
    pattern = re.compile(schemas["ProjectRatio"]["pattern"])
    assert not pattern.match(mockservedrefusals.RATE_SENT)
    assert all(pattern.match(each) for each in ("0", "1", "0.035", "0.1234", "0.12340"))
