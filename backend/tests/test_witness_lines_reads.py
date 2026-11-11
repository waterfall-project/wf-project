# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the service reads of the loaded witness, lines, rates and designation included (US-1570/L2).

Compared with the examples of the contract (``nodes_estimate*``, ``volume/nodes_thousand``,
``estimate_indicators``, ``workload*``, ``contributor_suggestions``, ``revisions``, ``project``,
``comparison*``), amounts and audit columns included, but for what the witness does not reach, each
named with its cause where the test stands:

- the reference is the offer 100 until the merge of the amendment 1 (EP-08): the budgeted amount of
  a line is that of its lineage in the 100, where the examples read the 101's; the indicators, the
  comparisons and the plan of the reference budget are measured to it, the project and the
  revisions name it;
- the provisions are EP-08's, the lines of the risks: a line of provision is absent, with the row
  numbers it shifts and the amounts it adds to the tasks above it, to the totals, to the indicators
  and to the comparisons;
- the previous figures (``previous_*``) and the actual costs that lock the subproject of a line
  (``editable_fields``) are EP-09's;
- a line whose task straddles two years is spread over them by the service, by the hours of each
  (WF-DEV-0040), where the generator of the examples kept the first year;
- the authors are the platform's, and the commands of a reader are those of its rights, not of
  the example's.
