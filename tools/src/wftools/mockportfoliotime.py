# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The views of the portfolio over time, summed from its projects (EP-02/L26, #287).

The aggregated workload (WF-PTF-0060), the S-curve of the portfolio (WF-PTF-0100) and the health
of the steering (WF-PTF-0110), today, over the three hundred projects of ``getPortfolioProjects``
(``wftools.mockportfolio``). The witness brings its own readings, read in memory — its workload,
its cost curve, its milestones (``wftools.mocktoday``) —; every other project brings what its row
and a few values drawn from the seed give, by simple formulas said here, to be replaced by the
kernel of EP-10 and EP-11:

- a project in progress works from a start drawn after the first quarter of the evolution of the
  indices — which nothing had yet been spent nor planned in (``mockportfolio``) — and before
  February 2026, to a finish drawn after today; its reference budget is spread in two pieces, its
  planned value (``mockportfolio.earned``) evenly over its days up to today and the rest over its
  days after, so that the curve and the performance tell the same planned value; its actual cost
  is spread over its days up to today — up to its last marked revision for a project whose costs
  have not been imported since (WF-PTF-0110) —, and what it has left to commit, its projection less
  its actual cost, over its days after today;
- an offer, when the pricing is included, is spread so over the days of a period drawn after
  today, its current estimate weighted by its probability of winning (WF-PTF-0060, WF-PTF-0100):
  it stands for the reference budget and for the projection of the project manager, nothing being
  spent;
- the labour of a project is the share of its remaining to commit — of its estimate for an offer —
  that the structure of the costs gives the labour (``mockportfolio``), parted between the
  electrical engineer and the commissioning technician by a share drawn for the project, at the
  hourly rate of the category of each role for the reference year; the cable fitter works on no
  project, and shows his capacity alone (decision of 2026-10-08 on #375);
- with the payment delays, the reference budget and what is left to commit are paid a delay drawn
  for the project, nought to sixty days, after their work, the actual cost as it is dated, as the
  witness does for its subcontracting (WF-IND-0100).

Nothing here reads the clock or draws at random: every value comes from the seed and from what it
describes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING, Any, cast

from wftools import (
    mockcurves,
    mockhistory,
    mockindicators,
    mockportfolio,
    mocktext,
    mocktoday,
)
from wftools.mockids import MILESTONES, identifier, universe
from wftools.mockportfolio import Earned, earned, identified_risks, portfolio, role_shares
from wftools.mockstructure import CENT, LABOUR_RATES, JsonObject, JsonValue, decimal, draw, money
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    COST_IMPORTS,
    IDENTIFIED,
    REGISTER,
    TODAY,
    by_identifier,
    fixture,
)

if TYPE_CHECKING:
    from collections.abc import Callable

DAY = TODAY.date()
"""The day every view of the portfolio is computed at: today, as every first example."""

STARTED_FROM, STARTED_TO = date(2025, 10, 1), date(2026, 1, 31)
"""When a generated project in progress may have started: after the first quarter of the evolution
of the indices, declared not computable (``mockportfolio``), and before the first revision a
generated project marked, on 2 February 2026."""

CREDIT_ON = date(2025, 12, 31)
"""The day of calculation of the variant ``portfolio_cost_curve_credit``."""

_LABOUR_OF_REMAINING, _LABOUR_OF_ESTIMATE = Decimal("0.5"), Decimal("0.55")
"""The share of the labour in the remaining to commit, and in an estimate: those of the
structure of the costs of the portfolio (``mockportfolio``)."""

UNDER_LOAD = Decimal("0.5")
"""The threshold of under-load the server retains when the request names none (WF-PTF-0060)."""

HORIZON = 6
"""The months of the workload when the request names no horizon, the month of today the first."""

CURVE_MONTHS = 12
"""The months of the S-curve: six past, the month of today and five to come."""

ORG_NODE = universe(470)
"""The node of organisation the filtered workload retains: the technical direction, whose
descendants hold every role of the universe (``org_nodes``, WF-REF-0070)."""


# --- Each project over time ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Course:
    """A generated project over time: its days of work, what it spreads on them, its labour.

    ``planned`` of ``budget`` is spread over its days up to today, the rest over those after;
    ``actual`` over its days up to ``spent_until``; ``left`` over its days after today; ``hours``
    are its labour hours left to work, by role; ``delay`` is how long after its work it pays it. An
    offer has its probability of winning already applied to its amounts.
    """

    start: date
    finish: date
    budget: Decimal
    planned: Decimal
    actual: Decimal
    spent_until: date
    left: Decimal
    hours: dict[str, Decimal]
    delay: timedelta


