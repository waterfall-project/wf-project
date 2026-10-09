# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the views of the portfolio over time: the workload, the S-curve, the health.

They try the simplifications of the fake back against the rules the views sum by, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockcurves, mockids, mockindicators, mockportfolio, mockstructure, mockwitness
from wftools import mockportfoliotime as views
from wftools.mockids import universe
from wftools.mockwitness import TODAY

type Node = dict[str, Any]

WITNESS, OFFER = universe(1), universe(2)
ENGINEER, TECHNICIAN, FITTER = universe(451), universe(452), universe(454)


@pytest.fixture(scope="module")
def rows() -> list[Node]:
    return cast("list[Node]", mockportfolio.portfolio()["items"])


def workload(part: list[Node], org: str | None = None) -> Node:
    return cast("Node", views.portfolio_workload(part, org))


def curve(part: list[Node], *, delays: bool = False, months: list[date] | None = None) -> Node:
    return cast("Node", views.portfolio_cost_curve(part, delays=delays, months=months))


def _hours(plan: Node) -> dict[tuple[str, str], Decimal]:
    return {
        (role["resource_role_id"], month["month"]): Decimal(month["hours"])
        for role in plan["roles"]
        for month in role["months"]
    }


def _points(curve: Node) -> dict[tuple[str, str], Decimal]:
    return {
        (series["name"], point["date"]): Decimal(point["amount"])
        for series in curve["series"]
        for point in series["points"]
    }


# --- The workload -------------------------------------------------------------------------------