"""

import copy
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from projects_support import PROJECTS
from sqlalchemy import select
from test_witness_lines import CABLER, INSTALLATION, OPENED, PROVISION, RATES_UPDATED, line_rows
from test_witness_projects import (
    PRJ_001,
    REVISION_100,
    REVISION_101,
    REVISION_102,
    example,
    instant,
    read,
)
from test_witness_tasks import REVISIONS, difference, structure_of

from waterfall.core.estimate.interface import roles_employed
from waterfall.core.estimate.tables import RevisionCategory
from waterfall.core.planning.tables import Node
from waterfall.core.revisions.interface import reference_year_of

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

# The day of the reading of the examples: the 3 June 2026, 14:05.
READ_AT = datetime(2026, 6, 3, 14, 5, tzinfo=UTC)
# The recapitulative "Poste de commande", whose estimate the examples read.
CORE = "01926f3a-7c00-7000-8000-000000000551"
# What a line of the examples carries that the witness does not (EP-09): the previous figures.
PREVIOUS = {
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
}
# What the service computes otherwise than the examples, compared apart, line by line.
APART = PREVIOUS | {"budgeted_amount", "reestimated_amount", "consumption_year"}
CENT = Decimal("0.01")

READS = {
    "nodes_estimate": f"?subtree_of={CORE}",
    "nodes_estimate_sorted": f"?subtree_of={CORE}&sort_by=base_amount&sort_order=desc",
    "nodes_estimate_filtered": (
        f"?subtree_of={CORE}&reestimated_amount_min=1000&reestimated_amount_max=10000"
    ),
    "nodes_estimate_hours": f"?subtree_of={CORE}&sort_by=hours&sort_order=desc",
    "volume/nodes_thousand": "",
}


def numbers(value: object) -> Decimal | None:
    """Read a text as an amount, ``None`` for any other value."""
    if not isinstance(value, str):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def deviations(
    ours: object, theirs: object, tolerance: Decimal = Decimal(0), path: str = ""
) -> set[str]:
    """Name the places where a reading differs from its example, by path.

    A text read as an amount is compared as one, within ``tolerance``; an absent key is a null one;
    the indexes of a list are left out of the path.
    """
    found: set[str] = set()
    left, right = ours, theirs
    if ours in (None, [], {}) and theirs in (None, [], {}):
        return found
    if isinstance(ours, dict) and isinstance(theirs, dict):
        mine, yours = cast("dict[str, object]", ours), cast("dict[str, object]", theirs)
        for key in sorted(set(mine) | set(yours)):
            found |= deviations(mine.get(key), yours.get(key), tolerance, f"{path}/{key}")
    elif isinstance(ours, list) and isinstance(theirs, list):
        listed, wished = cast("list[object]", ours), cast("list[object]", theirs)
        if len(listed) != len(wished):
            found.add(f"{path}[len]")
        for each, wanted in zip(listed, wished, strict=False):
            found |= deviations(each, wanted, tolerance, f"{path}[]")
    elif ours != theirs:
        a, b = numbers(left), numbers(right)
        zulu = isinstance(left, str) and left.replace("+00:00", "Z") == right
        if not zulu and (a is None or b is None or abs(a - b) > tolerance):
            found.add(path)
    return found


def keyed(items: list[dict[str, Any]], key: str = "node_id") -> dict[str, dict[str, Any]]:
    """Give the items of a reading by their identifier, in the order of the plan."""
    return {item[key]: item for item in items}


def line_differences(ours: dict[str, Any], theirs: dict[str, Any]) -> set[str]:
    """Name what a line read differs in from the example, but for what is read apart."""
    found = {
        key
        for key in set(ours) | set(theirs)
        if key
        not in {
            "estimate_line",
            "row_number",
            "editable_fields",
            "lock_version",
            "task",
            "origin_risk_id",
        }
        and deviations(ours.get(key), theirs.get(key))
    }
    kept = {k: v for k, v in ours["estimate_line"].items() if k not in APART}
    wanted = {k: v for k, v in theirs["estimate_line"].items() if k not in APART}
    found |= {f"estimate_line.{key}" for key in deviations(kept, wanted)}
    if ours["lock_version"] != theirs["lock_version"]:
        found.add("lock_version")
    return found


def test_the_comparison_of_a_line_bites_on_a_figure_off_by_a_cent() -> None:
    # The comparison is not a formality: a cent off in a base amount is a difference, and what is
    # read apart (the previous figures) is not.
    item = next(
        each for each in example("nodes_estimate")["items"] if each["kind"] == "estimate_line"
    )
    moved = copy.deepcopy(item)
    moved["estimate_line"]["base_amount"] = "1234.57"
    moved["estimate_line"]["previous_quantity"] = "9"
    assert line_differences(item, item) == set()
    assert line_differences(moved, item) == {"estimate_line./base_amount"}
    assert deviations({"a": "1.00"}, {"a": "1"}) == set()
    assert deviations({"a": "1.02"}, {"a": "1"}, Decimal("0.01")) == {"/a"}
    assert deviations({"a": None}, {}) == set()


@pytest.fixture
def the_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the day the service reads as today to the day of the examples."""
    monkeypatch.setattr("waterfall.api.workload.utc_now", lambda: READ_AT)
    monkeypatch.setattr("waterfall.api.estimate_indicators.utc_now", lambda: READ_AT)


def inflated(base_amount: Decimal, basis: tuple[int, Decimal], year: int) -> Decimal:
    """Give an amount inflated to a year: once per year since the reference year, never deflated."""
    reference_year, rate = basis
    return base_amount * (1 + rate) ** max(year - reference_year, 0)


def year_of(instant_: dict[str, Any]) -> str:
    """Give the year of a start or a finish of a task as a reading writes it."""
    return str(instant_["date"])[:4]


def amounts_under(items: dict[str, dict[str, Any]], name: str) -> dict[str, Decimal]:
    """Sum an amount of the lines of a reading under each task that bears them, summaries too."""
    sums: dict[str, Decimal] = {}
    for item in items.values():
        if item["kind"] != "estimate_line":
            continue
        above = item["parent_id"]
        while above is not None and above in items:
            sums[above] = sums.get(above, Decimal(0)) + Decimal(item["estimate_line"][name])
            above = items[above]["parent_id"]
    return sums


