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
from wftools.mockstructure import LABOUR_RATES, money
from wftools.mockwitness import SCHEDULED_AT, N, fixture

type Node = dict[str, Any]

LINES_REESTIMATED_ALONE = 2_768
"""The lines from the offer 100 to the reference 101 whose re-estimate alone changes, all of them
labour lines moved by the rates of 2026: the number the drawn structure gives, fixed by its seed."""


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


def _subproject(row: mockcore.Row) -> str:
    return cast("str | None", mockhistory.estimate_line(row)["subproject_id"]) or "unassigned"


def _lines_by_id(rows: list[mockcore.Row]) -> dict[str, Node]:
    """Return the facets of the lines of a reading, by node identifier."""
    return {
        cast("str", row.node["node_id"]): cast("Node", row.node["estimate_line"])
        for row in rows
        if row.kind == mockcore.ESTIMATE_LINE
    }


KEYS = ("subproject", "cost_category")
"""What changes of a line the key it counts under, and none of its amounts (#1751)."""


def _amounts(node: Node) -> list[str]:
    """Return what changed of a node besides its key: its amounts, its delay, its parent."""
    return [change for change in node.get("changes") or [] if change not in KEYS]


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
def test_a_line_that_changes_its_subproject_alone_moves_its_whole_amount_from_key_to_key() -> None:
    # #1751 (E-01): a line counts under the key it bears in each revision. The reference, and the
    # same revision where the laying of the terminal blocks passes from the control station to
    # the trials, its amounts kept: it is modified by its subproject, which « Écarts seulement »
    # retains, and counts its whole amount less under the one and more under the other; no nature
    # moves, and the deltas by subproject sum to those by nature, nil.
    rows = mockhistory.reference_rows()
    [first, other] = [entry["subproject_id"] for entry in fixture("subprojects")]

    def moved(row: mockcore.Row) -> mockcore.Row:
        facet = {**cast("Node", row.node["estimate_line"]), "subproject_id": other}
        return replace(row, node={**row.node, "estimate_line": facet})

    [line] = [row for row in rows if row.number == N.LABOUR]
    assert mockhistory.estimate_line(line)["subproject_id"] == first
    after = [moved(row) if row.number == N.LABOUR else row for row in rows]
    compared = mockcomparisons.comparison(rows, after, mockhistory.REFERENCE, mockhistory.REFERENCE)
    [node] = [node for node in compared["items"] if node["node_id"] == universe(N.LABOUR)]
    assert (node["difference"], node["changes"]) == ("modified", ["subproject"])
    kept = mockcomparisons.by_differences(compared, rows, after, mockdiff.DIFFERENCES)
    assert universe(N.LABOUR) in [node["node_id"] for node in kept["items"]]
    amount = money(line.amounts.budgeted)
    assert compared["amount_deltas"] == [
        {
            "dimension": "subproject",
            "key": key,
            "label": label,
            "budgeted_delta": delta,
            "reestimated_delta": delta,
        }
        for key, label, delta in (
            (first, "Poste de commande", f"-{amount}"),
            (other, "Essais et mise en service", amount),
        )
    ]


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_deltas_of_the_witness_by_subproject_sum_to_those_by_nature() -> None:
    # #1751 (E-01): the offer bore no subproject, the reference puts its lines of the installation
    # under the control station; « Câblage sur site », its budget unchanged, counts its whole
    # amount out of what bears no subproject and into the control station, modified by its
    # subproject. Each key's delta is the difference of its totals, and the deltas by subproject
    # sum to those by nature: 602 650,00 budgeted in `comparison`.
    compared = cast("Node", mockcomparisons.comparison_example(mockhistory.reference_rows()))
    value = cast("Node", compared["value"])
    [wiring] = [node for node in value["items"] if _label(node) == "Câblage sur site"]
    assert wiring["changes"] == ["reestimated_amount", "subproject"]
    by: dict[str, Decimal] = {}
    for entry in value["amount_deltas"]:
        by[entry["dimension"]] = by.get(entry["dimension"], Decimal(0)) + Decimal(
            entry["budgeted_delta"]
        )
    assert by == {"cost_type": Decimal("602650.00"), "subproject": Decimal("602650.00")}
    assert _summed(value) == {Decimal("602650.00"), Decimal("602950.00")}
    assert "la somme des écarts par sous-projet égale celle par nature" in str(compared["summary"])


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


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_witness_comparison_moves_the_reestimates_only_of_the_lines_the_amendment_changes(
    whole: Node,
) -> None:
    # Vérif : « les montants réestimés n'y diffèrent que par les lignes que le différentiel ajoute
    # ou retire, par celles des tâches démarrées qu'il termine et par celles dont il change l'année
    # de consommation ; une ligne existante dont le différentiel ne modifie que le montant budgété
    # ne présente aucun écart de montant réestimé ». From the offer 100 to the reference 101, the
    # amendment changes the hours of one line alone, and keeps the budget of the others (#467): a
    # line modified for its re-estimate alone bears the quantities it bore, and moves because its
    # year of consumption changes or, for labour, because the revision keeps the rates of 2026.
    offered = _lines_by_id(mockhistory.offer_rows())
    marked = _lines_by_id(mockhistory.reference_rows())
    # A line that changes its key alone — its subproject, its cost category — changes no amount
    # (#1751): what is tried here is what moves of its amounts.
    lines = [node for node in whole["items"] if node["kind"] == "estimate_line"]
    budget_changed = [node for node in lines if "budgeted_amount" in _amounts(node)]
    assert [node["node_id"] for node in budget_changed] == [universe(N.LABOUR)]
    assert _amounts(budget_changed[0]) == ["budgeted_amount", "reestimated_amount"]
    alone = [node for node in lines if _amounts(node) == ["reestimated_amount"]]
    assert len(alone) == LINES_REESTIMATED_ALONE
    # A line of disbursement would move by its year of consumption alone: none does, the offer
    # and the reference dating their lines alike from 2026 (#1628). Every one is a labour line.
    assert all(marked[node["node_id"]]["hours"] is not None for node in alone)
    rates = {2025: mockhistory.offer_rates(), 2026: LABOUR_RATES}
    for node in alone:
        before, after = offered[node["node_id"]], marked[node["node_id"]]
        for key in ("quantity", "hours", "unit_disbursement", "budgeted_amount"):
            assert before[key] == after[key]
        assert before["reestimated_amount"] != after["reestimated_amount"]
        # It moves because the reference keeps the rates of 2026, the offer those of 2025: its
        # amount at the rates of the reference year says it, whatever its year of consumption.
        hours = Decimal(after["quantity"]) * Decimal(after["hours"])
        for facet, year in ((before, 2025), (after, 2026)):
            assert facet["base_amount"] == money(hours * rates[year][facet["cost_category_id"]])


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
    assert sum(1 for node in modified if node["changes"]) == 4_251
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
    assert "4 251 modifiés par leurs propres valeurs" in summary
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