def _share(start: date, finish: date, day: date) -> Decimal:
    """Return the share of a span of days worked by the end of a day, from nought to one."""
    if day < start:
        return Decimal(0)
    if day >= finish:
        return Decimal(1)
    return Decimal((day - start).days + 1) / Decimal((finish - start).days + 1)


@cache
def _rates() -> dict[str, Decimal]:
    """Return the hourly rate of each active role, that of its category for the reference year."""
    return {
        role["resource_role_id"]: LABOUR_RATES[role["cost_category_id"]]
        for role in fixture("resource_roles")["items"]
        if role["is_active"]
    }


def _hours(project_id: JsonValue, labour: Decimal) -> dict[str, Decimal]:
    rates = _rates()
    return {
        role: (labour * share / rates[role]).quantize(CENT)
        for role, share in role_shares(project_id).items()
    }


def course(row: JsonObject) -> Course | None:
    """Return a generated project of the list over time, or nothing for an offer without estimate.

    A project in progress started between ``STARTED_FROM`` and ``STARTED_TO`` and finishes within
    two years after today; an offer would start within six months and last up to eighteen.
    """
    key = f"course/{row['project_id']}"
    delay = timedelta(days=draw(f"{key}/delay", 0, 60))
    if row["state"] == "in_progress":
        values: Earned = earned(row)
        left = values.projection - values.actual
        start = STARTED_FROM + timedelta(
            days=draw(f"{key}/started", 0, (STARTED_TO - STARTED_FROM).days)
        )
        finish = DAY + timedelta(days=draw(f"{key}/finish", 45, 720))
        marked = date.fromisoformat(cast("str", row["last_marked_at"])[:10])
        return Course(
            start,
            finish,
            values.budget,
            values.planned,
            values.actual,
            marked if no_cost_since_review(row) else DAY,
            left,
            _hours(row["project_id"], left * _LABOUR_OF_REMAINING),
            delay,
        )
    if row["current_estimate"] is None:
        return None
    weighted = Decimal(cast("str", row["current_estimate"])) * Decimal(
        cast("str", row["win_probability"])
    )
    start = DAY + timedelta(days=draw(f"{key}/start", 15, 180))
    finish = start + timedelta(days=draw(f"{key}/lasts", 120, 540))
    return Course(
        start,
        finish,
        weighted,
        Decimal(0),
        Decimal(0),
        DAY,
        weighted,
        _hours(row["project_id"], weighted * _LABOUR_OF_ESTIMATE),
        delay,
    )


def no_cost_since_review(row: JsonObject) -> bool:
    """Whether a generated project in progress has had no import of costs since its last mark.

    One in nine (WF-PTF-0110): the health of the steering signals it, and its actual cost stops at
    the day of that mark.
    """
    return draw(f"health/{row['project_id']}/costs", 0, 8) == 0


def _witness_id() -> str:
    return fixture("project")["project_id"]


def _holds_witness(rows: list[JsonObject]) -> bool:
    """Whether the rows summed hold the witness, which brings its own readings."""
    return any(row["project_id"] == _witness_id() for row in rows)


def _months(first: date, count: int) -> list[date]:
    """Return the last day of each of some months, from the month of a day."""
    found: list[date] = []
    end = mockcurves.month_end(first)
    for _ in range(count):
        found.append(end)
        end = mockcurves.month_end(end + timedelta(days=1))
    return found


