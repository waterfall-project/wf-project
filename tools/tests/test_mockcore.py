# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the core of the witness dated and priced, and of the readings of listNodes it gives.

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from wftools import (
    REPOSITORY,
    mockcore,
    mockdata,
    mockhistory,
    mockids,
    mockstructure,
    mockwitness,
    mockwrites,
)
from wftools.mockids import universe
from wftools.mockwitness import TODAY, Line, Task

type Node = dict[str, Any]

STUDIES, DETAILED_STUDIES, STUDIES_LINE, DESKS, REVIEW, ACCEPTANCE, FILE = (
    521,
    522,
    527,
    523,
    524,
    525,
    526,
)
CONTROL_STATION, WIRING, LABOUR, BLOCKS, PROVISION, MILESTONE = 551, 552, 553, 554, 555, 556
OCCURRED, REMINDER, REMINDER_LINE, TRANSPORT, TRANSPORT_LINE = 541, 542, 543, 544, 545
INSTALLATION, MOUNTING, ON_SITE, TESTS, COMMISSIONING, COMMISSIONING_LINE = (
    561,
    562,
    563,
    564,
    565,
    566,
)


@pytest.fixture(scope="module")
def rows() -> list[mockcore.Row]:
    return mockcore.core()


@pytest.fixture(scope="module")
def readings() -> dict[str, Any]:
    """Read the named examples back from the text the generator writes."""
    return {
        name: json.loads(mockdata.render(example))["value"]
        for name, example in mockdata.readings().items()
    }


def nodes(reading: Any) -> dict[int, Node]:
    """Return the nodes of a reading by the number of their identifier."""
    items = cast("list[Node]", reading["items"])
    return {int(node["node_id"][-4:]): node for node in items}


def facet(node: Node) -> Node:
    return cast("Node", node[node["kind"]])


LIST_NODES = (
    "nodes.json",
    "nodes_planning.json",
    "nodes_estimate.json",
    "nodes_estimate_sorted.json",
    "nodes_estimate_hours.json",
    "nodes_installation.json",
    "nodes_milestone.json",
    "nodes_risk_occurred.json",
)


def test_every_reading_names_a_node_by_one_identifier_one_lineage_and_one_figure(
    readings: dict[str, Any],
) -> None:
    # One tree: a node read in two examples is the same node, down to its amounts (#287, C1).
    seen: dict[str, Node] = {}
    lineages: dict[str, str] = {}
    for name in LIST_NODES:
        items = cast("list[Node]", readings[name]["items"])
        identifiers = [node["node_id"] for node in items]
        assert len(identifiers) == len(set(identifiers)), name
        for node in items:
            assert seen.setdefault(node["node_id"], node) == node, (name, node["node_id"])
            assert lineages.setdefault(node["lineage_id"], node["node_id"]) == node["node_id"]
    assert len(seen) == 24
    assert set(seen) == {
        universe(number)
        for name in ("nodes.json", "nodes_estimate.json", "nodes_installation.json")
        for number in nodes(readings[name])
    }
    # No lineage is also a node: the two families are apart.
    assert not set(lineages) & set(seen)
    assert all(lineage == mockcore.lineage(int(node[-4:])) for lineage, node in lineages.items())


def test_a_labour_line_is_priced_by_its_hours_and_the_rate_of_the_reference_year(
    readings: dict[str, Any],
) -> None:
    estimate = nodes(readings["nodes_estimate.json"])
    labour, blocks, provision = (facet(estimate[n]) for n in (LABOUR, BLOCKS, PROVISION))
    assert (labour["hours"], labour["unit_disbursement"]) == ("12.5", None)
    assert labour["base_amount"] == "1000.00"
    assert labour["resource_role_label"] == "Ingénieur électricien"
    assert (blocks["unit_disbursement"], blocks["base_amount"]) == ("1234.56", "1234.56")
    # Neither amount is entered; a labour line enters its role and its hours, not a
    # disbursement; another its disbursement, not hours; a provision none of them, nor its
    # nature: its quantity and its disbursement come from its risk.
    for node in estimate.values():
        assert not any("amount" in name for name in node["editable_fields"]), node["node_id"]
    assert "estimate_line.hours" in estimate[LABOUR]["editable_fields"]
    assert "estimate_line.unit_disbursement" not in estimate[LABOUR]["editable_fields"]
    assert "estimate_line.hours" not in estimate[BLOCKS]["editable_fields"]
    assert estimate[PROVISION]["editable_fields"] == [
        "estimate_line.label",
        "estimate_line.payment_delay_days",
        "estimate_line.subproject_id",
    ]
    assert estimate[PROVISION]["computed_fields"] == [
        "estimate_line.quantity",
        "estimate_line.unit_disbursement",
    ]
    assert (provision["is_computed"], provision["base_amount"]) == (True, "500.00")
    # The provision of 751 today, 1,250 at 40 %, budgeted at the 250 the reference 101 knew —
    # 1,000 at 25 % — which the reserve for risks counts, never the reference budget
    # (WF-RIS-0050): the budgeted total of the lot is 2,484.56, not the 2,734.56 of its lines.
    assert provision["budgeted_amount"] == str(mockwitness.REFERENCE_PROVISION_751)
    # The last review before the reference 101 was marked (1 February) is what justifies it.
    reviews = cast("list[dict[str, str]]", mockwitness.fixture("risk_reviews"))
    before = [
        review
        for review in reviews
        if date.fromisoformat(review["reviewed_on"]) <= mockwitness.AMENDMENT_MERGED.on
    ]
    known = max(before, key=lambda review: review["reviewed_on"])
    assert Decimal(known["severity"]) * Decimal(known["probability"]) == Decimal("250.00")
    assert facet(estimate[WIRING])["budgeted_amount"] == "2484.56"


