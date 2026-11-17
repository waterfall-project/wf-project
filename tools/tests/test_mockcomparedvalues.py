# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the values a comparison renders of its base: the revision read in progress (EP-27).

They try the contract of ``compareRevisions`` as US-2320/L1 changed it, on the examples the fake
back serves: the revision read current or marked, the values the base carried (``base``), their
deltas (``deltas``), the mark of a node judged on every value it carries (``other``), and the
totals of the base (``base_totals``, ``totals_delta``).
"""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockcomparisons, mockcore, mockdiff, mockhistory
from wftools.mockids import universe
from wftools.mockwitness import SCHEDULED_AT, N

type Node = dict[str, Any]

pytestmark = pytest.mark.requirement("WF-REV-0080-A")


def _with_task(row: mockcore.Row, **values: Any) -> mockcore.Row:
    """Return a row of a task with some values of its facet replaced."""
    facet = {**cast("Node", row.node["task"]), **values}
    return replace(row, node={**row.node, "task": facet})


def _compared(after: list[mockcore.Row]) -> list[Node]:
    """Return the nodes of the reference read against itself, changed as ``after`` says."""
    rows = mockhistory.reference_rows()
    compared = mockcomparisons.comparison(
        rows, after, mockhistory.REFERENCE, mockhistory.CURRENT, N.STUDIES
    )
    return cast("list[Node]", compared["items"])


def _node(nodes: list[Node], number: int) -> Node:
    [found] = [node for node in nodes if node["node_id"] == universe(number)]
    return found


def test_a_finish_pushed_back_five_days_is_modified_with_the_finish_of_the_base() -> None:
    # Vérif : « La révision en cours se compare à la révision marquée dont elle est issue : une
    # tâche dont la fin y est repoussée de cinq jours est présentée modifiée, avec la date de fin
    # de la base ; la date ramenée à celle de la base, la tâche n'est plus présentée modifiée. »
    rows = mockhistory.reference_rows()
    [design] = [row for row in rows if row.number == N.DESIGN_FILE]
    finish = cast("Node", cast("Node", design.node["task"])["finish"])
    later = date.fromisoformat(finish["date"]) + timedelta(days=5)
    pushed = _with_task(design, finish={**finish, "date": later.isoformat()})
    node = _node(_compared([pushed if row is design else row for row in rows]), N.DESIGN_FILE)
    assert (node["difference"], node["changes"]) == ("modified", ["dates"])
    assert node["base"] == {"task": {"finish": finish}}
    assert node["deltas"] == {"task": {"finish": 5}}
    back = _node(_compared(rows), N.DESIGN_FILE)
    assert (back["difference"], back["changes"], back["base"], back["deltas"]) == (
        "unchanged",
        [],
        None,
        None,
    )


def test_a_task_renamed_alone_is_modified_by_another_value_its_label_in_the_base() -> None:
    # A node of which any value differs is modified, a label included, which WF-REV-0080 does not
    # enumerate (`other`, decision of the author of 2026-11-15); a label bears no delta.
    rows = mockhistory.reference_rows()
    renamed = [
        _with_task(row, label="Dossier de conception révisé")
        if row.number == N.DESIGN_FILE
        else row
        for row in rows
    ]
    node = _node(_compared(renamed), N.DESIGN_FILE)
    assert (node["difference"], node["changes"]) == ("modified", ["other"])
    assert node["base"] == {"task": {"label": "Dossier de conception"}}
    assert node["deltas"] == {}


def test_a_duration_and_an_amount_bear_their_signed_deltas() -> None:
    # A duration in the unit of the duration read, an amount to the cent, the read less the base.
    rows = mockhistory.reference_rows()
    [design] = [row for row in rows if row.number == N.DESIGN_FILE]
    facet = cast("Node", design.node["task"])
    duration = cast("Node", facet["duration"])
    shorter = {**duration, "value": str(Decimal(duration["value"]) - 2)}
    cheaper = str(Decimal(facet["reestimated_amount"]) - Decimal("150.25"))
    changed = _with_task(design, duration=shorter, reestimated_amount=cheaper)
    node = _node(_compared([changed if row is design else row for row in rows]), N.DESIGN_FILE)
    assert node["changes"] == ["duration", "other"]
    assert node["deltas"] == {
        "task": {
            "duration": {"value": "-2", "unit": duration["unit"]},
            "reestimated_amount": "-150.25",
        }
    }


def test_the_mark_does_not_depend_on_the_fields_read_and_the_base_is_reduced_to_them() -> None:
    # A task renamed is modified on the planning as on the estimate; read with the amounts alone,
    # its base and its deltas carry none of what the reading leaves out.
    rows = mockhistory.reference_rows()
    renamed = [
        _with_task(row, label="Dossier révisé") if row.number == N.DESIGN_FILE else row
        for row in rows
    ]
    read = mockdiff.read_with_fields(_compared(renamed), ("task.reestimated_amount",))
    node = _node(read, N.DESIGN_FILE)
    assert (node["difference"], node["changes"], node["base"], node["deltas"]) == (
        "modified",
        ["other"],
        {},
        {},
    )
    assert set(node["task"]) == {"reestimated_amount"}


def test_the_current_revision_is_compared_with_the_reference_it_was_opened_from() -> None:
    # The example of the current revision read against the marked reference, on the installation
    # on site: read at the instant of the witness, never refused; its removed provision without
    # base, its lines modified by the remaining to commit the review wrote, none in the base.
    example = mockcomparisons.examples()["comparison_current.json"]
    value = cast("Node", example["value"])
    assert (value["from_revision_id"], value["to_revision_id"]) == (
        mockhistory.REFERENCE,
        mockhistory.CURRENT,
    )
    assert value["meta"]["scheduled_at"] == mockcore.stamp(SCHEDULED_AT)
    items = cast("list[Node]", value["items"])
    assert items[0]["node_id"] == universe(N.INSTALLATION)
    [removed] = [node for node in items if node["difference"] == mockdiff.REMOVED]
    assert (removed["base"], removed["deltas"]) == (None, None)
    lines = [
        node
        for node in items
        if node["kind"] == mockcore.ESTIMATE_LINE and node["difference"] == mockdiff.MODIFIED
    ]
    assert lines
    for line in lines:
        assert line["changes"] == ["other"]
        assert all(value is None for value in line["base"]["estimate_line"].values())
    assert "La révision en cours du témoin" in str(example["summary"])


@pytest.mark.parametrize(
    "name", ["comparison.json", "comparison_current.json", "comparison_moved.json"]
)
def test_the_totals_of_the_base_and_their_delta_answer_the_totals(name: str) -> None:
    # `totals_delta` is `totals` less `base_totals`, field by field (WF-IHM-0160), and the delta
    # of the budgeted amounts is that of the lines retained, `amount_deltas` summed by nature.
    value = cast("Node", mockcomparisons.examples()[name]["value"])
    totals, base, delta = value["totals"], value["base_totals"], value["totals_delta"]
    assert delta == mockcomparisons.totals_delta(totals, base)
    for key in ("task_count", "estimate_line_count"):
        assert delta[key] == totals[key] - base[key]
    by_nature = sum(
        (
            Decimal(entry["budgeted_delta"])
            for entry in value["amount_deltas"]
            if entry["dimension"] == "cost_type"
        ),
        Decimal(0),
    )
    assert Decimal(delta["budgeted_amount"]) == by_nature


def test_a_revision_compared_with_itself_has_equal_totals_and_no_base() -> None:
    # « Une révision comparée à elle-même garde sa réponse » : every node unchanged, without base.
    value = cast("Node", mockcomparisons.examples()["comparison_identical.json"]["value"])
    assert value["base_totals"] == value["totals"]
    assert {node["base"] for node in value["items"]} == {None}
    assert set(cast("Node", value["totals_delta"]).values()) <= {0, "0", "0.00"}


def test_the_reading_of_a_differential_never_says_another_value() -> None:
    # `other` is of a comparison alone: the read of a differential keeps the values WF-REV-0080
    # names, and renders neither base nor deltas (`NodeChange`).
    rows = mockhistory.reference_rows()
    renamed = [
        _with_task(row, label="Dossier révisé") if row.number == N.DESIGN_FILE else row
        for row in rows
    ]
    node = _node(mockdiff.marked(rows, renamed), N.DESIGN_FILE)
    assert (node["difference"], node["changes"]) == ("unchanged", [])
    assert "base" not in node
    assert "deltas" not in node
