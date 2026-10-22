# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the answers of the entries of a risk, and of the task its provision names (K5, #786).

They try the simplifications of the fake back against the readings of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import functools
import json
import re
from typing import Any, cast

from wftools import (
    REPOSITORY,
    mockamendment,
    mockcore,
    mockdata,
    mockriskwrites,
    mockwitness,
    mockwitnessrisks,
)
from wftools.mockhistory import stamp
from wftools.mockids import universe
from wftools.mockwitness import TODAY, N
from wftools.mockwitnessrisks import DELIVERY_DELAY, REGISTER

CITED = {
    ("risks.yaml", "createRisk", "201"): "risk_created",
    ("risks.yaml", "updateRisk", "200"): "risk_updated",
    ("risks.yaml", "reviewRisk", "201"): "risk_reviewed",
    ("risks.yaml", "declareRiskOccurrence", "202"): "task_occurrence_queued",
    ("risks.yaml", "createRisk", "422"): "risk_provision_task_refused",
    ("revisions.yaml", "moveNodes", "422"): "nodes_move_provision_refused",
}


@functools.cache
def _named() -> dict[str, Any]:
    return mockdata.named()


def example(name: str) -> dict[str, Any]:
    """Return an example as the generator writes it, read back from its text."""
    return cast("dict[str, Any]", json.loads(mockdata.render(_named()[f"{name}.json"])))


def _response(paths: str, operation: str, status: str) -> str:
    """Return the text of one response of an operation of the contract."""
    text = (REPOSITORY / "docs" / "api" / "paths" / paths).read_text(encoding="utf-8")
    block = text[text.index(f"operationId: {operation}") :]
    following = block.find("operationId:", len("operationId:"))
    block = block if following < 0 else block[:following]
    start = block.index(f"'{status}':")
    after = re.search(r"\n      '\d{3}':", block[start + 1 :])
    return block[start:] if after is None else block[start : start + 1 + after.start()]


def test_each_entry_of_a_risk_is_an_example_the_contract_cites_under_its_answer() -> None:
    for (paths, operation, status), name in CITED.items():
        assert f"fixtures/api/{name}.json" in _response(paths, operation, status), name
    assert {f"{name}.json" for name in CITED.values()} == set(mockriskwrites.examples())


def test_the_task_of_a_provision_is_the_parent_of_its_line_while_the_risk_is_identified() -> None:
    # #786: the register names the task that bears each line of provision; a risk not identified
    # bears no line, and names none.
    items = {item["risk_id"]: item for item in example("risks")["value"]["items"]}
    rows = {row.number: row for row in mockcore.current()}
    for risk in REGISTER:
        item = items[universe(risk.number)]
        if item["provision_node_id"] is None:
            assert item["provision_task"] is None
            continue
        parent = cast("int", rows[cast("int", risk.provision_line)].parent)
        assert item["provision_task"] == {"node_id": universe(parent), "label": rows[parent].label}
    assert items[universe(751)]["provision_task"]["node_id"] == universe(N.WIRING)
    assert example("risk")["value"] == items[universe(751)]


def test_a_risk_declared_without_a_task_bears_its_provision_on_the_first_root_task() -> None:
    created = example("risk_created")["value"]
    assert created["provision_task"] == {"node_id": universe(N.STUDIES), "label": "Études"}
    assert (created["lock_version"], created["state"]) == (1, "identified")
    # Its own structure opened empty with it: nothing to price yet, no provision.
    assert (created["severity"], created["provision_amount"]) == ("0.00", "0.00")
    structures = {each["structure_id"] for each in mockwitness.fixture("structures")}
    assert created["structure_id"] not in structures
    main = {cast("str", row.node["node_id"]) for row in mockcore.current()}
    assert created["provision_node_id"] not in main
    declared = stamp(mockriskwrites.DECLARED_AT)
    assert created["audit"]["created_at"] == created["audit"]["updated_at"] == declared
    assert created["last_review_on"] == TODAY.date().isoformat()
    assert all(entry["is_available"] for entry in created["available_commands"])