def test_a_task_sums_its_lines_and_its_subordinates_and_the_totals_sum_the_lines_alone(
    readings: dict[str, Any],
) -> None:
    estimate = nodes(readings["nodes_estimate.json"])
    wiring, lot = facet(estimate[WIRING]), facet(estimate[CONTROL_STATION])
    assert wiring["base_amount"] == "2734.56"
    assert (lot["base_amount"], lot["budgeted_amount"]) == ("2934.56", "2484.56")
    assert readings["nodes_estimate.json"]["totals"] == {
        "task_count": 6,
        "estimate_line_count": 5,
        "hours": "12.5",
        "base_amount": "2934.56",
        "budgeted_amount": "2484.56",
        "reestimated_amount": "2934.56",
        "inflated_amount": "2934.56",
    }
    # Read in the reference year, a line is not corrected: its amounts agree (WF-DEV-0030).
    for node in estimate.values():
        assert facet(node)["inflated_amount"] == facet(node)["base_amount"]


def test_the_lines_merged_by_the_occurrence_are_budgeted_nothing_in_the_same_tree(
    readings: dict[str, Any],
) -> None:
    occurred = nodes(readings["nodes_risk_occurred.json"])
    estimate = nodes(readings["nodes_estimate.json"])
    assert sorted(occurred) == [OCCURRED, REMINDER, REMINDER_LINE, TRANSPORT, TRANSPORT_LINE]
    # The subtree of 541 alone, read from the tree of the estimate, under the control station.
    assert all(occurred[number] == estimate[number] for number in occurred)
    assert occurred[OCCURRED]["parent_id"] == universe(CONTROL_STATION)
    for number, amount in ((REMINDER_LINE, "120.00"), (TRANSPORT_LINE, "80.00")):
        line = facet(occurred[number])
        assert (line["budgeted_amount"], line["reestimated_amount"]) == ("0.00", amount)
        assert line["is_computed"] is False
    assert not any(facet(node).get("is_computed") for node in occurred.values())
    assert readings["nodes_risk_occurred.json"]["totals"] == {
        "task_count": 3,
        "estimate_line_count": 2,
        "hours": "0",
        "base_amount": "200.00",
        "budgeted_amount": "0.00",
        "reestimated_amount": "200.00",
        "inflated_amount": "200.00",
    }
    assert mockwitness.RISK_752_OCCURRED.on < mockwitness.STUDIES_STARTED.on


def test_the_readings_are_read_today_the_third_of_june(readings: dict[str, Any]) -> None:
    # Not the middle of April any more (#287, C14): the studies are over, the wiring runs.
    assert date(2026, 6, 3) == mockcore.READ_ON
    planning = nodes(readings["nodes_planning.json"])
    studies = facet(planning[DETAILED_STUDIES])
    assert (studies["progress"], studies["completed_on"]) == ("completed", "2026-04-10")
    desks = facet(planning[DESKS])
    assert (desks["scheduling_mode"], desks["progress"]) == ("manual", "started")
    assert (desks["finish"]["date"], desks["finish_overdue"]) == ("2026-04-24", True)
    estimate = nodes(readings["nodes_estimate.json"])
    wiring = facet(estimate[WIRING])
    assert (wiring["progress"], wiring["started_on"]) == ("started", "2026-05-04")
    assert wiring["finish"] == {"date": "2026-06-30", "hours": "8"}
    assert "completed_on" not in wiring
    acceptance = facet(estimate[MILESTONE])
    assert acceptance["progress"] == "not_started"
    assert acceptance["start"] == acceptance["finish"] == {"date": "2026-06-30", "hours": "8"}
    assert all("2026-04" not in str(facet(node).get("start")) for node in estimate.values())
    for example in mockdata.readings().values():
        summary = str(example["summary"])
        assert "le 3 juin 2026" in summary or summary.startswith("Ce dont dépend"), summary


def test_the_progress_is_read_at_the_day_given() -> None:
    # Read in the middle of April, the same tree tells where it was then.
    # The reception of the studies is declared completed by a gesture made on 24 April: before it,
    # nothing completes it by itself (WF-RAE-0030).
    then = {row.number: facet(row.node) for row in mockcore.core(today=date(2026, 4, 15))}
    assert then[DETAILED_STUDIES]["progress"] == "completed"
    assert then[REVIEW]["progress"] == "started"
    assert then[ACCEPTANCE]["progress"] == "not_started"
    after = {row.number: facet(row.node) for row in mockcore.core(today=date(2026, 4, 24))}
    assert after[ACCEPTANCE]["progress"] == "completed"
    assert then[WIRING]["progress"] == "not_started"
    assert "started_on" not in then[WIRING]
    # A started task past its finish is overdue; the desks, declared started, already were.
    assert then[DESKS]["finish_overdue"] is False


