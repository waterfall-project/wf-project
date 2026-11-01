# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the refusals declared without a code, a condition nor an example (US-0702/L2, #1611).

The review of the contract before the freeze (D-03, D-10, E-05, E-12 to E-14, E-24, F-03, F-04,
F-11, H-05, H-08, I-06, I-17, A-05, C-01) and the decision of the author of the 2026-10-28 on the
counter: each refusal has its code or its condition, said by its operation, and an example
``wftools.mockdeclared`` writes; the five writes it names carry the counter. A test cites a
requirement where it takes up its Vérif.
"""

import json
import re
from decimal import Decimal
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcore, mockdeclared, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import N, fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
STATE = (409, "STATE_FORBIDS_OPERATION")


def _operations() -> dict[str, Entry]:
    """Return every operation of the contract, by its operationId."""
    found: dict[str, Entry] = {}
    for path in sorted((API / "paths").glob("*.yaml")):
        for item in cast("dict[str, Entry]", yaml.safe_load(path.read_text("utf-8"))).values():
            for operation in item.values():
                found[operation["operationId"]] = operation
    return found


def _cited(operation: str, status: str) -> list[str]:
    """Return the examples a status of an operation cites, by their file name, in their order."""
    answer = _operations()[operation]["responses"][status]
    examples = answer["content"]["application/problem+json"]["examples"]
    return [re.sub(r".*/(\w+)\.json$", r"\1", each["$ref"]) for each in examples.values()]


def _schemas(family: str) -> Entry:
    path = API / "components" / "schemas" / f"{family}.yaml"
    return cast("Entry", yaml.safe_load(path.read_text("utf-8")))


@pytest.mark.parametrize("name", sorted(mockdeclared.examples()))
def test_every_example_of_the_module_is_cited_by_an_operation(name: str) -> None:
    cited = [
        operation
        for operation, entry in _operations().items()
        for answer in cast("dict[str, Entry]", entry["responses"]).values()
        for content in cast("dict[str, Entry]", answer.get("content", {})).values()
        for example in cast("dict[str, Entry]", content.get("examples", {})).values()
        if cast("str", example.get("$ref", "")).endswith(f"/{name}")
    ]
    assert cited


# --- A state refused by its condition (D-03, E-12 to E-14, F-04, F-11, I-06, A-05) ------------

REFUSED = {
    "project_exit_terminal": ("exitProject", "project_not_terminal"),
    "project_exit_lost_in_progress": ("exitProject", "project_in_pricing"),
    "mark_revision_marked": ("markRevision", "revision_draft"),
    "revision_abandon_marked": ("abandonRevision", "revision_draft"),
    "structure_create_revision_marked": ("createCostStructure", "revision_draft"),
    "revision_create_background_running": ("createRevision", "no_background_task_running"),
    "node_tracking_marked_refused": ("setNodeTracking", "revision_draft"),
    "actual_cost_scope_terminal": ("setActualCostTrackedScope", "project_not_terminal"),
    "task_result_not_succeeded": ("getBackgroundTaskResult", "task_succeeded"),
}


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_state_is_refused_by_the_condition_the_operation_says(name: str) -> None:
    operation, condition = REFUSED[name]
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == STATE
    assert refused["params"] == {"missing_condition": condition}
    assert name in _cited(operation, "409")
    assert f"`{condition}`" in _operations()[operation]["responses"]["409"]["description"]


def _commands(holder: Entry) -> dict[str, list[str]]:
    return {
        each["command"]: each["missing_conditions"]
        for each in cast("list[Entry]", holder["available_commands"])
    }


def test_the_conditions_refused_are_the_ones_the_objects_say_beforehand() -> None:
    marked = _commands(fixture("revision_marked"))
    assert marked["mark"] == marked["abandon"] == marked["create_structure"] == ["revision_draft"]
    # A terminal project lists no command, not even unavailable: none would ever become available
    # (US-0702/L3); its refusals name `project_not_terminal` all the same.
    assert _commands(fixture("project_completed")) == {}
    assert "lose" not in _commands(fixture("project"))


@pytest.mark.requirement("WF-CYC-0080-A")
def test_an_exit_from_a_terminal_project_is_refused() -> None:
    # Vérif : « Toute tentative de transition depuis Terminé, Perdu ou Abandonné est refusée. »
    refused = fixture("project_exit_terminal")
    assert refused["params"] == {"missing_condition": "project_not_terminal"}
    assert fixture("project_completed")["state"] == "completed"


@pytest.mark.requirement("WF-CYC-0090-A")
def test_an_exit_without_its_confirmation_is_refused_by_its_code() -> None:
    # D-03: `confirmed` absent or false is a 400, as for the restoration (B-09).
    refused = fixture("project_exit_unconfirmed")
    assert (refused["status"], refused["code"]) == (400, "CONFIRMATION_REQUIRED")
    assert set(refused) == {"code", "status", "correlation_id"}
    assert _cited("exitProject", "400") == ["project_exit_unconfirmed"]


@pytest.mark.requirement("WF-PLA-0070-A")
def test_the_deletion_of_a_started_task_is_refused_by_naming_its_condition() -> None:
    # Vérif : « La suppression d'une tâche démarrée est refusée, et l'utilisateur est renvoyé vers
    # la mise à zéro de son reste à engager. » The condition is what the screen sends him by.
    [wiring] = [each for each in fixture("nodes_core")["items"] if each["node_id"] == universe(552)]
    assert wiring["task"]["progress"] == "started"
    refused = fixture("node_delete_started_refused")
    assert refused["params"] == {"missing_condition": "task_not_started"}
    description = _operations()["deleteNode"]["description"]
    assert "coût réel" not in description
    assert "démarrée ou terminée" in description


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_deletion_that_would_leave_a_provision_without_a_task_names_the_risks() -> None:
    # H-05, WF-RIS-0010: « la suppression de la dernière tâche d'une structure principale qui
    # porte une ligne de provision est refusée en nommant le risque ».
    refused = fixture("node_delete_last_provision_task_refused")
    assert (refused["status"], refused["code"]) == STATE
    assert refused["params"] == {
        "missing_condition": "at_least_one_task",
        "risks": [{"risk_id": universe(751), "label": "Risque de reprise du câblage"}],
    }
    assert _cited("deleteNode", "409") == [
        "node_delete_started_refused",
        "node_delete_last_provision_task_refused",
    ]


# --- A field refused by its motive (E-05, E-12, F-03, F-11) -----------------------------------


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_marking_under_a_version_name_already_borne_is_refused() -> None:
    # Vérif : « Le marquage d'une révision sous un nom de version déjà employé dans le projet est
    # refusé. » The marking, and the merge, which marks the revision.
    for operation, name in (
        ("markRevision", "mark_version_name_taken"),
        ("mergeCostStructure", "merge_version_name_taken"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == (409, "ALREADY_EXISTS"), name
        assert refused["fields"] == [
            {
                "pointer": "/version_name",
                "code": "ALREADY_EXISTS",
                "params": {"conflicting_object_id": universe(101)},
            }
        ], name
        assert name in _cited(operation, "409"), name


@pytest.mark.parametrize(
    ("operation", "name", "pointer", "code"),
    [
        pytest.param(
            "setPredecessors",
            "predecessors_duplicate",
            "/predecessors/1/predecessor_node_id",
            "DUPLICATE_PREDECESSOR",
            marks=pytest.mark.requirement("WF-PLA-0030-A"),
        ),
        (
            "setNodeTracking",
            "node_tracking_timeline_required",
            "/entries/0/timeline_id",
            "VALUE_REQUIRED",
        ),
        (
            "setNodeTracking",
            "node_tracking_timeline_unknown",
            "/entries/0/timeline_id",
            "UNKNOWN_TIMELINE",
        ),
    ],
)
def test_a_field_is_refused_by_its_motive(
    operation: str, name: str, pointer: str, code: str
) -> None:
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [{"pointer": pointer, "code": code}]
    assert name in _cited(operation, "422")


def test_a_tracking_entry_says_its_rule() -> None:
    entry = _schemas("revisions")["TrackingEntry"]
    said = entry["properties"]["timeline_id"]["description"]
    assert "VALUE_REQUIRED" in said
    assert "UNKNOWN_TIMELINE" in said
    assert "FIELD_NOT_ACCEPTED" in said
    assert "répétée" in entry["description"]


# --- The reference, the lists and the operations without a cause (C-01, D-10, I-17) -----------


@pytest.mark.parametrize(
    ("operation", "name", "permission"),
    [
        ("listOrgNodes", "org_nodes_inactive_forbidden", "resource_settings.write"),
        ("listCalendars", "calendars_inactive_forbidden", "resource_settings.write"),
        ("listCostTypes", "cost_types_inactive_forbidden", "cost_settings.write"),
    ],
)
@pytest.mark.requirement("WF-REF-0150-A")
def test_the_deactivated_objects_of_a_list_are_refused_without_their_permission(
    operation: str, name: str, permission: str
) -> None:
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (403, "PERMISSION_MISSING")
    assert refused["params"] == {"missing_permission": permission}
    assert _cited(operation, "403") == [name]
    assert "refusés par 403" in _operations()[operation]["description"]


def test_a_subproject_created_declares_the_404_and_an_export_no_409() -> None:
    assert "404" in _operations()["createSubproject"]["responses"]
    assert "409" not in _operations()["requestExport"]["responses"]


# --- The counter of the concurrent writes (decision of the author of the 2026-10-28) ----------

IN_QUERY = ("abandonRevision", "deleteRisk", "deleteSubproject")
IN_BODY = {"exitProject": "ProjectExit", "designateReferenceRevision": "ReferenceDesignation"}


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_five_writes_require_their_counter_and_declare_the_412() -> None:
    operations = _operations()
    for name in IN_QUERY:
        [counter] = [
            each
            for each in cast("list[Entry]", operations[name]["parameters"])
            if each.get("name") == "lock_version"
        ]
        assert (counter["in"], counter["required"]) == ("query", True), name
    schemas = {**_schemas("projects"), **_schemas("revisions")}
    for name, schema in IN_BODY.items():
        assert "lock_version" in schemas[schema]["required"], name
    for name in (*IN_QUERY, *IN_BODY):
        assert "412" in operations[name]["responses"], name
    # The deletions have no body: a counter absent or malformed is the 422 they share.
    for name in (*IN_QUERY, "deleteNode"):
        assert operations[name]["responses"]["422"] == {
            "$ref": "../components/responses.yaml#/LockVersionInvalid"
        }, name
        assert "requestBody" not in operations[name], name


def test_the_tracked_scope_stays_idempotent_without_a_counter_and_says_it() -> None:
    operation = _operations()["setActualCostTrackedScope"]
    assert "412" not in operation["responses"]
    assert "Une écriture sans compteur" in operation["description"]
    schema = _schemas("costs")["ScopeExclusion"]
    assert "lock_version" not in schema.get("properties", {})


@pytest.mark.requirement("WF-PLA-0070-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_task_deleted_leaves_its_provision_on_its_parent_task_and_the_quote_unchanged() -> None:
    # WF-PLA-0070: the provision lines of a task deleted are not deleted, they pass on another
    # task (WF-RIS-0010: the total of the quote is unchanged). The risk, not part of
    # `NodesWritten`, is read through getRisk; the line it bears is written one version further.
    moved = cast("Entry", fixture("node_deleted_provision_moved"))
    before, after = (cast("Entry", each) for each in mockdeclared.provision_readings())
    [line] = cast("list[Entry]", moved["nodes"])
    assert line["node_id"] == universe(N.PROVISION)
    assert line["kind"] == "estimate_line"
    assert line["parent_id"] == universe(N.INSTALLATION)
    ancestors = cast("list[Entry]", moved["ancestors"])
    assert [node["node_id"] for node in ancestors] == [universe(N.INSTALLATION)]
    # The mounting takes its two lines with it, 12 600,00 for 160 h; the provision stays (#1768).
    totals = cast("Entry", moved["totals"])
    assert Decimal(before["totals"]["base_amount"]) - Decimal(totals["base_amount"]) == Decimal(
        "12600.00"
    )
    assert Decimal(before["totals"]["hours"]) - Decimal(totals["hours"]) == 160
    assert totals["estimate_line_count"] == before["totals"]["estimate_line_count"] - 2
    assert totals == after["totals"]
    [was] = [node for node in before["items"] if node["node_id"] == line["node_id"]]
    assert was["parent_id"] == universe(N.MOUNTING)
    assert line["lock_version"] == was["lock_version"] + 1
    assert universe(N.MOUNTING) not in {node["node_id"] for node in after["items"]}
    assert "provision_moved" in _cited_ok("deleteNode")
    assert "écrites sous" in _operations()["deleteNode"]["responses"]["200"]["description"]


def _cited_ok(operation: str) -> list[str]:
    """Return the examples the 200 of an operation cites, by their name in the contract."""
    answer = _operations()[operation]["responses"]["200"]
    return list(answer["content"]["application/json"]["examples"])


def test_a_task_left_without_a_predecessor_keeps_its_progress() -> None:
    # #1768 (F-02): the commissioning, which followed the mounting deleted, goes back to the start
    # of the planning, in the past, not started still; its summary keeps its progress with it.
    moved = cast("Entry", fixture("node_deleted_provision_moved"))
    [placed] = [
        entry for entry in moved["rescheduled"] if entry["node_id"] == universe(N.COMMISSIONING)
    ]
    assert placed["start"]["date"] == "2026-03-02"
    read = _witness()
    assert read[universe(N.COMMISSIONING)]["task"]["progress"] == "not_started"
    [installation] = moved["ancestors"]
    assert installation["task"]["progress"] == "not_started"
    assert "started_on" not in installation["task"]
    said = " ".join(_operations()["deleteNode"]["description"].split())
    assert "sans changer d'état" in said


def test_no_write_generated_changes_the_progress_of_a_task() -> None:
    # #1768 (F-02): the invariant of the witness extends to every task, started or not — no
    # write generated but the gestures of the Kanban changes the progress of a task it renders,
    # nor redates a task started or completed (WF-RAE-0030, WF-PLA-0130). Each answer of a write
    # of the grids is held to the reading of the witness, the nodes it shares with it.
    gestures = set(_cited_ok("setTaskProgress"))
    read = _witness()
    tried = 0
    for path in sorted(mockwitness.FIXTURES.glob("*.json")):
        loaded: object = json.loads(path.read_text(encoding="utf-8"))["value"]
        if not isinstance(loaded, dict):
            continue
        value = cast("Entry", loaded)
        if not {"nodes", "ancestors", "rescheduled"} <= set(value):
            continue
        if path.stem in {_example_file(name) for name in gestures}:
            continue
        tried += 1
        for node in [*value["nodes"], *value["ancestors"]]:
            if node["kind"] == "task" and node["node_id"] in read:
                was = read[node["node_id"]]["task"]["progress"]
                assert node["task"]["progress"] == was, (path.name, node["node_id"])
        for entry in value["rescheduled"]:
            if entry["node_id"] in read:
                was = read[entry["node_id"]]["task"]
                if was["progress"] != "not_started":
                    assert (entry["start"], entry["finish"]) == (was["start"], was["finish"])
    assert tried > 30


def _witness() -> dict[str, Entry]:
    """Return the nodes of the witness read whole today, by identifier."""
    items = cast("list[Entry]", mockcore.whole(mockcore.current())["items"])
    return {node["node_id"]: node for node in items}


def _example_file(name: str) -> str:
    """Return the file an example of setTaskProgress names, from its name in the contract."""
    answer = _operations()["setTaskProgress"]["responses"]["200"]
    ref = answer["content"]["application/json"]["examples"][name]["$ref"]
    return re.sub(r".*/(\w+)\.json$", r"\1", ref)