def _months_before(day: date, count: int) -> date:
    """Return the first day of the month some months before that of a day."""
    rank = day.year * 12 + day.month - 1 - count
    return date(rank // 12, rank % 12 + 1, 1)


def _month(end: date) -> str:
    return end.strftime("%Y-%m")


def scope(rows: list[JsonObject], states: list[str], org: str | None = None) -> JsonObject:
    """Return the scope of a view of the portfolio today, as the server retains it."""
    labels = {node["org_node_id"]: node["label"] for node in fixture("org_nodes")}
    return {
        "states": cast("list[JsonValue]", states),
        "as_of": DAY.isoformat(),
        "from": None,
        "to": None,
        "org_node_id": org,
        "org_node_label": None if org is None else labels[org],
        "project_count": sum(1 for row in rows if row["state"] in states),
    }


# --- The aggregated workload (WF-PTF-0060) ------------------------------------------------------


def _witness_hours() -> dict[tuple[str, str], Decimal]:
    """Return the hours of the witness by role and month, as its own workload reads them."""
    plan = mockcurves.workload(mockindicators.today(), "current_remaining")
    return {
        (cast("str", role["resource_role_id"]), cast("str", month["month"])): Decimal(
            cast("str", month["hours"])
        )
        for role in cast("list[JsonObject]", plan["roles"])
        for month in cast("list[JsonObject]", role["months"])
    }


def _spread_hours(each: Course, role: str, end: date) -> Decimal:
    """Return the hours of a role a project works in the month that ends on a day, after today."""
    start = max(each.start, DAY + timedelta(days=1))
    if role not in each.hours or each.finish < start:
        return Decimal(0)
    month_start = end.replace(day=1)
    before = _share(start, each.finish, month_start - timedelta(days=1))
    return (each.hours[role] * (_share(start, each.finish, end) - before)).quantize(CENT)


def load_zone(load: Decimal, capacity: Decimal) -> str:
    """Return the zone of a month of a role, by its load against its capacity.

    Over its capacity in alert, under the threshold of under-load in watch, nominal between
    (WF-PTF-0060, WF-IHM-0070).
    """
    if load > capacity:
        return "alert"
    if load < capacity * UNDER_LOAD:
        return "watch"
    return "nominal"


def portfolio_workload(rows: list[JsonObject], org: str | None = None) -> JsonObject:
    """Return the answer of getPortfolioWorkload, the pricing included, today (WF-PTF-0060).

    For each active role under the node asked, each month of the horizon: the hours of the witness
    as its workload reads them, and those of every other project spread over its days after today;
    the capacity of the role, its monthly hours, all its people counted — the headcount a mere
    information (WF-REF-0100); the load ratio and its zone.
    """
    kept = None if org is None else mockcurves.org_subtree(org)
    months = _months(DAY, HORIZON)
    witness_id = _witness_id()
    witness = _witness_hours() if _holds_witness(rows) else {}
    courses = [found for row in rows if row["project_id"] != witness_id and (found := course(row))]
    roles: list[JsonValue] = []
    for role in by_identifier("resource_roles", "resource_role_id"):
        if not role["is_active"] or (kept is not None and role["org_node_id"] not in kept):
            continue
        identifier_ = role["resource_role_id"]
        capacity = Decimal(role["capacity"]["monthly_hours"])
        entries: list[JsonValue] = []
        for end in months:
            hours = witness.get((identifier_, _month(end)), Decimal(0)) + sum(
                (_spread_hours(each, identifier_, end) for each in courses), Decimal(0)
            )
            entries.append(
                {
                    "month": _month(end),
                    "hours": decimal(hours),
                    "load_ratio": mockindicators.ratio(hours, capacity, "no_capacity"),
                    "zone": load_zone(hours, capacity),
                }
            )
        roles.append(
            {
                "resource_role_id": identifier_,
                "label": role["label"],
                "capacity_monthly_hours": decimal(capacity.quantize(CENT)),
                "months": entries,
            }
        )
    return {
        "scope": scope(rows, ["in_progress", "pricing"], org),
        "under_load_threshold": decimal(UNDER_LOAD),
        "months": [_month(end) for end in months],
        "roles": roles,
    }


# --- The S-curve of the portfolio (WF-PTF-0100) -------------------------------------------------


def _at(points: list[JsonObject], day: date) -> Decimal:
    """Return a cumulative curve at the end of a day: its last point by then, nought before.

    The curves of the witness are read at the end of each month, where they bear a point; between
    two points the value of the first stands, the last of two points at a date the one after it.
    """
    found = Decimal(0)
    for point in points:
        if date.fromisoformat(cast("str", point["date"])) <= day:
            found = Decimal(cast("str", point["amount"]))
    return found


def _series(curve: JsonObject, name: str) -> list[JsonObject]:
    entries = cast("list[JsonObject]", curve["series"])
    return cast("list[JsonObject]", next(e for e in entries if e["name"] == name)["points"])


@dataclass(frozen=True, slots=True)
class Curves:
    """The three cumulative curves of a project at the end of a day, and its cash-out by month."""

    budget: Callable[[date], Decimal]
    actual: Callable[[date], Decimal]
    projection: Callable[[date], Decimal]


def _witness_curves(*, delays: bool) -> tuple[Curves, dict[str, tuple[Decimal, Decimal]]]:
    found = mocktoday.witness()
    curve = mockcurves.cost_curve(found.today, found.eras, found.costs, delays=delays)
    budget, actual = _series(curve, "reference_budget"), _series(curve, "actual_cost")
    projection = _series(curve, "project_manager_projection")
    months = {
        cast("str", month["month"]): (
            Decimal(cast("str", month["past"])),
            Decimal(cast("str", month["forecast"])),
        )
        for month in cast("list[JsonObject]", curve["cash_out_by_month"] or [])
    }
    return Curves(
        lambda day: _at(budget, day),
        lambda day: _at(actual, day),
        lambda day: _at(projection, day),
    ), months


def course_curves(each: Course, *, delays: bool, as_of: date = DAY) -> Curves:
    """Return the curves of a generated project, read at a day of calculation.

    The reference budget is the plan, whatever the day; the actual cost is what was spent by the
    day of calculation; the projection adds to it what was left to commit, over the days after.
    """
    shift = each.delay if delays else timedelta(0)
    after = DAY + timedelta(days=1)

    def budget(day: date) -> Decimal:
        paid = day - shift
        if paid <= DAY:
            return (each.planned * _share(each.start, DAY, paid)).quantize(CENT)
        rest = (each.budget - each.planned) * _share(max(each.start, after), each.finish, paid)
        return (each.planned + rest).quantize(CENT)

    def actual(day: date) -> Decimal:
        return (each.actual * _share(each.start, each.spent_until, min(day, as_of))).quantize(CENT)

    spent = actual(as_of)
    total = each.actual + each.left

    def projection(day: date) -> Decimal:
        start = max(each.start, as_of + timedelta(days=1))
        return spent + ((total - spent) * _share(start, each.finish, day - shift)).quantize(CENT)

    return Curves(budget, actual, projection)


def portfolio_cost_curve(
    rows: list[JsonObject],
    *,
    delays: bool = False,
    as_of: date = DAY,
    months: list[date] | None = None,
    states: tuple[str, ...] = ("in_progress", "pricing"),
) -> JsonObject:
    """Return the answer of getPortfolioCostCurve, the pricing included, today (WF-PTF-0100).

    Each point is the sum of the points of the projects at the end of a month: the reference
    budget over the twelve months, the actual cost up to the day of calculation, the projection of
    the project manager from it; with the payment delays, the disbursements and their detail by
    month, the past by month of the actual cost, what is to come by month of the projection. The
    witness brings its own curve, read today alone.
    """
    witness_id = _witness_id()
    own, cash = _witness_curves(delays=delays) if _holds_witness(rows) else (None, {})
    if own is not None and as_of != DAY:
        message = "the curve of the witness is read today alone"
        raise ValueError(message)
    others = [
        course_curves(found, delays=delays, as_of=as_of)
        for row in rows
        if row["project_id"] != witness_id and (found := course(row))
    ]
    curves = others if own is None else [own, *others]
    if months is None:
        months = _months(_months_before(DAY, CURVE_MONTHS // 2), CURVE_MONTHS)
    past = [end for end in months if end < as_of]
    ahead = [end for end in months if end > as_of]

    def summed(read: Callable[[Curves], Callable[[date], Decimal]], day: date) -> Decimal:
        return sum((read(each)(day) for each in curves), Decimal(0))

    def points(
        read: Callable[[Curves], Callable[[date], Decimal]], days: list[date]
    ) -> list[JsonValue]:
        return [{"date": day.isoformat(), "amount": money(summed(read, day))} for day in days]

    answer = scope(rows, list(states))
    answer["as_of"] = as_of.isoformat()
    return {
        "scope": answer,
        "payment_delays": delays,
        "series": [
            {"name": "reference_budget", "points": points(lambda c: c.budget, months)},
            {"name": "actual_cost", "points": points(lambda c: c.actual, [*past, as_of])},
            {
                "name": "project_manager_projection",
                "points": points(lambda c: c.projection, [as_of, *ahead]),
            },
        ],
        "cash_out_by_month": _cash_out(others, cash, months, as_of) if delays else None,
    }


def credit_perimeter(rows: list[JsonObject]) -> list[JsonObject]:
    """Return the projects in progress on ``CREDIT_ON``: those engendered already started then.

    The witness, then still in pricing — in progress from 15 January 2026 —, is not of them.
    """
    witness_id = _witness_id()
    return [
        row
        for row in rows
        if row["state"] == "in_progress"
        and row["project_id"] != witness_id
        and (found := course(row)) is not None
        and found.start <= CREDIT_ON
    ]


CREDIT_SHARE = Decimal("0.02")
"""The credit notes of December in the variant: two hundredths of what its documents carry."""


def portfolio_cost_curve_credit(rows: list[JsonObject]) -> JsonObject:
    """Return the S-curve as disbursements computed on 31 December 2025, from October.

    The projects then in progress, with the same courses; and the counterfactual of the variant,
    declared by its summary: if the invoices of December had not yet been imported, its credit
    notes alone already, December would be a month of net negative disbursement (WF-CRE-0010).
    """
    perimeter = credit_perimeter(rows)
    months = _months(date(2025, 10, 1), 3)
    curve = portfolio_cost_curve(
        perimeter, delays=True, as_of=CREDIT_ON, months=months, states=("in_progress",)
    )
    cash = cast("list[JsonObject]", curve["cash_out_by_month"])
    december = Decimal(cast("str", cash[-1]["past"]))
    credit = -(december * CREDIT_SHARE).quantize(CENT)
    cash[-1]["past"] = money(credit)
    november = Decimal(cast("str", _series(curve, "actual_cost")[-2]["amount"]))
    _series(curve, "actual_cost")[-1]["amount"] = money(november + credit)
    _series(curve, "project_manager_projection")[0]["amount"] = money(november + credit)
    return curve


def _cash_out(
    others: list[Curves],
    witness: dict[str, tuple[Decimal, Decimal]],
    months: list[date],
    as_of: date,
) -> list[JsonValue]:
    """Return the disbursements by month: the witness's own, and those of every other project.

    The past, what the actual cost grew by in the month up to the day of calculation; what is to
    come, what the projection grew by in the month after it; the month of that day both
    (WF-IND-0100).
    """
    found: list[JsonValue] = []
    for end in months:
        start = end.replace(day=1) - timedelta(days=1)
        spent = sum(
            (each.actual(min(end, as_of)) - each.actual(min(start, as_of)) for each in others),
            Decimal(0),
        )
        coming = sum(
            (
                each.projection(end) - each.projection(max(start, as_of))
                for each in others
                if end >= as_of
            ),
            Decimal(0),
        )
        own = witness.get(_month(end), (Decimal(0), Decimal(0)))
        found.append(
            {
                "month": _month(end),
                "past": money(own[0] + spent),
                "forecast": money(own[1] + coming),
            }
        )
    return found


# --- The quarterly evolution of the indices (WF-PTF-0070) -------------------------------------

_UNCOMPUTED = {"cost": "no_actual_cost", "schedule": "no_planned_value"}
"""Why an index of a quarter is not computable: nothing spent, or nothing planned, by its end."""


def _quarter_end(quarter: str) -> date:
    """Return the day a quarter is read at: its last day, or today for the quarter of today."""
    year, rank = int(quarter[:4]), int(quarter[-1])
    end = mockcurves.month_end(date(year, rank * 3, 1))
    return min(end, DAY)


def quarterly(rows: list[JsonObject]) -> list[JsonValue]:
    """Return the evolution of the indices of the projects in progress by quarter (WF-PTF-0070).

    Each quarter is read at its end — today for the last —, from the curves of the projects: the
    actual cost and the reference budget, the planned value, those of the S-curve at that day;
    the earned value, the witness's from its own curve, another's its earned value today by the
    share of its actual cost spent by then. Each index is a ratio of the sums (WF-PTF-0020); one
    whose denominator is nought is not computable, as in the first quarter, before any project
    started.
    """
    witness_id = _witness_id()
    found = mocktoday.witness()
    own = mockcurves.earned_value_curves(found.today, found.reference, found.costs)
    curve = mockcurves.cost_curve(found.today, found.eras, found.costs)
    progressing = [row for row in rows if row["state"] == "in_progress"]
    entries: list[JsonValue] = []
    for quarter in mockportfolio.QUARTERS:
        day = _quarter_end(quarter)
        actual = planned = value = Decimal(0)
        for row in progressing:
            if row["project_id"] == witness_id:
                actual += _at(_series(curve, "actual_cost"), day)
                planned += _at(_series(curve, "reference_budget"), day)
                value += _at(_series(own, "earned_value"), day)
                continue
            each = course(row)
            if each is None:
                continue
            curves = course_curves(each, delays=False)
            spent = curves.actual(day)
            actual += spent
            planned += curves.budget(day)
            value += earned(row).earned * spent / each.actual
        entries.append(
            {
                "quarter": quarter,
                "cost_index": _index(value, actual, "cost"),
                "schedule_index": _index(value, planned, "schedule"),
            }
        )
    return entries


def _index(value: Decimal, denominator: Decimal, index: str) -> JsonObject:
    if denominator == 0:
        return {"is_computable": False, "value": None, "reason": _UNCOMPUTED[index]}
    return {
        "is_computable": True,
        "value": decimal((value / denominator).quantize(CENT)),
        "reason": None,
    }


# --- The health of the steering (WF-PTF-0110) ---------------------------------------------------

SIGNALS = (
    "review_overdue",
    "risks_not_reviewed",
    "no_actual_cost_since_last_review",
    "contractual_milestone_overdue",
)
"""The four signals of the health of the steering, in the order of the contract (WF-PTF-0110)."""

_MILESTONE_LABELS = (
    "Réception usine",
    "Mise en service",
    "Réception des travaux",
    "Essais de performance",
)


def _weeks(marked: date) -> int:
    return (DAY - marked).days // 7


def _signal(row: JsonObject, code: str, zone: str, params: JsonObject | None = None) -> JsonObject:
    signal: JsonObject = {
        "project_id": row["project_id"],
        "project_label": row["label"],
        "can_open": row["can_open"],
        "zone": zone,
        "code": code,
    }
    if params is not None:
        signal["params"] = params
    return signal


def _witness_signals(row: JsonObject, limit: int) -> list[JsonValue]:
    """Return the signals of the witness, read from its chronology, register and milestones.

    A review is overdue past the limit since its last marked revision, the reference; a risk
    identified and not reviewed since; no import of costs since; a tracked milestone whose date by
    the reference is past and which is not completed (WF-PTF-0110).
    """
    signals: list[JsonValue] = []
    weeks = _weeks(AMENDMENT_MERGED.on)
    if weeks > limit:
        signals.append(_signal(row, "review_overdue", "watch", {"weeks_since_last_mark": weeks}))
    if any(
        risk.last.state == IDENTIFIED and risk.last.at < AMENDMENT_MERGED.instant
        for risk in REGISTER
    ):
        signals.append(_signal(row, "risks_not_reviewed", "watch"))
    if not any(event.instant > AMENDMENT_MERGED.instant for event in COST_IMPORTS):
        signals.append(_signal(row, "no_actual_cost_since_last_review", "watch"))
    marked = mockhistory.stamp(AMENDMENT_MERGED.instant)
    found = mocktoday.witness()
    tracking = mockindicators.milestone_tracking(found.points()[:-1], found.points()[-1])
    for milestone in cast("list[dict[str, Any]]", tracking["milestones"]):
        by_reference = [p for p in milestone["points"] if p["marked_at"] == marked]
        if not by_reference or milestone["completed_on"] is not None:
            continue
        reference_date = date.fromisoformat(by_reference[0]["forecast_date"])
        if reference_date < DAY:
            signals.append(
                _signal(
                    row,
                    "contractual_milestone_overdue",
                    "alert",
                    {
                        "lineage_id": milestone["lineage_id"],
                        "milestone_label": milestone["label"],
                        "reference_date": reference_date.isoformat(),
                    },
                )
            )
    return signals


def _drawn_signals(row: JsonObject, number: int, limit: int, *, has_risks: bool) -> list[JsonValue]:
    """Return the signals of a generated project: its review from its row, the others drawn.

    One project in six with identified risks has some not reviewed since its last mark, one in
    nine has had no import of costs since, one in eleven a milestone past its date by the
    reference and not completed, dated within the two months before today.
    """
    key = f"health/{row['project_id']}"
    signals: list[JsonValue] = []
    marked = date.fromisoformat(cast("str", row["last_marked_at"])[:10])
    if _weeks(marked) > limit:
        signals.append(
            _signal(row, "review_overdue", "watch", {"weeks_since_last_mark": _weeks(marked)})
        )
    if has_risks and draw(f"{key}/risks", 0, 5) == 0:
        signals.append(_signal(row, "risks_not_reviewed", "watch"))
    if no_cost_since_review(row):
        signals.append(_signal(row, "no_actual_cost_since_last_review", "watch"))
    if draw(f"{key}/milestone", 0, 10) == 0:
        label = _MILESTONE_LABELS[draw(f"{key}/label", 0, len(_MILESTONE_LABELS) - 1)]
        overdue = DAY - timedelta(days=draw(f"{key}/late", 3, 60))
        signals.append(
            _signal(
                row,
                "contractual_milestone_overdue",
                "alert",
                {
                    "lineage_id": identifier(MILESTONES, number),
                    "milestone_label": label,
                    "reference_date": overdue.isoformat(),
                },
            )
        )
    return signals


def pilot_health(rows: list[JsonObject], risky: set[str]) -> JsonObject:
    """Return the answer of getPortfolioPilotHealth over the projects in progress (WF-PTF-0110).

    Each project in the order of the list, its signals in the order of the contract; a review
    overdue and a risk or an import missing in watch, a milestone overdue in alert — WF-IHM-0070
    fixes no level, and a date past is the most pressing of the four. ``risky`` names the projects
    that bear identified risks.
    """
    limit = cast("int", fixture("reference_settings")["max_weeks_between_reviews"])
    witness_id = _witness_id()
    signals: list[JsonValue] = []
    for number, row in enumerate(rows, start=1):
        if row["state"] != "in_progress":
            continue
        if row["project_id"] == witness_id:
            signals.extend(_witness_signals(row, limit))
        else:
            signals.extend(_drawn_signals(row, number, limit, has_risks=row["project_id"] in risky))
    return {"scope": scope(rows, ["in_progress"]), "signals": signals}


# --- The examples ---------------------------------------------------------------------------------

_day = mocktext.day
_ZONES = {"alert": "en alerte", "watch": "en sous-charge"}


def _month_said(value: JsonValue) -> str:
    """Write a month of the contract as French does: juillet 2026."""
    year, month = cast("str", value).split("-")
    return _day(date(int(year), int(month), 1)).removeprefix("1er ")


def _listed(items: list[str]) -> str:
    """Join some words as French lists them: a, b et c."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} et {items[-1]}"


def _roles_said(plan: JsonObject) -> str:
    """Say each role of a workload: its headcount, and the months out of its nominal zone."""
    headcounts = {
        role["resource_role_id"]: Decimal(role["capacity"]["headcount"])
        for role in fixture("resource_roles")["items"]
    }
    said: list[str] = []
    for role in cast("list[JsonObject]", plan["roles"]):
        months = cast("list[JsonObject]", role["months"])
        label = cast("str", role["label"]).lower()
        article = "l'" if label[0] in "aeéèiouh" else "le "
        zones = [
            f"{_ZONES[zone]} en {_listed([_month_said(m['month']) for m in out])}"
            for zone in ("alert", "watch")
            if (out := [m for m in months if m["zone"] == zone])
        ]
        state = ", ".join(zones) if zones else "dans sa capacité tout l'horizon"
        if all(Decimal(cast("str", m["hours"])) == 0 for m in months):
            state = "sans charge — aucun projet ne l'emploie —, sa capacité seule, en sous-charge"
        said.append(
            f"{article}{label}, {mocktext.count(int(headcounts[role['resource_role_id']]))} "
            f"personnes, {state}"
        )
    return " ; ".join(said)


def examples() -> dict[str, JsonObject]:
    """Return the examples of the views of the portfolio over time, by file name."""
    rows = cast("list[JsonObject]", portfolio()["items"])
    risky = {cast("str", risk.row["project_id"]) for risk in identified_risks(rows)}
    plan = portfolio_workload(rows)
    filtered = portfolio_workload(rows, ORG_NODE)
    curve, cash = portfolio_cost_curve(rows), portfolio_cost_curve(rows, delays=True)
    credit = portfolio_cost_curve_credit(rows)
    december = cast("list[JsonObject]", credit["cash_out_by_month"])[-1]
    health = pilot_health(rows, risky)
    signals = cast("list[JsonObject]", health["signals"])
    counted = {code: sum(1 for s in signals if s["code"] == code) for code in SIGNALS}
    limit = cast("int", fixture("reference_settings")["max_weeks_between_reviews"])
    today = _day(DAY)
    months = _series(curve, "reference_budget")
    first, last = (cast("str", months[rank]["date"])[:7] for rank in (0, -1))
    scoped = cast("JsonObject", health["scope"])
    node = cast("str", cast("JsonObject", filtered["scope"])["org_node_label"]).lower()
    return {
        "portfolio_workload.json": mocktext.example(
            f"Le plan de charge agrégé du portefeuille au {today}, sur six mois, au seuil de "
            f"sous-charge de 50 % : les projets en cours sur leur reste à engager — le projet "
            f"témoin aux heures de son propre plan de charge — et, ajoutées par la requête au "
            f"périmètre par défaut, les offres en chiffrage sur leur devis pondéré par leur "
            f"probabilité de gain ; {_roles_said(plan)}. La capacité d'un rôle est ses heures "
            f"mensuelles, tout son effectif compris, seules comparées à la charge — l'effectif "
            f"n'est qu'une information (WF-REF-0100) — ; chaque mois porte sa zone, que le serveur "
            f"classe (WF-PTF-0060, WF-IHM-0070).",
            plan,
        ),
        "portfolio_workload_org_node.json": mocktext.example(
            f"Le même plan de charge agrégé, restreint à la "
            f"{node} : les trois rôles relèvent de ses descendants, le bureau d'études "
            f"électricité et l'atelier de câblage, et restent retenus, avec les mêmes charges ; "
            f"l'en-tête de la vue nomme le nœud (WF-PTF-0010, WF-PTF-0060, WF-REF-0070).",
            filtered,
        ),
        "portfolio_cost_curve.json": mocktext.example(
            f"La courbe en S du portefeuille au {today}, de "
            f"{_month_said(first)} à {_month_said(last)}, les projets en cours et, ajoutées "
            f"par la requête au périmètre par défaut, les offres en chiffrage : la somme des "
            f"budgets de référence cumulés, celle des coûts réels cumulés jusqu'au {today}, et "
            f"celle des projections du chef de projet au-delà. Chaque point est la somme des "
            f"points de ce mois sur les projets — le projet témoin aux points de sa propre courbe, "
            f"une offre à son devis pondéré par sa probabilité de gain, qui tient lieu de budget "
            f"et de projection — ; rien n'est recalculé (WF-PTF-0100, WF-IND-0100).",
            curve,
        ),
        "portfolio_cost_curve_payment_delays.json": mocktext.example(
            f"La même courbe en S demandée avec les délais de paiement : les décaissements — le "
            f"projet témoin les siens, les autres projets leur budget et ce qu'il leur reste à "
            f"engager payés un mois après leur travail, leur coût réel à la date de ses pièces —, "
            f"que cash_out_by_month détaille par mois, {_month_said(DAY.strftime('%Y-%m'))} "
            f"portant le passé et l'avenir (WF-PTF-0100, WF-IND-0100).",
            cash,
        ),
        "portfolio_cost_curve_credit.json": mocktext.example(
            f"La courbe en S du portefeuille en décaissements, calculée au {_day(CREDIT_ON)}, "
            f"d'octobre à décembre 2025, sur les "
            f"{mocktext.count(cast('int', cast('JsonObject', credit['scope'])['project_count']))} "
            f"projets alors en cours — le projet témoin, encore en chiffrage, n'en est pas —, "
            f"chacun suivant le même cours que dans la courbe d'aujourd'hui ; et si les factures "
            f"de décembre n'avaient pas encore été importées, ses seuls avoirs l'étant déjà : "
            f"décembre serait net négatif, "
            f"{mocktext.amount(Decimal(cast('str', december['past'])))} — un décaissement est un "
            f"montant signé, comme le coût réel dont il vient (WF-PTF-0100, WF-CRE-0010).",
            credit,
        ),
        "pilot_health.json": mocktext.example(
            f"La santé du pilotage au {today}, sur les "
            f"{mocktext.count(cast('int', scoped['project_count']))} "
            f"projets en cours : {mocktext.count(counted['review_overdue'])} revues en retard sur "
            f"le délai de {mocktext.count(limit)} semaines du référentiel, dont celle du projet "
            f"témoin, revu pour la dernière fois au marquage de sa référence le "
            f"{_day(AMENDMENT_MERGED.on)} ; {mocktext.count(counted['risks_not_reviewed'])} "
            f"projets "
            f"aux risques identifiés non réexaminés depuis leur dernière révision marquée ; "
            f"{mocktext.count(counted['no_actual_cost_since_last_review'])} sans coût réel importé "
            f"depuis ; ces signaux en vigilance ; et "
            f"{mocktext.count(counted['contractual_milestone_overdue'])} jalons contractuels dont "
            f"la date de référence est dépassée sans qu'ils soient terminés, en alerte — ceux du "
            f"projet témoin sont terminés ou à venir (WF-PTF-0110, WF-IHM-0070). Un signal dit si "
            f"le lecteur peut ouvrir son projet, comme la ligne de ce projet dans la liste "
            f"(WF-PTF-0030).",
            health,
        ),
    }
