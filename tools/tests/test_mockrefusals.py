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