def test_the_workload_sums_the_hours_of_the_projects_role_by_role_and_month_by_month(
    rows: list[Node],
) -> None:
    # The witness and half the others, then the other half: the plan of all is their sum.
    first, second = rows[: len(rows) // 2], rows[len(rows) // 2 :]
    whole, one, other = (workload(part) for part in (rows, first, second))
    summed = {key: value + _hours(other)[key] for key, value in _hours(one).items()}
    assert _hours(whole) == summed
    # The witness brings the hours of its own workload, on the remaining to commit.
    own = mockcurves.workload(mockindicators.today(), "current_remaining")
    alone = _hours(workload([row for row in rows if row["project_id"] == WITNESS]))
    for role in cast("list[Node]", own["roles"]):
        for month in role["months"]:
            if (role["resource_role_id"], month["month"]) in alone:
                assert alone[role["resource_role_id"], month["month"]] == Decimal(month["hours"])


def test_an_offer_weighs_its_estimate_by_its_probability_of_winning(rows: list[Node]) -> None:
    offers = [row for row in rows if row["state"] == "pricing" and row["current_estimate"]]
    assert len(offers) == 30
    for row in offers:
        found = views.course(row)
        assert found is not None
        weighted = Decimal(row["current_estimate"]) * Decimal(row["win_probability"])
        assert found.budget == found.left == weighted
        assert found.actual == 0
        assert found.start > TODAY.date()
    # The offer of the universe has no estimate yet: it weighs nothing.
    assert views.course(next(row for row in rows if row["project_id"] == OFFER)) is None


def test_the_cable_fitter_shows_his_capacity_without_load_and_every_month_its_zone() -> None:
    plan = mockwitness.fixture("portfolio_workload")
    roles = {role["resource_role_id"]: role for role in plan["roles"]}
    assert list(roles) == [ENGINEER, TECHNICIAN, FITTER]
    assert {month["hours"] for month in roles[FITTER]["months"]} == {"0"}
    zones: set[str] = set()
    for role in plan["roles"]:
        capacity = Decimal(role["capacity_monthly_hours"])
        for month in role["months"]:
            assert month["zone"] == views.load_zone(Decimal(month["hours"]), capacity)
            zones.add(month["zone"])
    # A month over its capacity, one under the threshold, one between (WF-PTF-0060).
    assert zones == {"alert", "watch", "nominal"}


@pytest.mark.parametrize(
    ("load", "zone"),
    [("101", "alert"), ("100", "nominal"), ("50", "nominal"), ("49.99", "watch"), ("0", "watch")],
)
def test_a_month_is_zoned_by_the_capacity_and_the_threshold_of_under_load(
    load: str, zone: str
) -> None:
    assert views.load_zone(Decimal(load), Decimal(100)) == zone


def test_the_filtered_workload_keeps_the_roles_under_the_node_and_names_it(
    rows: list[Node],
) -> None:
    filtered = mockwitness.fixture("portfolio_workload_org_node")
    assert filtered["scope"]["org_node_id"] == views.ORG_NODE
    assert filtered["scope"]["org_node_label"] == "Direction technique"
    assert filtered["roles"] == mockwitness.fixture("portfolio_workload")["roles"]
    workshop = workload(rows, universe(472))
    assert [role["resource_role_id"] for role in workshop["roles"]] == [FITTER]


# --- The S-curve --------------------------------------------------------------------------------


@pytest.mark.parametrize("delays", [False, True])
def test_each_point_of_the_curve_is_the_sum_of_the_points_of_the_projects(
    rows: list[Node], *, delays: bool
) -> None:
    first, second = rows[: len(rows) // 3], rows[len(rows) // 3 :]
    whole, one, other = (curve(part, delays=delays) for part in (rows, first, second))
    assert _points(whole) == {
        key: value + _points(other)[key] for key, value in _points(one).items()
    }
    if delays:
        months = zip(one["cash_out_by_month"], other["cash_out_by_month"], strict=True)
        assert whole["cash_out_by_month"] == [
            {
                "month": a["month"],
                "past": mockstructure.money(Decimal(a["past"]) + Decimal(b["past"])),
                "forecast": mockstructure.money(Decimal(a["forecast"]) + Decimal(b["forecast"])),
            }
            for a, b in months
        ]
    else:
        assert whole["cash_out_by_month"] is None


@pytest.mark.parametrize("delays", [False, True])
def test_the_curve_reads_the_witness_at_the_points_of_its_own_curve(
    rows: list[Node], *, delays: bool
) -> None:
    alone = curve([row for row in rows if row["project_id"] == WITNESS], delays=delays)
    own = mockwitness.fixture("cost_curve_payment_delays" if delays else "cost_curve")
    for name in ("reference_budget", "actual_cost", "project_manager_projection"):
        points = next(s["points"] for s in own["series"] if s["name"] == name)
        for point in next(s for s in alone["series"] if s["name"] == name)["points"]:
            before = [p for p in points if p["date"] <= point["date"]]
            assert point["amount"] == (before[-1]["amount"] if before else "0.00"), name
    if delays:
        months = {month["month"]: month for month in own["cash_out_by_month"]}
        for month in alone["cash_out_by_month"]:
            mine = months.get(month["month"], {"past": "0.00", "forecast": "0.00"})
            assert (month["past"], month["forecast"]) == (mine["past"], mine["forecast"])


def _progressing(rows: list[Node]) -> list[Node]:
    return [r for r in rows if r["state"] == "in_progress" and r["project_id"] != WITNESS]


def _curves(row: Node, *, delays: bool = False) -> views.Curves:
    found = views.course(row)
    assert found is not None
    return views.course_curves(found, delays=delays)


def test_the_reference_budget_of_a_project_today_is_its_planned_value(rows: list[Node]) -> None:
    day = TODAY.date()
    planned = Decimal(0)
    for row in _progressing(rows):
        values = mockportfolio.earned(row)
        assert values.planned <= values.budget
        assert _curves(row).budget(day) == values.planned
        assert _curves(row).budget(date(2030, 1, 1)) == values.budget
        planned += values.planned
    # Summed with the witness's, the planned value the performance of the portfolio gives.
    witness = mockwitness.fixture("project_indicators")
    performance = mockwitness.fixture("volume/portfolio_performance")
    earned = sum(
        (mockportfolio.earned(row).earned for row in rows if row["state"] == "in_progress"),
        Decimal(0),
    )
    assert planned + Decimal(witness["planned_value"]) == earned - Decimal(
        performance["schedule_variance"]
    )


def test_nothing_is_spent_by_the_end_of_the_quarter_declared_not_computable(
    rows: list[Node],
) -> None:
    end = date(2025, 9, 30)
    quarters = mockwitness.fixture("volume/portfolio_performance")["quarterly"]
    assert quarters[0]["quarter"] == "2025-Q3"
    assert quarters[0]["cost_index"]["reason"] == "no_actual_cost"
    for row in _progressing(rows):
        assert _curves(row).actual(end) == 0
        assert _curves(row).budget(end) == 0
    assert all(date.fromisoformat(cost["document_date"]) > end for cost in _costs())


def _costs() -> list[Node]:
    return mockwitness.fixture("actual_costs")["items"]


def test_a_project_without_costs_imported_since_its_review_spends_nothing_after_it(
    rows: list[Node],
) -> None:
    silent = [row for row in _progressing(rows) if views.no_cost_since_review(row)]
    assert silent
    for row in silent:
        marked = date.fromisoformat(row["last_marked_at"][:10])
        curves = _curves(row)
        assert curves.actual(marked) == mockportfolio.earned(row).actual
        assert curves.actual(TODAY.date()) == curves.actual(marked)
        assert curves.actual(marked - timedelta(days=7)) < curves.actual(marked)


def test_some_project_pays_in_the_month_of_today_what_it_works_after_today(
    rows: list[Node],
) -> None:
    day, end = TODAY.date(), date(2026, 6, 30)
    paying = [
        row
        for row in _progressing(rows)
        if _curves(row, delays=True).projection(end) > _curves(row, delays=True).projection(day)
    ]
    assert paying
    cash = mockwitness.fixture("portfolio_cost_curve_payment_delays")["cash_out_by_month"]
    june = next(month for month in cash if month["month"] == "2026-06")
    assert Decimal(june["past"]) > 0
    assert Decimal(june["forecast"]) > 0


def test_the_credit_variant_follows_the_courses_but_in_december(rows: list[Node]) -> None:
    credit = mockwitness.fixture("portfolio_cost_curve_credit")
    perimeter = cast("list[Node]", views.credit_perimeter(rows))
    assert WITNESS not in {row["project_id"] for row in perimeter}
    assert credit["scope"] == {
        **credit["scope"],
        "as_of": "2025-12-31",
        "states": ["in_progress"],
        "project_count": len(perimeter),
    }
    plain = cast(
        "Node",
        views.portfolio_cost_curve(
            perimeter,
            delays=True,
            as_of=views.CREDIT_ON,
            months=[date(2025, 10, 31), date(2025, 11, 30), date(2025, 12, 31)],
            states=("in_progress",),
        ),
    )
    for name in ("reference_budget", "actual_cost"):
        mine = next(s["points"] for s in credit["series"] if s["name"] == name)
        theirs = next(s["points"] for s in plain["series"] if s["name"] == name)
        assert mine[:2] == theirs[:2], name
    assert credit["cash_out_by_month"][:2] == plain["cash_out_by_month"][:2]
    # If the invoices of December had not been imported yet: a month of net negative cash-out.
    assert Decimal(credit["cash_out_by_month"][2]["past"]) < 0


def test_the_projection_starts_where_the_actual_cost_ends_today_and_never_falls() -> None:
    curve = mockwitness.fixture("portfolio_cost_curve")
    series = {s["name"]: s["points"] for s in curve["series"]}
    today = TODAY.date().isoformat()
    assert series["actual_cost"][-1]["date"] == series["project_manager_projection"][0]["date"]
    assert series["actual_cost"][-1] == series["project_manager_projection"][0]
    assert series["actual_cost"][-1]["date"] == today
    assert len(series["reference_budget"]) == views.CURVE_MONTHS
    for points in series.values():
        amounts = [Decimal(point["amount"]) for point in points]
        assert amounts == sorted(amounts)


# --- The health of the steering ---------------------------------------------------------------


def test_the_witness_is_signalled_its_review_overdue_and_nothing_else() -> None:
    health = mockwitness.fixture("pilot_health")
    own = [s for s in health["signals"] if s["project_id"] == WITNESS]
    weeks = (TODAY.date() - mockwitness.AMENDMENT_MERGED.on).days // 7
    assert own == [
        {
            "project_id": WITNESS,
            "project_label": "Modernisation du poste de commande",
            "can_open": True,
            "zone": "watch",
            "code": "review_overdue",
            "params": {"weeks_since_last_mark": weeks},
        }
    ]
    assert weeks == 17


def test_each_signal_names_a_project_in_progress_as_its_row_does(rows: list[Node]) -> None:
    health = mockwitness.fixture("pilot_health")
    limit = mockwitness.fixture("reference_settings")["max_weeks_between_reviews"]
    by_id = {row["project_id"]: row for row in rows}
    family = next(f for f in mockids.IDENTIFIERS if f.what == "jalons du portefeuille")
    codes: set[str] = set()
    for signal in health["signals"]:
        row = by_id[signal["project_id"]]
        assert row["state"] == "in_progress"
        assert (signal["project_label"], signal["can_open"]) == (row["label"], row["can_open"])
        codes.add(signal["code"])
        if signal["code"] == "review_overdue":
            marked = date.fromisoformat(row["last_marked_at"][:10])
            assert signal["params"]["weeks_since_last_mark"] == (TODAY.date() - marked).days // 7
            assert signal["params"]["weeks_since_last_mark"] > limit
        if signal["code"] == "contractual_milestone_overdue":
            assert signal["zone"] == "alert"
            assert family.holds(signal["params"]["lineage_id"])
            assert signal["params"]["reference_date"] < TODAY.date().isoformat()
    assert codes == set(views.SIGNALS)
    # A project marked within the limit is not signalled overdue.
    overdue = {s["project_id"] for s in health["signals"] if s["code"] == "review_overdue"}
    for row in rows:
        if row["state"] == "in_progress" and row["project_id"] not in overdue:
            marked = date.fromisoformat(row["last_marked_at"][:10])
            assert (TODAY.date() - marked).days // 7 <= limit


# --- The coverage of the risks ----------------------------------------------------------------


def test_the_reserve_and_the_occurred_cost_are_sums_over_the_projects_in_progress(
    rows: list[Node],
) -> None:
    risks = mockportfolio.portfolio_risks(rows)
    witness = mockwitness.fixture("risk_coverage")
    others = [
        mockportfolio.project_coverage(row)
        for row in rows
        if row["state"] == "in_progress" and row["project_id"] != WITNESS
    ]
    coverage = cast("Node", risks["coverage"])
    assert Decimal(coverage["reserve"]) == Decimal(witness["reserve"]) + sum(
        (reserve for reserve, _ in others), Decimal(0)
    )
    assert Decimal(coverage["occurred_cost"]) == Decimal(witness["occurred_cost"]) + sum(
        (cost for _, cost in others), Decimal(0)
    )
    assert cast("Node", risks["matrix"])["totals"]["reserve"] == coverage["reserve"]


def test_the_credit_variant_reads_at_its_day_what_the_curve_of_today_reads_then() -> None:
    credit = mockwitness.fixture("portfolio_cost_curve_credit")
    today = mockwitness.fixture("portfolio_cost_curve_payment_delays")

    def series(curve: Node, name: str) -> dict[str, Decimal]:
        points = next(s["points"] for s in curve["series"] if s["name"] == name)
        return {point["date"]: Decimal(point["amount"]) for point in points}

    end = "2025-12-31"
    assert series(credit, "reference_budget")[end] == series(today, "reference_budget")[end]
    assert next(iter(series(today, "reference_budget"))) == end
    # November spent, then the documents of December: what the curve of today spent by then.
    december = next(m for m in today["cash_out_by_month"] if m["month"] == "2025-12")
    spent = series(credit, "actual_cost")["2025-11-30"] + Decimal(december["past"])
    tolerance = Decimal("0.01") * credit["scope"]["project_count"]
    assert abs(spent - series(today, "actual_cost")[end]) <= tolerance
    # The counterfactual: the credit notes alone, two hundredths of those documents.
    assert Decimal(credit["cash_out_by_month"][2]["past"]) == -(
        Decimal(december["past"]) * views.CREDIT_SHARE
    ).quantize(Decimal("0.01"))


def test_the_quarterly_evolution_is_read_from_the_curves_of_the_projects(
    rows: list[Node],
) -> None:
    quarters = mockwitness.fixture("volume/portfolio_performance")["quarterly"]
    assert [q["quarter"] for q in quarters] == list(mockportfolio.QUARTERS)
    first, *others = quarters
    assert first["cost_index"]["reason"] == "no_actual_cost"
    assert first["schedule_index"]["reason"] == "no_planned_value"
    ends = [date(2025, 12, 31), date(2026, 3, 31), TODAY.date()]
    for quarter, end in zip(others, ends, strict=True):
        read = curve(rows, months=[end]) if end < TODAY.date() else curve(rows)
        spent = next(s for s in read["series"] if s["name"] == "actual_cost")["points"]
        actual = Decimal(next(p for p in spent if p["date"] == end.isoformat())["amount"])
        if end < TODAY.date():
            budget = next(s for s in read["series"] if s["name"] == "reference_budget")
            planned = Decimal(budget["points"][0]["amount"])
        else:
            planned = sum(
                (
                    mockportfolio.earned(row).planned
                    for row in rows
                    if row["state"] == "in_progress"
                ),
                Decimal(0),
            )
        # The schedule index over the cost index is the actual cost over the planned value.
        cost = Decimal(quarter["cost_index"]["value"])
        schedule = Decimal(quarter["schedule_index"]["value"])
        assert abs(schedule / cost - actual / planned) < Decimal("0.02"), quarter["quarter"]
    # The quarter of today is today's indices.
    performance = mockwitness.fixture("volume/portfolio_performance")
    assert others[-1]["cost_index"] == performance["cost_index"]["value"]