def test_a_summary_is_started_with_one_subordinate_and_completed_after_the_last(
    readings: dict[str, Any],
) -> None:
    planning = nodes(readings["nodes_planning.json"])
    estimate = nodes(readings["nodes_estimate.json"])
    # The desks still run: the studies are started, though every other subordinate is over.
    assert facet(planning[STUDIES])["progress"] == "started"
    assert facet(estimate[OCCURRED])["progress"] == "completed"
    assert facet(estimate[CONTROL_STATION])["progress"] == "started"
    for summary in (planning[STUDIES], estimate[CONTROL_STATION], estimate[OCCURRED]):
        assert summary["computed_fields"] == [
            "task.duration",
            "task.start",
            "task.finish",
            "task.progress",
        ]
        # A summary accepts its label, its description and its attachment to the work
        # breakdown (WF-PLA-0130).
        assert summary["editable_fields"] == [
            "task.label",
            "task.description",
            "task.order_item_id",
            "task.work_package_id",
        ]
        assert "total_float" not in facet(summary)
    # Its dates of progress are its subordinates': started with the first, completed with the
    # last — the studies are not completed, the occurrence is.
    assert facet(planning[STUDIES])["started_on"] == "2026-03-02"
    assert "completed_on" not in facet(planning[STUDIES])
    assert facet(estimate[OCCURRED])["started_on"] == "2026-05-04"
    assert facet(estimate[OCCURRED])["completed_on"] == "2026-05-15"
    assert facet(planning[STUDIES])["start"] == {"date": "2026-03-02", "hours": "0"}
    assert facet(planning[STUDIES])["finish"] == {"date": "2026-04-24", "hours": "8"}
    assert facet(planning[STUDIES])["duration"] == {"value": "40", "unit": "d"}


def test_the_critical_path_and_the_float_follow_the_links_of_the_core(
    readings: dict[str, Any],
) -> None:
    planning = nodes(readings["nodes_planning.json"])
    estimate = nodes(readings["nodes_estimate.json"])
    tasks = {**planning, **estimate}
    installation = nodes(readings["nodes_installation.json"])
    tasks = {**tasks, **installation}
    critical = [n for n, node in tasks.items() if facet(node).get("is_critical")]
    # The core is linked to the tasks drawn about it (#376): the lots of the control station
    # follow its factory acceptance, on the critical path of the whole structure, which ends in
    # August 2029; the installation on site leads to the commissioning of the control station.
    assert critical == [DETAILED_STUDIES, REVIEW, ACCEPTANCE, WIRING, MILESTONE]
    assert all(facet(tasks[n])["total_float"] == {"value": "0", "unit": "d"} for n in critical)
    assert facet(installation[MOUNTING])["total_float"] == {"value": "597.5", "unit": "d"}
    assert facet(installation[COMMISSIONING])["total_float"] == {"value": "597.5", "unit": "d"}
    # The design file, without a successor, may wait for the end of the whole structure.
    assert facet(planning[FILE])["total_float"] == {"value": "880.5", "unit": "d"}
    assert facet(installation[COMMISSIONING])["finish"] == {"date": "2027-01-01", "hours": "8"}
    assert facet(planning[FILE])["start"] == {"date": "2026-04-09", "hours": "0"}
    # A task in manual mode shows no float and is never critical; its successor is.
    assert (facet(planning[DESKS])["total_float"], facet(planning[DESKS])["is_critical"]) == (
        None,
        False,
    )
    assert planning[DESKS]["computed_fields"] == []
    assert {"task.start", "task.finish"} <= set(planning[DESKS]["editable_fields"])
    # The two tasks of the occurrence, in parallel with the wiring, may wait for the end too.
    assert facet(estimate[REMINDER])["total_float"] == {"value": "858.5", "unit": "d"}
    assert facet(estimate[TRANSPORT])["total_float"] == {"value": "858.5", "unit": "d"}


def test_a_milestone_is_a_task_of_no_duration_at_one_instant(readings: dict[str, Any]) -> None:
    planning = nodes(readings["nodes_planning.json"])
    milestone = nodes(readings["nodes_milestone.json"])
    for node in (planning[ACCEPTANCE], milestone[MILESTONE]):
        task = facet(node)
        assert (task["is_milestone"], task["duration"]) == (True, {"value": "0", "unit": "d"})
        assert task["start"] == task["finish"]
        assert "task.duration" not in node["editable_fields"]
    # Where its predecessors finish: the Friday at 8 hours, not the Monday after. Completed, a
    # milestone never started: it goes from not started to completed.
    assert facet(planning[ACCEPTANCE])["finish"] == {"date": "2026-04-24", "hours": "8"}
    assert facet(planning[ACCEPTANCE])["completed_on"] == "2026-04-24"
    assert "started_on" not in facet(planning[ACCEPTANCE])
    assert "started_on" not in facet(milestone[MILESTONE])
    assert planning[ACCEPTANCE]["predecessors"] == [
        {
            "predecessor_node_id": universe(REVIEW),
            "predecessor_row_number": 5,
            "link_type": "finish_to_start",
            "lag": {"value": "0", "unit": "d"},
        },
        {
            "predecessor_node_id": universe(DESKS),
            "predecessor_row_number": 4,
            "link_type": "start_to_start",
            "lag": {"value": "1", "unit": "w"},
        },
    ]


def test_a_reading_numbers_its_rows_in_the_whole_structure_and_sums_what_it_retains(
    readings: dict[str, Any],
) -> None:
    def numbers(name: str) -> list[int]:
        return [node["row_number"] for node in readings[name]["items"]]

    # The planning leaves out the line of row 3; the estimate follows the studies.
    assert numbers("nodes.json") == [1, 2, 3, 4, 5, 6, 7]
    assert numbers("nodes_planning.json") == [1, 2, 4, 5, 6, 7]
    assert numbers("nodes_estimate.json") == list(range(8, 19))
    assert numbers("nodes_risk_occurred.json") == [13, 14, 15, 16, 17]
    assert [node["level"] for node in readings["nodes_risk_occurred.json"]["items"]] == [
        2,
        3,
        4,
        3,
        4,
    ]
    # A link names its predecessor by its number, read or not.
    wiring = nodes(readings["nodes_estimate.json"])[WIRING]
    assert wiring["predecessors"][0]["predecessor_row_number"] == 6
    # A search renders the ancestors of what it finds, and counts them in no total.
    assert numbers("nodes_milestone.json") == [8, 18]
    assert readings["nodes_milestone.json"]["totals"]["task_count"] == 1
    assert readings["nodes_milestone.json"]["totals"]["estimate_line_count"] == 0
    # The tasks alone have the totals of the full reading: `kinds` renders, never sums (#487).
    assert readings["nodes_planning.json"]["totals"] == readings["nodes.json"]["totals"]
    assert readings["nodes_planning.json"]["totals"]["task_count"] == 6
    assert readings["nodes.json"]["totals"]["budgeted_amount"] == "100000.00"
    assert readings["nodes.json"]["totals"]["estimate_line_count"] == 1


