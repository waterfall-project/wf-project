# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of the estimate of an offer, drawn from its lines (US-2680/L1b).

An offer has a devis of 100 without provisions and a provision line of 50: the budget stops at 100,
the projection, provisions included, reaches 150, from a base of nought; the actual cost is empty;
the cash-out by month is that of the mode with the payment delays alone. The document is that of
the portfolio (``portfolio_offer_curves``): the two curves ``cost_curve`` and
``cost_curve_payment_delays``, which the portfolio weights then sums (US-2740).
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from planning_support import DAY

from waterfall.core.costs.interface import PROJECT
from waterfall.core.estimate.interface import IndicatorLine, Placement
from waterfall.core.indicators.offering import offer_curves_document
from waterfall.core.indicators.shaping import Context
from waterfall.core.planning.interface import WorkInstant, weekly_calendar

D = Decimal
EIGHT = D(8)
WEEK = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, D(0), D(0)))
AT = datetime(2026, 11, 2, 9, tzinfo=UTC)
CONTEXT = Context(uuid4(), "draft", AT, PROJECT, is_stored=False)


def line_of(amount: str, *, provision: bool = False, delay: int = 0) -> IndicatorLine:
    """Give a line of a task of the week of ``DAY``, the provision flagged, without a delay."""
    task = uuid4()
    held = Placement(WEEK, WorkInstant(DAY), WorkInstant(DAY + timedelta(days=4), EIGHT))
    value = D(amount)
    return IndicatorLine(
        uuid4(), task, task, None, None, value, value, delay, held, is_provision=provision
    )


def curves(*lines: IndicatorLine, context: Context = CONTEXT) -> dict[str, Any]:
    """Draw the curves of an offer whose remaining to commit is the amount of each line."""
    remaining = {each.node_id: each.reestimated_amount for each in lines}
    budgeted = [each for each in lines if not each.is_provision]
    return dict(offer_curves_document(budgeted, lines, remaining, DAY, context))


def series(document: dict[str, Any], kind: str, name: str) -> list[dict[str, str]]:
    """Give the points of a series of one of the two curves."""
    found = next(each for each in document[kind]["series"] if each["name"] == name)
    return found["points"]


def last_day(document: dict[str, Any], kind: str) -> str:
    """Give the day of the last point of the reference budget of one of the two curves."""
    return series(document, kind, "reference_budget")[-1]["date"]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_offer_budget_leaves_the_provisions_out_and_the_projection_counts_them() -> None:
    # [US-2680] « les courbes d'une offre » : a devis of 100 and a provision of 50: 100 at the final
    # budget, 150 at the final projection, the base of the projection being nought.
    document = curves(line_of("100.00"), line_of("50.00", provision=True))
    assert set(document) == {"cost_curve", "cost_curve_payment_delays"}
    for kind in document:
        assert series(document, kind, "reference_budget")[-1]["amount"] == "100.00"
        assert series(document, kind, "project_manager_projection")[-1]["amount"] == "150.00"
        assert series(document, kind, "project_manager_projection")[0]["amount"] == "0.00"


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_offer_has_no_actual_cost_and_the_cash_out_only_with_the_payment_delays() -> None:
    document = curves(line_of("100.00", delay=30), line_of("50.00", provision=True))
    for kind in document:
        assert series(document, kind, "actual_cost") == []
    assert document["cost_curve"]["payment_delays"] is False
    assert document["cost_curve"]["cash_out_by_month"] is None
    assert document["cost_curve_payment_delays"]["payment_delays"] is True
    cash_out = document["cost_curve_payment_delays"]["cash_out_by_month"]
    assert [(each["past"]) for each in cash_out] == ["0.00"] * len(cash_out)
    assert sum((D(each["forecast"]) for each in cash_out), D(0)) == D("150.00")


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_payment_delay_shifts_the_budget_of_the_offer_not_its_provision() -> None:
    # A delay of 60 days moves the 100 of the devis to the end of the budget a later month; a
    # provision line has none, whatever the delay it would carry (WF-IND-0100-A).
    plain = curves(line_of("100.00"))
    delayed = curves(line_of("100.00", delay=60))
    assert last_day(delayed, "cost_curve") == last_day(plain, "cost_curve")
    assert last_day(delayed, "cost_curve_payment_delays") > last_day(
        plain, "cost_curve_payment_delays"
    )


@pytest.mark.requirement("WF-IND-0100-A")
def test_an_offer_without_lines_has_no_point() -> None:
    document = curves()
    for kind in document:
        for name in ("reference_budget", "actual_cost"):
            assert series(document, kind, name) == []


def test_the_context_of_the_offer_is_the_one_given() -> None:
    marked = replace(CONTEXT, revision_status="marked")
    document = curves(line_of("100.00"), context=marked)
    assert document["cost_curve"]["context"]["revision_status"] == "marked"
