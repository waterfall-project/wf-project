# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the estimate lines of the witness written for the loader of the lines (US-1570/L1)."""

import json
from collections import Counter
from typing import Any

import pytest

from wftools import REPOSITORY, mockcore, mockdata, mockhistory, mockwitness, paths
from wftools import mockwitnesslines as module

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

FIXTURES = REPOSITORY / "fixtures" / "api"
FILE = FIXTURES / module.NAME

KEYS = {"revision", "node_id", "lineage_id", "task_lineage_id", "position", *module.ENTERED}
REVISIONS = (module.OFFER, module.REFERENCE, module.CURRENT)


def _read(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["value"]


def _lines(revision: int) -> list[dict[str, Any]]:
    return [line for line in _read(module.NAME)["lines"] if line["revision"] == revision]


def test_the_lines_are_held_by_the_check_of_make_mock_data_up_to_date() -> None:
    # The engendering yields the data announced; the file is held by the check.
    assert module.NAME in mockdata.named()
    assert module.NAME in mockdata.declared_names()
    assert FILE.read_text(encoding="utf-8") == mockdata.render(mockdata.named()[module.NAME])
    assert not [problem for problem in mockdata.check(FIXTURES) if module.NAME in problem]


def test_the_lines_are_declared_generated_by_make_mock_data() -> None:
    # A file written by the generator is declared so, and left out of a lot's size.
    declared = [
        entry for entry in paths.read().generated if f"fixtures/api/{module.NAME}" in entry.paths
    ]
    assert [entry.by for entry in declared] == ["make mock-data"]


def test_two_engenderings_give_the_same_bytes() -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. »
    first = mockdata.render(module.examples()[module.NAME])
    second = mockdata.render(module.examples()[module.NAME])
    assert first == second


def test_the_revisions_are_those_of_the_chronology_and_count_their_lines() -> None:
    # The revisions 100, 101 and 102 of PRJ-001, those the chronology opens, in its order.
    revisions = _read(module.NAME)["revisions"]
    assert [entry["revision"] for entry in revisions] == list(REVISIONS)
    assert [entry["line_count"] for entry in revisions] == [
        len(_lines(entry["revision"])) for entry in revisions
    ]
    opened = [
        write["revision"]
        for event in _read("project_state_transitions.json")["events"]
        for write in event["writes"]
        if write["kind"] == "revision_opened"
    ]
    assert opened == list(REVISIONS)


def test_each_line_gives_its_lineage_its_task_its_rank_and_its_facet_entered_alone() -> None:
    # The facet entered, as EstimateLineWrite carries it, and nothing computed: no amount, no year
    # of consumption — the service computes them, and the computed becomes the expected.
    for line in _read(module.NAME)["lines"]:
        assert set(line) == KEYS
        assert line["lineage_id"] != line["node_id"]
    for revision in REVISIONS:
        lineages = [line["lineage_id"] for line in _lines(revision)]
        assert len(lineages) == len(set(lineages)), revision


def test_a_line_names_a_task_the_file_of_the_tasks_gives_its_revision() -> None:
    # The slice of the lines writes after the slice of the tasks (register_revision_filler): the
    # task that bears a line is one witness_tasks.json gives the same revision.
    tasks = _read("witness_tasks.json")["tasks"]
    for revision in REVISIONS:
        known = {task["lineage_id"] for task in tasks if task["revision"] == revision}
        assert {line["task_lineage_id"] for line in _lines(revision)} <= known, revision


def test_the_lines_of_a_task_are_ranked_from_one_before_its_subordinates() -> None:
    # Node.position counts the lines of a task first: their ranks are 1, 2, … in the plan's order.
    for revision in REVISIONS:
        ranks: dict[str, list[int]] = {}
        for line in _lines(revision):
            ranks.setdefault(line["task_lineage_id"], []).append(line["position"])
        assert all(each == list(range(1, len(each) + 1)) for each in ranks.values()), revision


def test_the_lines_of_the_revision_in_progress_are_those_of_the_structure_of_a_thousand_tasks() -> (
    None
):
    # The volumes of §4.6.2: the five thousand lines of the main structure of the revision in
    # progress, its one provision left out — the declaration of a risk creates it, never an entry
    # (WF-RIS-0010) — each with the facet listNodes reads of it (nodes_thousand.json).
    items = _read("volume/nodes_thousand.json")["items"]
    read = {node["lineage_id"]: node for node in items if node["kind"] == "estimate_line"}
    assert len(read) == 5_000
    provisions = {key for key, node in read.items() if node["estimate_line"]["is_computed"]}
    assert len(provisions) == 1
    current = _lines(module.CURRENT)
    assert [line["lineage_id"] for line in current] == [
        key for key in read if key not in provisions
    ]
    parents = {node["node_id"]: node["lineage_id"] for node in items}
    for line in current:
        node = read[line["lineage_id"]]
        assert line["node_id"] == node["node_id"]
        assert line["task_lineage_id"] == parents[node["parent_id"]]
        assert line["position"] == node["position"]
        assert {key: line[key] for key in module.ENTERED} == {
            key: node["estimate_line"][key] for key in module.ENTERED
        }


def test_the_marked_revisions_are_their_structures_without_their_provisions() -> None:
    # The offer bears no provision, nor subproject; the reference bears three provisions, left
    # out; the offer and the reference share their lineages but for what the amendment 1 changed.
    structures = {
        module.OFFER: mockhistory.offer_rows(),
        module.REFERENCE: mockhistory.reference_rows(),
    }
    for revision, rows in structures.items():
        kept = [
            row.node["lineage_id"]
            for row in rows
            if row.kind == mockcore.ESTIMATE_LINE and not mockhistory.is_provision(row)
        ]
        assert [line["lineage_id"] for line in _lines(revision)] == kept, revision
    reference_rows = mockhistory.reference_rows()
    assert sum(1 for row in reference_rows if mockhistory.is_provision(row)) == 3
    assert {line["subproject_id"] for line in _lines(module.OFFER)} == {None}
    offered = {line["lineage_id"] for line in _lines(module.OFFER)}
    referenced = {line["lineage_id"] for line in _lines(module.REFERENCE)}
    # The rental of the bench of the trials on site, removed; the assistance to the trials, added.
    assert offered - referenced == {mockcore.lineage(mockwitness.N.SITE_TRIALS_LINE)}
    assert referenced - offered == {mockcore.lineage(mockwitness.N.TESTS_LINE)}


def test_a_labour_line_has_a_role_and_hours_and_another_a_unit_disbursement() -> None:
    # WF-DEV-0020: a role makes a labour line, with its effort; another has its disbursement.
    kinds: Counter[str] = Counter()
    for line in _read(module.NAME)["lines"]:
        labour = line["resource_role_id"] is not None
        kinds["labour" if labour else "other"] += 1
        assert (line["hours"] is not None) is labour
        assert (line["unit_disbursement"] is None) is labour
        assert line["payment_delay_days"] is not None
    assert kinds["labour"] > 0
    assert kinds["other"] > 0


def test_no_address_and_only_the_fictitious_labels_of_the_witness() -> None:
    # « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. »
    text = FILE.read_text(encoding="utf-8")
    assert "@" not in text
    labels = {line["label"] for line in _read(module.NAME)["lines"]}
    # Each the label the witness describes for the line, in one of its three structures.
    described = {
        row.label
        for rows in (mockcore.current(), mockhistory.offer_rows(), mockhistory.reference_rows())
        for row in rows
        if row.kind == mockcore.ESTIMATE_LINE
    }
    assert labels <= described