def test_a_search_of_the_structure_ignores_the_case_and_the_accents(
    rows: list[mockcore.Row],
) -> None:
    # « etudes » finds the tasks labelled « Études… », which hold it only without their accent.
    reading: dict[str, Any] = mockcore.search(rows, "etudes")
    found = {node["node_id"] for node in reading["items"]}
    accented = [row for row in rows if "Études" in row.label]
    assert accented
    assert all("etudes" not in row.label.lower() for row in accented)
    assert {cast("str", row.node["node_id"]) for row in accented} <= found


def test_the_dependencies_name_the_rows_of_the_tree_by_their_number_and_label(
    readings: dict[str, Any], rows: list[mockcore.Row]
) -> None:
    summary = readings["dependencies_summary.json"]
    assert (summary["node_id"], summary["field"]) == (universe(STUDIES), "task.finish")
    assert summary["depends_on"] == ["subordinates"]
    planning = nodes(readings["nodes_planning.json"])
    assert summary["rows"] == [
        {
            "node_id": universe(n),
            "row_number": planning[n]["row_number"],
            "label": facet(planning[n])["label"],
        }
        for n in (DETAILED_STUDIES, DESKS, REVIEW, ACCEPTANCE, FILE)
    ]
    # Read again after a row was inserted above them: the same rows, one further down.
    moved = readings["dependencies_summary_moved.json"]
    assert [row["row_number"] for row in moved["rows"]] == [3, 5, 6, 7, 8]
    assert [row["node_id"] for row in moved["rows"]] == [row["node_id"] for row in summary["rows"]]
    amount = readings["dependencies_task_amount.json"]
    assert (amount["node_id"], amount["depends_on"]) == (
        universe(WIRING),
        ["lines_and_subordinates"],
    )
    assert [row["row_number"] for row in amount["rows"]] == [10, 11, 12]
    for name, number, field, rule in (
        ("dependencies_labour.json", LABOUR, "estimate_line.base_amount", "hourly_rate"),
        ("dependencies_provision.json", PROVISION, "estimate_line.quantity", "risk"),
        ("dependencies_manual_float.json", DESKS, "task.total_float", "manual_mode"),
    ):
        answer = readings[name]
        assert (answer["node_id"], answer["field"]) == (universe(number), field)
        assert (answer["depends_on"], answer["rows"]) == ([rule], [])
    assert mockcore.dependencies(rows, BLOCKS, "estimate_line.base_amount")["depends_on"] == [
        "unit_disbursement"
    ]
    with pytest.raises(ValueError, match=r"task\.label of Études is not a computed value"):
        mockcore.dependencies(rows, STUDIES, "task.label")


def test_the_physical_progress_of_a_summary_is_the_budget_of_its_completed_tasks(
    readings: dict[str, Any],
) -> None:
    planning = nodes(readings["nodes_planning.json"])
    estimate = nodes(readings["nodes_estimate.json"])
    # The whole budget of the studies is on the detailed studies, completed; nothing of the
    # control station's is on a completed task; the occurrence has no budget at all.
    assert facet(planning[STUDIES])["physical_progress"] == mockstructure.computable("1")
    assert facet(estimate[CONTROL_STATION])["physical_progress"] == mockstructure.computable("0")
    assert facet(estimate[OCCURRED])["physical_progress"] == {
        "is_computable": False,
        "value": None,
        "reason": "no_budgeted_amount",
    }
    assert "physical_progress" not in facet(planning[DETAILED_STUDIES])


_STRUCTURE_NODES = next(f for f in mockids.IDENTIFIERS if f.what == "nœuds de la structure")
_STRUCTURE_LINEAGES = next(f for f in mockids.IDENTIFIERS if f.first == 600)

_RENAMED = {
    ("task_renamed.json", universe(WIRING)),
    ("task_renamed.json", mockcore.lineage(WIRING)),
}
"""The one node a write renames, by its node and its lineage, in the fixture that answers it
(``wftools.mockwrites`` generates it)."""


def _named(value: Any, found: list[tuple[str, str, str]]) -> None:
    """Collect each (identifier, kind, label) a value gives a node or a lineage of the core."""
    if isinstance(value, list):
        for item in cast("list[Any]", value):
            _named(item, found)
        return
    if not isinstance(value, dict):
        return
    fields = cast("dict[str, Any]", value)
    for key, family in (("node_id", _STRUCTURE_NODES), ("lineage_id", _STRUCTURE_LINEAGES)):
        identifier = fields.get(key)
        if not isinstance(identifier, str) or not family.holds(identifier):
            continue
        kind = fields.get("kind") or fields.get("target") or ""
        # A difference of an import on a link is named by its successor, the task whose column
        # of predecessors presents it (#364): its lineage and its label are the task's.
        kind = "task" if kind == "link" else kind
        label = fields.get("label") or fields.get("milestone_label")
        for facet_name in ("task", "estimate_line"):
            inner = fields.get(facet_name)
            if isinstance(inner, dict):
                label = cast("dict[str, Any]", inner).get("label", label)
        if isinstance(label, str):
            found.append((identifier, str(kind), label))
    for item in fields.values():
        _named(item, found)


