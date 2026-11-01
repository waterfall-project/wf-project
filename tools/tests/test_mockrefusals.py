# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the refusals of one form each, and of their examples (US-0702/L1, #1610).

The review of the contract before the freeze (D-05, J-01, J-02) and the decision of the author of
the 2026-10-28: a terminal project and a marked revision are refused everywhere by the 409 of
their condition, as the object says it beforehand. The tests hold the contract and the examples
``wftools.mockrefusals`` writes; a test cites a requirement where it takes up its Vérif.
"""

import json
import re
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockrefusals, mockwitness, mockwrites
from wftools.mockids import universe
from wftools.mockwitness import CABLE_FITTER, ENGINEER, fixture

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


def _commands(holder: Entry) -> dict[str, list[str]]:
    return {
        each["command"]: each["missing_conditions"]
        for each in cast("list[Entry]", holder["available_commands"])
    }


def test_a_terminal_project_refuses_its_timelines_by_the_condition_it_misses() -> None:
    # It lists no command any more, `manage_timelines` included (US-0702/L3): the call sent all
    # the same is refused by the condition, as any write of a terminal project.
    assert _commands(fixture("project_completed")) == {}
    for operation, name in (
        ("createTimeline", "timeline_create_terminal"),
        ("deleteTimeline", "timeline_delete_terminal"),
        ("designateReferenceRevision", "reference_designation_terminal"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": "project_not_terminal"}, name
        assert name in _cited(operation, "409"), name
    # The delete answers the shared 403 now, which names the qualities alone.
    assert "403" in _operations()["deleteTimeline"]["responses"]


def test_the_designation_on_a_terminal_project_names_its_condition_before_the_command() -> None:
    # #1674 (option 2 of the author): the 409 of `designateReferenceRevision` names
    # `project_not_terminal` too, judged before the conditions `designate_reference` lists, so that
    # the single rule of the refusals of US-0702 holds without an exception.
    answer = _operations()["designateReferenceRevision"]["responses"]["409"]
    said = " ".join(answer["description"].split())
    assert said.index("`project_not_terminal`") < said.index("`revision_marked`")
    # The terminal-project example is cited last on that 409 (#1674).
    assert _cited("designateReferenceRevision", "409")[-1] == "reference_designation_terminal"
    # The schemas that list the commands say it too (#1674).
    schemas = API / "components" / "schemas"
    projects = " ".join((schemas / "projects.yaml").read_text("utf-8").split())
    revisions = " ".join((schemas / "revisions.yaml").read_text("utf-8").split())
    assert "sur un projet terminal, il nomme d'abord `project_not_terminal` (#1674)" in projects
    assert "`project_not_terminal` d'abord sur un projet terminal" in revisions


def test_a_marked_revision_refuses_a_task_created_and_the_skeleton_by_revision_draft() -> None:
    commands = _commands(fixture("revision_marked"))
    assert commands["edit_planning"] == commands["generate_skeleton"] == ["revision_draft"]
    for operation, name in (
        ("createNode", "node_create_marked_refused"),
        ("generatePlanningSkeleton", "skeleton_marked_refused"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": "revision_draft"}, name
        assert name in _cited(operation, "409"), name
    assert fixture("revision_marked")["revision_id"] == mockrefusals.REFERENCE


def test_no_state_has_a_code_of_its_own_and_no_403_says_a_state() -> None:
    common = yaml.safe_load((API / "components" / "common.yaml").read_text("utf-8"))
    codes = common["ErrorCode"]["enum"]
    assert "PROJECT_TERMINAL" not in codes
    assert "REVISION_MARKED" not in codes
    forbidden = yaml.safe_load((API / "components" / "responses.yaml").read_text("utf-8"))
    said = forbidden["Forbidden"]["description"]
    assert "jamais par 403" in said
    assert "NOT_PROJECT_MANAGER" in said
    readme = (API / "README-fr.md").read_text("utf-8")
    assert "Le refus d'une commande qu'un état rend indisponible est un 409" in readme
    for path in sorted((API / "paths").glob("*.yaml")):
        text = path.read_text("utf-8")
        assert not re.search(r"(terminal|marquée)[^.]{0,80}par 403", text), path.name


def _shared() -> dict[str, Entry]:
    return cast(
        "dict[str, Entry]",
        yaml.safe_load((API / "components" / "responses.yaml").read_text("utf-8")),
    )


@pytest.mark.parametrize("name", sorted(mockrefusals.examples()))
def test_every_example_of_the_module_is_cited_by_an_operation(name: str) -> None:
    answers = [
        answer
        for operation in _operations().values()
        for answer in cast("dict[str, Entry]", operation["responses"]).values()
    ]
    cited = [
        example["$ref"]
        for answer in [*answers, *_shared().values()]
        if "content" in answer
        for content in cast("dict[str, Entry]", answer["content"]).values()
        for example in cast("dict[str, Entry]", content.get("examples", {})).values()
        if cast("str", example.get("$ref", "")).endswith(f"/{name}")
    ]
    assert cited


def test_every_operation_declares_the_unexpected_error_with_its_correlation() -> None:
    # J-07: the 500 is declared, by one shared answer, with its correlation (WF-OBS-0020).
    shared = "../components/responses.yaml#/InternalError"
    undeclared = [
        name
        for name, operation in _operations().items()
        if operation["responses"].get("500") != {"$ref": shared}
    ]
    assert undeclared == []
    [example] = _shared()["InternalError"]["content"]["application/problem+json"]["examples"]
    assert example == "internal_error"
    error = fixture("internal_error")
    assert (error["status"], error["code"]) == (500, "INTERNAL_ERROR")
    assert set(error) == {"code", "status", "correlation_id"}


def test_an_unknown_property_of_fields_is_refused_by_422_as_any_parameter_of_a_query() -> None:
    # J-10: no reading of the contract answers 400 for a parameter of its query.
    refused = fixture("nodes_fields_unknown")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [{"pointer": "/query/fields", "code": "FIELD_NOT_ACCEPTED"}]
    for operation in ("listNodes", "compareRevisions"):
        assert "400" not in _operations()[operation]["responses"], operation
        assert "nodes_fields_unknown" in _cited(operation, "422"), operation
    parameters = yaml.safe_load((API / "components" / "parameters.yaml").read_text("utf-8"))
    assert "(400)" not in parameters["NodeFields"]["description"]


# --- The catalogue: every code rendered by an operation, with an example (J-03, J-06, J-11) ----


def test_the_project_manager_quality_is_refused_by_its_code_as_the_command_said_it() -> None:
    commands = _commands(fixture("project_participant"))
    assert commands["update"][0] == "is_project_manager"
    refused = fixture("project_update_not_manager")
    assert (refused["status"], refused["code"]) == (403, "NOT_PROJECT_MANAGER")
    assert refused["params"] == {"missing_condition": "is_project_manager"}
    assert _cited("updateProject", "403") == [
        "project_update_not_manager",
        "project_update_not_contributor",
    ]
    not_contributor = fixture("project_update_not_contributor")
    assert (not_contributor["status"], not_contributor["code"]) == (403, "NOT_CONTRIBUTOR")
    assert not_contributor["params"] == {"missing_condition": "is_contributor"}


def test_the_codes_the_catalogue_named_without_an_example_are_carried_by_their_operation() -> None:
    # J-17: each code rendered by an operation is carried by an example that operation cites.
    carried = {
        "getMe": ("401", ["account_deactivated", "account_not_admitted"]),
        "putMyAvatar": ("400", ["avatar_malformed"]),
        "listAccessRoles": ("422", ["access_roles_number_invalid", "access_roles_date_invalid"]),
        "createResourceRole": ("422", ["resource_role_calendar_unknown"]),
    }
    for operation, (status, names) in carried.items():
        assert set(names) <= set(_cited(operation, status)), operation
    assert "avatar_too_large" in _cited("putMyAvatar", "413")
    shared = _shared()["Unauthorized"]["content"]["application/problem+json"]["examples"]
    assert "session_required" in shared
    codes = {
        "import_actual_costs_wbs_invalid": "WBS_ELEMENT_INVALID",
        "import_remaining_ambiguous_label": "AMBIGUOUS_TASK_LABEL",
    }
    served = _operations()["getImport"]["responses"]["200"]["content"]["application/json"]
    cited = [each["$ref"] for each in served["examples"].values()]
    for name, code in codes.items():
        assert any(each.endswith(f"/{name}.json") for each in cited), name
        [rejected] = fixture(name)["report"]["rejected"]
        assert rejected["code"] == code


@pytest.mark.requirement("WF-PRJ-0010-A")
def test_a_project_without_its_code_does_not_pass_in_progress_and_the_condition_is_named() -> None:
    # Vérif : « Le projet ne passe pas à En cours tant qu'il n'est pas renseigné, et la condition
    # manquante est nommée (WF-CYC-0050). »
    without = fixture("next_state_pricing_without_code")
    assert (without["current_state"], without["next_state"]) == ("pricing", "in_progress")
    assert without["trigger"] == "reference_designated_and_code_set"
    assert without["missing_conditions"] == ["project_code_set"]


def _core() -> list[Entry]:
    return cast("list[Entry]", fixture("nodes_core")["items"])


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_undo_of_a_change_another_contributor_took_up_since_names_the_object_in_conflict() -> (
    None
):
    # Vérif : « L'annulation d'une modification qu'un autre contributeur a depuis reprise est
    # refusée en nommant l'objet en conflit. »
    [line] = [each for each in _core() if each["node_id"] == universe(553)]
    for operation, name in (
        ("undoLastChange", "undo_later_change"),
        ("redoLastUndo", "redo_later_change"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == (409, "UNDO_CONFLICT"), name
        assert refused["params"] == {
            "conflicting_object_id": line["node_id"],
            "conflicting_object_label": line["estimate_line"]["label"],
        }, name
        assert name in _cited(operation, "409"), name
    for operation, name, condition in (
        ("undoLastChange", "undo_history_empty", "undo_history_not_empty"),
        ("redoLastUndo", "redo_history_empty", "redo_history_not_empty"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": condition}, name
        assert name in _cited(operation, "409"), name


def _subordinates(label: str) -> list[str]:
    """Return the direct subordinates of a summary of the witness, found by its label."""
    tasks = [each for each in _core() if each["kind"] == "task"]
    [summary] = [each for each in tasks if each["task"]["label"] == label]
    return [each["node_id"] for each in tasks if each["parent_id"] == summary["node_id"]]


@pytest.mark.requirement("WF-IHM-0030-A")
def test_the_finish_of_a_summary_entered_is_refused_by_naming_its_subordinates() -> None:
    # Vérif : « La tentative de modifier la date de fin d'une tâche récapitulative est refusée en
    # nommant ses subordonnées. »
    refused = fixture("task_summary_date_refused")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [
        {
            "pointer": "/finish",
            "code": "SUMMARY_TASK_DERIVED",
            "params": {"subordinate_node_ids": _subordinates("Poste de commande")},
        }
    ]
    assert "task_summary_date_refused" in _cited("updateTaskFacet", "422")


def test_the_state_of_a_summary_entered_is_refused_by_naming_its_subordinates() -> None:
    # WF-PLA-0040 : « son état n'est pas saisissable » (F-05).
    below = _subordinates("Études")
    refused = fixture("task_progress_summary_refused")
    assert (refused["status"], refused["code"]) == (422, "SUMMARY_TASK_DERIVED")
    assert refused["params"] == {"subordinate_node_ids": below}
    assert len(below) > 1
    assert _cited("setTaskProgress", "422") == ["task_progress_summary_refused"]


@pytest.mark.requirement("WF-DEV-0010-A")
def test_an_entry_and_a_marking_without_a_rate_are_refused_by_naming_the_categories() -> None:
    # Vérif : « Le refus énumère les catégories de coût sans taux horaire pour l'année de
    # référence. » The categories the missing rates list, on an entry and on a marking.
    missing = fixture("missing_rates")
    refused = fixture("estimate_line_rate_missing")
    assert (refused["status"], refused["code"]) == (422, "HOURLY_RATE_MISSING")
    assert refused["params"] == {"missing_rates": missing}
    assert "fields" not in refused
    failed = fixture("task_failed")
    assert (failed["kind"], failed["status"]) == ("revision_mark", "failed")
    assert failed["problem"]["params"] == {"missing_rates": missing}
    role = fixture("estimate_line_role_required")
    assert role["fields"] == [{"pointer": "/resource_role_id", "code": "RESOURCE_ROLE_REQUIRED"}]
    cited = _cited("updateEstimateLine", "422")
    assert {"estimate_line_rate_missing", "estimate_line_role_required"} <= set(cited)


# --- The refusals of the common tree declared without an example (F-17, #1648) ----------------


def _node(number: int) -> Entry:
    [node] = [each for each in _core() if each["node_id"] == universe(number)]
    return node


def test_a_field_a_node_does_not_accept_is_refused_on_it_as_the_node_says() -> None:
    milestone, labour = _node(556), _node(553)
    assert milestone["task"]["is_milestone"]
    assert "task.duration" not in milestone["editable_fields"]
    assert "estimate_line.unit_disbursement" not in labour["editable_fields"]
    for operation, name, pointer in (
        ("createNode", "node_create_field_not_accepted", "/estimate_line/unit_disbursement"),
        ("updateTaskFacet", "task_milestone_duration_refused", "/duration"),
        ("updateEstimateLine", "estimate_line_field_not_accepted", "/unit_disbursement"),
    ):
        refused = fixture(name)
        assert refused["fields"] == [{"pointer": pointer, "code": "FIELD_NOT_ACCEPTED"}], name
        assert name in _cited(operation, "422"), name
    reserved = fixture("estimate_line_provision_reserved")
    assert reserved["fields"] == [
        {"pointer": "/cost_category_id", "code": "PROVISION_CATEGORY_RESERVED"}
    ]
    assert "estimate_line_provision_reserved" in _cited("updateEstimateLine", "422")


def _named(identifiers: list[str]) -> list[Entry]:
    """Return roles of the reference as a refusal names them, read from the roles by hand."""
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    return [
        {key: roles[each][key] for key in ("resource_role_id", "code", "label")}
        for each in identifiers
    ]


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_line_that_would_leave_its_task_without_hours_names_the_roles_and_the_task() -> None:
    # #1684 (option A of the author): the refusal names the roles by their label, as it names the
    # task, so that the planning, which reads no role, names them too.
    wiring = _node(552)
    for operation, name, roles in (
        ("createNode", "node_create_without_hours", [451, 454]),
        ("updateEstimateLine", "estimate_line_without_hours", [454]),
        # A line of the commissioning technician moved under the wiring, beside the engineer's,
        # names both roles, as the Vérif of WF-PLA-0010 says (#779).
        ("moveNodes", "nodes_move_without_hours", [451, 452]),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == (422, "TASK_WITHOUT_WORKING_HOURS"), name
        assert refused["params"] == {
            "resource_roles": _named([universe(each) for each in roles]),
            "tasks": [
                {
                    "project_id": fixture("project")["project_id"],
                    "node_id": wiring["node_id"],
                    "label": wiring["task"]["label"],
                }
            ],
        }, name
        assert name in _cited(operation, "422"), name


def _without_hours(value: Any) -> list[Entry]:
    """Return the params of each refusal TASK_WITHOUT_WORKING_HOURS a value read from JSON holds."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _without_hours(item)]
    if not isinstance(value, dict):
        return []
    entry = cast("Entry", value)
    own = [entry["params"]] if entry.get("code") == "TASK_WITHOUT_WORKING_HOURS" else []
    return own + [found for item in entry.values() for found in _without_hours(item)]


