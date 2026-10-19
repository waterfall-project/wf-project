# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the refusals of a paste and of an import (EP-15/US-0460/L2, #1152, #1153).

As those of the other writes of the grids, they try the simplifications of the fake back against
the readings of the witness, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un
test qui ne couvre aucune exigence »).
"""

import json
import re
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockcore, mockdata, mockexchanges, mockwitness
from wftools.mockwitness import SUBPROJECT_CONTROL, SUBPROJECT_TESTS, N

type Node = dict[str, Any]


def _json(value: Any) -> Any:
    return json.loads(json.dumps(value))


@pytest.fixture(scope="module")
def read() -> dict[int, Node]:
    """Read the structure of the witness today, by the number of its nodes."""
    return {number: _json(each) for number, each in mockexchanges.read().items()}


def node(read: dict[int, Node], number: int) -> Node:
    return read[number]


def _operation(paths: str, name: str) -> str:
    text = (REPOSITORY / "docs" / "api" / "paths" / paths).read_text(encoding="utf-8")
    operation = text[text.index(f"operationId: {name}") :]
    end = operation.find("operationId:", len("operationId:"))
    return operation if end < 0 else operation[:end]


def _cited(text: str, status: str) -> list[str]:
    answer = text[text.index(f"'{status}':") :]
    answer = answer[: answer.index("\n      '", 1)]
    return re.findall(r"fixtures/api/(\w+)\.json", answer)


def _charged(subproject: str) -> bool:
    [entry] = [
        each for each in mockwitness.fixture("subprojects") if each["subproject_id"] == subproject
    ]
    return cast("bool", entry["has_actual_costs"])


def _named(line: Node) -> dict[str, Any]:
    facet = line["estimate_line"]
    named = {"subproject_id": facet["subproject_id"], "label": facet["subproject_label"]}
    return {"subproject": named}


def test_every_refusal_is_an_example_the_contract_cites_under_its_answer() -> None:
    examples = mockexchanges.examples()
    assert "paste_plan_subproject_held" in _cited(
        _operation("revisions.yaml", "previewPaste"), "200"
    )
    assert "import_remaining_subproject_held" in _cited(
        _operation("exchanges.yaml", "getImport"), "200"
    )
    assert "import_estimate_main_in_progress" in _cited(
        _operation("exchanges.yaml", "openImport"), "409"
    )
    assert set(examples) == {
        "paste_plan_subproject_held.json",
        "import_remaining_subproject_held.json",
        "import_estimate_main_in_progress.json",
    }
    assert set(examples) <= set(mockdata.named())


def test_a_line_held_by_its_subproject_refuses_another_and_none_but_not_its_own(
    read: dict[int, Node],
) -> None:
    # The labour of the wiring, started, borne by the control station, charged: held.
    labour = node(read, N.LABOUR)
    assert node(read, N.WIRING)["task"]["progress"] == "started"
    assert _charged(labour["estimate_line"]["subproject_id"])
    assert mockexchanges.is_held(labour)
    for other in (SUBPROJECT_TESTS, None):
        assert mockexchanges.held_refusal(labour, other) == {
            "code": "SUBPROJECT_HAS_ACTUAL_COSTS",
            "params": _named(labour),
        }
    assert mockexchanges.held_refusal(labour, SUBPROJECT_CONTROL) is None
    # A line of a task not started takes any; a provision computes its own, refused otherwise.
    commissioning = node(read, N.COMMISSIONING_LINE)
    assert node(read, N.COMMISSIONING)["task"]["progress"] == "not_started"
    assert not mockexchanges.is_held(commissioning)
    assert mockexchanges.held_refusal(commissioning, SUBPROJECT_TESTS) is None
    provision = node(read, N.PROVISION)
    assert not mockexchanges.is_held(provision)
    assert mockexchanges.held_refusal(provision, SUBPROJECT_TESTS) is None


def test_a_subproject_pasted_on_a_held_line_is_refused_and_names_it(
    read: dict[int, Node],
) -> None:
    plan = _json(mockexchanges.paste_plan_subproject_held())
    # The block writes the labour of the wiring, then the line below it in the order of the plan.
    ordered = [each["node_id"] for each in read.values()]
    labour = node(read, N.LABOUR)
    below = list(read.values())[ordered.index(labour["node_id"]) + 1]
    assert below["node_id"] == node(read, N.BLOCKS)["node_id"]
    assert mockexchanges.is_held(below)
    assert below["estimate_line"]["subproject_id"] == mockexchanges.PASTED[1]
    assert plan["rejected"] == [
        {
            "row": 0,
            "column": "subproject",
            "code": "SUBPROJECT_HAS_ACTUAL_COSTS",
            "params": _named(labour),
        }
    ]
    assert plan["accepted"] == 1


def test_a_line_in_the_tab_of_another_subproject_moves_unless_held(
    read: dict[int, Node],
) -> None:
    imported = _json(mockexchanges.import_remaining_subproject_held())
    report = imported["report"]
    assert (imported["kind"], imported["status"]) == ("remaining", "analysed")
    assert report["read_count"] == len(mockexchanges.IMPORTED)
    # The commissioning on site, of a task not started, changes subproject: a difference.
    commissioning = node(read, N.COMMISSIONING_LINE)
    assert commissioning["estimate_line"]["subproject_id"] != mockexchanges.TAB
    assert report["differences"] == [
        {
            "change": "updated",
            "target": "estimate_line",
            "lineage_id": mockcore.lineage(N.COMMISSIONING_LINE),
            "label": commissioning["estimate_line"]["label"],
            "fields": ["subproject"],
        }
    ]
    # The labour of the wiring, second line of the tab, its third row: rejected, the subproject
    # it may not leave named.
    assert report["rejected"] == [
        {"row": 3, "code": "SUBPROJECT_HAS_ACTUAL_COSTS", "params": _named(node(read, N.LABOUR))}
    ]
    assert report["refusals"] == []


def test_the_estimate_imported_on_the_main_structure_in_progress_names_its_condition() -> None:
    refused = mockexchanges.import_estimate_main_in_progress()
    # The structures listed are those of the current revision of the witness, in progress.
    project = mockwitness.fixture("project")
    assert project["current_revision_id"] == mockexchanges.main_structure()["revision_id"]
    assert project["state"] == "in_progress"
    assert (refused["code"], refused["status"]) == ("STATE_FORBIDS_OPERATION", 409)
    assert refused["params"] == {"missing_condition": "project_before_in_progress"}
    main = mockexchanges.main_structure()
    [command] = [each for each in main["available_commands"] if each["command"] == "edit_estimate"]
    assert command["missing_conditions"] == ["project_before_in_progress"]
    assert all(
        each["is_available"]
        for structure in mockwitness.fixture("structures")
        if structure["kind"] != "main"
        for each in structure["available_commands"]
        if each["command"] == "edit_estimate"
    )
