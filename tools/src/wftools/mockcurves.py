# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves and the workload of the witness, read from its revisions (EP-02/L24, #287).

The revisions are read in ``wftools.mockindicators``: here their amounts are spread in time —
the reference budget on the dates of the reference in force, stepped at each amendment, the
actual cost at the dates of its documents, the remaining to commit on the dates of the current
revision after today (WF-IND-0100, WF-IND-0110) — and their labour hours by month, against the
capacity of each role (WF-DEV-0070). A curve is read at the pace of the month, each point the
cumulative amount at the end of its month, from the end of the month before its first amount
(WF-IND-0100, WF-IND-0110, WF-DAT-0040); the day of the calculation is one point more on the series
that stop or start there, and an amendment two at its day. Each value counts the work of its day;
to be replaced by the kernel of EP-08 to EP-11.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockhistory
from wftools.mockcalendar import Calendar, Instant
from wftools.mockindicators import (
    END_OF_DAY,
    PROJECT,
    Cost,
    Flow,
    Reading,
    actual,
    budget,
    budgeted,
    context,
    earned,
    over,
    remaining_of,
)
from wftools.mockstructure import CENT, JsonObject, JsonValue, decimal, money
from wftools.mockwitness import TODAY, by_identifier, fixture

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from wftools import mockcore


def budget_flows(base: Reading, *, delays: bool = False, scope: str = PROJECT) -> list[Flow]:
    """Return the reference budget of a scope spread on the dates of the reference, by task."""
    return [
        over(base.bearer(line), line.amounts.budgeted, base.delays[line.number] if delays else 0)
        for line in budgeted(base, scope)
    ]


def remaining_flows(reading: Reading, *, delays: bool = False, scope: str = PROJECT) -> list[Flow]:
    """Return the remaining to commit of a scope spread on the dates of the current revision.

    Each line over the hours its task has left to work after the day of the reading; one whose
    task is past its finish whole at the day of the reading (WF-IND-0100, WF-RAE-0040). With the
    payment delays, each shifted by its line's, and a provision of a risk identified, which bears
    none, at the date of its task — its finish, or the day of the reading when it is past. The
    lines of the scope alone: the project, a subproject or none (WF-IND-0020).
    """
    after = Instant(reading.day, END_OF_DAY)
    flows: list[Flow] = []
    for line in reading.lines:
        amount = remaining_of(reading, line)
        if amount == 0 or not reading.in_scope(line, scope):
            continue
        placed = reading.bearer(line)
        calendar, delay = placed.calendar, reading.delays[line.number] if delays else 0
        if delays and mockhistory.is_provision(line):
            at = max(Instant(placed.finish.day, END_OF_DAY), after)
            flows.append(Flow(amount, calendar, at, at))
        else:
            flows.append(ahead(reading, line, amount, delay))
    return flows


def ahead(reading: Reading, line: mockcore.Row, amount: Decimal, delay: int = 0) -> Flow:
    """Return what is left of a line spread over the hours its task works after the reading.

    Over the part of the duration of its task after the day of the reading, pro rata of the
    hours of work: all its hours for a task not started, those after the day for one started or
    late to start; whole at the day of the reading for a task past its finish — in its month, for
    the workload (WF-IND-0100, WF-RAE-0040, WF-DEV-0070).
    """
    after = Instant(reading.day, END_OF_DAY)
    placed = reading.bearer(line)
    calendar = placed.calendar
    if placed.finish <= after:
        return Flow(amount, calendar, after, after, delay)
    return Flow(amount, calendar, max(placed.start, after), placed.finish, delay)


@dataclass(frozen=True, slots=True)
class _Placed:
    """A flow with what its calendar says of its bounds, once: the hours elapsed at each."""

    flow: Flow
    first: date
    last: date
    started: Decimal
    finished: Decimal

    @property
    def span(self) -> Decimal:
        """Return the hours of work the flow is spent over; none for one spent at once."""
        return self.finished - self.started

    def by(self, elapsed: Decimal) -> Decimal:
        """Return what the flow has spent when so many hours of its calendar have elapsed.

        What ``Flow.by`` returns at that day: the hours elapsed are clamped to the bounds of the
        flow, the hours of work of a calendar growing with its instants.
        """
        if self.span <= 0:
            return Decimal(0)
        done = min(max(elapsed, self.started), self.finished) - self.started
        return self.flow.amount * done / self.span