def test_every_refusal_of_a_task_without_hours_names_its_roles_by_their_label() -> None:
    # #1684: one form for every such refusal — an entry, a paste, an import, the reference —, the
    # roles by their identifier, code and label (`ProblemResourceRole`), never by identifiers alone.
    found = {
        path.stem: _without_hours(json.loads(path.read_text("utf-8"))["value"])
        for path in sorted(mockwitness.FIXTURES.glob("*.json"))
    }
    refusals = {name: params for name, params in found.items() if params}
    assert len(refusals) >= 7
    for name, all_params in refusals.items():
        for params in all_params:
            assert "resource_role_ids" not in params, name
            roles = cast("list[Entry]", params["resource_roles"])
            assert roles == _named([role["resource_role_id"] for role in roles]), name
    # The default calendar left without hours names no role: only tasks without labour lose them.
    [default] = refusals["calendar_default_without_hours"]
    assert default["resource_roles"] == []


def test_a_pasted_row_leaving_its_task_without_hours_is_refused_naming_roles_and_task() -> None:
    # WF-PLA-0010: « une saisie qui laisserait une tâche […] sans aucune heure travaillée dans la
    # semaine est refusée en nommant les rôles et la tâche en cause » — a paste is an entry, and
    # its refusal a row of the plan (`PasteRejection`, `ProblemParams.tasks`; #779).
    plan = fixture("paste_plan_without_hours")
    task = mockwrites.pasted_task()
    _, roles = mockwrites.known()
    # The roles the task would bear once the block written: the engineer stays beside the cable
    # fitter, on the first row and on a line the block does not cover. An empty cell of role
    # writes nothing: its line keeps its own.
    block = mockrefusals.WITHOUT_HOURS_BLOCK
    pasted = {line.number: row[2] for line, row in zip(task.lines, block, strict=False) if row[2]}
    borne = {
        roles[pasted[line.number]] if line.number in pasted else line.role for line in task.lines
    } - {None}
    assert borne == {ENGINEER, CABLE_FITTER}
    assert plan == {
        "paste_id": universe(997),
        "accepted": 2,
        "rejected": [
            {
                "row": 1,
                "column": "resource_role",
                "code": "TASK_WITHOUT_WORKING_HOURS",
                "params": {
                    "resource_roles": _named([ENGINEER, CABLE_FITTER]),
                    "tasks": [
                        {
                            "project_id": fixture("project")["project_id"],
                            "node_id": mockwitness.node_id(task.number),
                            "label": task.label,
                        }
                    ],
                },
            }
        ],
    }
    answer = _operations()["previewPaste"]["responses"]["200"]
    cited = answer["content"]["application/json"]["examples"]["without_hours"]["$ref"]
    assert cited.endswith("/paste_plan_without_hours.json")
    said = (API / "components" / "schemas" / "revisions.yaml").read_text(encoding="utf-8")
    rejection = " ".join(
        said.split("\nPasteRejection:\n", 1)[1].split("  properties:", 1)[0].split()
    )
    assert "`TASK_WITHOUT_WORKING_HOURS`" in rejection


