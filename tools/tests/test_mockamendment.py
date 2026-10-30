# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the amendment 2 of the witness, a differential of the current revision (#791, C-361).

They try the reading of the differential, marked against the main structure, and the report
before its merge against the description of the amendment and the structures the revisions list,
not the Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune
exigence »).
"""

import json
from typing import Any, cast

import pytest

from wftools import mockamendment, mockcore, mockdiff
from wftools.mockamendment import own_id
from wftools.mockwitness import N, fixture

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def whole() -> list[Node]:
    """Read the whole differential once, marked, as the contract carries it."""
    return cast("list[Node]", json.loads(json.dumps(mockamendment.marked())))


def _by_id(nodes: list[Node]) -> dict[str, Node]:
    return {node["node_id"]: node for node in nodes}


def test_the_current_revision_bears_the_amendment_2_not_merged_as_the_reference_did() -> None:
    # WF-REV-0100: a revision created from a marked one takes over its differentials; the
    # amendment 2 coexisted with the amendment 1 in the reference, and is not merged yet.
    current = fixture("project")["current_revision_id"]
    [amendment] = [each for each in fixture("structures") if each["kind"] == "amendment"]
    assert (amendment["revision_id"], amendment["label"]) == (current, mockamendment.LABEL)
    assert amendment["is_merged"] is False
    [before] = [
        each for each in fixture("structures_amendments") if each["label"] == amendment["label"]
    ]
    assert before["is_merged"] is False
    assert before["structure_id"] != amendment["structure_id"]


def test_the_reading_of_the_differential_marks_each_node_against_the_main_structure(
    whole: list[Node],
) -> None:
    # C-361: added, removed at its place and read only, moved and modified by its parent, a
    # summary modified by its content alone; every other node unchanged.
    marks = {node["node_id"]: (node["difference"], node["changes"]) for node in whole}
    assert {key for key, (mark, _) in marks.items() if mark == mockdiff.ADDED} == {
        own_id(number) for number in (N.SITE_TESTS, N.TESTS_RESUMED, N.TESTS_RESUMED_LINE)
    }
    removed = _by_id(whole)[own_id(N.TESTS_LINE)]
    assert (removed["difference"], removed["parent_id"]) == ("removed", own_id(N.MOUNTING))
    assert removed["editable_fields"] == []
    assert marks[own_id(N.MOUNTING)] == ("modified", [])
    assert marks[own_id(N.COMMISSIONING)] == ("modified", ["dates", "duration", "parent"])
    assert marks[own_id(N.COMMISSIONING_LINE)] == (
        "modified",
        ["budgeted_amount", "reestimated_amount"],
    )
    commissioning = _by_id(whole)[own_id(N.COMMISSIONING)]
    assert commissioning["parent_id"] == own_id(N.SITE_TESTS)
    assert [node["row_number"] for node in whole] == list(range(1, len(whole) + 1))
    main = mockcore.current()
    # The main structure, its line removed still rendered, and the three nodes added.
    assert len(whole) == len(main) + 3


def test_the_differential_names_its_nodes_by_its_own_identifiers_the_lineages_of_the_main(
    whole: list[Node],
) -> None:
    # #421: a node of the differential is not the node of the main structure it copies, though it
    # shares its lineage; no identifier of the main structure is rendered in the differential,
    # neither a node, nor its parent, nor a predecessor.
    main = {cast("str", row.node["node_id"]) for row in mockcore.current()}
    lineages = {cast("str", row.node["lineage_id"]) for row in mockcore.current()}
    named = [
        *(node["node_id"] for node in whole),
        *(node["parent_id"] for node in whole if node["parent_id"] is not None),
        *(link["predecessor_node_id"] for node in whole for link in node.get("predecessors", [])),
    ]
    assert not main & set(named)
    kept = [node for node in whole if node["difference"] != "added"]
    assert {node["lineage_id"] for node in kept} == lineages
    assert len({node["node_id"] for node in whole}) == len(whole)
    assert own_id(N.INSTALLATION) == "01926f3a-7c00-7000-8000-000000001261"
    assert own_id(N.TESTS_RESUMED_LINE) == "01926f3a-7c00-7000-8000-000000001293"


def test_no_task_of_the_differential_bears_what_the_main_structure_alone_bears(
    whole: list[Node],
) -> None:
    # WF-PLA-0170, WF-PLA-0060: neither attachment nor inscription in a differential, and its
    # tasks do not accept them (#1065).
    tasks = [node for node in whole if node["kind"] == "task"]
    assert all(
        not {"work_package_id", "order_item_id", "tracking"} & node["task"].keys() for node in tasks
    )
    assert all(not set(mockamendment.MAIN_ONLY) & set(node["editable_fields"]) for node in tasks)


def test_the_example_reads_the_installation_its_totals_without_the_line_removed() -> None:
    example = fixture("nodes_amendment")
    nodes = example["items"]
    assert nodes[0]["node_id"] == own_id(N.INSTALLATION)
    retained = [node for node in nodes if node["difference"] != "removed"]
    lines = [node for node in retained if node["kind"] == "estimate_line"]
    assert example["totals"]["task_count"] == len(retained) - len(lines)
    assert example["totals"]["estimate_line_count"] == len(lines)
    assert {node["difference"] for node in nodes} == {"added", "removed", "modified", "unchanged"}


def test_the_differences_alone_are_every_node_marked_their_totals_the_whole_differential(
    whole: list[Node],
) -> None:
    # #1398: « Écarts seulement » over the whole differential renders every node it adds,
    # withdraws or modifies — each ancestor of one of them modified itself, so none comes for the
    # tree alone — and no node unchanged; its totals are those of the whole differential.
    example = fixture("nodes_amendment_differences")
    assert example["items"] == [node for node in whole if node["difference"] != "unchanged"]
    kept = {node["node_id"] for node in example["items"]}
    assert all(node["parent_id"] is None or node["parent_id"] in kept for node in example["items"])
    assert example["totals"] == mockcore.whole(mockamendment.rows())["totals"]
    assert example["totals"] != fixture("nodes_amendment")["totals"]


def test_the_report_before_the_merge_says_what_the_differential_marks(whole: list[Node]) -> None:
    # WF-REV-0050: the tasks and lines added and removed are those the reading marks so; each node
    # updated is modified; the link of the commissioning moves from the mounting to the rework.
    report = fixture("structure_merge_report")
    differences = report["differences"]

    def labels(change: str, target: str | None = None) -> list[str]:
        return [
            each["label"]
            for each in differences
            if each["change"] == change
            and (target is None or each["target"] == target)
            and each["target"] != "link"
        ]

    def marked(mark: str) -> list[str]:
        return [node[node["kind"]]["label"] for node in whole if node["difference"] == mark]

    assert labels("added") == marked("added")
    assert labels("removed") == marked("removed")
    modified = {node["lineage_id"] for node in whole if node["difference"] == "modified"}
    assert {each["lineage_id"] for each in differences if each["change"] == "updated"} <= modified
    # A node the differential moves names its parent among the fields it changes, as its reading
    # does among its changes (#1194): the commissioning, under the trials on site.
    moved = {node["lineage_id"] for node in whole if "parent" in node["changes"]}
    named = {
        each["lineage_id"]
        for each in differences
        if each["change"] == "updated" and "parent" in each["fields"]
    }
    assert named == moved == {_by_id(whole)[own_id(N.COMMISSIONING)]["lineage_id"]}
    links = [
        (each["change"], each["predecessor_label"])
        for each in differences
        if each["target"] == "link"
    ]
    assert links == [
        ("added", "Reprise des essais de câblage"),
        ("removed", "Montage des armoires sur site"),
    ]
    commissioning = _by_id(whole)[own_id(N.COMMISSIONING)]
    [link] = commissioning["predecessors"]
    assert link["predecessor_node_id"] == own_id(N.TESTS_RESUMED)
    assert (report["completed_tasks"], report["refusals"]) == ([], [])