def test_a_node_or_a_lineage_of_the_core_bears_one_kind_and_one_label_in_the_whole_universe() -> (
    None
):
    # C1 and C17 (#287): the readings, the writes, the risks, the imports and the trackings name
    # the same node by the same identifier, lineage, kind and label — the comparison of two
    # revisions too, generated from the core since L23 (C12).
    names: dict[str, set[tuple[str, str]]] = {}
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        found: list[tuple[str, str, str]] = []
        _named(json.loads(path.read_text(encoding="utf-8"))["value"], found)
        for identifier, kind, label in found:
            if (path.name, identifier) not in _RENAMED:
                names.setdefault(identifier, set()).add((kind, label))
    contradictions = {identifier: kinds for identifier, kinds in names.items() if len(kinds) > 1}
    # A kind may be left unsaid (a tracking names a milestone by its label alone): the labels
    # must agree, and the kinds said must agree.
    for identifier, kinds in list(contradictions.items()):
        labels = {label for _, label in kinds}
        said = {kind for kind, _ in kinds if kind}
        if len(labels) == 1 and len(said) <= 1:
            del contradictions[identifier]
    assert contradictions == {}
    # The risk 751 names its line of provision, the import of the estimate its lines.
    risks = {risk["risk_id"]: risk for risk in mockwitness.fixture("risks")["items"]}
    assert risks[universe(751)]["provision_node_id"] == universe(PROVISION)
    assert mockwitness.fixture("risk")["provision_node_id"] == universe(PROVISION)
    cited = {
        difference["lineage_id"]
        for difference in mockwitness.fixture("import_analysed")["report"]["differences"]
        if difference["lineage_id"] is not None
    }
    assert cited == {mockcore.lineage(LABOUR), mockcore.lineage(BLOCKS)}


def test_an_example_that_names_a_label_of_the_core_names_it_by_the_core_identifiers(
    rows: list[mockcore.Row],
) -> None:
    # The converse of the test above: an example written by hand that names a task or a line of
    # the core by its label names it by the node or the lineage the core gives it, never by
    # another number of the families of the structure (C1, #287).
    by_label: dict[str, set[str]] = {}
    for row in rows:
        by_label.setdefault(row.label, set()).update(
            {universe(row.number), mockcore.lineage(row.number)}
        )
    strays: list[tuple[str, str, str]] = []
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        found: list[tuple[str, str, str]] = []
        _named(json.loads(path.read_text(encoding="utf-8"))["value"], found)
        strays.extend(
            (path.name, identifier, label)
            for identifier, _, label in found
            if label in by_label
            and (path.name, identifier) not in _RENAMED
            and identifier not in by_label[label]
        )
    assert strays == []


def test_a_name_declared_generated_that_the_generator_does_not_write_fails_the_check(
    tmp_path: Path,
) -> None:
    mockdata.write(tmp_path)
    assert mockdata.check(tmp_path) == []
    assert mockdata.check(tmp_path, [*mockdata.named(), "nodes_gone.json"]) == [
        "nodes_gone.json is declared generated by make mock-data, which does not write it"
    ]
    assert set(mockdata.declared_names()) == set(mockdata.named())


def test_the_readings_are_the_fixtures_the_front_reads(readings: dict[str, Any]) -> None:
    for name, value in readings.items():
        assert mockwitness.fixture(name.removesuffix(".json")) == value, name


def test_a_line_without_hours_nor_disbursement_cannot_be_priced() -> None:
    with pytest.raises(ValueError, match="the line 999 has neither hours nor a unit disbursement"):
        mockcore.price(Line(999, "Rien", mockwitness.EQUIPMENT), 2026)
    with pytest.raises(ValueError, match="a line is borne by a task"):
        _ = mockcore.Place(None, 0, 1, 1).bearing


def test_a_task_of_another_year_is_corrected_for_inflation() -> None:
    # A line consumed two years after the reference year, at 3 %: 1.03 x 1.03 its amount.
    later = Task(
        591,
        "Plus tard",
        days=1,
        manual=(date(2028, 1, 3), date(2028, 1, 3)),
        progress="not_started",
        lines=(Line(592, "Matériel", mockwitness.EQUIPMENT, unit=Decimal("100.00")),),
    )
    [task, line] = mockcore.core((later,))
    assert facet(line.node)["consumption_year"] == 2028
    assert (facet(line.node)["base_amount"], facet(line.node)["inflated_amount"]) == (
        "100.00",
        "106.09",
    )
    assert facet(task.node)["inflated_amount"] == "106.09"


def test_the_lot_of_the_control_station_bears_the_one_order_item_of_the_witness(
    readings: dict[str, Any],
) -> None:
    estimate = nodes(readings["nodes_estimate.json"])
    planning = nodes(readings["nodes_planning.json"])
    lot = facet(estimate[CONTROL_STATION])
    assert lot["order_item_id"] == mockwitness.ASSEMBLY.identifier
    assert lot["work_package_id"] is None
    assert lot["work_breakdown_label"] == "Fourniture et montage des armoires"
    # The same order item as the totals by order item of the estimate name (WF-DEV-0060).
    breakdown = mockwitness.fixture("estimate_indicators_breakdown")["by_order_item"]
    assert [entry["key"] for entry in breakdown] == [lot["order_item_id"]]
    # Neither the studies nor the occurrence bear one: an order item is borne by one summary.
    assert "order_item_id" not in facet(planning[STUDIES])
    assert "order_item_id" not in facet(estimate[OCCURRED])