@dataclass(frozen=True, slots=True)
class Spread:
    """Some flows summed at any day: what they have spent by the end of it, to the cent.

    The flows in the order they begin and in the order they are spent whole, with the sum of the
    amounts spent whole by each of the latter: at a day, those spent whole are summed at once, and
    the few under way — the tasks of a structure of a thousand are a dozen at a time — are read one
    by one, among the flows begun or among those not spent whole, whichever are the fewer.
    """

    by_first: tuple[_Placed, ...]
    by_last: tuple[_Placed, ...]
    firsts: tuple[date, ...]
    lasts: tuple[date, ...]
    whole: tuple[Decimal, ...]

    @classmethod
    def of(cls, flows: Iterable[Flow]) -> Spread:
        """Return some flows ready to be summed at any day."""
        placed = [
            _Placed(
                flow,
                flow.first,
                flow.last,
                flow.calendar.elapsed(flow.start),
                flow.calendar.elapsed(flow.finish),
            )
            for flow in flows
        ]
        by_first = tuple(sorted(placed, key=lambda each: each.first))
        by_last = tuple(sorted(placed, key=lambda each: each.last))
        total, sums = Decimal(0), [Decimal(0)]
        for each in by_last:
            total += each.flow.amount
            sums.append(total)
        return cls(
            by_first,
            by_last,
            tuple(each.first for each in by_first),
            tuple(each.last for each in by_last),
            tuple(sums),
        )

    def by(self, day: date) -> Decimal:
        """Return what the flows have spent by the end of a day, to the cent."""
        ended, begun = bisect_right(self.lasts, day), bisect_right(self.firsts, day)
        if begun <= len(self.by_last) - ended:
            under_way = [each for each in self.by_first[:begun] if each.last > day]
        else:
            under_way = [each for each in self.by_last[ended:] if each.first <= day]
        total = self.whole[ended]
        elapsed: dict[tuple[Calendar, int], Decimal] = {}
        for each in under_way:
            key = (each.flow.calendar, each.flow.delay)
            if key not in elapsed:
                shifted = Instant(day - timedelta(days=each.flow.delay), END_OF_DAY)
                elapsed[key] = each.flow.calendar.elapsed(shifted)
            total += each.by(elapsed[key])
        return total.quantize(CENT)


def month_end(day: date) -> date:
    """Return the last day of the month of a day."""
    following = (day.replace(day=1) + timedelta(days=32)).replace(day=1)
    return following - timedelta(days=1)


def month_before(day: date) -> date:
    """Return the last day of the month before that of a day: the origin of a curve."""
    return day.replace(day=1) - timedelta(days=1)


def month_ends(start: date, stop: date) -> list[date]:
    """Return the ends of the months from that of a day to that of another, both included."""
    found: list[date] = []
    end = month_end(start)
    while end <= month_end(stop):
        found.append(end)
        end = month_end(end + timedelta(days=1))
    return found


def days_of(flows: Sequence[Flow], since: Iterable[date] = ()) -> list[date]:
    """Return the days a curve of some flows is read at: the ends of their months (WF-IND-0100).

    From the end of the month before the first flow begins — or before an earlier day given, the
    step of an amendment —, where the curve starts at nought, to the end of the month the last is
    spent whole, each point the cumulative amount at the end of its month.
    """
    first = month_before(min([*(flow.first for flow in flows), *since]))
    return month_ends(first, max(flow.last for flow in flows))


def up_to(origin: date, day: date) -> list[date]:
    """Return the days a series that stops at the day of the calculation is read at.

    Its origin, the end of each month after it and before the day, and the day itself, one point
    more (WF-IND-0100, WF-IND-0110).
    """
    return sorted({origin, day, *(end for end in month_ends(origin, day) if origin < end < day)})


def _points(values: Iterable[tuple[date, Decimal]]) -> list[JsonValue]:
    return [{"date": day.isoformat(), "amount": money(amount)} for day, amount in values]


@dataclass(frozen=True, slots=True)
class Era:
    """A reference revision in force from a day.

    The first from the start, each other produced by an amendment, which steps the reference
    budget at its day (WF-IND-0100, WF-REV-0040).
    """

    since: date
    base: Reading


def budget_series(
    eras: Sequence[Era], day: date, *, delays: bool = False, scope: str = PROJECT
) -> list[JsonValue]:
    """Return the cumulative reference budget of a scope, by the reference in force at each day.

    At the end of each month; at the day of an amendment, two points: the budget of the reference
    before it, then that of the reference it produced, a vertical step (DECISIONS, « Les exemples
    des courbes »). No point for a scope no reference budgets a line of.
    """
    del day
    flows = [budget_flows(era.base, delays=delays, scope=scope) for era in eras]
    if not any(flows):
        return []
    steps = [era.since for era in eras[1:]]
    found = sorted({*days_of([f for each in flows for f in each], steps), *steps})
    spreads = [Spread.of(each) for each in flows]
    values: list[tuple[date, Decimal]] = []
    for each in found:
        rank = max(rank for rank, era in enumerate(eras) if rank == 0 or era.since <= each)
        if each in steps:
            values.append((each, spreads[rank - 1].by(each)))
        values.append((each, spreads[rank].by(each)))
    return _points(values)


