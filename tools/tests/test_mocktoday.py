# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the indicators of the witness today: estimate, remaining, project, curves, workload.

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from wftools import (
    mockcore,
    mockcosts,
    mockcurves,
    mockdata,
    mockhistory,
    mockindicators,
    mockstructure,
    mocktext,
    mocktoday,
    mockwitness,
)
from wftools.mockcalendar import Calendar, Instant
from wftools.mockids import universe
from wftools.mockindicators import Flow
from wftools.mockwitness import COMMISSIONING, CORE, ELECTRICAL_ENGINEERING, GENERATED

type Node = dict[str, Any]

CONTROL, TESTS = universe(801), universe(802)


@pytest.fixture(scope="module")
def today() -> dict[str, Any]:
    """Read the examples of the indicators back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mocktoday.examples().items()
    }


def _amount(envelope: Node) -> Decimal:
    assert envelope["is_computable"] is True
    return Decimal(envelope["value"])


def _series(curve: Node, name: str) -> list[Node]:
    return next(each["points"] for each in curve["series"] if each["name"] == name)


def test_the_estimate_today_sums_the_lines_of_the_whole_structure(today: dict[str, Any]) -> None:
    # EP-14/L45a: the estimate of the witness is that of its thousand tasks, the core's 121,534.56
    # among them.
    estimate = today["estimate_indicators"]
    whole: Any = mockcore.whole(mockcore.current())["totals"]
    core: Any = mockcore.whole(mockcore.alone())["totals"]
    total = _amount(estimate["total"])
    assert total == Decimal(whole["base_amount"]) == Decimal("65605723.89")
    assert Decimal(core["base_amount"]) == Decimal("121534.56")
    for parts in (estimate["by_cost_type"], estimate["by_subproject"]):
        assert sum(_amount(part["amount"]) for part in parts) == total
        assert sum(_amount(part["share"]) for part in parts) == 1
    assert [part.get("label") for part in estimate["by_subproject"]] == [
        "Poste de commande",
        "Essais et mise en service",
        None,
    ]
    # The order item is borne by the lot « Poste de commande » of the core: the total of its
    # subtree, which no drawn task is under.
    [item] = estimate["by_order_item"]
    lot: Any = mockcore.subtree(mockcore.current(), 551)["totals"]
    assert _amount(item["amount"]) == Decimal(lot["base_amount"]) == Decimal("2934.56")
    assert estimate["provisions_identified"] == "500.00"
    # The previous marked revision is the reference: its estimate held 910 of provisions, and the
    # same drawn lines at the same rates.
    reference = sum(row.amounts.base for row in mockhistory.reference_rows() if row.parent)
    assert _amount(estimate["delta_to_reference"]) == total - reference == Decimal("-210.00")
    assert estimate["delta_to_previous_revision"] == estimate["delta_to_reference"]


def test_the_estimate_the_offer_kept_has_neither_gap_nor_provision(today: dict[str, Any]) -> None:
    offer = today["estimate_indicators_breakdown"]
    assert offer["context"]["revision_id"] == mockhistory.OFFER
    assert offer["context"]["is_stored"] is True
    assert offer["context"]["computed_at"] == "2025-12-15T16:00:00Z"
    assert offer["delta_to_reference"] is None
    assert offer["delta_to_previous_revision"] is None
    assert offer["provisions_identified"] == "0.00"
    assert [part["label"] for part in offer["by_cost_type"]] == ["Main-d'œuvre", "Débours"]
    # Priced at the rates of 2025: 10 h of the connection at 78.50.
    assert _amount(offer["by_order_item"][0]["amount"]) == Decimal("785.00") + Decimal("1234.56")


def test_a_rate_missing_leaves_out_what_its_lines_touch(today: dict[str, Any]) -> None:
    estimate = today["estimate_indicators_missing_rates"]
    missing = today["missing_rates"]
    assert missing == [
        {"cost_category_id": ELECTRICAL_ENGINEERING, "label": "Ingénierie électrique", "year": 2026}
    ]
    assert estimate["total"]["params"]["missing_rates"] == missing
    computed = {
        part.get("label", "unassigned"): part["amount"]["is_computable"]
        for key in ("by_cost_type", "by_subproject", "by_order_item")
        for part in estimate[key]
    }
    # Every subproject bears labour of the electrical engineering, the drawn tasks' among it.
    assert computed == {
        "Main-d'œuvre": False,
        "Débours": True,
        "Provision": True,
        "Poste de commande": False,
        "Essais et mise en service": False,
        "unassigned": False,
        "Fourniture et montage des armoires": False,
    }
    shares = [part["share"] for key in ("by_cost_type", "by_subproject") for part in estimate[key]]
    assert not any(share["is_computable"] for share in shares)
    assert estimate["delta_to_reference"]["reason"] == "hourly_rate_missing"


def test_the_rate_update_proposes_the_rates_of_the_grid_for_2026(today: dict[str, Any]) -> None:
    # #232, C15: the revision 101, created in 2026 from the offer of 2025, is proposed for each
    # labour category of the offer the rate the grid of the rates gives for 2026, its rate of
    # 2025 beside — those at which the comparison prices the offer and the reference.
    grid: Any = mockdata.hourly_rate_grid()
    cells = {
        row["cost_category_id"]: dict(zip(grid["years"], row["cells"], strict=True))
        for row in grid["rows"]
    }
    proposal = today["rate_update"]
    assert proposal["target_year"] == 2026
    found = [
        (entry["cost_category_id"], entry["previous_amount"], entry["proposed_amount"])
        for entry in proposal["categories"]
    ]
    assert found == [
        (category, cells[category][2025]["amount"], cells[category][2026]["amount"])
        for category in (ELECTRICAL_ENGINEERING, COMMISSIONING)
    ]
    assert [entry[1:] for entry in found] == [("78.50", "80.00"), ("73.50", "75.00")]
    assert {entry["source"] for entry in proposal["categories"]} == {"reference_rate"}


def test_the_remaining_counts_each_line_by_the_state_of_its_task(today: dict[str, Any]) -> None:
    # Nothing for a task completed, the re-estimate of a task started, the budget of a task not
    # started; the lines budgeted nothing for their re-estimate, the provisions for their amount.
    witness = mockindicators.today()
    by_state: dict[str, Decimal] = {}
    for line in witness.lines:
        if mockhistory.is_provision(line) or line.amounts.budgeted == 0:
            key = "provision" if mockhistory.is_provision(line) else "merged"
        else:
            key = witness.progress(line)
        by_state[key] = by_state.get(key, Decimal(0)) + mockindicators.remaining_of(witness, line)
    assert by_state == {
        "completed": Decimal(0),
        "started": Decimal("416710.83"),
        "provision": Decimal("500.00"),
        "merged": Decimal("200.00"),
        "not_started": Decimal("66376117.89"),
    }
    # The core alone counts as it did before the structure was summed (EP-02/L24).
    core = mockindicators.today(CORE)
    assert sum(
        mockindicators.remaining_of(core, line)
        for line in core.lines
        if core.progress(line) == "started" and not mockhistory.is_provision(line)
    ) == Decimal("2234.56")
    left = today["remaining_indicators"]
    assert Decimal(left["total"]) == sum(by_state.values())
    assert sum(Decimal(part["amount"]) for part in left["by_cost_type"]) == Decimal(left["total"])
    assert sum(Decimal(part["share"]) for part in left["by_cost_type"]) == 1


def test_the_balances_sum_to_the_project_and_signal_the_one_over_its_budget(
    today: dict[str, Any],
) -> None:
    left = today["remaining_indicators"]
    balances = {entry["key"]: entry for entry in left["by_subproject"]}
    assert list(balances) == [CONTROL, TESTS, "unassigned"]
    assert sum(Decimal(entry["remaining"]) for entry in balances.values()) == Decimal(left["total"])
    for entry in balances.values():
        variance = Decimal(entry["budget"]) - Decimal(entry["actual_cost"])
        assert Decimal(entry["variance"]) == variance - Decimal(entry["remaining"])
        assert entry["is_over_budget"] is (Decimal(entry["variance"]) < 0)
        assert entry["zone"] == ("alert" if entry["is_over_budget"] else "nominal")
    # The invoice of the screens is the one cost of the control station, whose drawn lots follow
    # the factory acceptance and have not started; its budget is overrun by the inflation of its
    # remaining, projected on the years of consumption, and by the invoice.
    assert (balances[CONTROL]["actual_cost"], balances[CONTROL]["variance"]) == (
        "2400.00",
        "-1037316.10",
    )
    assert Decimal(balances[TESTS]["actual_cost"]) == sum(
        line.amount for line in mockcosts.drawn() if line.code == "SP-ESS"
    )
    assert left["coverage"] == {
        key: value for key, value in today_coverage().items() if key != "context"
    }
    # The sequel of the re-estimate made today: 200 less to commit on the control station.
    over = {
        entry["key"]: entry for entry in today["remaining_indicators_over_budget"]["by_subproject"]
    }
    assert Decimal(over[CONTROL]["remaining"]) == Decimal(balances[CONTROL]["remaining"]) - 200


def test_the_gaps_of_the_remaining_to_the_budget_have_one_sense(today: dict[str, Any]) -> None:
    # #466: the gap to the reference budget is the budget less the actual cost and the
    # remaining, as each balance of a subproject is: the balances sum to it, negative once the
    # budget is overrun — as the witness is since the invoice of the studies (EP-02/L25).
    for name in ("remaining_indicators", "remaining_indicators_over_budget"):
        left = today[name]
        balances = left["by_subproject"]
        gap = Decimal(left["delta_to_reference"])
        assert gap == sum(Decimal(entry["variance"]) for entry in balances)
        assert gap == sum(
            Decimal(entry["budget"]) - Decimal(entry["actual_cost"]) - Decimal(entry["remaining"])
            for entry in balances
        )
        assert gap < 0
    # The re-estimate made today commits 200 less: the margin grows by as much.
    gaps = [
        Decimal(today[name]["delta_to_reference"])
        for name in ("remaining_indicators", "remaining_indicators_over_budget")
    ]
    assert gaps[1] - gaps[0] == 200
    # The summaries name the one a margin and the other a gap (review 2 of EP-02/L35).
    for name, gap in zip(
        ("remaining_indicators", "remaining_indicators_over_budget"), gaps, strict=True
    ):
        summary = str(mocktoday.examples()[f"{name}.json"]["summary"])
        assert f"la marge sur le budget de référence, {mocktext.amount(gap)}" in summary
        assert "l'écart à la revue précédente, " in summary


def today_coverage() -> dict[str, Any]:
    """Return the coverage of the risks today, as the history of the witness reads it."""
    return mockhistory.coverage(mockcore.core(), mockhistory.reference_rows())


def test_the_indicators_of_the_scopes_sum_to_those_of_the_project() -> None:
    witness, base = mockindicators.today(), mockindicators.reference()
    costs = mockindicators.actual_costs()
    found: dict[str, Any] = {
        scope: mockindicators.project_indicators(witness, base, costs, scope)
        for scope, _ in mockindicators.scopes()
    }
    project = found.pop("project")
    for field in ("planned_value", "earned_value", "actual_cost", "remaining", "reference_budget"):
        assert sum(Decimal(each[field]) for each in found.values()) == Decimal(project[field])
    # The studies, completed on 10 April, earn their budget, and each drawn task completed its
    # own; the occurrence earns nothing. The actual cost is the invoices of the tracked scope.
    assert project["earned_value"] == "1449858.33"
    assert project["actual_cost"] == "1412970.20"
    assert project["reference_budget"] == "65430697.64"
    drawn = sum(
        line.amounts.budgeted
        for line in witness.lines
        if line.number >= GENERATED and witness.progress(line) == "completed"
    )
    assert Decimal(project["earned_value"]) == Decimal("100000.00") + drawn


def test_the_marked_reference_keeps_its_indicators_at_its_marking(today: dict[str, Any]) -> None:
    marked = today["project_indicators_marked"]
    assert marked["context"] == {
        "revision_id": mockhistory.REFERENCE,
        "revision_status": "marked",
        "computed_at": "2026-02-01T09:00:00Z",
        "scope": "project",
        "is_stored": True,
    }
    # Nothing started: the budget of each line projected on its year of consumption — the core's
    # in 2026, as the budget; the drawn tasks' up to 2029 — and the provisions of the three risks
    # it bore, 910.
    base = mockindicators.reference()
    projected = sum(
        mockstructure.inflated(
            line.amounts.budgeted, cast("int", base.facet(line)["consumption_year"])
        )
        for line in mockindicators.budgeted(base)
    )
    assert Decimal(marked["remaining"]) == projected + 910 == Decimal("68242478.05")
    assert Decimal(marked["remaining"]) > Decimal(marked["reference_budget"]) + 910
    assert marked["reference_budget"] == "65430697.64"
    assert marked["schedule_index"]["value"]["reason"] == "no_planned_value"


def test_the_marks_the_review_journey_reads(today: dict[str, Any]) -> None:
    # The review of a project (frontend/e2e/review.spec.ts) reads the indicators of the witness by
    # these figures, written there as each language shows them: a change of the generator that
    # moves them fails here.
    project = today["project_indicators"]
    assert project["context"]["computed_at"] == "2026-06-03T14:05:00Z"
    assert (
        project["remaining"],
        project["reference_budget"],
        project["planned_value"],
        project["schedule_variance"],
        project["schedule_index"]["value"]["value"],
        project["cost_index"]["value"]["value"],
    ) == ("66793528.72", "65430697.64", "1671458.13", "-221599.80", "0.8674", "1.0261")
    assert (project["schedule_index"]["zone"], project["cost_index"]["zone"]) == (
        "watch",
        "nominal",
    )


def test_the_curves_reach_the_budget_and_the_projection_of_the_project_manager(
    today: dict[str, Any],
) -> None:
    project = today["project_indicators"]
    curve = today["cost_curve"]
    assert _series(curve, "reference_budget")[-1]["amount"] == project["reference_budget"]
    assert (
        _series(today["earned_value_curves"], "planned_value")[-1]["amount"]
        == (project["reference_budget"])
    )
    actual = _series(curve, "actual_cost")
    projection = _series(curve, "project_manager_projection")
    assert actual[-1] == projection[0] == {"date": "2026-06-03", "amount": "1412970.20"}
    assert projection[-1]["amount"] == project["projections"]["project_manager"]
    earned = _series(today["earned_value_curves"], "earned_value")
    assert earned[-1] == {"date": "2026-06-03", "amount": project["earned_value"]}


def test_an_amendment_steps_the_budget_by_two_points_at_its_date(today: dict[str, Any]) -> None:
    curve = today["cost_curve_amendment"]
    budget = _series(curve, "reference_budget")
    for step in curve["steps"]:
        before, after = (point["amount"] for point in budget if point["date"] == step["date"])
        assert step["cause"] == "amendment"
        if step["date"] == "2026-03-10":
            # During the studies: what the new reference had planned more by that day.
            assert (before, after) == ("23333.33", "26833.33")
        else:
            assert before == after == "0.00"
    assert [step["amount"] for step in curve["steps"]] == ["2865.00", "15000.00"]
    assert budget[-1]["amount"] == "65445697.64"


def test_the_disbursements_to_come_sum_to_the_remaining(today: dict[str, Any]) -> None:
    curve = today["cost_curve_payment_delays"]
    months = curve["cash_out_by_month"]
    to_come = sum(Decimal(month["forecast"]) for month in months)
    assert to_come == Decimal(today["remaining_indicators"]["total"])
    past = sum(Decimal(month["past"]) for month in months)
    assert past == Decimal(today["project_indicators"]["actual_cost"])
    for month in months:
        if month["month"] < "2026-06":
            assert month["forecast"] == "0.00"
        if month["month"] > "2026-06":
            assert month["past"] == "0.00"
    # The studies are paid a month after their work: nothing by the end of March.
    assert {"date": "2026-03-31", "amount": "0.00"} in _series(curve, "reference_budget")


def test_the_milestones_follow_the_revisions_that_bear_them(today: dict[str, Any]) -> None:
    studies, acceptance = today["milestone_tracking"]["milestones"]
    # The reception of the studies, kept by every revision, completed on 24 April: its last
    # point on the diagonal, none after.
    assert studies["completed_on"] == "2026-04-24"
    assert [point["forecast_date"] for point in studies["points"]] == ["2026-04-24"] * 3
    assert studies["points"][-1]["marked_at"] == "2026-04-24T00:00:00Z"
    # The factory acceptance, added by the amendment 1: no point by the offer (C13).
    assert [point["marked_at"] for point in acceptance["points"]] == [
        "2026-02-01T09:00:00Z",
        "2026-06-03T14:05:00Z",
    ]
    assert {point["forecast_date"] for point in acceptance["points"]} == {"2026-06-30"}


def test_the_workload_spreads_the_hours_of_the_lines_not_completed(today: dict[str, Any]) -> None:
    witness = mockindicators.today()
    for role in today["workload"]["roles"]:
        lines = [
            line
            for line in witness.lines
            if witness.facet(line)["resource_role_id"] == role["resource_role_id"]
            and witness.progress(line) != "completed"
        ]
        assert sum(Decimal(month["hours"]) for month in role["months"]) == sum(
            line.hours for line in lines
        )
        # On the remaining to commit, what is left to work: never a month before today.
        assert all(month["month"] >= "2026-06" for month in role["months"])
    roles = [role["resource_role_id"] for role in today["workload"]["roles"]]
    assert roles == [universe(451), universe(452), universe(454)]
    # In the core, the wiring, started on 4 May, has its 12.5 hours left in June, after the
    # calculation; the reference spreads them over the whole task, May and June. The structure
    # adds the hours of the drawn tasks to those months.
    core = _loaded(mockcurves.workload(mockindicators.today(CORE), "current_remaining"))
    engineer = core[0]["months"][0]
    assert (engineer["month"], engineer["hours"]) == ("2026-06", "12.5")
    planned = _loaded(
        mockcurves.workload(
            mockindicators.reference(mockwitness.reference(CORE)), "reference_budget"
        )
    )[0]["months"][:2]
    assert [(month["month"], month["hours"]) for month in planned] == [
        ("2026-05", "5.95"),
        ("2026-06", "6.55"),
    ]
    june = today["workload"]["roles"][0]["months"][0]
    assert (june["month"], june["hours"]) == ("2026-06", "1465.75")
    assert Decimal(june["hours"]) > Decimal(engineer["hours"])


def _loaded(plan: mockstructure.JsonObject) -> list[Node]:
    """Return the roles of a workload, read back from the text the generator writes."""
    return cast("list[Node]", json.loads(json.dumps(plan))["roles"])


def test_a_node_of_organisation_retains_the_roles_under_it_alone(today: dict[str, Any]) -> None:
    # The cabling workshop holds the cable fitter; the engineer and the technician, of the
    # electrical design office above it, are left out.
    filtered = today["workload_org_node"]
    assert filtered["org_node_label"] == "Atelier de câblage"
    assert [role["resource_role_id"] for role in filtered["roles"]] == [universe(454)]
    everyone = {role["resource_role_id"]: role for role in today["workload"]["roles"]}
    assert filtered["roles"] == [everyone[universe(454)]]


def test_the_evolution_of_the_indices_keeps_the_revisions_marked_in_progress(
    today: dict[str, Any],
) -> None:
    # The offer, marked while pricing, kept the indicators of its estimate alone: no point; the
    # reference at its marking, then the current revision today (WF-DAT-0040, #468).
    for scope in today["index_history"]["scopes"]:
        assert [point["revision_id"] for point in scope["points"]] == [
            mockhistory.REFERENCE,
            mockhistory.CURRENT,
        ]
    # The tracking of the milestones keeps the forecast of the offer.
    studies = today["milestone_tracking"]["milestones"][0]
    assert studies["points"][0]["marked_at"] == "2025-12-15T16:00:00Z"


def test_the_state_at_a_marking_is_read_in_the_transitions_of_the_project_not_from_its_date() -> (
    None
):
    # The offer was marked while pricing, the reference In progress (`state_transitions`).
    assert mockindicators.state_at(mockwitness.OFFER_MARKED.instant) == "pricing"
    assert mockindicators.state_at(mockwitness.AMENDMENT_MERGED.instant) == "in_progress"
    assert mockindicators.state_at(mockwitness.INSTALLED.instant) is None
    # Suspended after its order, a project marks no revision In progress, whatever the date; a
    # transition at the very instant of the marking counts.
    at = mockwitness.AMENDMENT_MERGED.instant
    transitions: list[mockstructure.JsonObject] = [
        {"to_state": "in_progress", "occurred_at": "2026-01-15T11:00:00Z"},
        {"to_state": "suspended", "occurred_at": mockhistory.stamp(at)},
    ]
    assert mockindicators.state_at(at, transitions) == "suspended"


def test_one_run_writes_the_portfolio_from_the_indicators_it_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The portfolio sums the indicators of the witness: it reads them in memory, not from the
    # file the same command writes, so that indicators changed are written whole by one run.
    monkeypatch.setattr(mocktoday, "actual_costs", _no_costs)
    mockdata.write(tmp_path)
    assert mockdata.check(tmp_path) == []
    written = json.loads((tmp_path / "project_indicators.json").read_text("utf-8"))["value"]
    assert written["cost_index"]["value"]["reason"] == "no_actual_cost"
    rows = json.loads((tmp_path / "volume" / "portfolio_projects.json").read_text("utf-8"))
    witness = rows["value"]["items"][0]
    assert witness["cost_index"] == written["cost_index"]
    assert witness["cost_index"] != mockwitness.fixture("project_indicators")["cost_index"]


def _no_costs(known: Sequence[mockwitness.CostLine] | None = None) -> list[mockindicators.Cost]:
    """Stand for the actual costs of the witness with none at all, whatever the lines given."""
    del known
    return []


def test_each_subproject_in_alert_is_named_in_the_summary_and_none_said_nominal() -> None:
    # The summaries of the remaining to commit follow the zones the answer gives (WF-RAE-0020):
    # a scope in alert is named with its overrun, and never said nominal.
    for name in ("remaining_indicators", "remaining_indicators_over_budget"):
        example = json.loads(mockdata.render(mocktoday.examples()[f"{name}.json"]))
        summary = example["summary"]
        for entry in example["value"]["by_subproject"]:
            label = entry.get("label")
            named = "l'ensemble hors sous-projet" if label is None else f"« {label} »"
            if entry["zone"] == "alert":
                overrun = mocktext.amount(-Decimal(entry["variance"]))
                assert f"{named}, en alerte, dépasse son budget de {overrun}" in summary, name
                assert f"{named} nominal" not in summary, name


def _by_date(points: list[Node]) -> dict[str, list[Decimal]]:
    """Return the amounts of a series by date: two at the date of a step, before and after."""
    found: dict[str, list[Decimal]] = {}
    for point in points:
        found.setdefault(point["date"], []).append(Decimal(point["amount"]))
    return found


def _spent_by(points: list[Node], day: str) -> Decimal:
    """Return the cumulative actual cost a series reaches by a day: nothing before its first."""
    return max(
        ((point["date"], Decimal(point["amount"])) for point in points if point["date"] <= day),
        default=("", Decimal(0)),
    )[1]


@pytest.mark.parametrize("delays", [False, True])
def test_the_curves_of_the_scopes_sum_to_the_curve_of_the_project(*, delays: bool) -> None:
    # Each series of the cost curve counts the lines of its scope alone (`scope`, WF-IND-0020):
    # at every date the curves of the scopes share with the project's, those of the subprojects
    # and of what belongs to none sum to the project's. Every scope has lines and costs in the
    # whole structure, the tests and commissioning by the lots « Ligne d'essais » (EP-14/L45a).
    found = mocktoday.witness()
    curves: dict[str, Any] = {
        scope: mockcurves.cost_curve(
            found.today, found.eras, found.costs, delays=delays, scope=scope
        )
        for scope, _ in mockindicators.scopes()
    }
    project = curves.pop("project")
    assert all(_series(curves[TESTS], name) for name in ("reference_budget", "actual_cost"))
    for name in ("reference_budget", "actual_cost", "project_manager_projection"):
        whole = _by_date(_series(project, name))
        parts = [_by_date(_series(curve, name)) for curve in curves.values()]
        drawn = [part for part in parts if part]
        common = [day for day in whole if all(day in part for part in drawn)]
        assert len(common) >= 2, name
        # Each scope is read to the cent: the parts summed may miss the whole by their rounding.
        tolerance = Decimal("0.01") * (len(drawn) - 1)
        for day in common:
            summed = [sum(amounts) for amounts in zip(*(part[day] for part in drawn), strict=True)]
            assert len(summed) == len(whole[day]), (name, day)
            for part, total in zip(summed, whole[day], strict=True):
                assert abs(part - total) <= tolerance, (name, day)
    # The actual cost steps at the dates of documents alone: read at every date of the project's.
    for day, amounts in _by_date(_series(project, "actual_cost")).items():
        spent = [_spent_by(_series(curve, "actual_cost"), day) for curve in curves.values()]
        assert sum(spent) == amounts[-1], day
    steps = sum(Decimal(step["amount"]) for curve in curves.values() for step in curve["steps"])
    assert steps == sum(Decimal(step["amount"]) for step in project["steps"])
    if delays:
        # Each scope's months from its own first document: summed month by month, to the cent of
        # each scope.
        months = [
            {month["month"]: month for month in curve["cash_out_by_month"]}
            for curve in curves.values()
        ]
        for month in project["cash_out_by_month"]:
            for key in ("past", "forecast"):
                summed = sum(
                    (
                        Decimal(part[month["month"]][key])
                        for part in months
                        if month["month"] in part
                    ),
                    Decimal(0),
                )
                assert abs(summed - Decimal(month[key])) <= tolerance, (month["month"], key)
    assert {curve["context"]["scope"] for curve in curves.values()} == set(curves)


def test_the_curve_of_a_subproject_counts_its_lines_alone(today: dict[str, Any]) -> None:
    curve = today["cost_curve_subproject"]
    project: dict[str, Any] = mockindicators.project_indicators(
        mockindicators.today(), mockindicators.reference(), mockindicators.actual_costs(), CONTROL
    )
    assert curve["context"]["scope"] == CONTROL
    assert _series(curve, "reference_budget")[-1]["amount"] == project["reference_budget"]
    assert _series(curve, "actual_cost")[-1]["amount"] == project["actual_cost"] == "2400.00"
    assert (
        _series(curve, "project_manager_projection")[-1]["amount"]
        == project["projections"]["project_manager"]
    )
    # The offer declared no subproject: the amendment 1 gave the control station its whole budget.
    assert [step["amount"] for step in curve["steps"]] == [project["reference_budget"]]
    assert today["cost_curve"]["steps"][0]["amount"] != curve["steps"][0]["amount"]


def test_the_evolution_of_the_indices_of_a_scope_is_its_entry_alone(today: dict[str, Any]) -> None:
    whole, alone = today["index_history"], today["index_history_subproject"]
    [entry] = alone["scopes"]
    assert entry == next(each for each in whole["scopes"] if each["scope"] == CONTROL)
    assert alone["context"] == {**whole["context"], "scope": CONTROL}
    assert whole["context"]["scope"] == "project"


def test_a_scope_without_line_nor_cost_has_nothing_to_draw(today: dict[str, Any]) -> None:
    # A declared variant since EP-14/L45a: the core read alone, where no line relates to the tests
    # and commissioning; in the whole structure, the lots « Ligne d'essais » do.
    curve = today["cost_curve_subproject_empty"]
    for name in ("cost_curve_subproject_empty", "cost_curve_subproject_empty_payment_delays"):
        summary = str(mocktoday.examples()[f"{name}.json"]["summary"])
        assert "le cœur" in summary
        assert summary.startswith(("Variante contrefactuelle", "La même variante"))
    found = mocktoday.witness()
    whole = mockcurves.cost_curve(found.today, found.eras, found.costs, scope=TESTS)
    assert all(_series(whole, name) for name in ("reference_budget", "actual_cost"))
    assert curve["context"]["scope"] == TESTS
    assert [each["points"] for each in curve["series"]] == [[], [], []]
    assert curve["steps"] == []
    assert curve["cash_out_by_month"] is None
    delayed = today["cost_curve_subproject_empty_payment_delays"]
    assert delayed["payment_delays"] is True
    assert [each["points"] for each in delayed["series"]] == [[], [], []]
    assert delayed["steps"] == []
    assert delayed["cash_out_by_month"] == []


def test_a_scope_without_budget_draws_its_cost_and_its_projection(today: dict[str, Any]) -> None:
    # The counterfactual variant: the offer, which declared no subproject, still the reference.
    curve, budgeted = today["cost_curve_subproject_unbudgeted"], today["cost_curve_subproject"]
    assert curve["context"]["scope"] == CONTROL
    assert _series(curve, "reference_budget") == []
    assert curve["steps"] == []
    spent = _series(curve, "actual_cost")
    # Drawn from the day before its first document, the invoice of the control station.
    assert spent[0] == {"date": "2026-05-17", "amount": "0.00"}
    assert spent[-1] == _series(budgeted, "actual_cost")[-1]
    projection = _series(curve, "project_manager_projection")
    assert projection == _series(budgeted, "project_manager_projection")


def test_the_spread_sums_the_flows_as_each_flow_spends() -> None:
    # The flows summed at once once spent whole, and read one by one while under way, give at
    # every day what the sum of each flow gives: on two calendars, with and without a delay, from
    # before the first flow begins to after the last is spent.
    standard = Calendar("standard", tuple(Decimal(h) for h in (8, 8, 8, 8, 8, 0, 0)))
    four_days = Calendar("four", tuple(Decimal(h) for h in (10, 10, 10, 10, 0, 0, 0)))
    flows = [
        Flow(Decimal("1234.56"), standard, _at(6, 1), _at(6, 12, 8)),
        Flow(Decimal("80.00"), four_days, _at(6, 4, 6), _at(6, 18, 4), 30),
        Flow(Decimal("500.00"), standard, _at(6, 30, 8), _at(6, 30, 8)),
        Flow(Decimal("99.99"), standard, _at(7, 13), _at(8, 7, 8), 7),
        Flow(Decimal("0.01"), four_days, _at(7, 14), _at(7, 14, 10)),
    ]
    spread = mockcurves.Spread.of(flows)
    days = {flow.first - timedelta(days=1) for flow in flows} | {flow.last for flow in flows}
    days |= {_at(5, 1).day, _at(6, 15).day, _at(7, 31).day, _at(9, 30).day}
    for day in sorted(days):
        expected = sum((flow.by(day) for flow in flows), Decimal(0)).quantize(Decimal("0.01"))
        assert spread.by(day) == expected, day
    assert spread.by(_at(9, 30).day) == sum((flow.amount for flow in flows), Decimal(0))
    # On the budget of the witness too, at the ends of a few months and at the day of today.
    base = mockindicators.reference()
    budget = mockcurves.budget_flows(base, delays=True)
    whole = mockcurves.Spread.of(budget)
    for day in (date(2026, 4, 30), date(2026, 6, 3), date(2027, 12, 31), date(2029, 9, 30)):
        expected = sum((flow.by(day) for flow in budget), Decimal(0)).quantize(Decimal("0.01"))
        assert whole.by(day) == expected, day


def _at(month: int, day: int, hours: int = 0) -> Instant:
    return Instant(date(2026, month, day), Decimal(hours))


def test_the_summaries_count_the_drawn_tasks_completed_and_the_curves_step_at_their_completion(
    today: dict[str, Any],
) -> None:
    # The indicators of the project and the curves of earned value say how many drawn tasks are
    # completed — those the invoices of the actual costs are of (EP-14/L45a) —, and the earned
    # value steps at each day one completed, after the studies on 10 April.
    invoices = mockcosts.drawn()
    assert len(invoices) == 21
    for name in ("project_indicators", "earned_value_curves"):
        summary = str(mocktoday.examples()[f"{name}.json"]["summary"])
        assert f"{len(invoices)} tâches tirées" in summary, name
    earned = _series(today["earned_value_curves"], "earned_value")
    days = {point["date"] for point in earned}
    assert {line.on.isoformat() for line in invoices} | {"2026-04-10"} <= days
    witness = mockindicators.today()
    for point in earned:
        day = date.fromisoformat(point["date"])
        assert Decimal(point["amount"]) == mockindicators.earned(witness, day), point
