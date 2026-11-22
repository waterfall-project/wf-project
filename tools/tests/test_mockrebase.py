# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the contract of the update of a differential and of its examples (US-3050/L1).

The reprise of the conception of EP-08 of 2026-11-19 (#4034) writes into the contract
``getStructureRebaseReport`` and ``rebaseCostStructure``, the state ``is_up_to_date`` of a
structure, its command ``rebase``, and two conditions: ``structure_out_of_date`` for the update of
a differential up to date, ``structure_up_to_date`` for the merge of one out of date. Each
refusal has its example, ``wftools.mockrebase`` writes them, and the structures of the witness
say the state of each differential.
"""

import re
from typing import Any, cast

import yaml

from wftools import REPOSITORY, mockrebase
from wftools.mockamendment import own_id
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
REBASE = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rebase"


def _paths() -> dict[str, Entry]:
    return cast("dict[str, Entry]", yaml.safe_load((API / "paths" / "revisions.yaml").read_text()))


def _operations() -> dict[str, Entry]:
    """Return the operations of the revisions, by their operationId."""
    return {
        operation["operationId"]: operation
        for item in _paths().values()
        for operation in item.values()
    }


def _schemas(family: str) -> dict[str, Entry]:
    path = API / "components" / "schemas" / f"{family}.yaml"
    return cast("dict[str, Entry]", yaml.safe_load(path.read_text("utf-8")))


def _cited(operation: str, status: str, media: str = "application/problem+json") -> list[str]:
    """Return the examples a status of an operation cites, by their file name, in their order."""
    examples = _operations()[operation]["responses"][status]["content"][media]["examples"]
    return [re.sub(r".*/(\w+)\.json$", r"\1", each["$ref"]) for each in examples.values()]


def _commands(holder: Entry) -> dict[str, list[str]]:
    return {
        each["command"]: each["missing_conditions"]
        for each in cast("list[Entry]", holder["available_commands"])
    }


def _before(text: str, order: list[str]) -> bool:
    places = [text.index(f"`{each}`") for each in order]
    return places == sorted(places)


def test_the_report_and_the_update_share_the_path_of_the_structure() -> None:
    item = _paths()[REBASE]
    assert (item["get"]["operationId"], item["post"]["operationId"]) == (
        "getStructureRebaseReport",
        "rebaseCostStructure",
    )
    body = item["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert body.endswith("#/StructureRebase")
    answer = item["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert answer.endswith("#/CostStructure")


def test_the_confirmation_carries_the_counters_the_report_read() -> None:
    schemas = _schemas("revisions")
    counters = {"main_structure_lock_version", "structure_lock_version"}
    assert set(schemas["StructureRebase"]["required"]) == {"confirmed", *counters}
    report = schemas["StructureRebaseReport"]
    assert set(report["required"]) == {*counters, "differences", "refusals"}
    # No schema of a difference of its own: those of an import and of a merge (#4034).
    for name in ("differences", "refusals"):
        assert report["properties"][name]["items"]["$ref"].startswith("exchanges.yaml#/")


def test_the_update_names_the_conditions_of_the_abandonment_then_its_own() -> None:
    order = [
        "project_not_terminal",
        "revision_draft",
        "no_background_task_running",
        "unmerged_amendment_exists",
        "structure_out_of_date",
    ]
    assert _before(_operations()["rebaseCostStructure"]["responses"]["409"]["description"], order)


def test_the_merge_names_the_state_of_the_differential_after_its_conditions() -> None:
    description = _operations()["mergeCostStructure"]["responses"]["409"]["description"]
    assert _before(
        description,
        ["unmerged_amendment_exists", "revision_draft", "may_create_revision"],
    )
    assert description.index("`structure_up_to_date`") > description.index("`may_create_revision`")
    # The state of the differential is a condition: judged before the name of version (as
    # markRevision judges its state before its name), so that the clause of ALREADY_EXISTS comes
    # after it — the clause itself, not the sentence that names it beside structure_up_to_date
    # (#4185).
    clause = description.index("Or a version name already used")
    assert description.index("`structure_up_to_date`") < clause
    report = _operations()["getStructureMergeReport"]["responses"]["409"]["description"]
    assert "`structure_up_to_date`" in report
    for operation in ("getStructureMergeReport", "mergeCostStructure"):
        assert "merge_out_of_date_refused" in _cited(operation, "409")
    conditions = _schemas("projects")["CommandCondition"]["enum"]
    assert {"structure_up_to_date", "structure_out_of_date"} <= set(conditions)


def test_every_example_of_the_module_is_cited_by_its_operation() -> None:
    cited = {
        *_cited("getStructureRebaseReport", "200", "application/json"),
        *_cited("getStructureRebaseReport", "409"),
        *_cited("rebaseCostStructure", "200", "application/json"),
        *_cited("rebaseCostStructure", "409"),
        *_cited("rebaseCostStructure", "412"),
        *_cited("rebaseCostStructure", "422"),
        *_cited("mergeCostStructure", "409"),
    }
    assert {name.removesuffix(".json") for name in mockrebase.examples()} <= cited


def test_the_report_presents_a_difference_of_each_sort() -> None:
    report = fixture("structure_rebase_report")
    changes = [each["change"] for each in report["differences"]]
    assert set(changes) == {"added", "updated", "removed", "kept"}
    assert report["refusals"] == []
    # An addition enters the differential under its lineage in the main structure.
    assert all(each["lineage_id"] for each in report["differences"])
    [kept] = [each for each in report["differences"] if each["change"] == "kept"]
    assert kept["fields"] == ["hours"]


def test_the_refused_variant_names_the_loop_by_the_nodes_of_the_differential() -> None:
    refused = fixture("structure_rebase_report_refused")
    [reason] = refused["refusals"]
    assert reason["code"] == "LINK_CYCLE"
    nodes = [each["node_id"] for each in reason["params"]["cycle"]]
    assert nodes == [own_id(number) for number in mockrebase.CYCLE]
    applied = fixture("structure_rebase_link_cycle")
    assert (applied["status"], applied["code"]) == (422, "LINK_CYCLE")
    assert applied["params"] == reason["params"]


def test_the_counters_follow_the_structures_of_the_witness() -> None:
    [main] = [each for each in fixture("structures") if each["kind"] == "main"]
    [amendment] = [each for each in fixture("structures") if each["kind"] == "amendment"]
    report = fixture("structure_rebase_report")
    assert report["main_structure_lock_version"] > main["lock_version"]
    assert report["structure_lock_version"] == amendment["lock_version"]
    stale = fixture("structure_rebase_stale")
    assert stale["params"] == {"expected_lock_version": amendment["lock_version"]}
    rebased = fixture("structure_rebased")
    assert rebased["lock_version"] == amendment["lock_version"] + 1
    assert rebased["is_up_to_date"] is True


def test_the_state_is_said_of_an_unmerged_differential_alone() -> None:
    # « À jour » se lit sur la structure (#4034): null for the main structure and a merged
    # differential or a consumed own estimate; the amendment 2
    # is out of date in the reference, which the merge of the amendment 1 marked, up to date in the
    # current revision; rebase is listed where delete is, unavailable on an up to date one.
    expected = {"structures": True, "structures_amendments": False}
    for name, state in expected.items():
        for structure in fixture(name):
            commands = _commands(structure)
            if structure["kind"] == "amendment" and not structure["is_merged"]:
                assert structure["is_up_to_date"] is state, name
                assert ("structure_out_of_date" in commands["rebase"]) is state, name
                assert commands["rebase"][: len(commands["delete"])] == commands["delete"]
            elif structure["kind"] == "risk" and not structure["is_merged"]:
                # EP-30: the own estimate of a risk not consumed is up to date or not
                # (US-3070/L2, test_mockownestimate).
                assert isinstance(structure["is_up_to_date"], bool), (name, structure["label"])
                assert "rebase" in commands, (name, structure["label"])
            else:
                assert structure["is_up_to_date"] is None, (name, structure["label"])
                assert "rebase" not in commands, (name, structure["label"])
    created = fixture("amendment_created")
    assert created["is_up_to_date"] is True
    assert _commands(created)["rebase"] == ["structure_out_of_date"]
