# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves and the workload of the witness, read from its revisions (EP-02/L24, #287).

The revisions are read in ``wftools.mockindicators``: here their amounts are spread in time —
the reference budget on the dates of the reference in force, stepped at each amendment, the
actual cost at the dates of its documents, the remaining to commit on the dates of the current
revision after today (WF-IND-0100, WF-IND-0110) — and their labour hours by month, against the
capacity of each role (WF-DEV-0070). A curve is read at the day before its first amount, at the
end of each month, at the days an amount starts or ends and at the day of the calculation, each
value counting the work of its day; to be replaced by the kernel of EP-08 to EP-11.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockhistory
from wftools.mockcalendar import Instant
from wftools.mockindicators import (
    END_OF_DAY,
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


def budget_flows(base: Reading, *, delays: bool = False) -> list[Flow]:
    """Return the reference budget spread on the dates of the reference, each line by its task."""
    return [
        over(base.bearer(line), line.amounts.budgeted, base.delays[line.number] if delays else 0)
        for line in budgeted(base)
    ]


def remaining_flows(reading: Reading, *, delays: bool = False) -> list[Flow]:
    """Return the remaining to commit spread on the dates of the current revision, after today.

    Each line over the hours its task has left to work after the day of the reading; one whose
    task has none left on the first working day after (WF-IND-0100). With the payment delays,
    each shifted by its line's, and a provision of a risk identified at the date of its task —
    its finish, or the first working day after today when it is past.
    """
    after = Instant(reading.day, END_OF_DAY)
    flows: list[Flow] = []
    for line in reading.lines:
        amount = remaining_of(reading, line)
        if amount == 0:
            continue
        placed = reading.bearer(line)
        calendar, delay = placed.calendar, reading.delays[line.number] if delays else 0
        if delays and mockhistory.is_provision(line):
            upcoming = calendar.start_at(after)
            at = max(Instant(placed.finish.day), Instant(upcoming.day))
            flows.append(Flow(amount, calendar, at, at))
        else:
            flows.append(ahead(reading, line, amount, delay))
    return flows


def ahead(reading: Reading, line: mockcore.Row, amount: Decimal, delay: int = 0) -> Flow:
    """Return what is left of a line spread over the hours its task works after the reading.

    All its hours for a task not started, those after the day of the reading for one started;
    on the first working day after it for a task with none left (WF-RAE-0010, WF-IND-0100).
    """
    after = Instant(reading.day, END_OF_DAY)
    placed = reading.bearer(line)
    calendar = placed.calendar
    if placed.finish <= after:
        upcoming = calendar.start_at(after)
        return Flow(amount, calendar, upcoming, upcoming, delay)
    return Flow(amount, calendar, max(placed.start, after), placed.finish, delay)


def cumulated(flows: Iterable[Flow], day: date) -> Decimal:
    """Return what some flows have spent by the end of a day, to the cent."""
    return sum((flow.by(day) for flow in flows), Decimal(0)).quantize(CENT)


def month_end(day: date) -> date:
    """Return the last day of the month of a day."""
    following = (day.replace(day=1) + timedelta(days=32)).replace(day=1)
    return following - timedelta(days=1)


def days_of(flows: Sequence[Flow], extra: Iterable[date] = ()) -> list[date]:
    """Return the days a curve of some flows is read at, from the day before the first.

    The day before each flow starts and the day it ends, the end of each month, and the days
    asked that fall within.
    """
    first = min(flow.first for flow in flows) - timedelta(days=1)
    last = max(flow.last for flow in flows)
    found = {first, last}
    for flow in flows:
        found.update((flow.first - timedelta(days=1), flow.last))
    end = month_end(first)
    while end < last:
        found.add(end)
        end = month_end(end + timedelta(days=1))
    found.update(day for day in extra if first <= day <= last)
    return sorted(found)


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


def budget_series(eras: Sequence[Era], day: date, *, delays: bool = False) -> list[JsonValue]:
    """Return the cumulative reference budget, by the reference in force at each day.

    At the day of an amendment, two points: the budget of the reference before it, then that of
    the reference it produced, a vertical step (DECISIONS, « Les exemples des courbes »).
    """
    flows = [budget_flows(era.base, delays=delays) for era in eras]
    steps = [era.since for era in eras[1:]]
    found = sorted({*days_of([f for each in flows for f in each], [day]), *steps})
    values: list[tuple[date, Decimal]] = []
    for each in found:
        rank = max(rank for rank, era in enumerate(eras) if rank == 0 or era.since <= each)
        if each in steps:
            values.append((each, cumulated(flows[rank - 1], each)))
        values.append((each, cumulated(flows[rank], each)))
    return _points(values)


def actual_series(costs: list[Cost], origin: date, day: date) -> list[JsonValue]:
    """Return the cumulative actual cost by date of document, up to the day (WF-IND-0100)."""
    found = sorted({origin, day, *(cost.on for cost in costs if origin < cost.on <= day)})
    return _points((each, actual(costs, each)) for each in found)


def cost_curve(
    reading: Reading, eras: Sequence[Era], costs: list[Cost], *, delays: bool = False
) -> JsonObject:
    """Return the curve of the cumulative costs (`CurveSeries`, WF-IND-0100).

    The reference budget by the dates of the reference in force, stepped at each amendment; the
    actual cost by date of document up to today; beyond, the projection of the project manager,
    the remaining spread on the dates of the current revision. With the payment delays, each
    amount shifted by its line's, the provisions of the risks identified at the date of their
    task: the disbursements, past and to come, by month.
    """
    day = reading.day
    budget_points = budget_series(eras, day, delays=delays)
    origin = date.fromisoformat(cast("str", cast("JsonObject", budget_points[0])["date"]))
    flows = remaining_flows(reading, delays=delays)
    spent = actual(costs, day)
    projection = [day, *(each for each in days_of(flows) if each > day)]
    cash_out = cash_out_by_month(flows, costs, day) if delays else None
    return {
        "context": context(reading, at=TODAY),
        "payment_delays": delays,
        "series": [
            {"name": "reference_budget", "points": budget_points},
            {"name": "actual_cost", "points": actual_series(costs, origin, day)},
            {
                "name": "project_manager_projection",
                "points": _points((each, spent + cumulated(flows, each)) for each in projection),
            },
        ],
        "steps": [
            {
                "date": era.since.isoformat(),
                "amount": money(budget(era.base) - budget(eras[rank].base)),
                "cause": "amendment",
            }
            for rank, era in enumerate(eras[1:])
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
    while end <= last:
        future = cumulated(flows, end)
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

    The planned value on the reference in force, recomputed whole on it (WF-DEV-0080), to its
    end; the earned value by date of completion and the actual cost by date of document, up to
    today.
    """
    day = reading.day
    flows = budget_flows(base)
    found = days_of(flows, [day])
    completions = {
        completed
        for line in budgeted(reading)
        if (completed := reading.completed_on(cast("int", line.parent))) is not None
        and completed <= day
        and line.amounts.budgeted != 0
    }
    earned_days = sorted({found[0], day, *completions})
    return {
        "context": context(reading, at=TODAY),
        "payment_delays": False,
        "series": [
            {"name": "planned_value", "points": _points((d, cumulated(flows, d)) for d in found)},
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
            while end <= month_end(max(flow.last for flow in flows)):
                done = cumulated(flows, end)
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
        "roles": roles,
    }