def actual_series(costs: list[Cost], origin: date, day: date) -> list[JsonValue]:
    """Return the cumulative actual cost by date of document, month by month up to the day.

    Each point the lines dated by the end of its month, the last the day of the calculation
    (WF-IND-0100, WF-IND-0110).
    """
    return _points((each, actual(costs, each)) for each in up_to(origin, day))


def in_scope(costs: Iterable[Cost], scope: str) -> list[Cost]:
    """Return the lines of actual cost of a scope: all for the project (WF-IND-0020)."""
    return [cost for cost in costs if cost.counts_in(scope)]


def cost_curve(
    reading: Reading,
    eras: Sequence[Era],
    costs: list[Cost],
    *,
    delays: bool = False,
    scope: str = PROJECT,
) -> JsonObject:
    """Return the curve of the cumulative costs of a scope (`CurveSeries`, WF-IND-0100).

    The reference budget by the dates of the reference in force, stepped at each amendment; the
    actual cost by date of document up to today; beyond, the projection of the project manager,
    the remaining spread on the dates of the current revision. With the payment delays, each
    amount shifted by its line's, the provisions of the risks identified at the date of their
    task: the disbursements, past and to come, by month. Of a subproject, or of what belongs to
    none, the lines of that scope alone, and a step what an amendment changed of its budget —
    none where it changed nothing (`scope`, WF-IND-0020). A scope without a line in any reference
    or in the current revision, nor a line of actual cost, has nothing to draw: its three series
    without a point, no step, no month of disbursement.
    """
    day = reading.day
    costs = in_scope(costs, scope)
    budget_points = budget_series(eras, day, delays=delays, scope=scope)
    flows = remaining_flows(reading, delays=delays, scope=scope)
    drawn = bool(budget_points or costs or flows)
    if budget_points:
        origin = date.fromisoformat(cast("str", cast("JsonObject", budget_points[0])["date"]))
    else:
        origin = month_before(min((cost.on for cost in costs), default=day))
    spent = actual(costs, day)
    projection = [day, *(each for each in (days_of(flows) if flows else []) if each > day)]
    cash_out = (cash_out_by_month(flows, costs, day) if drawn else []) if delays else None
    left = Spread.of(flows)
    return {
        "context": context(reading, stored=reading.is_stored, scope=scope),
        "payment_delays": delays,
        "series": [
            {"name": "reference_budget", "points": budget_points},
            {"name": "actual_cost", "points": actual_series(costs, origin, day) if drawn else []},
            {
                "name": "project_manager_projection",
                # It starts from the actual cost at the day (WF-IND-0100): what is past its
                # finish, whole at that day, is in the point of the end of its month.
                "points": _points(
                    (each, spent + (left.by(each) if each > day else Decimal(0)))
                    for each in (projection if drawn else [])
                ),
            },
        ],
        "steps": [
            {"date": era.since.isoformat(), "amount": money(change), "cause": "amendment"}
            for rank, era in enumerate(eras[1:])
            if (change := budget(era.base, scope) - budget(eras[rank].base, scope)) != 0
        ],
        "cash_out_by_month": cash_out,
    }


def cash_out_by_month(flows: list[Flow], costs: list[Cost], day: date) -> list[JsonValue]:
    """Return the disbursements by month, from the first document to the last flow to come.

    The past by month of date of document, up to the day of the calculation — the lines of cost
    carry no delay of payment —; what is to come by month of the flows shifted by theirs; the
    month of the calculation both (WF-IND-0100).
    """
    first = min((cost.on for cost in costs), default=day).replace(day=1)
    last = month_end(max((flow.last for flow in flows), default=day))
    months: list[JsonValue] = []
    end, before = month_end(first), Decimal(0)
    spread = Spread.of(flows)
    while end <= last:
        future = spread.by(end)
        start = end.replace(day=1)
        past = sum((cost.amount for cost in costs if start <= cost.on <= min(end, day)), Decimal(0))
        months.append(
            {
                "month": end.strftime("%Y-%m"),
                "past": money(past),
                "forecast": money(future - before),
            }
        )
        end, before = month_end(end + timedelta(days=1)), future
    return months


