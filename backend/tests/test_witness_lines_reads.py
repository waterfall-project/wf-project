# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the service reads of the loaded witness, lines, rates and designation included (US-1570/L2).

Compared with the examples of the contract (``nodes_estimate*``, ``volume/nodes_thousand``,
``estimate_indicators``, ``workload*``, ``contributor_suggestions``, ``revisions``, ``project``,
``comparison*``), amounts and audit columns included, but for what the witness does not reach, each
named with its cause where the test stands:

- the authors are the platform's, and the commands of a reader are those of its rights, not of
  the example's; the counters follow the writes of the loading;
- a node of a marked revision is the witness's own, the examples read the identifiers of the
  revision in progress: the nodes of a comparison are matched by lineage.

Since EP-08 (US-2650/L1), the reference is the 101 the merge of the amendment 1 marks, and the risks
bear their provision lines: what the examples read of the reference and of the provisions is read
as they read it, without reserve.
"""

import copy
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, cast

import pytest
from projects_support import PROJECTS
from sqlalchemy import select
from test_witness_lines import CABLER, INSTALLATION, MERGED, OCCURRED, PROVISION, line_rows
from test_witness_projects import REVISION_100, REVISION_101, REVISION_102, instant
from test_witness_tasks import REVISIONS, difference, structure_of
from witness_support import PRJ_001, READ_AT, example, read

from waterfall.core.estimate.interface import roles_employed
from waterfall.core.estimate.tables import RevisionCategory
from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from uuid import UUID

    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")
# The requirement of the amount deltas of the comparison (US-1530): a test of them cites it too.
COMPARISON_REQUIREMENT = "WF-REV-0080-A"

# The recapitulative "Poste de commande", whose estimate the examples read.
CORE = "01926f3a-7c00-7000-8000-000000000551"
# A line of provision is read computed, closed to the entry and to the remaining, its budgeted
# amount the provision of the reference, as the examples read it (#4274).
BUDGETED = "budgeted_amount"

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
    """Name what a line read differs in from the example, but for its counter.

    Its counter follows the writes of the loading; a line of provision is read as any (#4274).
    """
    beside = {"estimate_line", "row_number", "editable_fields", "lock_version", "task"}
    found = {
        key
        for key in set(ours) | set(theirs)
        if key not in beside and deviations(ours.get(key), theirs.get(key))
    }
    found |= {
        f"estimate_line.{key}" for key in deviations(ours["estimate_line"], theirs["estimate_line"])
    }
    return found


def test_the_comparison_of_a_line_bites_on_a_figure_off_by_a_cent() -> None:
    # The comparison is not a formality: a cent off in a base amount is a difference.
    item = next(
        each for each in example("nodes_estimate")["items"] if each["kind"] == "estimate_line"
    )
    moved = copy.deepcopy(item)
    moved["estimate_line"]["base_amount"] = "1234.57"
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


@pytest.mark.parametrize("name", list(READS))
def test_the_estimate_read_of_the_loaded_witness_is_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    # Every node in the order of the plan, at its row, the line of provision of 751 included; the
    # tasks as the slice of the tasks reads them, the lines to the cent, their budgeted amount the
    # 101's, their previous figures those of the 101, which reviewed them (EP-08); the totals those
    # of the example.
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
    base = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_102}/structures/{structure}/nodes"
    body = read(api, witness, realm, f"{base}{READS[name]}")
    expected = example(name)
    got, wanted = keyed(body["items"]), keyed(expected["items"])
    assert list(got) == list(wanted)
    assert PROVISION in got or name == "nodes_estimate_filtered"
    read_on = date.fromisoformat(body["meta"]["scheduled_at"][:10])
    for key, item in got.items():
        theirs = wanted[key]
        assert item["row_number"] == theirs["row_number"], key
        if item["kind"] == "task":
            assert not difference(item, theirs, read_on), (name, item["task"]["label"])
        else:
            assert not line_differences(item, theirs), (name, item["estimate_line"]["label"])
            assert item["editable_fields"] == theirs["editable_fields"], key
    # The budgeted total counts the provision the reference fixed, as the example (#4274).
    assert deviations(body["totals"], expected["totals"]) == set()
    assert body["meta"]["summary_depth"] == expected["meta"]["summary_depth"]
    assert body["meta"]["scheduled_at"] == instant(OCCURRED).isoformat().replace("+00:00", "Z")


@pytest.mark.parametrize("name", ["estimate_indicators", "volume/estimate_indicators_volume"])
def test_the_indicators_are_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None, name: str
) -> None:
    # The provision of 751 and the delta measured to the 101, the reference (EP-08).
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/estimate-indicators")
    assert deviations(body, example(name)) == set()


def by_role(plan: dict[str, Any]) -> dict[str, Any]:
    """Give a plan of workload with its roles in the order of their identifiers."""
    return {**plan, "roles": sorted(plan["roles"], key=lambda each: each["resource_role_id"])}


def summed_tasks(role: dict[str, Any]) -> dict[str, str]:
    """Give the hours of the tasks of a role summed month by month, as the contract writes them."""
    sums: dict[str, Decimal] = defaultdict(Decimal)
    for task in role["tasks"]:
        for month in task["months"]:
            sums[month["month"]] += Decimal(month["hours"])
    return {month: str(sums[month]) for month in sorted(sums)}


def tasks_are_their_nodes(
    api: ContractClient, witness: Database, realm: TestRealm, body: dict[str, Any], revision: UUID
) -> None:
    """Check that each task of a plan has the row and the label of the node it names.

    The nodes are those of the main structure of the revision, read as ``listNodes`` gives them: a
    row of another task, or one row for all, is not the row of the node.
    """
    with witness.transaction() as session:
        structure = structure_of(session, revision)
    url = f"{PROJECTS}/{PRJ_001}/revisions/{revision}/structures/{structure}/nodes"
    nodes = keyed(read(api, witness, realm, url)["items"])
    tasks = [task for role in body["roles"] for task in role["tasks"]]
    assert tasks
    for task in tasks:
        node = nodes[task["node_id"]]
        assert node["kind"] == "task"
        assert (task["row_number"], task["label"]) == (node["row_number"], node["task"]["label"])


@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_workload_of_the_remaining_is_the_example_within_a_rounding_of_a_hundredth(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # Every role and every month of the plan, the capacities and the totals; the service orders the
    # roles by the category of their nature (``RoleSort``), the example by their identifier.
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/workload?basis=current_remaining")
    expected = example("workload")
    # The detail of each role too, its tasks the same nodes in the same order (WF-DEV-0090).
    assert deviations(by_role(body), by_role(expected), Decimal("0.02")) == set()
    tasks_are_their_nodes(api, witness, realm, body, REVISION_102)
    assert [each["resource_role_id"][-3:] for each in body["roles"]] != [
        each["resource_role_id"][-3:] for each in expected["roles"]
    ]
    assert len(body["monthly_totals"]) == 39
    total = sum(Decimal(each["hours"]) for each in body["monthly_totals"])
    assert total == sum(Decimal(m["hours"]) for r in body["roles"] for m in r["months"])


@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_workload_of_the_reference_budget_is_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The plan of the 101, the reference (EP-08): every role, month and task of the example, each
    # task the node of the 101 it names, which the example reads under the identifier of the 102.
    del the_day
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/workload?basis=reference_budget")
    expected = example("workload_reference_budget")
    assert body["context"]["revision_id"] == str(REVISION_101)
    found = deviations(by_role(body), by_role(expected), Decimal("0.02"))
    assert found <= {"/roles[]/tasks[]/node_id"}
    for role in body["roles"]:
        assert summed_tasks(role) == {each["month"]: each["hours"] for each in role["months"]}
    tasks_are_their_nodes(api, witness, realm, body, REVISION_101)


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


def test_the_revisions_of_the_loaded_witness_are_the_examples_but_for_the_authors(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The commands are those of the reader's rights (``available_commands``), the authors the
    # platform's, the counters and the instants those of the writes of the loading; the 101, marked
    # by the merge of the amendment 1, is the reference (EP-08).
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/revisions")
    expected = example("revisions")
    found = deviations(
        without(body, {"available_commands"}), without(expected, {"available_commands"})
    )
    assert found <= {f"/items[]{each}" for each in AUTHORS} | {
        "/items[]/audit/updated_at",
        "/items[]/lock_version",
    }
    assert [each["is_reference"] for each in body["items"]] == [False, True, False]
    got = {each["revision_id"]: each for each in body["items"]}
    assert got[str(REVISION_101)]["audit"]["updated_at"] == instant(MERGED).isoformat().replace(
        "+00:00", "Z"
    )


def test_the_project_of_the_loaded_witness_is_the_example_but_for_the_authors(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}")
    expected = example("project")
    found = deviations(
        without(body, {"available_commands"}), without(expected, {"available_commands"})
    )
    assert found == AUTHORS | {"/lock_version"}
    assert body["reference_revision_id"] == str(REVISION_101)
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
# The comparisons of the offer 100 and of the reference 101 the examples read.
COMPARED = {"comparison", "comparison_differences"}


def base_of(item: dict[str, Any]) -> Any:
    """Give the base of a node of a comparison as the witness and the example can share it.

    Each predecessor by its link alone, not the node it names nor its row, which the identifiers of
    each revision move (``test_comparison`` holds the node it names).
    """
    base = item["base"]
    if not base or "predecessors" not in base:
        return base
    shared = [(each["link_type"], each["lag"]) for each in base["predecessors"]]
    return {**base, "predecessors": shared}


def label_of(item: dict[str, Any]) -> tuple[str, str]:
    """Give the kind and the label of a node of a comparison."""
    held: dict[str, Any] = item.get("task") or item.get("estimate_line") or {}
    return item["kind"], str(held.get("label"))


@pytest.mark.parametrize("name", sorted(COMPARED))
def test_the_comparison_of_two_revisions_is_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    # From the offer 100 to the reference 101, by lineage: the same nodes in the same order, each
    # added, removed or modified by the same fields, the same figures, the same base (US-2320), the
    # provision lines the risks declared in the 101 included (EP-08); the identifiers are those of
    # each revision, so the nodes are matched by lineage.
    with witness.transaction() as session:
        main = structure_of(session, REVISION_101)
        installation = session.scalar(
            select(Node.id).where(Node.structure_id == main, Node.lineage_id == INSTALLATION)
        )
    asked = f"&subtree_of={installation}" if name == "comparison" else "&difference=added,removed"
    url = (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison"
        f"?from_revision_id={REVISION_100}&to_revision_id={REVISION_101}{asked}"
    )
    body = read(api, witness, realm, url)
    expected = example(name)
    got, wanted = keyed(body["items"], "lineage_id"), keyed(expected["items"], "lineage_id")
    assert list(got) == list(wanted)
    for key, item in got.items():
        theirs = wanted[key]
        for field in ("kind", "difference", "level", "changes"):
            assert item[field] == theirs[field], (label_of(item), field)
        assert base_of(item) == base_of(theirs), label_of(item)
        assert deviations(item.get("deltas"), theirs.get("deltas")) == set(), label_of(item)
        if item["kind"] == "estimate_line":
            # A line of provision too, its budgeted amount the provision it carries (#4274).
            figures = (*FIGURES, BUDGETED)
            ours = {each: item["estimate_line"][each] for each in figures}
            assert (
                deviations(ours, {each: theirs["estimate_line"][each] for each in figures}) == set()
            )
        else:
            assert label_of(item) == label_of(theirs)
    for key in ("from_revision_id", "to_revision_id"):
        assert body[key] == expected[key], key
    # The budgeted deltas and totals count the provisions the reference fixed (#4274).
    assert body["amount_deltas"] == expected["amount_deltas"]
    for key in ("totals", "base_totals", "totals_delta"):
        assert deviations(body[key], expected[key]) == set(), key
    assert body["meta"]["scheduled_at"] == instant(MERGED).isoformat().replace("+00:00", "Z")


def test_the_comparison_of_the_whole_structure_marks_the_nodes_of_the_example(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # Read whole, reduced to what the screen shows: the same marks on the same labels, the three
    # lines of provision included (EP-08); the example carries the identifiers of the revision in
    # progress, so nodes are counted by what they are.
    url = (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison?from_revision_id={REVISION_100}"
        f"&to_revision_id={REVISION_101}&fields=kind,task.label,estimate_line.label"
    )
    body = read(api, witness, realm, url)
    expected = example("volume/comparison_volume")

    def counted(items: list[dict[str, Any]]) -> Counter[tuple[str, str, str, tuple[str, ...]]]:
        return Counter(
            (*label_of(item), item["difference"], tuple(item["changes"])) for item in items
        )

    assert counted(body["items"]) == counted(expected["items"])
    assert [item["level"] for item in body["items"]] == [
        item["level"] for item in expected["items"]
    ]


@pytest.mark.requirement(COMPARISON_REQUIREMENT)
def test_the_amount_deltas_of_the_whole_comparison_are_the_lines_of_the_two_revisions_summed(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # US-1530 (#1752): each line counts under the key it bears in each revision, the keys at two
    # nought deltas left out, the sum by subproject equal to the sum by nature. Read whole, the
    # deltas are the amounts of the lines of the 101 less those of the 100, summed by key straight
    # from the rows, the provision lines included (EP-08). The nodes reduced to their kind: the
    # deltas are those of the whole comparison, which the fields do not reduce, and its 10 000
    # nodes in full cost some twenty seconds of validation (#2716).
    url = (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison?from_revision_id={REVISION_100}"
        f"&to_revision_id={REVISION_101}&fields=kind"
    )
    body = read(api, witness, realm, url)
    expected = example("volume/comparison_volume")
    with witness.transaction() as session:
        lines = {
            number: line_rows(session, REVISIONS[number], provisions=True) for number in (100, 101)
        }
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
    # The re-estimated deltas, key by key, from the rows; the deltas are the example's, the
    # provision of the risks and the budgets of the 101 included (EP-08).
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
    # The budgeted deltas too, the provisions the reference fixed included (#4274).
    assert body["amount_deltas"] == expected["amount_deltas"]