def test_a_line_of_a_completed_task_re_estimated_is_refused_by_the_condition_it_names() -> None:
    line = _node(527)
    assert line["estimate_line"]["remaining_entry"]["missing_conditions"] == ["task_not_completed"]
    refused = fixture("remaining_completed_refused")
    assert refused["params"] == {"missing_condition": "task_not_completed"}
    assert "remaining_completed_refused" in _cited("setLineRemaining", "409")
    assert "description" in _operations()["applyPaste"]["responses"]["409"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_writes_that_carry_their_counter_say_a_stale_one_by_the_counter_current() -> None:
    # US-0702/L2 (E-13, E-24) gave them their counter; US-0703/L8 their 412 example; #1733 gave its
    # counter to the deletion of an access role. Each names the counter its object bears in the
    # witness, sent with the one before: the role created today, saved since (`mockaudit`).
    subproject = cast("list[Entry]", fixture("subprojects"))[0]
    saved = fixture("access_role_created")["lock_version"] + 1
    for operation, name, current in (
        ("abandonRevision", "revision_abandon_stale", fixture("revision")["lock_version"]),
        ("exitProject", "project_exit_stale", fixture("project")["lock_version"]),
        (
            "designateReferenceRevision",
            "reference_designate_stale",
            fixture("project")["lock_version"],
        ),
        ("deleteRisk", "risk_delete_stale", fixture("risk")["lock_version"]),
        ("deleteSubproject", "subproject_delete_stale", subproject["lock_version"]),
        ("deleteAccessRole", "access_role_delete_stale", saved),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == (412, "STALE_LOCK_VERSION"), name
        assert refused["params"] == {"expected_lock_version": current}, name
        assert _cited(operation, "412") == [name], operation
