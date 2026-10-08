# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the indicators of the witness today: estimate, remaining, project, curves, workload.

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from wftools import (
    mockcore,
    mockdata,
    mockhistory,
    mockindicators,
    mockstructure,
    mocktext,
    mocktoday,
    mockwitness,
)
from wftools.mockwitness import COMMISSIONING, ELECTRICAL_ENGINEERING, universe

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


def test_the_estimate_today_sums_the_lines_of_the_core(today: dict[str, Any]) -> None:
    estimate = today["estimate_indicators"]
    core: Any = mockcore.whole(mockcore.core())["totals"]
    total = _amount(estimate["total"])
    assert total == Decimal(core["base_amount"]) == Decimal("121534.56")
    for parts in (estimate["by_cost_type"], estimate["by_subproject"]):
        assert sum(_amount(part["amount"]) for part in parts) == total
        assert sum(_amount(part["share"]) for part in parts) == 1
    # The order item is borne by the lot « Poste de commande »: the total of its subtree.
    [item] = estimate["by_order_item"]
    lot: Any = mockcore.subtree(mockcore.core(), 551)["totals"]
    assert _amount(item["amount"]) == Decimal(lot["base_amount"])
    assert estimate["provisions_identified"] == "500.00"
    # The previous marked revision is the reference: its estimate held 910 of provisions.
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
    assert computed == {
        "Main-d'œuvre": False,
        "Débours": True,
        "Provision": True,
        "Poste de commande": False,
        "unassigned": True,
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
        "started": Decimal("2234.56"),
        "provision": Decimal("500.00"),
        "merged": Decimal("200.00"),
        "not_started": Decimal("18300.00"),
    }
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
    # The invoice of the screens of the control station is over the estimate of its lines.
    assert (balances[CONTROL]["actual_cost"], balances[CONTROL]["variance"]) == (
        "2400.00",
        "-2400.00",
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
    # The studies, completed on 10 April, earn their budget; the occurrence earns nothing.
    assert project["earned_value"] == "100000.00"
    assert project["actual_cost"] == "105400.00"
    assert project["reference_budget"] == "120534.56"


def test_the_marked_reference_keeps_its_indicators_at_its_marking(today: dict[str, Any]) -> None:
    marked = today["project_indicators_marked"]
    assert marked["context"] == {
        "revision_id": mockhistory.REFERENCE,
        "revision_status": "marked",
        "computed_at": "2026-02-01T09:00:00Z",
        "scope": "project",
        "is_stored": True,
    }
    # Nothing started: the budget and the provisions of the three risks it bore, 910.
    assert Decimal(marked["remaining"]) == Decimal(marked["reference_budget"]) + 910
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
    ) == ("21234.56", "120534.56", "101223.69", "-1223.69", "0.9879", "0.9488")


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
    assert actual[-1] == projection[0] == {"date": "2026-06-03", "amount": "105400.00"}
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
    assert budget[-1]["amount"] == "135534.56"


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
    # The wiring, started on 4 May, has its 12.5 hours left in June, after the calculation;
    # the reference spreads them over the whole task, May and June.
    engineer = today["workload"]["roles"][0]["months"][0]
    assert (engineer["month"], engineer["hours"]) == ("2026-06", "12.5")
    planned = today["workload_reference_budget"]["roles"][0]["months"][:2]
    assert [(month["month"], month["hours"]) for month in planned] == [
        ("2026-05", "5.95"),
        ("2026-06", "6.55"),
    ]


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
    monkeypatch.setattr(mocktoday, "actual_costs", list)
    mockdata.write(tmp_path)
    assert mockdata.check(tmp_path) == []
    written = json.loads((tmp_path / "project_indicators.json").read_text("utf-8"))["value"]
    assert written["cost_index"]["value"]["reason"] == "no_actual_cost"
    rows = json.loads((tmp_path / "volume" / "portfolio_projects.json").read_text("utf-8"))
    witness = rows["value"]["items"][0]
    assert witness["cost_index"] == written["cost_index"]
    assert witness["cost_index"] != mockwitness.fixture("project_indicators")["cost_index"]


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
