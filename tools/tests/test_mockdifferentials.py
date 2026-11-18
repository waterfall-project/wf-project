# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the abandonment of a differential and of the registration refused on it (US-2550/L2).

The conception of EP-08 writes ``deleteCostStructure``, its command ``delete`` and the action of
the audit log ``structure_abandon`` into the contract, and the refusal of ``setNodeTracking`` on a
structure other than the main one (#2497): each refusal has its condition, said by its operation,
and an example ``wftools.mockdifferentials`` writes; the structures of the witness list ``delete``
on a differential not merged alone.
"""

import re
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockdifferentials
from wftools.mockwitness import fixture

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


def _cited(operation: str, status: str) -> list[str]:
    """Return the examples a status of an operation cites, by their file name, in their order."""
    answer = _operations()[operation]["responses"][status]
    examples = answer["content"]["application/problem+json"]["examples"]
    return [re.sub(r".*/(\w+)\.json$", r"\1", each["$ref"]) for each in examples.values()]


def _enumeration(family: str, schema: str) -> list[str]:
    path = API / "components" / "schemas" / f"{family}.yaml"
    return cast("list[str]", yaml.safe_load(path.read_text("utf-8"))[schema]["enum"])


def _commands(holder: Entry) -> dict[str, list[str]]:
    return {
        each["command"]: each["missing_conditions"]
        for each in cast("list[Entry]", holder["available_commands"])
    }


REFUSED = {
    "structure_delete_main_refused": ("deleteCostStructure", "unmerged_amendment_exists"),
    "structure_delete_revision_marked": ("deleteCostStructure", "revision_draft"),
    "node_tracking_amendment_refused": ("setNodeTracking", "main_structure"),
}


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_state_is_refused_by_the_condition_the_operation_says(name: str) -> None:
    operation, condition = REFUSED[name]
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": condition}
    assert name in _cited(operation, "409")
    assert f"`{condition}`" in _operations()[operation]["responses"]["409"]["description"]


def test_every_example_of_the_module_is_cited_by_its_operation() -> None:
    cited = {
        *_cited("deleteCostStructure", "409"),
        *_cited("deleteCostStructure", "412"),
        *_cited("setNodeTracking", "409"),
    }
    assert {name.removesuffix(".json") for name in mockdifferentials.examples()} <= cited


def test_the_abandonment_names_its_conditions_in_the_order_of_the_conception() -> None:
    # Conception of EP-08, « Le contrat »: `project_not_terminal`, `revision_draft`,
    # `no_background_task_running`, then `unmerged_amendment_exists`.
    description = _operations()["deleteCostStructure"]["responses"]["409"]["description"]
    order = [
        "project_not_terminal",
        "revision_draft",
        "no_background_task_running",
        "unmerged_amendment_exists",
    ]
    assert [description.index(f"`{each}`") for each in order] == sorted(
        description.index(f"`{each}`") for each in order
    )
    for condition in ("main_structure", "unmerged_amendment_exists"):
        assert condition in _enumeration("projects", "CommandCondition")


def test_a_stale_abandonment_names_the_counter_the_differential_bears() -> None:
    refused = fixture("structure_delete_stale")
    [amendment] = [each for each in fixture("structures") if each["kind"] == "amendment"]
    assert (refused["status"], refused["code"]) == (412, "STALE_LOCK_VERSION")
    assert refused["params"] == {"expected_lock_version": amendment["lock_version"]}
    assert _cited("deleteCostStructure", "412") == ["structure_delete_stale"]
    parameters = _operations()["deleteCostStructure"]["parameters"]
    assert {"name": "lock_version", "in": "query", "required": True}.items() <= next(
        each for each in parameters if each.get("name") == "lock_version"
    ).items()


def test_delete_is_listed_on_a_differential_not_merged_alone() -> None:
    # Each differential is merged or abandoned independently (WF-REV-0100): the abandonment is a
    # command of the differential not merged, with the state conditions of the opening of a
    # differential, in the same order; never on a structure it could not abandon.
    assert _enumeration("revisions", "StructureCommand")[-1] == "delete"
    for name, revision in (
        ("structures", "revision"),
        ("structures_amendments", "revision_marked"),
    ):
        opening = _commands(fixture(revision))["create_structure"]
        for structure in fixture(name):
            commands = _commands(structure)
            if structure["kind"] == "amendment" and not structure["is_merged"]:
                assert commands["delete"] == opening, (name, structure["label"])
            else:
                assert "delete" not in commands, (name, structure["label"])
    assert _commands(fixture("amendment_created"))["delete"] == []


def test_the_abandonment_of_a_differential_is_an_action_of_the_audit_log() -> None:
    actions = _enumeration("audit", "AuditAction")
    assert actions.index("structure_abandon") == actions.index("structure_merge") + 1
    assert "structure_abandon" in _operations()["deleteCostStructure"]["description"]
    created = _operations()["createCostStructure"]["description"]
    assert "`deleteCostStructure`" in created
