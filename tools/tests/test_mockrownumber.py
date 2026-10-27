# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the resolution of a row number and of the columns a grid knew, in the contract.

They try the contract and its examples, not the service (EP-16/US-0650, #1288, #1260): the
resolution of a number names the node the witness structure numbers so, whatever the rows a grid
read, an unknown number is refused as an object that does not exist, and the examples of the
preferences of a grid keep the columns it hid and widened among those it knew. None cites a
requirement: the parts « au contrat » of US-0650 have none of their own.
"""

import json
from pathlib import Path
from typing import Any, cast

import yaml

from wftools import REPOSITORY, mockwitness
from wftools.mockwitness import fixture

API = REPOSITORY / "docs" / "api"
PATH = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rows/{row_number}"
RESOLVED = {"row_number_task": "task", "row_number_estimate_line": "estimate_line"}
"""The resolutions written by hand, and the kind of the node each names."""
UNKNOWN = 6001
"""The number the refusal asks: the one after the last row of the witness structure."""
PREFERENCES = ("me_grid_settings", "me_auditor", "preferences_page_size")
"""The examples whose grids the front wrote, each with the columns it offered."""


def resolution() -> dict[str, Any]:
    """Return the operation `resolveRowNumber`, as its file of the contract writes it."""
    paths = yaml.safe_load((API / "paths" / "revisions.yaml").read_text(encoding="utf-8"))
    return cast("dict[str, Any]", paths[PATH]["get"])


def numbered() -> dict[int, dict[str, Any]]:
    """Return the nodes of the witness structure by their number: the first example of listNodes."""
    volume = mockwitness.FIXTURES / "volume" / "nodes_thousand.json"
    nodes = json.loads(volume.read_text(encoding="utf-8"))["value"]["items"]
    return {node["row_number"]: node for node in nodes}


def label_of(node: dict[str, Any]) -> str:
    """Return the label of a node: that of its task or of its line of the estimate."""
    return cast("str", (node.get("task") or node["estimate_line"])["label"])


def test_the_operation_is_in_the_contract_with_its_examples_the_task_first() -> None:
    operation = resolution()
    assert operation["operationId"] == "resolveRowNumber"
    served = operation["responses"]["200"]["content"]["application/json"]
    assert served["schema"]["$ref"].endswith("#/RowNumberResolution")
    cited = [Path(each["$ref"]).stem for each in served["examples"].values()]
    # The fake back serves the first whatever the number: a task, which a predecessor may be.
    assert cited == list(RESOLVED)
    refused = operation["responses"]["404"]["content"]["application/problem+json"]["examples"]
    assert [Path(each["$ref"]).stem for each in refused.values()] == ["row_number_unknown"]
    reference = (API / "openapi.yaml").read_text(encoding="utf-8")
    assert f"  {PATH}:" in reference


def test_a_number_resolves_to_the_node_the_whole_structure_numbers_so() -> None:
    nodes = numbered()
    for name, kind in RESOLVED.items():
        resolved = fixture(name)
        node = nodes[resolved["row_number"]]
        assert resolved == {
            "node_id": node["node_id"],
            "row_number": node["row_number"],
            "label": label_of(node),
            "kind": kind,
        }, name
        assert node["kind"] == kind, name


def test_the_task_resolved_is_one_the_grid_of_the_planning_did_not_read() -> None:
    # The number a predecessor is entered by, out of the rows the planning of « Études » read.
    read = {node["row_number"] for node in fixture("nodes_planning")["items"]}
    task = fixture("row_number_task")
    assert task["row_number"] not in read
    predecessors = {
        each["predecessor_row_number"]
        for node in fixture("nodes_planning")["items"]
        for each in node.get("predecessors", [])
    }
    assert task["row_number"] not in predecessors


def test_a_number_no_node_bears_is_refused_as_an_object_that_does_not_exist() -> None:
    assert max(numbered()) == UNKNOWN - 1
    refused = fixture("row_number_unknown")
    assert set(refused) == {"code", "status", "correlation_id"}
    assert (refused["status"], refused["code"]) == (404, "NOT_FOUND")
    summary = json.loads(
        (mockwitness.FIXTURES / "row_number_unknown.json").read_text(encoding="utf-8")
    )["summary"]
    assert f"Le numéro {UNKNOWN} " in summary


def test_a_grid_written_keeps_the_columns_it_hid_and_widened_among_those_it_knew() -> None:
    grids = 0
    for name in PREFERENCES:
        value = fixture(name)
        preferences = value.get("display_preferences", value)
        for grid, settings in cast("dict[str, Any]", preferences["grids"]).items():
            known = set(settings["known_columns"])
            assert len(known) == len(settings["known_columns"]) <= 64, (name, grid)
            assert set(settings.get("hidden_columns", [])) <= known, (name, grid)
            assert set(settings.get("column_widths", {})) <= known, (name, grid)
            grids += 1
    assert grids == 5


def test_a_column_the_grid_hides_by_default_and_did_not_know_is_hidden() -> None:
    # The estimate of the account was set before the grid offered « Sous-projet », hidden by
    # default (`GridColumn.hidden`): absent from the columns it knew, it stays hidden.
    estimate = fixture("me_grid_settings")["display_preferences"]["grids"]["estimate"]
    assert "subproject" not in estimate["known_columns"]
    assert "subproject" not in estimate["hidden_columns"]
    summary = json.loads(
        (mockwitness.FIXTURES / "me_grid_settings.json").read_text(encoding="utf-8")
    )["summary"]
    assert "« Sous-projet », masquée par défaut, elle ne la connaît pas" in summary
