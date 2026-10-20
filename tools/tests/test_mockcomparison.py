# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the comparison of two revisions read by the window of a subtree (#1193).

They try what a window of the comparison retains and the deltas it counts, not the Vérif of a
requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

from wftools import mockhistory
from wftools.mockids import universe
from wftools.mockwitness import N

type Node = dict[str, Any]


def _summed(compared: Node) -> set[Decimal]:
    """Return the sums of the deltas of a comparison, one by dimension, as a set."""
    return {
        sum(
            (
                Decimal(entry["delta"])
                for entry in compared["amount_deltas"]
                if entry["dimension"] == dimension
            ),
            Decimal(0),
        )
        for dimension in ("cost_type", "subproject")
    }


def test_a_line_moved_into_a_subtree_brings_its_whole_delta_and_leaves_none_behind() -> None:
    # The deltas count each retained line by its parent in the revision compared, for its whole
    # delta (`amount_deltas`): the detailed engineering, moved from the studies under the mounting
    # on site and raised by 500, counts 500 in the installation on site — not its whole amount —,
    # nothing in the studies, and the two windows sum to the whole.
    rows = mockhistory.reference_rows()
    raised = Decimal(500)
    moved = [
        replace(
            row, parent=N.MOUNTING, amounts=replace(row.amounts, base=row.amounts.base + raised)
        )
        if row.number == N.STUDIES_LINE
        else row
        for row in rows
    ]

    def read(subtree_of: int | None) -> Node:
        return mockhistory.comparison(
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
    window = mockhistory.comparison(
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
    assert _summed(window) == {-removed.amounts.base}
