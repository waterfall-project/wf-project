# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the values a comparison renders of its base: the revision read in progress (EP-27).

They try the contract of ``compareRevisions`` as US-2320/L1 changed it, on the examples the fake
back serves: the revision read current or marked, the values the base carried (``base``), their
deltas (``deltas``), the mark of a node judged on every value it carries (``other``), and the
totals of the base (``base_totals``, ``totals_delta``).
"""

import json
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcomparisons, mockcore, mockdiff, mockhistory
from wftools.mockids import identifier, universe
from wftools.mockwitness import FIXTURES, SCHEDULED_AT, N, fixture

type Node = dict[str, Any]

pytestmark = pytest.mark.requirement("WF-REV-0080-A")


def _with_task(row: mockcore.Row, **values: Any) -> mockcore.Row:
    """Return a row of a task with some values of its facet replaced."""
    facet = {**cast("Node", row.node["task"]), **values}
    return replace(row, node={**row.node, "task": facet})


def _with_line(row: mockcore.Row, **values: Any) -> mockcore.Row:
    """Return a row of a line with some values of its facet replaced."""
    facet = {**cast("Node", row.node["estimate_line"]), **values}
    return replace(row, node={**row.node, "estimate_line": facet})


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


def _node_of(nodes: list[Node], number: int, rows: list[mockcore.Row]) -> Node:
    """Return the node of a row, as a comparison renders it."""
    [row] = [row for row in rows if row.number == number]
    [found] = [node for node in nodes if node["node_id"] == row.node["node_id"]]
    return found


def _compared_whole(before: list[mockcore.Row], after: list[mockcore.Row]) -> list[Node]:
    """Return the nodes of two sets of rows compared, over the whole structure."""
    return mockdiff.marked(before, after, compared=True)


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


@pytest.mark.requirement("WF-REV-0080-A")
@pytest.mark.requirement("WF-IHM-0160-A")
def test_the_planning_variant_carries_a_shifted_finish_a_removed_line_and_branches_unchanged() -> (
    None
):
    # EP-27, #3778; WF-REV-0080 (the delayed finish, the removed line, the amount modified) and
    # WF-IHM-0160 (the totals and the deltas of the amounts, the removed line counted in the base
    # alone): a task whose finish is later than its base's (`base.task.finish`,
    # `deltas.task.finish`), a line removed without base, an amount modified, and whole branches
    # without difference, a summary included, for the screen to fold.
    example = mockcomparisons.examples()["comparison_planning.json"]
    assert str(example["summary"]).startswith("Variante contrefactuelle")
    value = cast("Node", example["value"])
    items = {node["node_id"]: node for node in cast("list[Node]", value["items"])}
    delayed = items[universe(N.DESIGN_FILE)]
    assert delayed["difference"] == mockdiff.MODIFIED
    assert {"dates", "duration"} <= set(delayed["changes"])
    assert delayed["deltas"]["task"]["finish"] == mockcomparisons.PLANNING_DELAY_DAYS
    assert "finish" in delayed["base"]["task"]
    removed = items[universe(N.PROVISION)]
    assert (removed["difference"], removed["base"], removed["deltas"]) == ("removed", None, None)
    amount = items[universe(N.LABOUR)]
    assert amount["difference"] == mockdiff.MODIFIED
    assert Decimal(amount["deltas"]["estimate_line"]["budgeted_amount"]) > 0
    branch = [
        items[universe(number)]
        for number in (
            N.INSTALLATION,
            N.MOUNTING,
            N.WIRING_ON_SITE,
            N.TESTS_LINE,
            N.COMMISSIONING,
            N.COMMISSIONING_LINE,
            N.REFERENCE_PROVISION_753,
        )
    ]
    assert {(node["difference"], node["base"], node["deltas"]) for node in branch} == {
        ("unchanged", None, None)
    }
    assert branch[0]["task"]["is_summary"] is True
    # The removed provision is in the base and not in the read: 8 lines read, 9 in the base.
    assert value["totals"]["estimate_line_count"] == 8
    assert value["base_totals"]["estimate_line_count"] == 9
    [provision] = [
        entry
        for entry in value["amount_deltas"]
        if entry["dimension"] == "cost_type" and entry["label"] == "Provision"
    ]
    assert Decimal(provision["budgeted_delta"]) == Decimal("-250000.00")


@pytest.mark.parametrize(
    "name",
    [
        "comparison.json",
        "comparison_current.json",
        "comparison_moved.json",
        "comparison_planning.json",
    ],
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
    # « Une révision comparée à elle-même garde sa réponse » : every node unchanged, without base
    # nor deltas, and the totals of the base those read, their delta zero field by field.
    value = cast("Node", mockcomparisons.examples()["comparison_identical.json"]["value"])
    assert value["base_totals"] == value["totals"]
    assert {(node["difference"], node["base"], node["deltas"]) for node in value["items"]} == {
        ("unchanged", None, None)
    }
    assert value["totals_delta"] == {
        "task_count": 0,
        "estimate_line_count": 0,
        "hours": "0",
        "base_amount": "0.00",
        "budgeted_amount": "0.00",
        "reestimated_amount": "0.00",
    }


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


def _identified_anew(rows: list[mockcore.Row]) -> tuple[list[mockcore.Row], list[mockcore.Row]]:
    """Return the rows of a revision, and the same rows as a copy of it names them.

    The service copies a revision under new identifiers, the lineage kept (WF-DAT-0030): each node,
    each predecessor and the bearing task of each line named anew; each line given its bearing task
    on both sides, its parent, which the witness leaves out.
    """
    anew = {cast("str", row.node["node_id"]): identifier(9, at) for at, row in enumerate(rows)}
    ids = {row.number: cast("str", row.node["node_id"]) for row in rows}

    def bearing(row: mockcore.Row, names: dict[str, str]) -> mockcore.Row:
        if row.kind != mockcore.ESTIMATE_LINE or row.parent is None:
            return row
        return _with_line(row, bearing_task_node_id=names.get(ids[row.parent], ids[row.parent]))

    before = [bearing(row, {}) for row in rows]
    after: list[mockcore.Row] = []
    for row in rows:
        node = {**bearing(row, anew).node, "node_id": anew[cast("str", row.node["node_id"])]}
        if node.get("predecessors"):
            node["predecessors"] = [
                {**link, "predecessor_node_id": anew[link["predecessor_node_id"]]}
                for link in cast("list[Node]", node["predecessors"])
            ]
        after.append(replace(row, node=node))
    return before, after


def test_a_copy_under_new_identifiers_of_the_same_lineage_is_unchanged() -> None:
    # WF-REV-0080-A, matched by lineage (WF-DAT-0030-A): a parent, a predecessor and the bearing
    # task of a line are compared by the lineage of the node they name (`ComparedNodeBase`): a
    # revision copied under new identifiers is compared unchanged with its source, node by node.
    before, after = _identified_anew(mockhistory.reference_rows())
    nodes = mockdiff.marked(before, after, compared=True)
    marks = {(node["difference"], tuple(cast("list[str]", node["changes"]))) for node in nodes}
    assert marks == {("unchanged", ())}


def test_a_line_carried_by_another_task_names_the_bearing_task_of_the_base_as_rendered() -> None:
    # WF-REV-0080-A, the value of the base: the bearing task of the base is named by the node the
    # comparison renders for it, found by lineage, not by the identifier the base gives it.
    before, after = _identified_anew(mockhistory.reference_rows())
    moved = [
        _with_line(row, bearing_task_node_id=identifier(9, 0))
        if row.number == N.WIRING_ON_SITE
        else row
        for row in after
    ]
    node = _node_of(mockdiff.marked(before, moved, compared=True), N.WIRING_ON_SITE, moved)
    assert (node["difference"], node["changes"]) == ("modified", ["other"])
    [mounting] = [row for row in after if row.number == N.MOUNTING]
    assert node["base"] == {"estimate_line": {"bearing_task_node_id": mounting.node["node_id"]}}


def test_the_risk_a_node_comes_from_is_compared_as_it_is() -> None:
    # A risk keeps its identifier in every revision (WF-RIS-0020): a node whose origin changes is
    # modified by another value, its risk of the base in `base`.
    rows = mockhistory.reference_rows()
    risk = universe(701)
    from_risk = [
        replace(row, node={**row.node, "origin_risk_id": risk})
        if row.number == N.WIRING_ON_SITE
        else row
        for row in rows
    ]
    node = _node(_compared_whole(rows, from_risk), N.WIRING_ON_SITE)
    assert (node["difference"], node["changes"]) == ("modified", ["other"])
    assert node["base"] == {"origin_risk_id": None}


def test_a_subproject_renamed_alone_changes_nothing_of_the_line() -> None:
    # WF-REV-0080-A, what makes a node modified: a label resolved on read follows its identifier
    # (`ComparedNodeBase`): a subproject renamed, its identifier kept, neither marks the line nor
    # says `subproject`; another subproject, its label goes with it in `base`, and `changes` says
    # `subproject` alone.
    rows = mockhistory.reference_rows()
    [wiring] = [row for row in rows if row.number == N.WIRING_ON_SITE]
    facet = cast("Node", wiring.node["estimate_line"])
    renamed = [
        _with_line(row, subproject_label="Poste de commande renommé") if row is wiring else row
        for row in rows
    ]
    node = _node(_compared_whole(rows, renamed), N.WIRING_ON_SITE)
    assert (node["difference"], node["changes"], node["base"]) == ("unchanged", [], None)
    other = [
        _with_line(row, subproject_id=universe(802), subproject_label="Installation")
        if row is wiring
        else row
        for row in rows
    ]
    node = _node(_compared_whole(rows, other), N.WIRING_ON_SITE)
    assert (node["difference"], node["changes"]) == ("modified", ["subproject"])
    assert node["base"] == {
        "estimate_line": {
            "subproject_id": facet["subproject_id"],
            "subproject_label": facet["subproject_label"],
        }
    }


def test_a_duration_whose_unit_changes_and_an_amount_left_null_are_refused() -> None:
    # WF-REV-0080-A, the deltas of a modified node (`TaskDeltas`, WF-IHM-0150): the witness never
    # changes the unit of a duration from one revision to the other, and a facet always carries
    # its amounts; the generator refuses to write either delta rather than one the contract does
    # not hold.
    rows = mockhistory.reference_rows()
    [design] = [row for row in rows if row.number == N.DESIGN_FILE]
    facet = cast("Node", design.node["task"])
    duration = cast("Node", facet["duration"])
    unit = "w" if duration["unit"] != "w" else "d"
    for changed in (
        _with_task(design, duration={**duration, "unit": unit}),
        _with_task(design, base_amount=None),
    ):
        with pytest.raises(ValueError, match=r"task\.(duration|base_amount)"):
            _compared_whole(rows, [changed if row is design else row for row in rows])


def _bases(value: Any) -> list[Node]:
    """Return the line facets of every base a value holds (`ComparedNodeBase.estimate_line`)."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _bases(item)]
    if not isinstance(value, dict):
        return []
    entry = cast("Node", value)
    base = cast("Node", entry.get("base") or {})
    own: list[Node] = [base["estimate_line"]] if "estimate_line" in base else []
    return [*own, *(found for item in entry.values() for found in _bases(item))]


