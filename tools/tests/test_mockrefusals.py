# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the refusals of one form each, and of their examples (US-0702/L1, #1610).

The review of the contract before the freeze (D-05, J-01, J-02) and the decision of the author of
the 2026-10-28: a terminal project and a marked revision are refused everywhere by the 409 of
their condition, as the object says it beforehand. The tests hold the contract and the examples
``wftools.mockrefusals`` writes; a test cites a requirement where it takes up its Vérif.
"""

import re
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockrefusals
from wftools.mockwitness import fixture

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


def test_a_terminal_project_refuses_its_timelines_by_the_condition_its_command_names() -> None:
    commands = _commands(fixture("project_completed"))
    assert commands["manage_timelines"] == ["project_not_terminal"]
    for operation, name in (
        ("createTimeline", "timeline_create_terminal"),
        ("deleteTimeline", "timeline_delete_terminal"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": "project_not_terminal"}, name
        assert name in _cited(operation, "409"), name
    # The delete answers the shared 403 now, which names the qualities alone.
    assert "403" in _operations()["deleteTimeline"]["responses"]


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
    assert mockrefusals.REFERENCE == fixture("revision_marked")["revision_id"]


def test_no_state_has_a_code_of_its_own_and_no_403_says_a_state() -> None:
    common = yaml.safe_load((API / "components" / "common.yaml").read_text("utf-8"))
    codes = common["ErrorCode"]["enum"]
    assert "PROJECT_TERMINAL" not in codes
    assert "REVISION_MARKED" not in codes
    forbidden = yaml.safe_load((API / "components" / "responses.yaml").read_text("utf-8"))
    said = forbidden["Forbidden"]["description"]
    assert "jamais par 403" in said
    assert "NOT_PROJECT_MANAGER" in said
    readme = (API / "README.md").read_text("utf-8")
    assert "Le refus d'une commande qu'un état rend indisponible est un 409" in readme
    for path in sorted((API / "paths").glob("*.yaml")):
        text = path.read_text("utf-8")
        assert not re.search(r"(terminal|marquée)[^.]{0,80}par 403", text), path.name


@pytest.mark.parametrize("name", sorted(mockrefusals.examples()))
def test_every_example_of_the_module_is_cited_by_an_operation(name: str) -> None:
    stem = name.removesuffix(".json")
    cited = {
        stem
        for operation in _operations().values()
        for answer in cast("dict[str, Entry]", operation["responses"]).values()
        if isinstance(answer, dict) and "content" in answer
        for content in cast("dict[str, Entry]", answer["content"]).values()
        for example in cast("dict[str, Entry]", content.get("examples", {})).values()
        if cast("str", example.get("$ref", "")).endswith(f"/{name}")
    }
    assert cited == {stem}


# --- The catalogue: every code rendered by an operation, with an example (J-03, J-06, J-11) ----


def test_the_project_manager_quality_is_refused_by_its_code_as_the_command_said_it() -> None:
    commands = _commands(fixture("project_participant"))
    assert commands["update"][0] == "is_project_manager"
    refused = fixture("project_update_not_manager")
    assert (refused["status"], refused["code"]) == (403, "NOT_PROJECT_MANAGER")
    assert refused["params"] == {"missing_condition": "is_project_manager"}
    assert _cited("updateProject", "403") == ["project_update_not_manager"]


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
    [line] = [each for each in _core() if each["node_id"] == mockrefusals.universe(553)]
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
