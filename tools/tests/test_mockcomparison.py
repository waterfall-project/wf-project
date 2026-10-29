# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the comparison of two revisions read by the window of a subtree, and with `fields`.

They try what a window of the comparison retains and the deltas it counts, and the volume of the
comparison read whole with the fields of its screen (#1201, #1208); one alone tries a Vérif, the
two deltas of WF-REV-0080 (US-0701/L1, E-02).
"""

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockcomparisons, mockcore, mockdata, mockdiff, mockhistory
from wftools.mockdating import Amounts
from wftools.mockids import universe
from wftools.mockstructure import money
from wftools.mockwitness import SCHEDULED_AT, N

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def whole() -> Node:
    """Return the comparison of the offer and the reference read whole, without a filter (#1193)."""
    return cast(
        "Node",
        mockcomparisons.comparison(
            mockhistory.offer_rows(),
            mockhistory.reference_rows(),
            mockhistory.OFFER,
            mockhistory.REFERENCE,
        ),
    )


def _label(node: Node) -> str:
    return cast("str", node[node["kind"]]["label"])


def _summed(compared: Node) -> set[Decimal]:
    """Return the sums of the deltas of a comparison, by dimension and by amount, as a set."""
    return {
        sum(
            (
                Decimal(entry[key])
                for entry in compared["amount_deltas"]
                if entry["dimension"] == dimension
            ),
            Decimal(0),
        )
        for dimension in ("cost_type", "subproject")
        for key in ("budgeted_delta", "reestimated_delta")
    }


def test_a_line_moved_into_a_subtree_brings_its_whole_delta_and_leaves_none_behind() -> None:
    # The deltas count each retained line by its parent in the revision compared, for its whole
    # delta (`amount_deltas`): the detailed engineering, moved from the studies under the mounting
    # on site and raised by 500, counts 500 in the installation on site — not its whole amount —,
    # nothing in the studies, and the two windows sum to the whole.
    rows = mockhistory.reference_rows()
    raised = Decimal(500)
    moved = [
        replace(row, parent=N.MOUNTING, amounts=row.amounts + Amounts(raised, raised, raised))
        if row.number == N.STUDIES_LINE
        else row
        for row in rows
    ]

    def read(subtree_of: int | None) -> Node:
        return mockcomparisons.comparison(
            rows, moved, mockhistory.REFERENCE, mockhistory.REFERENCE, subtree_of
        )

    installation, studies = read(N.INSTALLATION), read(N.STUDIES)
    line = universe(N.STUDIES_LINE)
    assert line in [node["node_id"] for node in installation["items"]]
    assert line not in [node["node_id"] for node in studies["items"]]
    assert _summed(installation) == _summed(read(None)) == {raised}
    assert studies["amount_deltas"] == []


def test_the_subtree_of_a_removed_task_is_the_one_it_had_with_its_removed_nodes() -> None:
    # `subtree_of` names a task of the tree rendered, a removed one included: the trials on site,
    # which the reference no longer bears, read with their line at its place, totals of no line of
    # the reference, the delta of the line removed.
    offer = mockhistory.offer_rows()
    window = mockcomparisons.comparison(
        offer, mockhistory.reference_rows(), mockhistory.OFFER, mockhistory.REFERENCE, N.SITE_TRIALS
    )
    items = cast("list[Node]", window["items"])
    assert [node["node_id"] for node in items] == [
        universe(N.SITE_TRIALS),
        universe(N.SITE_TRIALS_LINE),
    ]
    assert {node["difference"] for node in items} == {"removed"}
    totals = cast("Node", window["totals"])
    assert (totals["task_count"], totals["estimate_line_count"]) == (0, 0)
    [removed] = [row for row in offer if row.number == N.SITE_TRIALS_LINE]
    assert _summed(window) == {-removed.amounts.budgeted, -removed.amounts.reestimated}
    assert removed.amounts.budgeted == removed.amounts.reestimated


@pytest.mark.requirement("WF-REV-0080-A")
def test_a_line_whose_budget_alone_changes_presents_no_delta_of_its_reestimate() -> None:
    # Vérif : « une ligne existante dont le différentiel ne modifie que le montant budgété ne
    # présente aucun écart de montant réestimé ». The reference, and the same revision where a
    # differential gave the laying of the terminal blocks other quantities of reference, its
    # current ones kept: the line is modified by its budget alone, its nature and its subproject
    # bear a delta of the budgeted amounts, none of the re-estimated ones.
    rows = mockhistory.reference_rows()

    def rebudget(row: mockcore.Row) -> mockcore.Row:
        budgeted = row.amounts.budgeted + 750
        facet = {**cast("Node", row.node["estimate_line"]), "budgeted_amount": money(budgeted)}
        node = {**row.node, "estimate_line": facet}
        return replace(row, node=node, amounts=replace(row.amounts, budgeted=budgeted))

    rebudgeted = [rebudget(row) if row.number == N.LABOUR else row for row in rows]
    compared = mockcomparisons.comparison(
        rows, rebudgeted, mockhistory.REFERENCE, mockhistory.REFERENCE
    )
    nodes = cast("list[Node]", compared["items"])
    [line] = [node for node in nodes if node["node_id"] == universe(N.LABOUR)]
    assert (line["difference"], line["changes"]) == ("modified", ["budgeted_amount"])
    deltas = cast("list[Node]", compared["amount_deltas"])
    assert [entry["dimension"] for entry in deltas] == ["cost_type", "subproject"]
    assert {(entry["budgeted_delta"], entry["reestimated_delta"]) for entry in deltas} == {
        ("750.00", "0.00")
    }


def test_a_reading_with_fields_renders_what_it_names_besides_the_four() -> None:
    # #166: a property of Node named is rendered whole, a property of a facet renders the facet
    # with it alone, and a facet of which nothing is named, or that the node does not bear, is
    # omitted; node_id, row_number, level and lock_version are always rendered.
    task: Node = {
        "node_id": "n1",
        "lineage_id": "l1",
        "kind": "task",
        "row_number": 1,
        "level": 1,
        "lock_version": 3,
        "predecessors": [{"predecessor_row_number": 2}],
        "task": {"label": "Tâche", "duration": "5"},
    }
    line: Node = {
        "node_id": "n2",
        "lineage_id": "l2",
        "kind": "estimate_line",
        "row_number": 2,
        "level": 2,
        "lock_version": 1,
        "estimate_line": {"label": "Ligne", "quantity": "2"},
    }
    read = mockcore.with_fields([task, line], ["predecessors", "task.label"])
    assert read == [
        {
            "node_id": "n1",
            "row_number": 1,
            "level": 1,
            "lock_version": 3,
            "predecessors": [{"predecessor_row_number": 2}],
            "task": {"label": "Tâche"},
        },
        {"node_id": "n2", "row_number": 2, "level": 2, "lock_version": 1},
    ]


def test_the_volume_of_the_comparison_is_the_whole_comparison_read_with_the_fields_of_its_screen(
    whole: Node,
) -> None:
    # #1201, point 2: the volume the bound of the screen is tried on is the comparison read whole,
    # at the scale of the witness, each node reduced by `fields` to the kind and the label the
    # screen shows, besides the four and the mark always rendered (US-0500/L6).
    volume = mockcomparisons.comparison_volume()
    read = cast("Node", volume["value"])
    assert len(read["items"]) == 5_999
    modified = (node for node in read["items"] if node["difference"] == "modified")
    assert sum(1 for node in modified if node["changes"]) == 2_770
    kept = {*mockdiff.ALWAYS, "kind", "task", "estimate_line"}
    for node, entire in zip(read["items"], whole["items"], strict=True):
        assert set(node) <= kept
        assert {key: node[key] for key in mockdiff.ALWAYS} == {
            key: entire[key] for key in mockdiff.ALWAYS
        }
        assert node["kind"] == entire["kind"]
        assert node[node["kind"]] == {"label": _label(entire)}
    rest = ("from_revision_id", "to_revision_id", "totals", "meta", "amount_deltas")
    assert {key: read[key] for key in rest} == {key: whole[key] for key in rest}
    summary = str(volume["summary"])
    assert "5 999 nœuds" in summary
    assert "2 770 modifiés par leurs propres valeurs" in summary
    assert "852 925,00 et 1 034 848,01 en tout" in summary


VOLUME_BOUND = 1_500_000
"""The bytes the volume of the comparison stays under, written as the fixture is (#1204)."""


def test_the_volume_of_the_comparison_stays_under_its_bound() -> None:
    # #1204: the volume is read by the screen and versioned; a reading that renders more than the
    # fields of the screen, or nodes rendered whole, would make it grow past its bound.
    written = mockdata.render(mockcomparisons.comparison_volume()).encode("utf-8")
    assert len(written) < VOLUME_BOUND


def test_the_moved_variant_bears_a_task_moved_under_another_summary_marked_modified() -> None:
    # The criterion « une tâche déplacée sous une autre récapitulative est présentée modifiée »
    # (WF-REV-0080-A) is read by the front on an example (#1105): the commissioning, under the
    # control station in the counterfactual offer, is rendered once under the installation on
    # site, modified by its parent alone; the window keeps the totals and the deltas of the first.
    rows = mockhistory.reference_rows()
    example = mockcomparisons.comparison_moved(rows)
    first = cast("Node", mockcomparisons.comparison_example(rows)["value"])
    moved = cast("Node", example["value"])
    items = cast("list[Node]", moved["items"])
    [task] = [node for node in items if "parent" in node["changes"]]
    assert (task["node_id"], task["kind"], task["difference"], task["changes"]) == (
        universe(N.COMMISSIONING),
        "task",
        "modified",
        ["parent"],
    )
    assert task["parent_id"] == universe(N.INSTALLATION)
    ids = [node["node_id"] for node in items]
    assert ids.count(universe(N.COMMISSIONING)) == 1
    assert set(ids) == {node["node_id"] for node in first["items"]}
    rest = ("from_revision_id", "to_revision_id", "totals", "meta", "amount_deltas")
    assert {key: moved[key] for key in rest} == {key: first[key] for key in rest}
    summary = str(example["summary"])
    assert summary.startswith("Variante contrefactuelle : ")
    assert "« Mise en service » sous la récapitulative « Poste de commande »" in summary


def test_a_comparison_to_a_revision_in_progress_is_dated_at_the_instant_of_the_witness() -> None:
    """The revision compared, not marked, is read as any structure in progress (WF-DAT-0020)."""
    compared = cast(
        "Node",
        mockcomparisons.comparison(
            mockhistory.reference_rows(),
            mockhistory.reference_rows(),
            mockhistory.REFERENCE,
            mockhistory.CURRENT,
        ),
    )

    assert compared["meta"]["scheduled_at"] == mockcore.stamp(SCHEDULED_AT)