def test_the_tasks_inscribed_name_the_timelines_of_the_witness_and_its_tracked_milestones(
    readings: dict[str, Any],
) -> None:
    core = nodes(readings["nodes_core.json"])
    timelines = {entry["timeline_id"]: entry["label"] for entry in readings["timelines.json"]}
    assert list(timelines.values()) == ["Comité de pilotage", "Revue client"]
    inscribed = {
        number: [entry["timeline_id"] for entry in facet(node).get("tracking", [])]
        for number, node in core.items()
        if node["kind"] == "task"
    }
    steering, customer = timelines
    assert {number: entries for number, entries in inscribed.items() if entries} == {
        STUDIES: [steering],
        ACCEPTANCE: [steering, customer, None],
        MILESTONE: [steering, customer, None],
        COMMISSIONING: [steering],
    }
    # The milestones of the time/time tracking are those its diagram follows (WF-PLA-0060).
    tracked = mockwitness.fixture("milestone_tracking")["milestones"]
    assert [entry["lineage_id"] for entry in tracked] == [
        core[ACCEPTANCE]["lineage_id"],
        core[MILESTONE]["lineage_id"],
    ]


def test_the_nested_variant_has_four_levels_of_tasks_a_summary_at_the_third(
    readings: dict[str, Any],
) -> None:
    nested = nodes(readings["nodes_nested.json"])
    levels = {number: node["level"] for number, node in nested.items()}
    assert (levels[INSTALLATION], levels[CONTROL_STATION], levels[OCCURRED]) == (1, 2, 3)
    assert levels[REMINDER] == levels[TRANSPORT] == 4
    assert facet(nested[OCCURRED])["is_summary"] is True
    assert all(node["kind"] == "task" for node in nested.values())


def test_the_task_tree_reads_the_summaries_down_to_the_level_asked(
    readings: dict[str, Any],
) -> None:
    # #463: the four levels of the nested variant asked at the level 2 — the summaries of the
    # first two, under the node of the project the front draws; no leaf, no milestone, and not
    # the subtree of the occurrence, a summary of the third. Nothing sums.
    tree = readings["nodes_summaries.json"]
    found = nodes(tree)
    assert list(found) == [STUDIES, INSTALLATION, CONTROL_STATION]
    assert all(facet(node)["is_summary"] and node["level"] <= 2 for node in found.values())
    assert tree["totals"]["task_count"] == 3
    assert tree["totals"]["estimate_line_count"] == 0


def test_a_reading_says_the_level_of_the_deepest_summary_of_its_structure_whatever_it_retains() -> (
    None
):
    # #494: each example of listNodes the contract cites says the depth of the structure it reads,
    # whatever it retains — a filter, a search, a timeline, `kinds`, the level asked.
    contract = (REPOSITORY / "docs/api/paths/revisions.yaml").read_text(encoding="utf-8")
    block = contract[contract.index("operationId: listNodes") :]
    block = block[: block.index("'400'")]
    cited = set(re.findall(r"fixtures/api/(\S+)\.json", block))
    current, alone = mockcore.current(), mockcore.alone()
    nested = mockcore.alone(mockdata.nested())
    structures = {
        "volume/nodes_thousand": current,
        "nodes": current,
        "nodes_milestone": current,
        "nodes_estimate": current,
        "nodes_estimate_sorted": current,
        "nodes_estimate_hours": current,
        "nodes_installation": current,
        "nodes_planning": current,
        "nodes_risk_occurred": current,
        "nodes_timeline": current,
        "nodes_core": alone,
        "nodes_nested": nested,
        "nodes_summaries": nested,
    }
    depths = {name: mockcore.summary_depth(rows) for name, rows in structures.items()}
    depths["nodes_summaries_leaves"] = 0
    assert set(depths) == cited
    assert (depths["nodes"], depths["nodes_core"], depths["nodes_summaries"]) == (2, 2, 3)
    for name, depth in depths.items():
        assert mockwitness.fixture(name)["meta"] == {"summary_depth": depth}, name
    # A reading without a filter renders every summary: its depth is that of its own items.
    for name in ("volume/nodes_thousand", "nodes_core"):
        read = mockwitness.fixture(name)
        deepest = max(
            node["level"]
            for node in read["items"]
            if node["kind"] == "task" and node["task"]["is_summary"]
        )
        assert read["meta"] == {"summary_depth": deepest}, name
    # The tree asked at the level 2 is told the third exists, which it does not render.
    shown = mockwitness.fixture("nodes_summaries")["items"]
    assert max(node["level"] for node in shown) == 2


def test_a_timeline_reads_the_tasks_inscribed_on_it_without_their_ancestors(
    readings: dict[str, Any],
) -> None:
    # #463: the steering committee, in the order of the plan, without the lot and the
    # installation that bear what is inscribed on it: a timeline is no tree (WF-PLA-0140).
    found = nodes(readings["nodes_timeline.json"])
    assert list(found) == [STUDIES, ACCEPTANCE, MILESTONE, COMMISSIONING]
    # Every task inscribed on it is rendered: those whose `tracking` names it, in the core.
    entry = {"kind": "timeline", "timeline_id": mockwitness.STEERING}
    inscribed = [
        row.number
        for row in mockcore.core()
        if row.kind == mockcore.TASK
        and entry in cast("list[Node]", cast("Node", row.node["task"]).get("tracking", []))
    ]
    assert list(found) == inscribed
    for node in found.values():
        entries = cast("list[Node]", facet(node)["tracking"])
        assert {"kind": "timeline", "timeline_id": mockwitness.STEERING} in entries