# How many lines of each read differ from the example in what is read apart: the budgeted amount
# (the reference is the 100, the example's the 101), the re-estimated one and the year (a task on
# two years), the fields editable (an actual cost, EP-09).
LINES_APART = {
    "nodes_estimate": {"budgeted": 1, "reestimated": 0, "year": 0, "editable": 2},
    "nodes_estimate_sorted": {
        "budgeted": 1,
        "reestimated": 0,
        "year": 0,
        "editable": 2,
    },
    "nodes_estimate_filtered": {
        "budgeted": 1,
        "reestimated": 0,
        "year": 0,
        "editable": 2,
    },
    "nodes_estimate_hours": {
        "budgeted": 1,
        "reestimated": 0,
        "year": 0,
        "editable": 2,
    },
    "volume/nodes_thousand": {
        "budgeted": 120,
        "reestimated": 118,
        "year": 48,
        "editable": 18,
    },
}


def projection_apart(
    sheet: dict[str, Any],
    example_sheet: dict[str, Any],
    task: dict[str, Any],
    basis: tuple[int, Decimal],
) -> list[str]:
    """Check how a line is projected otherwise than the example, and name what differs.

    On a task straddling two years the line is spread by the hours of each (WF-DEV-0040): it costs
    between its base amount inflated to the year the task starts and to the year it ends, where the
    example kept the first, and its year of consumption is one of the two. Elsewhere nothing
    differs: the service rounds a half cent away from zero, as ``Money`` and the generator do
    (#2618).
    """
    label = sheet["label"]
    starts, ends = int(year_of(task["start"])), int(year_of(task["finish"]))
    ours, theirs = (
        Decimal(sheet["reestimated_amount"]),
        Decimal(example_sheet["reestimated_amount"]),
    )
    found: list[str] = []
    if starts != ends:
        low = inflated(Decimal(sheet["base_amount"]), basis, starts)
        high = inflated(Decimal(sheet["base_amount"]), basis, ends)
        assert abs(theirs - low) <= CENT, label
        assert low - CENT <= ours <= high + CENT, label
        assert int(sheet["consumption_year"]) in {starts, ends}, label
        found += ["reestimated"] * (ours != theirs)
        found += ["year"] * (sheet["consumption_year"] != example_sheet["consumption_year"])
        return found
    assert sheet["consumption_year"] == example_sheet["consumption_year"], label
    assert ours == theirs, label
    return found


def sums_hold(
    name: str,
    reads: tuple[dict[str, Any], dict[str, Any]],
    got: dict[str, dict[str, Any]],
    absent: list[str],
) -> None:
    """Check the amounts of the tasks and the totals of a read of the estimate against its lines.

    The amounts of a task are those of its lines; the totals those of the lines read. The base
    amount, the hours and the counts are the example's but for the line of provision the witness
    lacks (``absent``).
    """
    body, expected = reads
    wanted = keyed(expected["items"])
    lines = {key: item for key, item in got.items() if item["kind"] == "estimate_line"}
    totals, wanted_totals = body["totals"], expected["totals"]
    if name != "nodes_estimate_filtered":
        for amount in ("base_amount", "budgeted_amount", "reestimated_amount"):
            sums = amounts_under(got, amount)
            for key, item in got.items():
                if item["kind"] == "task":
                    assert Decimal(item["task"][amount]) == sums.get(key, Decimal(0)), key
    for amount in ("base_amount", "budgeted_amount", "reestimated_amount"):
        assert Decimal(totals[amount]) == sum(
            (Decimal(item["estimate_line"][amount]) for item in lines.values()), Decimal(0)
        )
    provision = sum(
        (Decimal(wanted[key]["estimate_line"]["base_amount"]) for key in absent), Decimal(0)
    )
    assert Decimal(totals["base_amount"]) == Decimal(wanted_totals["base_amount"]) - provision
    assert totals["hours"] == wanted_totals["hours"]
    assert totals["estimate_line_count"] == wanted_totals["estimate_line_count"] - len(absent)
    # A filter of the line retains lines, and the tasks above them are rendered for the tree alone:
    # the filtered read counts none, as the example and ``NodeTotals`` say (#2699).
    assert totals["task_count"] == wanted_totals["task_count"]
    assert body["meta"]["summary_depth"] == expected["meta"]["summary_depth"]
    assert body["meta"]["scheduled_at"] == instant(OPENED[102]).isoformat().replace("+00:00", "Z")


