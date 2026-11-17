# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The decimals the service writes without a bound are refused by 422 (US-1980/L2, L3).

#2875: a ``numeric`` column without precision refuses more than 16 383 decimals, one with a
precision (``numeric(14, 2)``) a whole part that crosses it, and PostgreSQL's ``DataError`` would
be a 500. As US-1840 does for the thresholds, each field refuses at its pointer a value of more
than ten decimals, or whose whole part crosses its column: the constants of the units of duration,
the durations and the lags of the planning, the unit disbursement and the quantity of a line, the
hours of a labour line (#2997), and the product of a disbursement and a quantity, at the quantity
(#2996); the recalculation at a constant at its maximum is tried (#2998); the product of a labour
line (#3035) and its re-estimated amount, projected by the inflation (#3039), refused at the
quantity, or at the field that carries the rate a change would reproject written lines with; and
the redating of a task that carries a written line past its column, at the fields sent that date it
(#3094, US-2260/L3); a move, at its parent, a change of the default calendar or of the units of
duration, at the days or the constants changed, a paste and the designation of a default calendar,
which send no field that carries it, without one (#3401, US-2400/L1). The scenario of the finding
is replayed on the test database.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import YEAR, Costing, Lines, costing
from history_support import counter
from installed_reference import holding
from nodes_support import Tree, faults, opened, refusal
from paste_support import apply as apply_paste
from paste_support import planned
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene

from waterfall.core.planning.interface.paste import DURATION
from waterfall.platform.decimals import exceeds_precision

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

UNITS = "/api/v1/reference/duration-units"
PRECISION = "VALIDATION_FAILED"
# Twenty thousand decimals, which PostgreSQL would not keep; eleven decimals, a final zero counted;
# eleven digits before the point.
OVERFLOWING = "8." + "0" * 20_000
ELEVEN_DECIMALS = "8.00000000001"
ELEVEN_DIGITS = "12345678901"
TOO_PRECISE = [OVERFLOWING, ELEVEN_DECIMALS, ELEVEN_DIGITS]


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def put_units(api: ContractClient, headers: dict[str, str], **sent: str) -> Any:
    """Set the constants of the units of duration, the ones not named left at 8, 40 and 20."""
    read = api.get(UNITS, headers=headers).json()
    body = {
        "hours_per_day": "8",
        "hours_per_week": "40",
        "days_per_month": "20",
        "lock_version": read["lock_version"],
        **sent,
    }
    return api.put(UNITS, headers=headers, json=body)


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize("name", ["hours_per_day", "hours_per_week", "days_per_month"])
@pytest.mark.parametrize("value", TOO_PRECISE)
def test_a_constant_of_more_than_ten_decimals_is_refused_at_its_field_and_nothing_is_written(
    api: ContractClient, stage: Scene, realm: TestRealm, name: str, value: str
) -> None:
    changing = holding(stage.database, realm, "resource_settings.write")
    refused = put_units(api, changing, **{name: value})
    assert faults(refused) == [(f"/{name}", PRECISION, {})]
    kept = api.get(UNITS, headers=changing).json()
    assert (kept["hours_per_day"], kept["hours_per_week"], kept["days_per_month"]) == (
        "8",
        "40",
        "20",
    )
    assert kept["lock_version"] == 1


@pytest.mark.requirement("WF-PLA-0160-A")
def test_constants_of_ten_decimals_are_written(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    changing = holding(stage.database, realm, "resource_settings.write")
    written = put_units(api, changing, hours_per_day="7.1234567891", hours_per_week="1234567890")
    assert written.status_code == 200, written.text


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize("value", TOO_PRECISE)
def test_a_duration_of_more_than_ten_decimals_is_refused_at_its_field_by_a_creation_and_a_change(
    tree: Tree, value: str
) -> None:
    sent = {"duration": {"value": value, "unit": "d"}}
    created = tree.create("Études", task=sent)
    assert faults(created) == [("/task/duration/value", PRECISION, {})]
    assert tree.labels() == []
    node = tree.made("Études")
    changed = tree.change(node, duration=sent["duration"])
    assert faults(changed) == [("/duration/value", PRECISION, {})]
    assert tree.node(node["node_id"])["task"]["duration"] == {"value": "1", "unit": "d"}


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_duration_of_ten_decimals_is_kept(tree: Tree) -> None:
    node = tree.made("Études", task={"duration": {"value": "1.1234567891", "unit": "d"}})
    assert node["task"]["duration"]["value"] == "1.1234567891"


@pytest.mark.requirement("WF-PLA-0030-A")
@pytest.mark.parametrize("value", [*TOO_PRECISE, "-" + OVERFLOWING])
def test_a_lag_of_more_than_ten_decimals_is_refused_at_its_rank_and_nothing_is_written(
    tree: Tree, value: str
) -> None:
    first, second = tree.made("Préparation"), tree.made("Reprise")
    link = {"predecessor_node_id": first["node_id"], "link_type": "finish_to_start"}
    sent = {
        "predecessors": [{**link, "lag": {"value": value, "unit": "d"}}],
        "lock_version": second["lock_version"],
    }
    path = f"{tree.path}/nodes/{second['node_id']}/predecessors"
    refused = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert faults(refused) == [("/predecessors/0/lag/value", PRECISION, {})]
    assert tree.node(second["node_id"])["predecessors"] == []


@pytest.mark.requirement("WF-DEV-0020-A")
@pytest.mark.parametrize("value", ["1" + "0" * 13, "1" + "0" * 12])
def test_a_unit_disbursement_beyond_its_column_is_refused_at_its_field_and_nothing_is_created(
    tree: Tree, lines: Lines, costs: Costing, value: str
) -> None:
    # Thirteen digits before the point overflow numeric(14, 2): the scenario of #2875. The decimals
    # of a disbursement are bounded by ``Money`` (two) before the service, so none is tried here.
    task = tree.made("Câblage")
    refused = lines.create(
        task, quantity="1", cost_category_id=str(costs.material), unit_disbursement=value
    )
    assert faults(refused) == [("/estimate_line/unit_disbursement", PRECISION, {})]
    assert tree.items("?kinds=estimate_line") == []


@pytest.mark.requirement("WF-DEV-0020-A")
@pytest.mark.parametrize("value", ["1" + "0" * 10, "1.00000000001", OVERFLOWING])
def test_a_quantity_beyond_its_column_is_refused_at_its_field_at_the_creation_and_the_change(
    tree: Tree, lines: Lines, costs: Costing, value: str
) -> None:
    # Eleven digits before the point overflow numeric(14, 4).
    task = tree.made("Câblage")
    held = {"cost_category_id": str(costs.material), "unit_disbursement": "3.00"}
    refused = lines.create(task, quantity=value, **held)
    assert faults(refused) == [("/estimate_line/quantity", PRECISION, {})]
    line = lines.made(task, quantity="1", **held)["nodes"][0]
    changed = lines.change(line, quantity=value)
    assert faults(changed) == [("/quantity", PRECISION, {})]
    assert len(tree.items("?kinds=estimate_line")) == 1


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_negative_quantity_beyond_its_column_has_one_fault_at_its_field(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    refused = lines.create(
        task,
        quantity="-1" + "0" * 11,
        cost_category_id=str(costs.material),
        unit_disbursement="3.00",
    )
    assert faults(refused) == [("/estimate_line/quantity", "VALUE_OUT_OF_RANGE", {"minimum": 0})]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_figures_at_the_edge_of_their_column_are_kept(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    held = {"cost_category_id": str(costs.material)}
    many = lines.made(task, quantity="9999999999.9999", unit_disbursement="0.00", **held)
    dear = lines.made(task, quantity="1", unit_disbursement="999999999999.99", **held)
    assert many["nodes"][0]["estimate_line"]["quantity"] == "9999999999.9999"
    assert dear["nodes"][0]["estimate_line"]["unit_disbursement"] == "999999999999.99"


@pytest.mark.requirement("WF-DEV-0020-A")
@pytest.mark.parametrize("value", ["1" + "0" * 10, ELEVEN_DECIMALS, OVERFLOWING])
def test_the_hours_of_a_labour_line_beyond_their_column_are_refused_at_their_field(
    tree: Tree, lines: Lines, costs: Costing, value: str
) -> None:
    # #2997: eleven digits before the point overflow numeric(12, 2); ten decimals are the bound.
    task = tree.made("Câblage")
    refused = lines.create(task, quantity="1", resource_role_id=str(costs.role), hours=value)
    assert faults(refused) == [("/estimate_line/hours", PRECISION, {})]
    assert tree.items("?kinds=estimate_line") == []
    line = lines.made(task, quantity="1", resource_role_id=str(costs.role), hours="1")["nodes"][0]
    changed = lines.change(line, hours=value)
    assert faults(changed) == [("/hours", PRECISION, {})]
    assert len(tree.items("?kinds=estimate_line")) == 1


@pytest.mark.requirement("WF-DEV-0020-A")
def test_the_hours_at_the_edge_of_their_column_are_kept(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    kept = lines.made(task, quantity="0", resource_role_id=str(costs.role), hours="9999999999.99")
    assert kept["nodes"][0]["estimate_line"]["hours"] == "9999999999.99"


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_product_beyond_the_base_amount_is_refused_at_the_quantity_and_nothing_is_created(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #2996: a quantity and a unit disbursement each within their column, 10^6 x (10^12 - 0.01),
    # whose product crosses the twelve digits of base_amount (numeric(14, 2)).
    task = tree.made("Câblage")
    held = {"cost_category_id": str(costs.material), "unit_disbursement": "999999999999.99"}
    refused = lines.create(task, quantity="1000000", **held)
    assert faults(refused) == [("/estimate_line/quantity", PRECISION, {})]
    assert tree.items("?kinds=estimate_line") == []
    line = lines.made(task, quantity="1", **held)["nodes"][0]
    changed = lines.change(line, quantity="1000000")
    assert faults(changed) == [("/quantity", PRECISION, {})]
    by_disbursement = lines.change(line, quantity="2", unit_disbursement="999999999999.99")
    assert faults(by_disbursement) == [("/quantity", PRECISION, {})]
    cheaper = lines.changed(line, quantity="2", unit_disbursement="1.00")
    assert cheaper["nodes"][0]["estimate_line"]["quantity"] == "2"


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_product_rounding_one_cent_above_the_base_amount_is_refused_at_the_quantity(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    held = {"cost_category_id": str(costs.material)}
    kept = lines.made(task, quantity="1", unit_disbursement="999999999999.99", **held)
    assert kept["nodes"][0]["estimate_line"]["base_amount"] == "999999999999.99"
    # Each within its column; 1.01 x 990099009900.99 = 999999999999.9999 rounds up to 10^12:
    # thirteen digits, refused at the quantity.
    refused = lines.create(task, quantity="1.01", unit_disbursement="990099009900.99", **held)
    assert faults(refused) == [("/estimate_line/quantity", PRECISION, {})]
    rounding = lines.create(task, quantity="1.0001", unit_disbursement="999900009999.99", **held)
    assert faults(rounding) == [("/estimate_line/quantity", PRECISION, {})]


@pytest.mark.requirement("WF-IHM-0050-A")
@pytest.mark.parametrize("text", ["\u0663", "\u0663 d", "3,\u0665 d", "3.\u0665"])
def test_a_pasted_duration_written_with_other_digits_than_0_to_9_is_no_duration(
    text: str,
) -> None:
    assert DURATION.fullmatch(text) is None


@pytest.mark.requirement("WF-IHM-0050-A")
@pytest.mark.parametrize(("text", "value"), [("3 d", "3"), ("2,5w", "2,5"), ("1.25", "1.25")])
def test_a_pasted_duration_of_digits_0_to_9_is_read(text: str, value: str) -> None:
    found = DURATION.fullmatch(text)
    assert found is not None
    assert found.group(1) == value


@pytest.mark.requirement("WF-DAT-0100-A")
@pytest.mark.parametrize(
    ("text", "whole_digits", "exceeds"),
    [
        ("999999999999.99", 12, False),
        ("1000000000000", 12, True),
        ("9999999999", 10, False),
        ("10000000000", 10, True),
        ("0.1234567890", 10, False),
        ("0.12345678901", 10, True),
        ("-10000000000", 10, True),
    ],
)
def test_the_whole_digits_of_a_column_bound_a_decimal_beside_its_ten_decimals(
    text: str, whole_digits: int, exceeds: bool
) -> None:
    assert exceeds_precision(Decimal(text), whole_digits) is exceeds


MOST = "9999999999.9999999999"
DEPENDING = {"hours_per_day": "d", "hours_per_week": "w", "days_per_month": "mo"}


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize("name", list(DEPENDING))
def test_the_recalculation_with_a_constant_at_its_maximum_redates_a_plan_it_does_not_convert(
    api: ContractClient, tree: Tree, stage: Scene, realm: TestRealm, name: str
) -> None:
    # #2998: ten digits before the point and ten decimals, the bound of L2. The recalculation did
    # not fail: a duration in hours or minutes depends on no constant and is dated as before.
    hours = tree.made("Heures", task={"duration": {"value": "3", "unit": "h"}})
    minutes = tree.made("Minutes", task={"duration": {"value": "90", "unit": "min"}})
    finishes = [tree.node(each["node_id"])["task"]["finish"] for each in (hours, minutes)]
    changing = holding(stage.database, realm, "resource_settings.write")
    written = put_units(api, changing, **{name: MOST})
    assert written.status_code == 200, written.text
    assert written.json()[name] == MOST
    assert [tree.node(each["node_id"])["task"]["finish"] for each in (hours, minutes)] == finishes


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize("name", list(DEPENDING))
def test_a_constant_at_its_maximum_carrying_a_task_beyond_the_horizon_is_refused_by_422_not_500(
    api: ContractClient, tree: Tree, stage: Scene, realm: TestRealm, name: str
) -> None:
    # The task that converts by the constant is carried beyond fifteen years
    # (PROJECT_HORIZON_EXCEEDED, WF-PLA-0150): a refusal that names the project, nothing is written.
    tree.made("Converti", task={"duration": {"value": "1", "unit": DEPENDING[name]}})
    changing = holding(stage.database, realm, "resource_settings.write")
    refused = put_units(api, changing, **{name: MOST})
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "PROJECT_HORIZON_EXCEEDED"
    assert api.get(UNITS, headers=changing).json()[name] != MOST


HUGE = "1000000"
RATES = "/api/v1/reference/cost-categories"


def project_url(stage: Scene) -> str:
    """Give the address of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def inflated(api: ContractClient, stage: Scene, rate: str) -> Any:
    """Change the rate of inflation of the project at the counter read; give the answer."""
    held = api.get(project_url(stage), headers=stage.manager.headers).json()["lock_version"]
    sent = {"inflation_rate": rate, "lock_version": held}
    return api.patch(project_url(stage), headers=stage.manager.headers, json=sent)


def in_two_years(tree: Tree) -> dict[str, Any]:
    """Make a task consumed two years after the year of reference."""
    return in_years(tree, 2)


def in_years(tree: Tree, years: int, label: str = "Exploitation") -> dict[str, Any]:
    """Make a manual task of two days, consumed some years after the year of reference."""
    start = date(YEAR + years, 3, 1)
    start += timedelta(days=-start.weekday() % 7)
    return tree.made(
        label,
        task={
            "scheduling_mode": "manual",
            "start": {"date": start.isoformat()},
            "finish": {"date": (start + timedelta(days=1)).isoformat()},
        },
    )


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_labour_product_beyond_the_base_amount_is_refused_at_the_quantity_and_nothing_is_written(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3035: 10^6 x 10^6 hours x 65.00 = 6.5 x 10^13, each figure within its column, the product
    # beyond the twelve digits of base_amount (numeric(14, 2)).
    task = tree.made("Câblage")
    held = {"resource_role_id": str(costs.role)}
    refused = lines.create(task, quantity=HUGE, hours=HUGE, **held)
    assert faults(refused) == [("/estimate_line/quantity", PRECISION, {})]
    assert tree.items("?kinds=estimate_line") == []
    line = lines.made(task, quantity="1", hours="1", **held)["nodes"][0]
    changed = lines.change(line, quantity=HUGE, hours=HUGE)
    assert faults(changed) == [("/quantity", PRECISION, {})]
    by_hours = lines.change(line, quantity="2000000", hours="5000000")
    assert faults(by_hours) == [("/quantity", PRECISION, {})]
    kept = tree.items("?kinds=estimate_line")[0]["estimate_line"]
    assert (kept["quantity"], kept["hours"], kept["base_amount"]) == ("1", "1", "65.00")
    cheaper = lines.changed(line, quantity="2", hours="1")
    assert cheaper["nodes"][0]["estimate_line"]["base_amount"] == "130.00"


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_labour_product_is_judged_only_when_its_figures_are_not_refused_already(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    refused = lines.create(
        task, quantity=HUGE, hours=ELEVEN_DIGITS, resource_role_id=str(costs.role)
    )
    assert faults(refused) == [("/estimate_line/hours", PRECISION, {})]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_labour_product_within_the_base_amount_is_kept(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # One engineer for 10^6 hours at 65.00: 65 000 000.00, not refused.
    task = tree.made("Câblage")
    kept = lines.made(task, quantity="1", hours=HUGE, resource_role_id=str(costs.role))["nodes"][0]
    assert kept["estimate_line"]["base_amount"] == "65000000.00"


@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_rate_that_reprices_a_written_line_beyond_the_base_amount_is_refused_at_its_amount(
    realm: TestRealm, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3035: 1000 x 100 000 hours x 65.00 = 6.5 x 10^9; the rate raised to 100 000.00 gives 10^13.
    task = tree.made("Câblage")
    lines.made(task, quantity="1000", hours="100000", resource_role_id=str(costs.role))
    api = tree.api
    changing = holding(tree.stage.database, realm, "cost_settings.read", "cost_settings.write")
    url = f"{RATES}/{costs.labour}/hourly-rates/{YEAR}"
    version = 1
    refused = api.put(url, headers=changing, json={"amount": "100000.00", "lock_version": version})
    assert faults(refused) == [("/amount", PRECISION, {})]
    kept = api.get(f"{RATES}/{costs.labour}/hourly-rates", headers=changing).json()
    assert [each["amount"] for each in kept if each["year"] == YEAR] == ["65.00"]
    line = tree.items("?kinds=estimate_line")[0]["estimate_line"]
    assert line["base_amount"] == "6500000000.00"
    allowed = api.put(url, headers=changing, json={"amount": "1000.00", "lock_version": version})
    assert allowed.status_code == 200, allowed.text


@pytest.mark.requirement("WF-DEV-0030-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_reestimated_amount_beyond_its_column_is_refused_at_the_quantity(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3039: a base amount at its limit, consumed two years after the reference at 3 %: the
    # re-estimated amount, 1.0609 x 999 999 999 999.99, has thirteen digits.
    assert inflated(api, stage, "0.03").status_code == 200
    later = in_two_years(tree)
    held = {"cost_category_id": str(costs.material), "unit_disbursement": "999999999999.99"}
    refused = lines.create(later, quantity="1", **held)
    assert faults(refused) == [("/estimate_line/quantity", PRECISION, {})]
    assert tree.items("?kinds=estimate_line") == []
    now = tree.made("Études")
    line = lines.made(now, quantity="1", **held)["nodes"][0]
    assert line["estimate_line"]["reestimated_amount"] == "999999999999.99"
    changed = lines.change(line, quantity="1.5", unit_disbursement="500000000000.00")
    assert changed.status_code == 200, changed.text


@pytest.mark.requirement("WF-PRJ-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_an_inflation_that_reprojects_a_written_line_beyond_its_column_is_refused_at_its_rate(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3039: the line, written without inflation, is at its limit two years after the reference;
    # the rate of inflation of the project, 3 %, would carry its re-estimated amount past it.
    later = in_two_years(tree)
    held = {"cost_category_id": str(costs.material), "unit_disbursement": "999999999999.99"}
    line = lines.made(later, quantity="1", **held)["nodes"][0]
    refused = inflated(api, stage, "0.03")
    assert faults(refused) == [("/inflation_rate", PRECISION, {})]
    read = api.get(project_url(stage), headers=stage.manager.headers).json()
    assert Decimal(read["inflation_rate"]) == 0
    kept = tree.items("?kinds=estimate_line")[0]["estimate_line"]
    assert kept["reestimated_amount"] == line["estimate_line"]["reestimated_amount"]


@pytest.mark.requirement("WF-DEV-0030-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_rate_that_carries_only_the_reestimated_amount_beyond_its_column_is_refused_at_its_amount(
    realm: TestRealm, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3039: the line is consumed two years after the reference, the inflation is 3 %; the rate
    # raised to 950 000 000.00 gives 1000 h x 950 000 000.00 = 9.5 x 10^11, within base_amount, and
    # 1.0609 times that, past reestimated_amount.
    api = tree.api
    assert inflated(api, tree.stage, "0.03").status_code == 200
    later = in_two_years(tree)
    lines.made(later, quantity="1", hours="1000", resource_role_id=str(costs.role))
    changing = holding(tree.stage.database, realm, "cost_settings.read", "cost_settings.write")
    url = f"{RATES}/{costs.labour}/hourly-rates/{YEAR}"
    refused = api.put(url, headers=changing, json={"amount": "950000000.00", "lock_version": 1})
    assert faults(refused) == [("/amount", PRECISION, {})]
    kept = api.get(f"{RATES}/{costs.labour}/hourly-rates", headers=changing).json()
    assert [each["amount"] for each in kept if each["year"] == YEAR] == ["65.00"]
    line = tree.items("?kinds=estimate_line")[0]["estimate_line"]
    assert line["base_amount"] == "65000.00"


def at_its_limit(lines: Lines, costs: Costing, task: dict[str, Any]) -> None:
    """Give a task a line of material at its most, consumed in the year of reference."""
    held = {"cost_category_id": str(costs.material), "unit_disbursement": "999999999999.99"}
    line = lines.made(task, quantity="1", **held)["nodes"][0]
    assert line["estimate_line"]["reestimated_amount"] == "999999999999.99"


def kept_line(tree: Tree) -> tuple[str, str, int]:
    """Read the amounts and the year of the only line of the structure."""
    line = tree.items("?kinds=estimate_line")[0]["estimate_line"]
    return line["base_amount"], line["reestimated_amount"], line["consumption_year"]


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_duration_that_carries_a_written_line_beyond_its_column_is_refused_at_the_duration(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3094: the task of the line, a day of this year, lengthened to five hundred days, is consumed
    # over three years at 3 %: the shares of the next two, projected, carry the re-estimated amount
    # past its twelve digits. The refusal is at the duration, the field that redates it.
    assert inflated(api, stage, "0.03").status_code == 200
    task = tree.made("Câblage")
    at_its_limit(lines, costs, task)
    before = kept_line(tree)
    read = tree.node(task["node_id"])
    refused = tree.change(read, duration={"value": "500", "unit": "d"})
    assert faults(refused) == [("/duration", PRECISION, {})]
    assert kept_line(tree) == before
    assert tree.node(task["node_id"])["task"] == read["task"]


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_mode_sent_with_a_duration_that_carries_a_line_beyond_its_column_is_named_in_dating_order(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3303: the mode and the duration both redate the task: each is named, in the order of DATING
    # (scheduling_mode, duration); nothing is written.
    assert inflated(api, stage, "0.03").status_code == 200
    task = tree.made("Câblage")
    at_its_limit(lines, costs, task)
    before = kept_line(tree)
    read = tree.node(task["node_id"])
    refused = tree.change(read, scheduling_mode="automatic", duration={"value": "500", "unit": "d"})
    assert faults(refused) == [
        ("/scheduling_mode", PRECISION, {}),
        ("/duration", PRECISION, {}),
    ]
    assert kept_line(tree) == before
    assert tree.node(task["node_id"])["task"] == read["task"]


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_dates_that_carry_a_written_line_beyond_its_column_are_refused_at_each_date_sent(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3094: a manual task of this year moved two years on at 3 %: 1.0609 times the amount at its
    # limit. Both dates sent redate the task: each is named; nothing is written.
    assert inflated(api, stage, "0.03").status_code == 200
    task = in_years(tree, 0)
    at_its_limit(lines, costs, task)
    before = kept_line(tree)
    read = tree.node(task["node_id"])
    later = in_years(tree, 2, "Plus tard")["task"]
    start, finish = ({"date": later[end]["date"]} for end in ("start", "finish"))
    refused = tree.change(read, start=start, finish=finish)
    assert faults(refused) == [("/start", PRECISION, {}), ("/finish", PRECISION, {})]
    assert kept_line(tree) == before
    assert tree.node(task["node_id"])["task"]["start"] == read["task"]["start"]
    renamed = tree.change(read, label="Câblage")
    assert renamed.status_code == 200, renamed.text


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_predecessors_that_carry_a_written_line_beyond_its_column_are_refused_at_the_predecessors(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3094: the automatic task of the line, made to follow a task two years on, starts after it:
    # its amount, at its limit, is projected two years at 3 %.
    assert inflated(api, stage, "0.03").status_code == 200
    task = tree.made("Câblage")
    at_its_limit(lines, costs, task)
    before = kept_line(tree)
    first = in_years(tree, 2, "Plus tard")
    read = tree.node(task["node_id"])
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": first["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "0", "unit": "d"},
            }
        ],
        "lock_version": read["lock_version"],
    }
    path = f"{tree.path}/nodes/{task['node_id']}/predecessors"
    refused = api.put(path, headers=stage.manager.headers, json=sent)
    assert faults(refused) == [("/predecessors", PRECISION, {})]
    assert kept_line(tree) == before
    assert tree.node(task["node_id"])["task"] == read["task"]


# --- The other writes that price written lines again (US-2400/L1, #3401) -------------------------

CALENDARS = "/api/v1/reference/calendars"
THIRTY_DAYS = {"duration": {"value": "30", "unit": "d"}}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def thirty_days_at_its_limit(
    api: ContractClient, stage: Scene, lines: Lines, costs: Costing
) -> dict[str, Any]:
    """Give a task of thirty days of this year a line at its most, the project inflating at 3 %."""
    assert inflated(api, stage, "0.03").status_code == 200
    task = lines.tree.made("Câblage", task=THIRTY_DAYS)
    at_its_limit(lines, costs, task)
    return task


def halved(lines: Lines) -> None:
    """Halve the quantity of the only line of the structure, which then crosses no column."""
    [line] = lines.tree.items("?kinds=estimate_line")
    lines.changed(line, quantity="0.5")


def default_of(api: ContractClient, headers: dict[str, str]) -> dict[str, Any]:
    """Read the default calendar."""
    listed = api.get(f"{CALENDARS}?sort_by=is_default", headers=headers).json()["items"]
    return next(each for each in listed if each["is_default"])


def three_days_a_week() -> dict[str, str]:
    """Give a week of eight hours from Monday to Wednesday, none after."""
    return dict(zip(WEEKDAYS, ("8", "8", "8", "0", "0", "0", "0"), strict=True))


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_line_moved_to_a_task_that_carries_it_past_its_column_is_refused_at_the_parent(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3401 (US-2400): the line at its limit, moved under a task two years on at 3 %, is consumed
    # there: 1.0609 times its amount. The parent sent gives it the dates of that task: the refusal
    # names it; nothing is written.
    assert inflated(api, stage, "0.03").status_code == 200
    task = tree.made("Câblage")
    at_its_limit(lines, costs, task)
    before = kept_line(tree)
    later = in_years(tree, 2, "Plus tard")
    [line] = tree.items("?kinds=estimate_line")
    sent = {
        "node_ids": [line["node_id"]],
        "parent_id": later["node_id"],
        "lock_version": counter(tree),
    }
    refused = api.post(f"{tree.path}/nodes/move", headers=stage.manager.headers, json=sent)
    assert faults(refused) == [("/parent_id", PRECISION, {})]
    assert kept_line(tree) == before
    assert tree.items("?kinds=estimate_line")[0]["parent_id"] == task["node_id"]


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_paste_that_carries_a_written_line_past_its_column_is_refused_without_a_field(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # #3401 (US-2400): a duration of five hundred days pasted on the task of the line carries its
    # shares over three years at 3 %. The confirmation sends the plan, its confirmation and the
    # counter, none of the cells: no field of the request carries the change, and the refusal
    # names none (docs/api/DECISIONS.md); nothing is written. The line halved, the paste is made.
    assert inflated(api, stage, "0.03").status_code == 200
    task = tree.made("Câblage")
    at_its_limit(lines, costs, task)
    before = kept_line(tree)
    read = tree.node(task["node_id"])
    plan = planned(tree, task, "duration", [["500"]])
    assert (plan["accepted"], plan["rejected"]) == (1, [])
    refused = apply_paste(tree, plan)
    assert refusal(refused) == (422, PRECISION, {})
    assert refused.json().get("fields", []) == []
    assert kept_line(tree) == before
    assert tree.node(task["node_id"])["task"] == read["task"]
    halved(lines)
    again = apply_paste(tree, planned(tree, task, "duration", [["500"]]))
    assert again.status_code == 200, again.text


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_hours_per_day_that_carry_a_written_line_past_its_column_are_refused_at_the_constant(
    api: ContractClient, stage: Scene, realm: TestRealm, lines: Lines, costs: Costing
) -> None:
    # #3401 (US-2400): the task of thirty days, at sixteen hours a day, lasts 480 hours on the
    # calendar of eight: past the year, its share of the next one projected at 3 %. The hours per
    # day, the one constant changed, carry the change; the two sent as they were are not named.
    task = thirty_days_at_its_limit(api, stage, lines, costs)
    before = kept_line(lines.tree)
    changing = holding(stage.database, realm, "resource_settings.write")
    refused = put_units(api, changing, hours_per_day="16")
    assert faults(refused) == [("/hours_per_day", PRECISION, {})]
    assert api.get(UNITS, headers=changing).json()["hours_per_day"] == "8"
    assert kept_line(lines.tree) == before
    assert lines.tree.node(task["node_id"])["task"]["finish"] == task["task"]["finish"]


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_hours_of_the_default_calendar_that_carry_a_line_past_its_column_are_refused_at_each_day(
    api: ContractClient, stage: Scene, realm: TestRealm, lines: Lines, costs: Costing
) -> None:
    # #3401 (US-2400): the default calendar left with three days of eight hours, the task of thirty
    # days lasts ten weeks, past the year. Each day whose hours change is named, in the order of
    # the week; the days sent as they were are not; nothing is written.
    task = thirty_days_at_its_limit(api, stage, lines, costs)
    before = kept_line(lines.tree)
    changing = holding(stage.database, realm, "resource_settings.read", "resource_settings.write")
    calendar = default_of(api, changing)
    sent = {
        "label": calendar["label"],
        "weekly_hours": three_days_a_week(),
        "lock_version": calendar["lock_version"],
    }
    path = f"{CALENDARS}/{calendar['calendar_id']}"
    refused = api.patch(path, headers=changing, json=sent)
    assert faults(refused) == [
        ("/weekly_hours/thursday", PRECISION, {}),
        ("/weekly_hours/friday", PRECISION, {}),
    ]
    assert default_of(api, changing)["weekly_hours"] == calendar["weekly_hours"]
    assert kept_line(lines.tree) == before
    assert lines.tree.node(task["node_id"])["task"]["finish"] == task["task"]["finish"]


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_default_calendar_designated_that_carries_a_line_past_its_column_has_no_field(
    api: ContractClient, stage: Scene, realm: TestRealm, lines: Lines, costs: Costing
) -> None:
    # #3401 (US-2400): a calendar of three days a week designated the default lengthens the task of
    # thirty days past the year. The designation sends its counter alone: no field carries the
    # change, and the refusal names none (docs/api/DECISIONS.md); nothing is written. The line
    # halved, the calendar is designated.
    task = thirty_days_at_its_limit(api, stage, lines, costs)
    before = kept_line(lines.tree)
    changing = holding(stage.database, realm, "resource_settings.read", "resource_settings.write")
    former = default_of(api, changing)
    body = {"label": "Trois jours", "weekly_hours": three_days_a_week()}
    created = api.post(CALENDARS, headers=changing, json=body)
    assert created.status_code == 201, created.text
    shorter = created.json()
    path = f"{CALENDARS}/{shorter['calendar_id']}/default"
    refused = api.put(path, headers=changing, json={"lock_version": shorter["lock_version"]})
    assert refusal(refused) == (422, PRECISION, {})
    assert refused.json().get("fields", []) == []
    assert default_of(api, changing)["calendar_id"] == former["calendar_id"]
    assert kept_line(lines.tree) == before
    assert lines.tree.node(task["node_id"])["task"]["finish"] == task["task"]["finish"]
    halved(lines)
    designated = api.put(path, headers=changing, json={"lock_version": shorter["lock_version"]})
    assert designated.status_code == 200, designated.text


@pytest.mark.requirement("WF-DEV-0040-A")
@pytest.mark.requirement("WF-DAT-0100-A")
def test_hours_of_a_calendar_that_is_not_the_default_redate_and_reprice_nothing(
    api: ContractClient, stage: Scene, realm: TestRealm, lines: Lines, costs: Costing
) -> None:
    # #3401 (US-2400): the hours of the task of thirty days, at its limit, would carry its line past
    # the year on the default calendar cut to three days (see above). On another calendar, no task
    # of EP-06 is on it: the change is kept (200), nothing is redated nor priced again.
    task = thirty_days_at_its_limit(api, stage, lines, costs)
    before = kept_line(lines.tree)
    changing = holding(stage.database, realm, "resource_settings.read", "resource_settings.write")
    body = {"label": "Autre semaine", "weekly_hours": dict(zip(WEEKDAYS, "8888800", strict=True))}
    created = api.post(CALENDARS, headers=changing, json=body)
    assert created.status_code == 201, created.text
    other = created.json()
    assert not other["is_default"]
    sent = {
        "label": other["label"],
        "weekly_hours": three_days_a_week(),
        "lock_version": other["lock_version"],
    }
    changed = api.patch(f"{CALENDARS}/{other['calendar_id']}", headers=changing, json=sent)
    assert changed.status_code == 200, changed.text
    assert changed.json()["weekly_hours"] == three_days_a_week()
    assert kept_line(lines.tree) == before
    assert lines.tree.node(task["node_id"])["task"]["finish"] == task["task"]["finish"]