def test_a_risk_modified_moves_its_line_to_the_task_designated_and_keeps_its_provision() -> None:
    created, updated = example("risk_created")["value"], example("risk_updated")["value"]
    assert updated["lock_version"] == created["lock_version"] + 1
    assert updated["provision_task"]["node_id"] == universe(mockriskwrites.DESIGNATED)
    assert updated["mitigation_notes"] == mockriskwrites.MITIGATION
    kept = ("risk_id", "provision_node_id", "provision_amount", "severity", "structure_id")
    assert [updated[key] for key in kept] == [created[key] for key in kept]
    assert updated["audit"]["created_at"] == created["audit"]["created_at"]
    assert updated["audit"]["updated_at"] > updated["audit"]["created_at"]
    assert updated["audit"]["updated_at"] == stamp(TODAY)


def test_a_risk_confirmed_without_change_is_reviewed_today_and_one_version_further() -> None:
    read, reviewed = example("risk")["value"], example("risk_reviewed")["value"]
    assert reviewed["lock_version"] == read["lock_version"] + 1
    assert reviewed["last_review_on"] == TODAY.date().isoformat()
    assert reviewed["audit"]["updated_at"] == stamp(TODAY)
    changed = {"lock_version", "last_review_on", "audit"}
    assert {key: value for key, value in reviewed.items() if key not in changed} == {
        key: value for key, value in read.items() if key not in changed
    }


def test_the_occurrence_queued_is_the_one_of_the_delay_of_the_cabinets() -> None:
    queued = example("task_occurrence_queued")["value"]
    assert (queued["kind"], queued["status"]) == ("risk_occurrence", "queued")
    assert queued["submitted_at"] == stamp(DELIVERY_DELAY.last.at)
    assert DELIVERY_DELAY.last.state == mockwitnessrisks.OCCURRED
    others = [
        path.name
        for path in mockwitness.FIXTURES.glob("*.json")
        if path.name != "task_occurrence_queued.json"
        and queued["task_id"] in path.read_text(encoding="utf-8")
    ]
    assert others == []


def test_a_provision_designated_on_a_task_of_another_structure_is_refused_on_its_field() -> None:
    refused = example("risk_provision_task_refused")["value"]
    assert refused["fields"] == [{"pointer": "/provision_task_id", "code": "UNKNOWN_TASK"}]
    assert mockriskwrites.REFUSED_TASK not in {row.number for row in mockcore.current()}
    label = {row.number: row.label for row in mockamendment.rows()}[mockriskwrites.REFUSED_TASK]
    assert label in example("risk_provision_task_refused")["summary"]


def test_a_risk_declared_today_is_said_a_counterfactual_from_the_first_words() -> None:
    # The convention of #1196: a counterfactual opens its summary by saying it (#1228).
    assert example("risk_created")["summary"].startswith("Variante contrefactuelle : ")


def test_a_line_of_provision_moved_in_the_grid_is_refused_and_names_its_risk() -> None:
    # #1227: the line of provision moves by the form of its risk alone, which designates its task.
    refused = example("nodes_move_provision_refused")["value"]
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    risk = {
        "risk_id": universe(mockwitnessrisks.REWORK.number),
        "label": mockwitnessrisks.REWORK.label,
    }
    assert refused["fields"] == [
        {
            "pointer": "/node_ids/0",
            "code": "PROVISION_LINE_MOVED_BY_RISK",
            "params": {"risk": risk},
        }
    ]
    rows = {row.number: row for row in mockcore.current()}
    line = rows[cast("int", mockwitnessrisks.REWORK.provision_line)]
    assert cast("dict[str, Any]", line.node["estimate_line"])["is_computed"]
    assert line.parent == N.WIRING != mockriskwrites.PROVISION_MOVED_UNDER
    summary = example("nodes_move_provision_refused")["summary"]
    assert rows[mockriskwrites.PROVISION_MOVED_UNDER].label in summary