@pytest.mark.parametrize("name", list(READS))
def test_the_estimate_read_of_the_loaded_witness_is_the_example_but_for_what_it_does_not_reach(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
        offer = line_rows(session, REVISION_100)
        basis = (
            reference_year_of(session, REVISION_102),
            Decimal(example("project")["inflation_rate"]),
        )
    base = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_102}/structures/{structure}/nodes"
    body = read(api, witness, realm, f"{base}{READS[name]}")
    expected = example(name)
    got, wanted = keyed(body["items"]), keyed(expected["items"])
    # The only node the witness lacks is the line of provision of the risk of the core (EP-08).
    absent = sorted(wanted.keys() - got.keys())
    assert absent == ([] if name == "nodes_estimate_filtered" else [PROVISION])
    assert got.keys() <= wanted.keys()
    # The order of the plan, but for that line; the row numbers it shifts by one below it.
    assert list(got) == [key for key in wanted if key in got]
    gone = sorted(wanted[key]["row_number"] for key in absent)
    for key, item in got.items():
        shifted = wanted[key]["row_number"] - bisect_left(gone, wanted[key]["row_number"])
        assert item["row_number"] == shifted, key
    # The tasks, as the slice of the tasks reads them, their amounts apart.
    for key, item in got.items():
        if item["kind"] == "task":
            assert not difference(item, wanted[key]), (name, item["task"]["label"])
    # The lines: everything the file enters, the base amount and the place are the example's; what
    # is read apart is counted, and each difference has its cause.
    lines = {key: item for key, item in got.items() if item["kind"] == "estimate_line"}
    found = {"budgeted": 0, "reestimated": 0, "year": 0, "editable": 0}
    for key, item in lines.items():
        theirs = wanted[key]
        assert not line_differences(item, theirs), (name, item["estimate_line"]["label"])
        sheet, example_sheet = item["estimate_line"], theirs["estimate_line"]
        task = got[item["parent_id"]]["task"]
        before = offer.get(UUID(item["lineage_id"]))
        # The budgeted amount: the re-estimated one of the lineage in the offer, the reference.
        assert Decimal(sheet["budgeted_amount"]) == (
            Decimal(0) if before is None else before[1].reestimated_amount
        ), sheet["label"]
        found["budgeted"] += sheet["budgeted_amount"] != example_sheet["budgeted_amount"]
        # The re-estimated amount and the year: the same but where the task straddles two years.
        for each in projection_apart(sheet, example_sheet, task, basis):
            found[each] += 1
        # The risk that originates a line is EP-08's.
        assert item["origin_risk_id"] is None
        # The previous figures are EP-09's; the subproject of a line of a started task is locked
        # by the actual costs the example holds (EP-09).
        assert all(sheet[each] is None for each in PREVIOUS)
        if item["editable_fields"] != theirs["editable_fields"]:
            assert set(item["editable_fields"]) - set(theirs["editable_fields"]) == {
                "estimate_line.subproject_id"
            }
            assert set(theirs["editable_fields"]) <= set(item["editable_fields"])
            assert task["progress"] != "not_started"
            found["editable"] += 1
    assert found == LINES_APART[name]
    sums_hold(name, (body, expected), got, absent)


INDICATORS = {
    "/by_cost_type[]/amount/value",
    "/by_cost_type[]/share/value",
    "/by_cost_type[len]",
    "/by_subproject[]/amount/value",
    "/by_subproject[]/share/value",
    "/by_work_package[]/amount/value",
    "/by_work_package[]/share/value",
    "/delta_to_previous_revision/value",
    "/delta_to_reference/value",
    "/provisions_identified",
    "/total/value",
}