@pytest.mark.parametrize(
    "asked",
    [
        (mockdiff.ADDED,),
        (mockdiff.REMOVED,),
        (mockdiff.MODIFIED,),
        (mockdiff.ADDED, mockdiff.REMOVED),
        mockdiff.DIFFERENCES,
    ],
)
def test_the_filter_of_the_differences_retains_the_marks_asked_with_their_ancestors(
    whole: Node, asked: tuple[str, ...]
) -> None:
    # #1398: each node judged on its own mark, a line unchanged not retained with its task; the
    # ancestors of a node retained rendered, each modified by its content, so that the tree stays a
    # tree; the totals those of the reading without the filter, the deltas those of its lines.
    offer, reference = mockhistory.offer_rows(), mockhistory.reference_rows()
    read = cast("Node", mockcomparisons.by_differences(whole, offer, reference, asked))
    items: list[Node] = read["items"]
    by_id = {node["node_id"]: node for node in whole["items"]}
    expected: set[str] = set()
    for node in whole["items"]:
        if node["difference"] in asked:
            at = node["node_id"]
            while at is not None:
                expected.add(at)
                at = by_id[at]["parent_id"]
    assert items == [node for node in whole["items"] if node["node_id"] in expected]
    assert read["meta"] == whole["meta"]
    for node in items:
        assert node["parent_id"] is None or node["parent_id"] in expected
        if node["difference"] not in asked:
            assert (node["kind"], node["difference"]) == (mockcore.TASK, mockdiff.MODIFIED)
    # The totals are those of the reference structure, recomputed on every row, not those of the
    # lines retained (#1398): the sum of these alone is not the quantity of anything.
    assert read["totals"] == mockcore.whole(reference)["totals"]
    lines = {node["node_id"] for node in items if node["kind"] == mockcore.ESTIMATE_LINE}
    retained_budget = sum(
        (row.amounts.budgeted for row in reference if row.node["node_id"] in lines), Decimal(0)
    )
    assert Decimal(read["totals"]["budgeted_amount"]) != retained_budget

    def delta(dimension: str, field: str, key: str | None = None) -> Decimal:
        kept = [
            Decimal(entry[f"{field}_delta"])
            for entry in read["amount_deltas"]
            if entry["dimension"] == dimension and key in (None, entry["key"])
        ]
        return sum(kept, Decimal(0))

    def retained(rows: list[mockcore.Row], field: str, subproject: str | None = None) -> Decimal:
        return sum(
            (
                getattr(row.amounts, field)
                for row in rows
                if row.node["node_id"] in lines and subproject in (None, _subproject(row))
            ),
            Decimal(0),
        )

    for field in ("budgeted", "reestimated"):
        summed = retained(reference, field) - retained(offer, field)
        assert delta("cost_type", field) == summed
        assert delta("subproject", field) == summed
    for entry in read["amount_deltas"]:
        if entry["dimension"] == "subproject":
            key = entry["key"]
            for field in ("budgeted", "reestimated"):
                assert Decimal(entry[f"{field}_delta"]) == retained(
                    reference, field, key
                ) - retained(offer, field, key)


def test_the_example_of_the_differences_reads_the_additions_and_withdrawals_alone() -> None:
    # #1398: two of the three marks combined over the whole structure, the ancestors with them,
    # each a task modified by its content alone.
    example = mockcomparisons.examples()["comparison_differences.json"]
    items = cast("list[Node]", cast("Node", example["value"])["items"])
    assert {node["difference"] for node in items} == {"added", "removed", "modified"}
    assert all(
        node["kind"] == mockcore.TASK and not node["changes"]
        for node in items
        if node["difference"] == mockdiff.MODIFIED
    )
    assert "difference=added,removed" in cast("str", example["summary"])