def earned_value_curves(reading: Reading, base: Reading, costs: list[Cost]) -> JsonObject:
    """Return the curves of earned value (`CurveSeries`, WF-IND-0110).

    At the pace of the month (WF-IND-0110): the planned value on the reference in force,
    recomputed whole on it (WF-DEV-0080), to its end; the earned value by date of completion —
    a task completed steps it at the point of its month — and the actual cost by date of
    document, up to today, one point more.
    """
    day = reading.day
    flows = budget_flows(base)
    found = days_of(flows)
    earned_days = up_to(found[0], day)
    planned = Spread.of(flows)
    return {
        "context": context(reading, stored=reading.is_stored),
        "payment_delays": False,
        "series": [
            {"name": "planned_value", "points": _points((d, planned.by(d)) for d in found)},
            {
                "name": "earned_value",
                "points": _points((d, earned(reading, d)) for d in earned_days),
            },
            {"name": "actual_cost", "points": actual_series(costs, found[0], day)},
        ],
        "steps": [],
        "cash_out_by_month": None,
    }


# --- The workload -------------------------------------------------------------------------------


def org_subtree(org: str) -> set[str]:
    """Return a node of the organisation and the nodes under it (WF-REF-0070)."""
    found = {org}
    for node in fixture("org_nodes"):
        if node["parent_id"] in found:
            found.add(node["org_node_id"])
    return found


def workload(reading: Reading, basis: str, org: str | None = None) -> JsonObject:
    """Return the workload of the project by role and by month (`WorkloadPlan`, WF-DEV-0070).

    The hours of the labour lines, each spread over its task pro rata of its hours of work in
    each month — on the remaining to commit, without the lines of the tasks completed —, each
    active role with its capacity beside, its monthly hours, all its people counted
    (WF-REF-0100); over its capacity, a month is in alert. No ratio of the load to the capacity:
    the plan of a project presents none, the capacity being that of the whole installation —
    the aggregated workload keeps it (decision of the author on #375, option b, WF-PTF-0060).
    Filtered by a node of organisation, the roles under it alone.
    """
    kept = None if org is None else org_subtree(org)
    roles: list[JsonValue] = []
    for role in by_identifier("resource_roles", "resource_role_id"):
        if not role["is_active"] or (kept is not None and role["org_node_id"] not in kept):
            continue
        lines = [
            line
            for line in reading.lines
            if reading.facet(line)["resource_role_id"] == role["resource_role_id"]
        ]
        if basis == "current_remaining":
            # What is left to work: never a month before the calculation (WF-DEV-0070).
            flows = [
                ahead(reading, line, line.hours)
                for line in lines
                if reading.progress(line) != "completed"
            ]
        else:
            flows = [over(reading.bearer(line), line.hours) for line in lines]
        capacity = Decimal(role["capacity"]["monthly_hours"])
        months: list[JsonValue] = []
        if flows:
            end, before = month_end(min(flow.first for flow in flows)), Decimal(0)
            spread = Spread.of(flows)
            while end <= month_end(max(flow.last for flow in flows)):
                done = spread.by(end)
                hours = done - before
                if hours:
                    months.append(
                        {
                            "month": end.strftime("%Y-%m"),
                            "hours": decimal(hours),
                            "zone": "alert" if hours > capacity else "nominal",
                        }
                    )
                end, before = month_end(end + timedelta(days=1)), done
        roles.append(
            {
                "resource_role_id": role["resource_role_id"],
                "label": role["label"],
                "org_node_id": role["org_node_id"],
                "capacity_monthly_hours": decimal(capacity.quantize(CENT)),
                "months": months,
            }
        )
    named = {node["org_node_id"]: node["label"] for node in fixture("org_nodes")}
    return {
        "context": context(reading, at=TODAY),
        "basis": basis,
        "org_node_id": org,
        "org_node_label": None if org is None else named[org],
        "monthly_totals": monthly_totals(cast("list[JsonObject]", roles)),
        "roles": roles,
    }


def monthly_totals(roles: list[JsonObject]) -> list[JsonValue]:
    """Return the hours of the roles retained, month by month (`WorkloadPlan.monthly_totals`).

    From the first month a role loads to the last, without a gap, a month without load at nought:
    the label of the top of each bar, which the front does not sum (WF-DEV-0070, #1247).
    """
    totals: dict[str, Decimal] = {}
    for role in roles:
        for month in cast("list[JsonObject]", role["months"]):
            key = cast("str", month["month"])
            totals[key] = totals.get(key, Decimal(0)) + Decimal(cast("str", month["hours"]))
    found: list[JsonValue] = []
    if not totals:
        return found
    end = month_end(date.fromisoformat(f"{min(totals)}-01"))
    while (key := end.strftime("%Y-%m")) <= max(totals):
        found.append({"month": key, "hours": decimal(totals.get(key, Decimal(0)))})
        end = month_end(end + timedelta(days=1))
    return found