def test_the_core_is_dated_in_the_order_of_its_links_whatever_the_order_of_the_plan(
    readings: dict[str, Any],
) -> None:
    # The review linked to the design file too, a predecessor further down the plan: dated after
    # it, it starts after the design file finishes, 15 April, and names it by its row.
    review = next(task for task in mockcore.tasks_in_order() if task.number == REVIEW)
    roots = mockwrites.amended(
        mockwitness.CORE,
        mockwrites.on_task(REVIEW, links=(*review.links, mockwitness.Link(FILE))),
    )
    dated = mockcore.schedule(roots)
    assert dated[FILE].finish.day == date(2026, 4, 15)
    assert dated[REVIEW].start.day > dated[FILE].finish.day
    node = next(row.node for row in mockcore.core(roots) if row.number == REVIEW)
    links = cast("list[dict[str, Any]]", node["predecessors"])
    assert [link["predecessor_row_number"] for link in links] == [2, 7]
    # Unlinked, the order of the plan stands; the whole reading gives every row and the totals.
    order = [task.number for task in mockcore.in_link_order(mockcore.tasks_in_order())]
    assert order == [task.number for task in mockcore.tasks_in_order()]
    whole = readings["nodes_core.json"]
    assert [item["row_number"] for item in whole["items"]] == list(range(1, 25))
    assert whole["totals"]["task_count"] == 15


def test_a_leaf_accepts_its_attachment_to_the_work_breakdown_after_its_other_fields(
    readings: dict[str, Any],
) -> None:
    # Every task, leaf included, accepts an order item or a work package (#411, WF-PLA-0130):
    # an automatic leaf enters neither date, a manual one both, in the order of `EditableField`.
    nodes = {node["node_id"]: node for node in readings["nodes_planning.json"]["items"]}
    assert nodes[universe(522)]["editable_fields"] == [
        "task.label",
        "task.description",
        "task.scheduling_mode",
        "task.duration",
        "task.progress",
        "task.order_item_id",
        "task.work_package_id",
    ]
    assert nodes[universe(523)]["editable_fields"] == [
        "task.label",
        "task.description",
        "task.scheduling_mode",
        "task.duration",
        "task.start",
        "task.finish",
        "task.progress",
        "task.order_item_id",
        "task.work_package_id",
    ]


def _numbers(answer: Any) -> dict[str, list[int]]:
    """Return the numbers of the tasks of each column of a Kanban, read back as JSON."""
    columns = cast("dict[str, list[Node]]", json.loads(json.dumps(answer)))
    return {key: [int(node["node_id"][-3:]) for node in nodes] for key, nodes in columns.items()}


def _ready(answer: Any) -> list[int]:
    """Return the tasks not started of a Kanban whose predecessors are all completed."""
    ready = [node for node in answer["not_started"] if node["predecessors_completed"]]
    return [int(node["node_id"][-3:]) for node in ready]


def test_the_kanban_holds_every_task_by_its_state_the_milestones_to_complete_flagged() -> None:
    # Today (#425): every task not started — the factory acceptance waits for the wiring, the
    # mounting and the commissioning for it, none flagged —, the operator desks and the wiring
    # started, the tasks completed, which the Kanban reopens; never a summary, whose progress
    # derives from its subordinates.
    answer = mockcore.startable(mockcore.core())
    today = _numbers(answer)
    assert today == {
        "not_started": [MILESTONE, MOUNTING, COMMISSIONING],
        "started": [DESKS, WIRING],
        "completed": [DETAILED_STUDIES, REVIEW, ACCEPTANCE, FILE, REMINDER, TRANSPORT],
    }
    assert _ready(answer) == []
    # The wiring declared completed: the factory acceptance, a milestone, has its predecessors
    # completed, and is flagged; the mounting on site after it waits for it.
    completed = mockcore.startable(mockcore.core(mockdata.wiring_completed()))
    later = _numbers(completed)
    assert later["not_started"] == [MILESTONE, MOUNTING, COMMISSIONING]
    assert later["started"] == [DESKS]
    assert WIRING in later["completed"]
    assert _ready(completed) == [MILESTONE]
    # The finish declared is never after today, and the factory acceptance keeps its 30 June
    # (C13), an instant.
    wiring = next(row for row in mockcore.core(mockdata.wiring_completed()) if row.number == WIRING)
    declared = cast("dict[str, Any]", json.loads(json.dumps(wiring.node["task"])))
    assert date.fromisoformat(declared["finish"]["date"]) <= TODAY.date()
    assert declared["completed_on"] == TODAY.date().isoformat()
    acceptance = cast("list[Node]", json.loads(json.dumps(completed["not_started"])))[0]["task"]
    assert acceptance["start"] == acceptance["finish"] == {"date": "2026-06-30", "hours": "8"}


# --- The previous review of the remaining to commit (WF-RAE-0040) -------------------------------


