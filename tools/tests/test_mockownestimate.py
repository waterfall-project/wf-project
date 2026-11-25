# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the contract of the own estimate of a risk read as a differential (US-3070/L2).

EP-30 makes the own estimate of a risk a differential of the main structure, whole in the current
revision and pruned at the marking (#4585): ``CostStructure`` says its state, the recomposition is
an operation of its own, the update of a differential reaches it, two conditions name what it
lacks, and ``wftools.mockownestimate`` writes the examples of the own estimate of 751.
"""

import re
from decimal import Decimal
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockamendment, mockcore, mockdiff, mockownestimate, mockrebase
from wftools.mockids import universe
from wftools.mockwitness import N, fixture, lineage_id

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
STRUCTURE = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}"
CONDITIONS = ("own_estimate_whole", "own_estimate_up_to_date")


def _operations() -> dict[str, Entry]:
    """Return the operations of the contract, by their operationId."""
    found: dict[str, Entry] = {}
    for path in (API / "paths").glob("*.yaml"):
        for item in cast("dict[str, Entry]", yaml.safe_load(path.read_text("utf-8"))).values():
            for operation in item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    found[cast("str", operation["operationId"])] = cast("Entry", operation)
    return found


def _schemas(family: str) -> dict[str, Entry]:
    path = API / "components" / "schemas" / f"{family}.yaml"
    return cast("dict[str, Entry]", yaml.safe_load(path.read_text("utf-8")))


def _cited(operation: str, status: str, media: str = "application/problem+json") -> list[str]:
    """Return the examples a status of an operation cites, by their file name."""
    examples = _operations()[operation]["responses"][status]["content"][media]["examples"]
    return [re.sub(r".*/(\w+)\.json$", r"\1", each["$ref"]) for each in examples.values()]


def _commands(holder: Entry) -> dict[str, list[str]]:
    return {
        each["command"]: each["missing_conditions"]
        for each in cast("list[Entry]", holder["available_commands"])
    }


def _label(node: Entry) -> str:
    return cast("str", node[node["kind"]]["label"])


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_own_estimate_designates_an_addition_a_charge_and_an_abandonment() -> None:
    # « une tâche ajoutée après une tâche du projet, une ligne existante portée à plus d'heures et
    # une tâche existante abandonnée sont présentées ajoutée, modifiée et retirée » (#4585).
    items = fixture("nodes_risk_estimate")["items"]
    marks = {_label(item): (item["difference"], item["changes"]) for item in items}
    assert marks["Reprise du câblage des armoires"] == ("added", [])
    assert marks["Recâblage des armoires"] == ("added", [])
    assert marks["Raccordement des borniers"] == ("modified", ["reestimated_amount"])
    assert marks["Dossier de conception"] == ("removed", [])
    assert {mark for mark, _ in marks.values()} <= set(mockdiff.DIFFERENCES)
    # Its nodes have identifiers of their own and the lineages of the main structure (#421).
    [line] = [item for item in items if _label(item) == "Raccordement des borniers"]
    assert line["node_id"] == mockownestimate.own_id(N.LABOUR) == universe(N.LABOUR + 1500)
    assert line["lineage_id"] == lineage_id(N.LABOUR)
    for item in items:
        assert not set(item["editable_fields"]) & set(mockamendment.MAIN_ONLY)


@pytest.mark.story("US-3150")
def test_the_own_estimate_keeps_the_severity_of_the_register() -> None:
    # « à gravité égale » (#4585): the gap of the totals of the own estimate and of its base is the
    # severity the register reads, so that the reserve and what depends on it hold.
    risk = fixture("risk")
    whole = fixture("nodes_risk_estimate")["totals"]["reestimated_amount"]
    base = mockcore.whole(mockownestimate.rows(mockownestimate.base()))["totals"]
    gap = Decimal(whole) - Decimal(cast("str", cast("Entry", base)["reestimated_amount"]))
    assert gap == Decimal(risk["severity"]) == Decimal("1250000.00")


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_own_estimate_bears_no_provision_line() -> None:
    rows = mockownestimate.rows(mockownestimate.own_estimate())
    provisions = {row.number for row in mockcore.current() if "Provision" in row.label}
    assert provisions
    assert not provisions & {row.number for row in rows}


@pytest.mark.story("US-3070")
def test_the_pruned_own_estimate_keeps_what_it_designates_under_its_ancestors() -> None:
    reading = fixture("nodes_risk_estimate_pruned")
    items = reading["items"]
    assert [item["row_number"] for item in items] == list(range(1, len(items) + 1))
    designated = {_label(item) for item in items if item["difference"] != "unchanged"}
    assert designated == {
        "Dossier de conception",
        "Raccordement des borniers",
        "Reprise du câblage des armoires",
        "Recâblage des armoires",
    }
    # Its ancestors and the ends of its links are presented unchanged; nothing else of the project.
    unchanged = {_label(item) for item in items if item["difference"] == "unchanged"}
    assert unchanged == {
        "Études",
        "Poste de commande",
        "Câblage des armoires",
        "Installation sur site",
        "Mise en service",
    }
    rows = {item["node_id"]: item["row_number"] for item in items}
    for item in items:
        for link in item.get("predecessors", []):
            assert rows[link["predecessor_node_id"]] == link["predecessor_row_number"]
    assert reading["totals"]["estimate_line_count"] == 2


def test_the_report_of_the_update_keeps_the_charge_and_announces_the_severity() -> None:
    report = fixture("structure_rebase_report_risk")
    [kept] = [each for each in report["differences"] if each["change"] == "kept"]
    assert (kept["label"], kept["fields"]) == ("Raccordement des borniers", ["hours"])
    severity = Decimal(report["severity"])
    assert severity == mockownestimate.updated_severity() < mockownestimate.SEVERITY
    assert Decimal(report["provision_amount"]) == (severity * Decimal("0.4")).quantize(
        Decimal("0.01")
    )
    listed = mockownestimate.listed()
    assert report["structure_lock_version"] == listed["lock_version"]
    # The severity and the provision of an amendment are null (#4621).
    for name in ("structure_rebase_report", "structure_rebase_report_refused"):
        amendment = fixture(name)
        assert (amendment["severity"], amendment["provision_amount"]) == (None, None)


def test_the_clean_report_signals_nothing_and_announces_the_severity() -> None:
    # #4775: the main branch of the screen, the update that asks nothing.
    clean = fixture("structure_rebase_report_risk_clean")
    assert {each["change"] for each in clean["differences"]} == {"added", "updated", "removed"}
    assert clean["refusals"] == []
    assert Decimal(clean["severity"]) == mockownestimate.SEVERITY
    assert Decimal(clean["provision_amount"]) == mockownestimate.provision(mockownestimate.SEVERITY)
    signalled = fixture("structure_rebase_report_risk")
    assert clean["structure_lock_version"] == signalled["structure_lock_version"]
    assert clean["main_structure_lock_version"] == signalled["main_structure_lock_version"] - 1


def test_the_refused_variant_names_the_loop_by_the_nodes_of_the_own_estimate() -> None:
    refused = fixture("structure_rebase_report_risk_refused")
    [reason] = refused["refusals"]
    assert reason["code"] == "LINK_CYCLE"
    nodes = [each["node_id"] for each in reason["params"]["cycle"]]
    assert nodes == [mockownestimate.own_id(number) for number in mockownestimate.CYCLE]
    assert (refused["severity"], refused["provision_amount"]) == (None, None)
    applicable = fixture("structure_rebase_report_risk")
    writes = mockownestimate.RELINKING_WRITES
    assert refused["main_structure_lock_version"] == applicable["main_structure_lock_version"] + (
        writes
    )


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_structures_say_the_state_of_each_own_estimate() -> None:
    states = {
        each["structure_id"]: (each["is_pruned"], each["is_up_to_date"], _commands(each))
        for each in fixture("structures")
    }
    assert states[universe(204)] == (
        False,
        True,
        {"edit_planning": [], "edit_estimate": [], "rebase": ["structure_out_of_date"]},
    )
    pruned, up_to_date, commands = states[universe(206)]
    assert (pruned, up_to_date, commands["rebase"]) == (False, False, [])
    assert commands["edit_estimate"] == ["own_estimate_up_to_date"]
    # Consumed by its occurrence: pruned, its state null, no update.
    pruned, up_to_date, commands = states[universe(205)]
    assert (pruned, up_to_date, "rebase" in commands) == (True, None, False)
    assert states[universe(201)][:2] == (None, None)
    main = [each for each in fixture("structures") if each["kind"] == "main"]
    own = [each for each in fixture("structures") if each["kind"] == "risk"]
    assert {each["planning_start_on"] for each in own} == {main[0]["planning_start_on"]}


def test_the_recomposition_makes_the_own_estimate_whole() -> None:
    recomposed = fixture("structure_recomposed")
    assert (recomposed["is_pruned"], recomposed["kind"]) == (False, "risk")
    assert "recompose" not in _commands(recomposed)
    refused = fixture("structure_rebase_risk_pruned_refused")
    assert refused["params"] == {"missing_condition": "own_estimate_whole"}
    marked = fixture("structure_recompose_revision_marked")
    assert marked["params"] == {"missing_condition": "revision_draft"}


def test_the_late_recomposition_leaves_the_own_estimate_out_of_date() -> None:
    # #4775: whole, out of date, its update offered and its entry waiting for it.
    late = fixture("structure_recomposed_late")
    whole = fixture("structure_recomposed")
    assert (late["is_pruned"], late["is_up_to_date"]) == (False, False)
    moved = {"is_up_to_date", "available_commands"}
    assert {key: late[key] for key in late if key not in moved} == {
        key: whole[key] for key in whole if key not in moved
    }
    commands = _commands(late)
    assert commands == {
        "edit_planning": ["own_estimate_up_to_date"],
        "edit_estimate": ["own_estimate_up_to_date"],
        "rebase": [],
    }


def test_the_recomposition_is_listed_on_a_pruned_own_estimate_not_consumed() -> None:
    # #4620: `recompose` is listed on that one only, and the entry and the update wait for it.
    structures = {each["structure_id"]: each for each in fixture("structures_next_revision")}
    own = structures[universe(209)]
    assert (own["is_pruned"], own["revision_id"]) == (True, universe(104))
    assert _commands(own)["recompose"] == []
    waiting = {"edit_planning", "edit_estimate", "rebase"}
    assert {name for name in waiting if _commands(own)[name] == ["own_estimate_whole"]} == waiting
    assert "recompose" not in _commands(structures[universe(210)])
    assert all("recompose" not in _commands(each) for each in fixture("structures"))


def test_the_planning_start_of_an_own_estimate_is_read_only_even_unchanged() -> None:
    # The exception of `FIELD_READ_ONLY`, for `updateCostStructure`.
    refused = fixture("structure_update_own_start_read_only")
    assert refused["fields"] == [{"pointer": "/planning_start_on", "code": "FIELD_READ_ONLY"}]
    common = yaml.safe_load((API / "components" / "common.yaml").read_text("utf-8"))
    assert common["ErrorCode"]["enum"].count("FIELD_READ_ONLY") == 1
    assert "structure_update_own_start_read_only" in _cited("updateCostStructure", "422")[-1]


def test_the_recomposition_is_an_operation_of_its_own() -> None:
    operation = _operations()["recomposeCostStructure"]
    assert "requestBody" not in operation
    answer = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert answer.endswith("#/CostStructure")
    paths = yaml.safe_load((API / "paths" / "revisions.yaml").read_text("utf-8"))
    assert paths[f"{STRUCTURE}/recompose"]["post"]["operationId"] == "recomposeCostStructure"
    assert "recompose" in _schemas("revisions")["StructureCommand"]["enum"]


def test_the_two_conditions_are_named_where_the_conception_says() -> None:
    # #4623: the writes of the tree, the import, the review, the report and the occurrence.
    # The third, `own_estimate_pruned`, is the one the recomposition names.
    enum = _schemas("projects")["CommandCondition"]["enum"]
    assert set(CONDITIONS) | {"own_estimate_pruned"} <= set(enum)
    assert (
        "`own_estimate_pruned`"
        in _operations()["recomposeCostStructure"]["responses"]["409"]["description"]
    )
    operations = _operations()
    for name in (
        "createNode",
        "updateTaskFacet",
        "updateEstimateLine",
        "setPredecessors",
        "moveNodes",
        "deleteNode",
        "applyPaste",
        "applyImport",
        "reviewRisk",
        "getRiskOccurrenceReport",
        "declareRiskOccurrence",
    ):
        description = operations[name]["responses"]["409"]["description"]
        places = [description.index(f"`{each}`") for each in CONDITIONS]
        assert places == sorted(places), name


def test_the_failure_of_a_marking_names_the_risks() -> None:
    # #4625: one more reason of the failure of the background tasks of a marking and of a merge.
    common = yaml.safe_load((API / "components" / "common.yaml").read_text("utf-8"))
    assert "OWN_ESTIMATES_OUT_OF_DATE" in common["ErrorCode"]["enum"]
    for name in ("markRevision", "mergeCostStructure"):
        assert "`OWN_ESTIMATES_OUT_OF_DATE`" in _operations()[name]["description"], name


def test_every_example_of_the_module_is_cited_by_its_operation() -> None:
    cited = {
        *_cited("listNodes", "200", "application/json"),
        *_cited("getStructureRebaseReport", "200", "application/json"),
        *_cited("getStructureRebaseReport", "409"),
        *_cited("rebaseCostStructure", "200", "application/json"),
        *_cited("recomposeCostStructure", "200", "application/json"),
        *_cited("recomposeCostStructure", "409"),
        *_cited("listCostStructures", "200", "application/json"),
        *_cited("updateCostStructure", "422"),
    }
    assert {name.removesuffix(".json") for name in mockownestimate.examples()} <= cited
    assert set(mockownestimate.examples()).isdisjoint(mockrebase.examples())