def volume_excess(witness: Database) -> Decimal:
    """Give how much more the lines of the revision in progress cost than the example's, in all.

    The lines on two years, spread by the service, and the provision the witness lacks (EP-08),
    which the example sums: the difference of the re-estimated amounts of the lines they share. The
    lines are those the database holds, which the read of the structure compares with the example
    (``test_the_estimate_read_of_the_loaded_witness_is_the_example_but_for_what_it_does_not_reach``):
    read through the API, their 5 999 nodes would cost each process some twenty seconds (#2716).
    """
    with witness.transaction() as session:
        ours = {str(node.id): facet for node, facet in line_rows(session, REVISION_102).values()}
    wanted = keyed(example("volume/nodes_thousand")["items"])
    return sum(
        (
            facet.reestimated_amount - Decimal(wanted[key]["estimate_line"]["reestimated_amount"])
            for key, facet in ours.items()
        ),
        Decimal(0),
    ) - Decimal(wanted[PROVISION]["estimate_line"]["reestimated_amount"])


@pytest.mark.parametrize("name", ["estimate_indicators", "volume/estimate_indicators_volume"])
def test_the_indicators_are_the_example_but_for_the_provisions_and_the_reference(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None, name: str
) -> None:
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/estimate-indicators")
    expected = example(name)
    assert deviations(body, expected) == INDICATORS
    # The structure is that of the example, a nature short: the provision (EP-08), nought here.
    assert [each["key"] for each in body["by_cost_type"]] == [
        each["key"] for each in expected["by_cost_type"] if each["label"] != "Provision"
    ]
    assert body["provisions_identified"] == "0.00"
    # The total is the lines', the example's but for its provision and the lines on two years: the
    # difference is exactly that of the lines read.
    ours, theirs = Decimal(body["total"]["value"]), Decimal(expected["total"]["value"])
    assert ours - theirs == volume_excess(witness)
    assert body["by_work_package"][0]["amount"]["value"] == "2434.56"
    for dimension in ("by_cost_type", "by_subproject"):
        assert sum(Decimal(each["amount"]["value"]) for each in body[dimension]) == ours
    # Measured to the offer, the reference: the delta is that of the revision in progress to it.
    with witness.transaction() as session:
        offer = sum(
            (facet.reestimated_amount for _, facet in line_rows(session, REVISION_100).values()),
            Decimal(0),
        )
    assert Decimal(body["delta_to_reference"]["value"]) == ours - offer
    assert body["delta_to_previous_revision"]["value"] == "200.00"


def by_role(plan: dict[str, Any]) -> dict[str, Any]:
    """Give a plan of workload with its roles in the order of their identifiers."""
    return {**plan, "roles": sorted(plan["roles"], key=lambda each: each["resource_role_id"])}


