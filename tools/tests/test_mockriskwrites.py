# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the answers of the entries of a risk, and of the task its provision names (K5, #786).

They try the simplifications of the fake back against the readings of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »), but the
two that hold what the contract says of the confirmation of an occurrence (US-0680).
"""

import functools
import json
import re
from decimal import Decimal
from typing import Any, cast

import pytest
import yaml

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

CITED = (
    ("risks.yaml", "createRisk", "201", "risk_created"),
    ("risks.yaml", "updateRisk", "200", "risk_updated"),
    ("risks.yaml", "reviewRisk", "201", "risk_reviewed"),
    ("risks.yaml", "reviewRisk", "201", "risk_dismissed"),
    ("risks.yaml", "reviewRisk", "201", "risk_reidentified"),
    ("risks.yaml", "listRiskReviews", "200", "risk_reviews_reviewed"),
    ("risks.yaml", "declareRiskOccurrence", "202", "task_occurrence_queued"),
    ("risks.yaml", "createRisk", "422", "risk_provision_task_refused"),
    ("revisions.yaml", "moveNodes", "422", "nodes_move_provision_refused"),
    ("revisions.yaml", "setLineRemaining", "409", "remaining_provision_refused"),
    ("revisions.yaml", "listNodes", "200", "nodes_risk_estimate"),
    ("risks.yaml", "getRiskOccurrenceReport", "200", "risk_occurrence_report"),
    ("risks.yaml", "getRiskOccurrenceReport", "409", "risk_occurrence_not_identified"),
    ("risks.yaml", "declareRiskOccurrence", "409", "risk_occurrence_not_identified"),
    ("risks.yaml", "declareRiskOccurrence", "412", "risk_occurrence_report_stale"),
)
"""Each example of the entries of a risk, under the answer of the operation that cites it."""


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
    for paths, operation, status, name in CITED:
        assert f"fixtures/api/{name}.json" in _response(paths, operation, status), name
    # The confirmation of an occurrence is cited under the body of its request, not an answer.
    sent = "risk_occurrence_sent.json"
    assert {f"{name}.json" for *_, name in CITED} | {sent} == set(mockriskwrites.examples())


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


def test_the_reviews_read_after_the_confirmation_begin_with_the_review_of_today() -> None:
    read, after = example("risk_reviews")["value"], example("risk_reviews_reviewed")["value"]
    reviewed = example("risk_reviewed")["value"]
    [today, *before] = after
    assert before == read
    assert today["reviewed_on"] == reviewed["last_review_on"] == TODAY.date().isoformat()
    kept = ("probability", "severity", "state")
    assert [today[key] for key in kept] == [read[0][key] for key in kept]
    assert [today[key] for key in kept] == [reviewed[key] for key in kept]


def test_a_risk_dismissed_today_bears_no_provision_and_is_a_declared_counterfactual() -> None:
    # #421: the witness confirms 751 today at the version the dismissal would give it.
    read, dismissed = example("risk")["value"], example("risk_dismissed")["value"]
    assert example("risk_dismissed")["summary"].startswith("Variante contrefactuelle : ")
    assert dismissed["lock_version"] == example("risk_reviewed")["value"]["lock_version"]
    assert dismissed["lock_version"] == read["lock_version"] + 1
    assert (read["state"], dismissed["state"]) == ("identified", "dismissed")
    assert (dismissed["provision_node_id"], dismissed["provision_task"]) == (None, None)
    kept = ("probability", "severity", "provision_cost_category_id", "structure_id")
    assert [dismissed[key] for key in kept] == [read[key] for key in kept]
    assert dismissed["last_review_on"] == TODAY.date().isoformat()
    commands = dismissed["available_commands"]
    missing = {each["command"]: each["missing_conditions"] for each in commands}
    assert missing == {
        "update": [],
        "update_provision": ["risk_identified"],
        "review": [],
        "declare_occurrence": ["risk_identified"],
        "delete": ["risk_not_cited"],
    }


def test_a_dismissed_risk_identified_again_recreates_its_line_on_the_task_it_designated() -> None:
    # #1227: the line recreated is borne by the task the risk designated, still one of the main
    # structure; its category still active, none is asked.
    items = {item["risk_id"]: item for item in example("risks")["value"]["items"]}
    read = items[universe(mockwitnessrisks.AUTOMATION_ENGINEER.number)]
    returned = example("risk_reidentified")["value"]
    assert (read["state"], returned["state"]) == ("dismissed", "identified")
    assert returned["lock_version"] == read["lock_version"] + 1
    assert read["provision_cost_category_is_active"] is True
    assert returned["provision_cost_category_id"] == read["provision_cost_category_id"]
    rows = {row.number: row for row in mockcore.current()}
    assert returned["provision_task"] == {
        "node_id": universe(N.COMMISSIONING),
        "label": rows[N.COMMISSIONING].label,
    }
    # Its line is a node of its own, which no reading of the witness renders (#421).
    line = universe(mockriskwrites.REIDENTIFIED_LINE)
    assert returned["provision_node_id"] == line
    assert mockriskwrites.REIDENTIFIED_LINE not in rows
    others = [
        path.name
        for path in mockwitness.FIXTURES.rglob("*.json")
        if path.name != "risk_reidentified.json" and line in path.read_text(encoding="utf-8")
    ]
    assert others == []
    assert all(
        each["is_available"] is (each["command"] != "delete")
        for each in returned["available_commands"]
    )


def test_the_answers_of_a_review_come_after_those_prism_serves_first() -> None:
    # Prism serves the first example of an answer: the confirmation, and the reviews as the
    # witness reads them.
    for operation, status, first, then in (
        ("reviewRisk", "201", "risk_reviewed", ("risk_dismissed", "risk_reidentified")),
        ("listRiskReviews", "200", "risk_reviews", ("risk_reviews_reviewed",)),
    ):
        said = _response("risks.yaml", operation, status)
        for name in then:
            assert said.index(f"/{first}.json") < said.index(f"/{name}.json"), name


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


# --- The report before the occurrence (US-0680, #1383) -----------------------------------------


def _structures() -> list[dict[str, Any]]:
    """Return the structures of the current revision, an example written by hand."""
    return cast("list[dict[str, Any]]", mockwitness.fixture("structures"))


def _structure(structure_id: str) -> dict[str, Any]:
    [found] = [each for each in _structures() if each["structure_id"] == structure_id]
    return found


def test_the_own_estimate_of_the_rework_totals_its_severity_on_its_own_structure() -> None:
    # The severity of a risk is the total of its own estimate (WF-RIS-0010): the structure 204,
    # which `structures` lists as the rework's, totals the 1,250,000 the register reads.
    estimate = example("nodes_risk_estimate")["value"]
    risk = example("risk")["value"]
    assert risk["risk_id"] == universe(mockwitnessrisks.REWORK.number)
    assert estimate["totals"]["reestimated_amount"] == risk["severity"] == "1250000.00"
    structure = _structure(risk["structure_id"])
    assert (structure["kind"], structure["risk_id"]) == ("risk", risk["risk_id"])
    assert risk["structure_id"] == universe(204)


def test_the_own_estimate_is_read_unmarked_and_accepts_nothing_of_the_main_structure() -> None:
    # WF-PLA-0170: neither a lot, nor a post, nor an inscription on an own estimate; and an own
    # estimate is read against nothing (`Node.difference`).
    items = example("nodes_risk_estimate")["value"]["items"]
    assert [item["kind"] for item in items] == ["task", "estimate_line", "task", "estimate_line"]
    for item in items:
        assert "difference" not in item
        assert not set(item["editable_fields"]) & set(mockamendment.MAIN_ONLY)
    main = {row.number for row in mockcore.current()}
    assert not {universe(number) for number in main} & {item["node_id"] for item in items}


def _label(node: dict[str, Any]) -> str:
    return cast("str", node[node["kind"]]["label"])


def test_the_report_adds_the_own_estimate_modifies_the_bearer_and_removes_the_provision() -> None:
    report = example("risk_occurrence_report")["value"]
    items = example("nodes_risk_estimate")["value"]["items"]
    added = [each for each in report["differences"] if each["change"] == "added"]
    assert [(each["target"], each["label"]) for each in added] == [
        (item["kind"], _label(item)) for item in items
    ]
    assert all(each["lineage_id"] is None and each["fields"] == [] for each in added)
    rows = {row.number: row for row in mockcore.current()}
    line = rows[cast("int", mockwitnessrisks.REWORK.provision_line)]
    bearer = rows[cast("int", line.parent)]
    assert not cast("dict[str, Any]", bearer.node["task"])["is_milestone"]
    *_, updated, removed = report["differences"]
    assert (updated["change"], updated["target"], updated["label"]) == (
        "updated",
        "task",
        bearer.label,
    )
    assert updated["lineage_id"] == bearer.node["lineage_id"]
    assert (removed["change"], removed["target"], removed["label"]) == (
        "removed",
        "estimate_line",
        line.label,
    )
    assert removed["lineage_id"] == line.node["lineage_id"]
    assert len(report["differences"]) == len(added) + 2
    assert report["refusals"] == []


def test_the_bearer_is_changed_by_the_dates_it_comes_to_span() -> None:
    # The bearer becomes the summary of the tasks merged under it, which keep the dates they had in
    # the own estimate (WF-RIS-0060, WF-PLA-0040): a date it changes is a field of its `updated`.
    report = example("risk_occurrence_report")["value"]
    [updated] = [each for each in report["differences"] if each["change"] == "updated"]
    tasks = [
        item["task"]
        for item in example("nodes_risk_estimate")["value"]["items"]
        if item["kind"] == "task"
    ]
    rows = {row.number: row for row in mockcore.current()}
    bearer = cast("dict[str, Any]", rows[N.WIRING].node["task"])

    def instant(value: dict[str, str]) -> tuple[str, Decimal]:
        return value["date"], Decimal(value["hours"])

    start = min(instant(task["start"]) for task in tasks)
    finish = max(instant(task["finish"]) for task in tasks)
    assert ("start" in updated["fields"]) == (start != instant(bearer["start"]))
    assert ("finish" in updated["fields"]) == (finish != instant(bearer["finish"]))
    assert updated["fields"] == [
        field for field in mockriskwrites.SCHEDULE if field in updated["fields"]
    ]
    assert updated["fields"]


def test_the_report_withdraws_the_provision_and_returns_the_counters_read() -> None:
    report = example("risk_occurrence_report")["value"]
    risk = example("risk")["value"]
    rows = {row.number: row for row in mockcore.current()}
    line = rows[cast("int", mockwitnessrisks.REWORK.provision_line)]
    facet = cast("dict[str, Any]", line.node["estimate_line"])
    assert report["provision_amount"] == risk["provision_amount"] == facet["reestimated_amount"]
    [main] = [each for each in _structures() if each["kind"] == "main"]
    assert report["main_structure_lock_version"] == main["lock_version"]
    assert report["risk_lock_version"] == risk["lock_version"]


def test_the_occurrence_of_a_risk_not_identified_is_refused_by_the_condition_it_lacks() -> None:
    refused = example("risk_occurrence_not_identified")["value"]
    items = {item["risk_id"]: item for item in example("risks")["value"]["items"]}
    risk = items[universe(mockriskwrites.NOT_IDENTIFIED.number)]
    assert risk["state"] != "identified"
    [command] = [
        each for each in risk["available_commands"] if each["command"] == "declare_occurrence"
    ]
    assert command["missing_conditions"] == ["risk_identified"]
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": "risk_identified"}
    assert risk["label"] in example("risk_occurrence_not_identified")["summary"]


def test_a_stale_confirmation_returns_the_version_of_the_risk_the_path_names() -> None:
    # #296: a 412 returns the current version of the object the path names, and nothing else.
    refused = example("risk_occurrence_report_stale")["value"]
    assert (refused["status"], refused["code"]) == (412, "STALE_LOCK_VERSION")
    assert refused["params"] == {"expected_lock_version": example("risk")["value"]["lock_version"]}


def _schema(file: str, name: str) -> dict[str, Any]:
    """Return one schema of the contract, as its component file writes it."""
    text = (REPOSITORY / "docs" / "api" / "components" / file).read_text(encoding="utf-8")
    return cast("dict[str, Any]", yaml.safe_load(text)[name])


def _occurrence() -> dict[str, Any]:
    """Return the path of the occurrence of a risk, as the contract writes it."""
    text = (REPOSITORY / "docs" / "api" / "paths" / "risks.yaml").read_text(encoding="utf-8")
    paths = cast("dict[str, Any]", yaml.safe_load(text))
    return cast("dict[str, Any]", paths["/projects/{project_id}/risks/{risk_id}/occurrence"])


@pytest.mark.requirement("WF-RIS-0010-A")
@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_write_in_the_own_estimate_advances_the_counter_the_confirmation_carries() -> None:
    # The severity follows any change of the own estimate (WF-RIS-0010), which the report lists and
    # no counter of the main structure guards: a write in it advances `Risk.lock_version`, which the
    # report reads and the confirmation carries, so that a report it made stale is refused by 412.
    risk = _schema("schemas/risks.yaml", "Risk")["properties"]["lock_version"]
    structure = _schema("schemas/revisions.yaml", "CostStructure")["properties"]["lock_version"]
    assert "`RiskOccurrence`" in risk["description"]
    assert "`Risk.lock_version`" in structure["description"]
    report = _schema("schemas/risks.yaml", "RiskOccurrenceReport")
    confirmation = _schema("schemas/risks.yaml", "RiskOccurrence")
    assert set(mockriskwrites.READ) <= set(report["required"])
    assert set(confirmation["required"]) == {"confirmed", *mockriskwrites.READ}
    witness = example("risk")["value"]
    report_read = example("risk_occurrence_report")["value"]
    assert report_read["risk_lock_version"] == witness["lock_version"]
    stale = example("risk_occurrence_report_stale")["value"]
    assert stale["params"]["expected_lock_version"] == witness["lock_version"]


@pytest.mark.requirement("WF-RIS-0060-A")
@pytest.mark.requirement("WF-REV-0010-A")
def test_the_confirmation_returns_whether_its_report_creates_the_current_revision() -> None:
    # Without a current revision, the occurrence creates one (WF-RIS-0060) by copy of the last
    # marked revision (WF-REV-0010): the report says so and the confirmation returns it as read,
    # as the report of the merge of an amendment (#790), so that a current revision born since the
    # reading, or gone, makes it refused by 412. The witness has a current revision.
    for name in ("RiskOccurrenceReport", "RiskOccurrence"):
        schema = _schema("schemas/risks.yaml", name)
        assert "creates_current_revision" in schema["required"], name
        assert schema["properties"]["creates_current_revision"]["type"] == "boolean", name
    revisions = mockwitness.fixture("revisions")["items"]
    assert [each["status"] for each in revisions].count("draft") == 1
    report = example("risk_occurrence_report")["value"]
    assert report["creates_current_revision"] is False
    sent = example("risk_occurrence_sent")["value"]
    assert sent == {"confirmed": True, **{name: report[name] for name in mockriskwrites.READ}}
    post = _occurrence()["post"]
    examples = post["requestBody"]["content"]["application/json"]["examples"]
    assert examples == {"sent": {"$ref": "../../../fixtures/api/risk_occurrence_sent.json"}}
    assert "`creates_current_revision`" in post["responses"]["412"]["description"]