def test_a_line_of_today_shows_its_quantities_and_amount_at_the_previous_review() -> None:
    today = {row.number: row for row in mockcore.current()}
    marked = {row.number: row for row in mockcore.core(mockwitness.reference())}
    lines = [
        row
        for row in today.values()
        if row.kind == mockcore.ESTIMATE_LINE and row.number < mockwitness.GENERATED
    ]
    assert len(lines) == 9
    for row in lines:
        facet = cast("Node", row.node["estimate_line"])
        before = marked.get(row.number)
        if before is None:
            # Merged by the occurrence after the reference was marked: no previous review.
            assert row.number in {REMINDER_LINE, TRANSPORT_LINE}
            assert all(facet[name] is None for name in mockcore.PREVIOUS)
            continue
        was = cast("Node", before.node["estimate_line"])
        assert facet["previous_quantity"] == was["quantity"] == "1"
        assert facet["previous_hours"] == was["hours"]
        assert facet["previous_unit_disbursement"] == was["unit_disbursement"]
        assert facet["previous_reestimated_amount"] == was["reestimated_amount"]
    # A line drawn about the core was in the reference as it is today: nothing re-estimated.
    drawn = next(
        row
        for row in today.values()
        if row.kind == mockcore.ESTIMATE_LINE and row.number > mockwitness.GENERATED
    )
    line = cast("Node", drawn.node["estimate_line"])
    assert line["previous_quantity"] == line["quantity"]
    assert line["previous_reestimated_amount"] == line["reestimated_amount"]
    # The provision of 751, at 500 today, was at the 250 the reference knew.
    provision = cast("Node", today[PROVISION].node["estimate_line"])
    assert (provision["unit_disbursement"], provision["previous_unit_disbursement"]) == (
        "500.00",
        "250.00",
    )
    labour = cast("Node", today[LABOUR].node["estimate_line"])
    assert (labour["previous_hours"], labour["previous_unit_disbursement"]) == ("12.5", None)


def test_a_marked_revision_shows_no_previous_review() -> None:
    for row in mockcore.core(mockwitness.reference()):
        if row.kind == mockcore.ESTIMATE_LINE:
            facet = cast("Node", row.node["estimate_line"])
            assert all(facet[name] is None for name in mockcore.PREVIOUS)


def test_a_task_in_manual_mode_bounds_its_predecessors_whose_float_may_be_negative() -> None:
    # WF-PLA-0100 (#402, #464): a date entered by hand downstream bounds its predecessors. The
    # task of five days from 2 March finishes on Friday 6 March; its successor, set by hand to
    # start on Wednesday 4 March, asks it to finish by Tuesday evening: three days late, critical.
    first = Task(1, "Préparation", days=5)
    imposed = Task(
        2,
        "Livraison imposée",
        days=5,
        links=(mockwitness.Link(1),),
        manual=(date(2026, 3, 4), date(2026, 3, 10)),
        progress="not_started",
    )
    rows = mockcore.core([Task(3, "Lot", children=(first, imposed))])
    tasks = {row.number: cast("Node", row.node["task"]) for row in rows}
    assert tasks[1]["finish"] == {"date": "2026-03-06", "hours": "8"}
    assert tasks[1]["total_float"] == {"value": "-3", "unit": "d"}
    assert tasks[1]["is_critical"] is True
    # The task entered by hand shows no float itself.
    assert (tasks[2]["total_float"], tasks[2]["is_critical"]) == (None, False)


@pytest.mark.parametrize(
    ("name", "number"),
    [("nodes_installation.json", COMMISSIONING), ("nodes_planning.json", REVIEW)],
)
def test_a_reading_says_the_critical_path_only_where_its_task_is_on_it(
    name: str, number: int
) -> None:
    # Said from the float the reading gives, never written by hand (#376).
    example = mockdata.readings()[name]
    task = facet(nodes(json.loads(mockdata.render(example))["value"])[number])
    summary = str(example["summary"])
    assert ("chemin critique" in summary) is task["is_critical"]
    if not task["is_critical"]:
        assert f"{task['total_float']['value'].replace('.', ',')} jours ouvrés de marge" in summary


def test_the_comparison_names_the_lines_reestimated_without_being_designated() -> None:
    example = mockhistory.examples()["comparison.json"]
    changed = cast("list[Node]", cast("Node", example["value"])["changed"])
    kept = [entry["label"] for entry in changed if entry["changes"] == ["reestimated_amount"]]
    assert kept == ["Câblage sur site", "Mise en service sur site"]
    assert all(f"« {label} »" in str(example["summary"]) for label in kept)


def test_the_two_kanbans_read_the_same_structure_their_tasks_not_written_alike() -> None:
    # Both read the whole structure, filtered to its core: a task the gesture does not write keeps
    # the float the structure gives it, in one as in the other (#376).
    readings = mockdata.readings()

    def floats(name: str) -> dict[str, Any]:
        value = cast("dict[str, list[Node]]", json.loads(mockdata.render(readings[name]))["value"])
        return {
            node["node_id"]: node["task"]["total_float"]
            for column in value.values()
            for node in column
        }

    today, gesture = floats("startable_tasks.json"), floats("startable_tasks_milestone.json")
    written = {universe(WIRING), universe(MILESTONE)}
    assert today.keys() == gesture.keys()
    assert {key: today[key] for key in today.keys() - written} == {
        key: gesture[key] for key in gesture.keys() - written
    }
    # The design file, without a successor, has the float of the whole structure, not the core's.
    assert today[universe(FILE)] == {"value": "880.5", "unit": "d"}


def test_a_quantity_is_an_exact_decimal_rendered_as_the_contract_carries_it() -> None:
    # A quantity of 2.5 times a disbursement of 100: 250 exactly, the quantity written 2.5.
    line = Line(
        1, "Location", mockwitness.EQUIPMENT, unit=Decimal("100.00"), quantity=Decimal("2.5")
    )
    assert mockcore.price(line, 2026).base == Decimal(250)
    [_, row] = mockcore.core([Task(2, "Tâche", days=1, lines=(line,))])
    assert cast("Node", row.node["estimate_line"])["quantity"] == "2.5"