def test_the_workload_of_the_remaining_is_the_example_within_a_rounding_of_a_hundredth(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # Every role and every month of the plan, the capacities and the totals; the service orders the
    # roles by the category of their nature (``RoleSort``), the example by their identifier.
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/workload?basis=current_remaining")
    expected = example("workload")
    assert deviations(by_role(body), by_role(expected), Decimal("0.02")) == set()
    assert [each["resource_role_id"][-3:] for each in body["roles"]] != [
        each["resource_role_id"][-3:] for each in expected["roles"]
    ]
    assert len(body["monthly_totals"]) == 39
    total = sum(Decimal(each["hours"]) for each in body["monthly_totals"])
    assert total == sum(Decimal(m["hours"]) for r in body["roles"] for m in r["months"])


def test_the_workload_of_the_reference_budget_is_that_of_the_offer_where_the_example_reads_the_101(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/workload?basis=reference_budget")
    expected = example("workload_reference_budget")
    assert body["context"]["revision_id"] == str(REVISION_100)
    assert expected["context"]["revision_id"] == str(REVISION_101)
    found = deviations(by_role(body), by_role(expected), Decimal("0.02"))
    assert found == {"/context/revision_id", "/monthly_totals[]/hours", "/roles[]/months[]/hours"}


def test_the_contributors_the_lines_employ_are_proposed_as_the_example_does(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The lines of the revision in progress employ the role of the cable fitter, whose node holds
    # the account of Sacha Lefèvre, created attached to it as ``users.json`` has it (#2698).
    with witness.transaction() as session:
        employed = roles_employed(session, PRJ_001)
    assert CABLER in employed
    assert len(employed) == 3
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/contributors/suggestions")
    expected = example("contributor_suggestions")
    assert expected[0]["resource_role_ids"] == [str(CABLER)]
    assert body == expected


def without(value: Any, names: set[str]) -> Any:
    """Give a reading without the keys ``names``, at any depth."""
    if isinstance(value, list):
        return [without(each, names) for each in cast("list[object]", value)]
    if isinstance(value, dict):
        held = cast("dict[str, object]", value)
        return {key: without(each, names) for key, each in held.items() if key not in names}
    return value


AUTHORS = {
    "/audit/created_by/display_name",
    "/audit/created_by/kind",
    "/audit/created_by/user_id",
    "/audit/updated_by/display_name",
    "/audit/updated_by/kind",
    "/audit/updated_by/user_id",
}


def test_the_revisions_of_the_loaded_witness_are_the_examples_but_for_the_reference_and_the_authors(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The commands are those of the reader's rights (``available_commands``), the authors the
    # platform's; the offer is the reference, designated at the order (event 7), where the example
    # marks the 101; the revision in progress was not edited (its counter and its instant).
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/revisions")
    expected = example("revisions")
    found = deviations(
        without(body, {"available_commands"}), without(expected, {"available_commands"})
    )
    assert found == {f"/items[]{each}" for each in AUTHORS} | {
        "/items[]/audit/updated_at",
        "/items[]/is_reference",
        "/items[]/lock_version",
    }
    got = {each["revision_id"]: each for each in body["items"]}
    assert [each["is_reference"] for each in body["items"]] == [False, False, True]
    assert got[str(REVISION_100)]["audit"]["updated_at"] == "2026-01-15T11:00:00Z"
    assert got[str(REVISION_101)]["audit"] == next(
        each["audit"] for each in expected["items"] if each["revision_id"] == str(REVISION_101)
    ) | {"created_by": {"kind": "platform"}, "updated_by": {"kind": "platform"}}


def test_the_project_of_the_loaded_witness_is_the_example_but_for_the_reference_and_the_authors(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}")
    expected = example("project")
    found = deviations(
        without(body, {"available_commands"}), without(expected, {"available_commands"})
    )
    assert found == AUTHORS | {"/lock_version", "/reference_revision_id"}
    assert body["reference_revision_id"] == str(REVISION_100)
    # State, rate, probability, order and code are the example's: the witness enters them.
    for key in ("state", "inflation_rate", "win_probability", "order_received_on", "code"):
        assert body[key] == expected[key]


FIGURES = (
    "label",
    "cost_category_id",
    "resource_role_id",
    "quantity",
    "hours",
    "unit_disbursement",
    "payment_delay_days",
    "subproject_id",
    "base_amount",
)
# The nodes of each comparison the witness lacks: the lines of provision (EP-08) and the tasks
# above them that the example gives as modified for their sake alone.
LACKING = {
    "comparison": {("estimate_line", "Provision — indisponibilité de l'automaticien")},
    "comparison_differences": {
        ("task", "Câblage des armoires"),
        ("task", "Mise en service"),
        ("estimate_line", "Provision — risque de reprise du câblage"),
        ("estimate_line", "Provision — retard de livraison des armoires"),
        ("estimate_line", "Provision — indisponibilité de l'automaticien"),
    },
}


def label_of(item: dict[str, Any]) -> tuple[str, str]:
    """Give the kind and the label of a node of a comparison."""
    held: dict[str, Any] = item.get("task") or item.get("estimate_line") or {}
    return item["kind"], str(held.get("label"))


@pytest.mark.parametrize("name", list(LACKING))
def test_the_comparison_of_two_revisions_is_the_example_but_for_the_provisions_and_reference(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    # From the offer 100 to the 101, by lineage: the same nodes, each as added, removed or modified
    # by the same fields, the same figures; the identifiers are those of each revision (derived for
    # a marked one), so the nodes are matched by lineage.
    with witness.transaction() as session:
        installation = session.scalar(
            select(Node.id).where(Node.revision_id == REVISION_101, Node.lineage_id == INSTALLATION)
        )
    asked = f"&subtree_of={installation}" if name == "comparison" else "&difference=added,removed"
    url = (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison"
        f"?from_revision_id={REVISION_100}&to_revision_id={REVISION_101}{asked}"
    )
    body = read(api, witness, realm, url)
    expected = example(name)
    got, wanted = keyed(body["items"], "lineage_id"), keyed(expected["items"], "lineage_id")
    assert {label_of(wanted[key]) for key in wanted.keys() - got.keys()} == LACKING[name]
    assert got.keys() <= wanted.keys()
    assert list(got) == [key for key in wanted if key in got]
    for key, item in got.items():
        theirs = wanted[key]
        for field in ("kind", "difference", "changes", "level"):
            assert item[field] == theirs[field], (label_of(item), field)
        if item["kind"] == "estimate_line":
            ours = {each: item["estimate_line"][each] for each in FIGURES}
            assert (
                deviations(ours, {each: theirs["estimate_line"][each] for each in FIGURES}) == set()
            )
        else:
            assert item["task"]["label"] == theirs["task"]["label"]
    # The deltas are measured to the offer, the reference: the labour is raised by the rates alone.
    assert (body["from_revision_id"], body["to_revision_id"]) == (
        expected["from_revision_id"],
        expected["to_revision_id"],
    )
    nature = {
        each["key"]: each for each in body["amount_deltas"] if each["dimension"] == "cost_type"
    }
    assert "01926f3a-7c00-7000-8000-000000000463" not in nature
    assert nature["01926f3a-7c00-7000-8000-000000000461"]["budgeted_delta"] == "0.00"
    assert body["meta"]["scheduled_at"] == instant(RATES_UPDATED).isoformat().replace("+00:00", "Z")
    lacking_lines = len([each for each in LACKING[name] if each[0] == "estimate_line"])
    assert body["totals"]["estimate_line_count"] == (
        expected["totals"]["estimate_line_count"] - lacking_lines
    )
    assert body["totals"]["hours"] == expected["totals"]["hours"]
    assert body["totals"]["task_count"] == expected["totals"]["task_count"]


def test_the_comparison_of_the_whole_structure_marks_the_nodes_of_the_example_but_provisions(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # Read whole, reduced to what the screen shows: the same marks on the same labels, but for the
    # three lines of provision the witness lacks; the example carries the identifiers of the
    # revision in progress, so nodes are counted by what they are.
    url = (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison?from_revision_id={REVISION_100}"
        f"&to_revision_id={REVISION_101}&fields=kind,task.label,estimate_line.label"
    )
    body = read(api, witness, realm, url)
    expected = example("volume/comparison_volume")

    def counted(items: list[dict[str, Any]]) -> Counter[tuple[str, str, str, tuple[str, ...]]]:
        # The budgeted amount of a line moves from the 100 to the 101 only for the reference the
        # example reads (the 101's own): the offer, the reference here, keeps the budgets it gave.
        return Counter(
            (
                *label_of(item),
                item["difference"],
                tuple(each for each in item["changes"] if each != "budgeted_amount"),
            )
            for item in items
        )

    lacking = counted(expected["items"]) - counted(body["items"])
    extra = counted(body["items"]) - counted(expected["items"])
    assert not extra, list(extra.items())[:8]
    assert sum(lacking.values()) == 3
    assert {key[0:3] for key in lacking} == {
        ("estimate_line", "Provision — retard de livraison des armoires", "added"),
        ("estimate_line", "Provision — risque de reprise du câblage", "added"),
        ("estimate_line", "Provision — indisponibilité de l'automaticien", "added"),
    }
    assert [item["level"] for item in body["items"] if item["kind"] == "task"] == [
        item["level"] for item in expected["items"] if item["kind"] == "task"
    ]


def test_the_amount_deltas_of_the_whole_comparison_are_the_lines_of_the_two_revisions_summed(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # US-1530 (#1752): each line counts under the key it bears in each revision, the keys at two
    # nought deltas left out, the sum by subproject equal to the sum by nature. Read whole, the
    # deltas are the amounts of the lines of the 101 less those of the 100, summed by key straight
    # from the rows; the example's differ by the lines on two years (re-estimated), the reference
    # (budgeted) and the provision the witness lacks (EP-08), the nature of which is absent. The
    # budgeted deltas are held to the sum by subproject equal to the sum by nature (#1752). The
    # nodes reduced to their kind: the deltas are those of the whole comparison, which the fields
    # do not reduce, and its 10 000 nodes in full cost some twenty seconds of validation (#2716).
    url = (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison?from_revision_id={REVISION_100}"
        f"&to_revision_id={REVISION_101}&fields=kind"
    )
    body = read(api, witness, realm, url)
    expected = example("volume/comparison_volume")
    with witness.transaction() as session:
        lines = {number: line_rows(session, REVISIONS[number]) for number in (100, 101)}
        natures = {
            number: dict(
                session.execute(
                    select(RevisionCategory.cost_category_id, RevisionCategory.cost_type_id).where(
                        RevisionCategory.revision_id == REVISIONS[number]
                    )
                ).all()
            )
            for number in (100, 101)
        }
    summed: defaultdict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    for number, sign in ((101, 1), (100, -1)):
        for _, facet in lines[number].values():
            subproject = "unassigned" if facet.subproject_id is None else str(facet.subproject_id)
            keys = {
                "cost_type": str(natures[number][facet.cost_category_id]),
                "subproject": subproject,
            }
            for dimension, key in keys.items():
                summed[dimension, key, "reestimated_delta"] += sign * facet.reestimated_amount
    found = {
        (each["dimension"], each["key"], name): Decimal(each[name])
        for each in body["amount_deltas"]
        for name in ("budgeted_delta", "reestimated_delta")
    }
    # The re-estimated deltas, key by key, from the rows; the budgeted ones are the reference's
    # (the offer), their keys those of the re-estimated deltas or one more at most.
    assert {k: a for k, a in found.items() if k[2] == "reestimated_delta" and a} == {
        key: amount for key, amount in summed.items() if amount
    }
    for name in ("budgeted_delta", "reestimated_delta"):
        by = {
            dimension: sum(
                (
                    amount
                    for (kind, _, each), amount in found.items()
                    if (kind, each) == (dimension, name)
                ),
                Decimal(0),
            )
            for dimension in ("cost_type", "subproject")
        }
        assert by["cost_type"] == by["subproject"], name
    # The keys are the example's but for the nature of the provision; the budgeted delta of the
    # disbursements, which the offer and the 101 do not budget differently, is the example's.
    ours = {(each["dimension"], each["key"]) for each in body["amount_deltas"]}
    theirs = {(each["dimension"], each["key"]) for each in expected["amount_deltas"]}
    assert theirs - ours == {("cost_type", "01926f3a-7c00-7000-8000-000000000463")}
    assert ours <= theirs
    disbursements = ("cost_type", "01926f3a-7c00-7000-8000-000000000462", "budgeted_delta")
    assert found[disbursements] == next(
        Decimal(each["budgeted_delta"])
        for each in expected["amount_deltas"]
        if (each["dimension"], each["key"]) == disbursements[:2]
    )