def test_the_identifiers_a_base_names_are_those_of_the_reference_and_the_project() -> None:
    # WF-REV-0080-A, the value of the base: a line of `base` is partial, which
    # ``test_mockcostsettings`` leaves out of the categories employed: each category, role and
    # subproject it names is one the witness holds.
    held = {
        "cost_category_id": fixture("volume/cost_categories")["items"],
        "resource_role_id": fixture("resource_roles")["items"],
        "subproject_id": fixture("subprojects"),
    }
    bases = [
        line
        for path in sorted(FIXTURES.rglob("comparison*.json"))
        for line in _bases(json.loads(path.read_text(encoding="utf-8")))
    ]
    assert bases
    for key, items in held.items():
        named = {line[key] for line in bases if line.get(key) is not None}
        assert named <= {item[key] for item in items}, key


def test_include_differences_is_a_parameter_of_the_comparison_alone() -> None:
    # WF-REV-0080-A, the comparison in the grids: `include_differences` retains the nodes in
    # difference that a progress filter leaves out; a comparison has some, the reading of a
    # structure (`listNodes`) none (`ComparisonIncludeDifferences`).
    text = (REPOSITORY / "docs/api/paths/revisions.yaml").read_text("utf-8")
    paths = cast("dict[str, dict[str, Any]]", yaml.safe_load(text))
    operations = [
        cast("Node", operation)
        for item in paths.values()
        for operation in item.values()
        if isinstance(operation, dict)
    ]
    declaring = {
        cast("str", operation["operationId"])
        for operation in operations
        if any(
            parameter.get("$ref", "").endswith("#/ComparisonIncludeDifferences")
            for parameter in cast("list[dict[str, str]]", operation.get("parameters", []))
        )
    }
    assert declaring == {"compareRevisions"}
