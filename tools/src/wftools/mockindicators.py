# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the witness today, read from its structure and its history (EP-02/L24, #287).

The core is described once in ``wftools.mockwitness``, the thousand tasks drawn about it in
``wftools.mockstructure``, the whole dated and priced in ``wftools.mockcore``; its marked
revisions — the offer and the reference — are described on the whole structure in
``wftools.mockhistory``. Here the indicators the examples carry are read from those three revisions
and from the actual costs of the universe, the whole structure summed (EP-14/L45a), at the instant
each example names:

- the indicators of the estimate (WF-DEV-0060) and the hourly rates it misses or would update
  (WF-DEV-0010, WF-REV-0060);
- the remaining to commit, its balances by subproject and the coverage of the risks (WF-RAE-0010,
  WF-RAE-0020, WF-RIS-0050);
- the indicators of earned value of the project and of each subproject, the evolution of the
  indices and the tracking of the milestones (WF-IND-0010 to WF-IND-0090, WF-IND-0130);
and, in ``wftools.mockcurves``, the curves and the workload; ``wftools.mocktoday`` writes them
as the examples of the contract.

The formulas are simple and said here, to be replaced by the kernel of EP-07 to EP-11. An amount
spread over a task is spread pro rata of the hours of work of the task's calendar (WF-DEV-0080,
WF-DEV-0070) — the structure employs one calendar for each task, that of its roles —; a value at a
day counts the work of that day, whatever the hour of the calculation. The actual costs are the
lines of the tracked scope the witness describes and those of its drawn tasks completed
(``mockcosts.lines``), at their date of document (WF-IND-0010). Nothing here reads the clock, nor a
file the same command writes.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockcosts, mockhistory
from wftools.mockcalendar import Calendar, Instant
from wftools.mockstructure import (
    CENT,
    LABOUR_RATES,
    REFERENCE_YEAR,
    JsonObject,
    JsonValue,
    computable,
    decimal,
    described,
    inflated,
    labels,
    money,
    partition,
    share,
)
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    OFFER_MARKED,
    TODAY,
    TRACKED,
    CostLine,
    Task,
    by_identifier,
    fixture,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from datetime import datetime

READ_ON = TODAY.date()
"""The day the indicators of the current revision are read: the work of that day counted."""

END_OF_DAY = Decimal(24)
"""The hours of an instant at the end of a day: every hour of work of the day elapsed."""

PROJECT, UNASSIGNED = "project", "unassigned"
"""The scopes that are not a subproject: the whole project, and what belongs to none."""

_NO_ACTUAL, _NO_PLANNED, _NO_EARNED = "no_actual_cost", "no_planned_value", "no_earned_value"
_NO_BUDGET, _NO_SPENDING = "no_reference_budget", "no_actual_or_remaining"
_MISSING = "hourly_rate_missing"


# --- The revisions read -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Reading:
    """A revision of the witness read at an instant: its rows priced, its tasks dated, its delays.

    Its instant is that of its calculation: today for the current revision, its marking for a
    marked one (WF-IND-0010).
    """

    revision: str
    at: datetime
    rows: tuple[mockcore.Row, ...]
    dated: Mapping[int, mockcore.Dated]
    delays: Mapping[int, int]
    by_number: Mapping[int, mockcore.Row]

    @property
    def day(self) -> date:
        """Return the day of the reading: the work of that day is counted."""
        return self.at.date()

    @property
    def lines(self) -> list[mockcore.Row]:
        """Return the lines of the revision, in the order of the plan."""
        return [row for row in self.rows if row.kind == mockcore.ESTIMATE_LINE]

    def facet(self, row: mockcore.Row) -> JsonObject:
        """Return the facet of a node: its task or its line."""
        return cast("JsonObject", row.node[row.kind])

    def task(self, number: int) -> JsonObject:
        """Return the facet of the task of a number."""
        return self.facet(self.by_number[number])

    def bearer(self, line: mockcore.Row) -> mockcore.Dated:
        """Return the task that bears a line, dated."""
        return self.dated[cast("int", line.parent)]

    def progress(self, line: mockcore.Row) -> str:
        """Return the progress of the task that bears a line, at the day of the reading."""
        return cast("str", self.task(cast("int", line.parent))["progress"])

    def completed_on(self, number: int) -> date | None:
        """Return the day a task completed, if it did (WF-PLA-0130)."""
        completed = self.task(number).get("completed_on")
        return None if completed is None else date.fromisoformat(cast("str", completed))

    def subproject(self, line: mockcore.Row) -> str | None:
        """Return the subproject of a line, none for one of the project alone."""
        return cast("str | None", self.facet(line)["subproject_id"])

    def in_scope(self, line: mockcore.Row, scope: str) -> bool:
        """Whether a line belongs to a scope: the project, a subproject, or none (WF-IND-0020)."""
        if scope == PROJECT:
            return True
        return (self.subproject(line) or UNASSIGNED) == scope

    def below(self, number: int) -> set[int]:
        """Return the numbers of the nodes under a task, it included."""
        found = {number}
        for row in self.rows:
            if row.parent in found:
                found.add(row.number)
        return found


def read(
    revision: str,
    roots: Iterable[Task],
    at: datetime,
    rates: Mapping[str, Decimal] = LABOUR_RATES,
    previous: Iterable[Task] = (),
) -> Reading:
    """Read a revision described at an instant, its lines at the rates given.

    Its lines show their quantities in the previous review described, if any (WF-RAE-0040). A
    revision is read once: the indicators, the curves and the portfolio read the same one again
    and again.
    """
    return _read(revision, tuple(roots), at, tuple(sorted(rates.items())), tuple(previous))


@functools.cache
def _read(
    revision: str,
    roots: tuple[Task, ...],
    at: datetime,
    rates: tuple[tuple[str, Decimal], ...],
    previous: tuple[Task, ...],
) -> Reading:
    rows = tuple(mockcore.core(roots, at.date(), dict(rates), previous))
    by_number = {row.number: row for row in rows}
    return Reading(revision, at, rows, mockcore.schedule(roots), delays(rows), by_number)


def delays(rows: Iterable[mockcore.Row]) -> dict[int, int]:
    """Return the payment delay of each line, in days, as its node renders it (WF-IND-0100).

    The curve of the disbursements shifts a line by the delay the grid of the estimate shows
    for it, read from the same node.
    """
    return {
        row.number: cast("int", cast("JsonObject", row.node[row.kind])["payment_delay_days"])
        for row in rows
        if row.kind == mockcore.ESTIMATE_LINE
    }


def today(roots: Iterable[Task] | None = None) -> Reading:
    """Return the current revision 102 read today, on the whole structure as described.

    Or on the structure given: the one a write leaves, or the core alone for a declared variant.
    Its previous review is the reference as marked, read from the structure as described
    (``mockcore.REFERENCE``, WF-RAE-0040).
    """
    return read(
        mockhistory.CURRENT,
        described() if roots is None else roots,
        TODAY,
        previous=mockcore.REFERENCE,
    )


def reference(roots: Iterable[Task] | None = None) -> Reading:
    """Return the reference 101 read on the day it was marked, 1 February 2026.

    As marked on the whole structure (``mockcore.REFERENCE``), or as described by the roots given.
    """
    return read(
        mockhistory.REFERENCE,
        mockcore.REFERENCE if roots is None else roots,
        AMENDMENT_MERGED.instant,
    )


def offer(roots: Iterable[Task] | None = None) -> Reading:
    """Return the offer 100 read on the day it was marked, at the rates of its year, 2025.

    Described from the whole structure of today, or from the roots given (``mockhistory.offer``).
    """
    return read(
        mockhistory.OFFER,
        mockhistory.offer(roots),
        OFFER_MARKED.instant,
        mockhistory.offer_rates(),
    )


# --- The actual costs ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Cost:
    """A line of actual cost of the tracked scope: its date of document, amount and subproject."""

    on: date
    amount: Decimal
    subproject: str | None

    def counts_in(self, scope: str) -> bool:
        """Whether the line counts in a scope: the project, or its own (WF-IND-0020)."""
        return scope in (PROJECT, self.subproject or UNASSIGNED)


def actual_costs(known: Sequence[CostLine] | None = None) -> list[Cost]:
    """Return the lines of actual cost of the tracked scope known today, by date of document.

    Those the witness describes and the invoices of its drawn tasks completed (``mockcosts.lines``)
    — or the lines given —, as the consultation of the costs presents them (``mockcosts``): the
    lines of the imports of March and April, the invoice of the control station the import of
    3 June brought, and the invoices of the drawn tasks (WF-CRE-0010, WF-IND-0010); a line excluded
    from the tracked scope is not a cost (WF-CRE-0030).
    """
    found = [Cost(on, amount, subproject) for on, amount, subproject in mockcosts.tracked(known)]
    return sorted(found, key=lambda cost: cost.on)


def actual(costs: Iterable[Cost], day: date, scope: str = PROJECT) -> Decimal:
    """Return the actual cost at a day: the lines dated that day or before (WF-IND-0010)."""
    return sum(
        (cost.amount for cost in costs if cost.on <= day and cost.counts_in(scope)),
        Decimal(0),
    )


# --- The amounts of a revision ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Flow:
    """An amount spent over hours of work of a calendar, or at once, shifted by some days."""

    amount: Decimal
    calendar: Calendar
    start: Instant
    finish: Instant
    delay: int = 0

    @property
    def first(self) -> date:
        """Return the first day the flow may spend, shifted by its delay."""
        return self.start.day + timedelta(days=self.delay)

    @property
    def last(self) -> date:
        """Return the day the flow is spent whole, shifted by its delay."""
        return self.finish.day + timedelta(days=self.delay)

    def by(self, day: date) -> Decimal:
        """Return what the flow has spent by the end of a day: whole at once, or pro rata."""
        shifted = day - timedelta(days=self.delay)
        total = self.calendar.work_between(self.start, self.finish)
        if total <= 0:
            return self.amount if shifted >= self.finish.day else Decimal(0)
        end = min(max(Instant(shifted, END_OF_DAY), self.start), self.finish)
        return self.amount * self.calendar.work_between(self.start, end) / total


def over(placed: mockcore.Dated, amount: Decimal, delay: int = 0) -> Flow:
    """Return an amount spread over the hours of work of a task."""
    return Flow(amount, placed.calendar, placed.start, placed.finish, delay)


def worked(placed: mockcore.Dated, day: date) -> Decimal:
    """Return the share of a task's hours of work done by the end of a day.

    A task of no duration, a milestone, is whole at its date (WF-DEV-0080).
    """
    return over(placed, Decimal(1)).by(day)


def budgeted(reading: Reading, scope: str = PROJECT) -> list[mockcore.Row]:
    """Return the lines of a scope counted in the reference budget: all but the provisions."""
    return [
        line
        for line in reading.lines
        if reading.in_scope(line, scope) and not mockhistory.is_provision(line)
    ]


def budget(reading: Reading, scope: str = PROJECT) -> Decimal:
    """Return the reference budget of a scope: its budgeted amounts, but the provisions'."""
    return sum((line.amounts.budgeted for line in budgeted(reading, scope)), Decimal(0))


def planned(base: Reading, day: date, scope: str = PROJECT) -> Decimal:
    """Return the planned value at a day: the budget spread on the dates of the reference.

    Each line counted in the reference budget, at its budgeted amount, pro rata of the hours its
    task works up to the day as the reference dates it (WF-DEV-0080).
    """
    spread = sum(
        (line.amounts.budgeted * worked(base.bearer(line), day) for line in budgeted(base, scope)),
        Decimal(0),
    )
    return spread.quantize(CENT)


def earned(reading: Reading, day: date, scope: str = PROJECT) -> Decimal:
    """Return the earned value at a day: the budget of the tasks completed by then.

    The budgeted amounts of the lines borne by the tasks completed that day or before, the day
    of completion making faith; the lines the occurrence of a risk merged earn nothing
    (WF-IND-0030).
    """
    merged = {row.number for row in mockhistory.merged_lines(list(reading.rows))}
    total = Decimal(0)
    for line in budgeted(reading, scope):
        completed = reading.completed_on(cast("int", line.parent))
        if line.number not in merged and completed is not None and completed <= day:
            total += line.amounts.budgeted
    return total


def remaining_of(reading: Reading, line: mockcore.Row) -> Decimal:
    """Return what a line counts in the remaining to commit (WF-RAE-0010).

    A line of provision of a risk identified, its amount; a line budgeted nothing, added after
    the reference, its amount re-estimated whatever its task; otherwise nothing on a task
    completed, the amount re-estimated on a task started, the budgeted amount projected on its
    year of consumption on a task not started.
    """
    if mockhistory.is_provision(line):
        return line.amounts.base
    if line.amounts.budgeted == 0:
        return line.amounts.inflated
    progress = reading.progress(line)
    if progress == "completed":
        return Decimal(0)
    if progress == "started":
        return line.amounts.inflated
    year = cast("int", reading.facet(line)["consumption_year"])
    return inflated(line.amounts.budgeted, year)


def remaining(reading: Reading, scope: str = PROJECT) -> Decimal:
    """Return the remaining to commit of a scope (WF-RAE-0010)."""
    return sum(
        (remaining_of(reading, line) for line in reading.lines if reading.in_scope(line, scope)),
        Decimal(0),
    )


def scopes() -> list[tuple[str, str | None]]:
    """Return the scopes of calculation, the project first, then each subproject, then none."""
    subprojects = [(entry["subproject_id"], entry["label"]) for entry in fixture("subprojects")]
    return [(PROJECT, None), *subprojects, (UNASSIGNED, None)]


# --- Envelopes ----------------------------------------------------------------------------------


def context(
    reading: Reading,
    *,
    stored: bool = False,
    at: datetime | None = None,
    scope: str = PROJECT,
) -> JsonObject:
    """Return the context of a calculation (`CalculationContext`, WF-IHM-0020).

    At the instant of the reading, or at another — a curve of a marked revision is computed
    today, nothing keeping it (WF-DAT-0040); ``stored`` for what a marking kept; for the scope
    computed, the whole project by default (WF-IND-0020).
    """
    draft = reading.revision == mockhistory.CURRENT
    return {
        "revision_id": reading.revision,
        "revision_status": "draft" if draft else "marked",
        "computed_at": mockhistory.stamp(reading.at if at is None else at),
        "scope": scope,
        "is_stored": stored,
    }


def not_computable(reason: str, params: JsonObject | None = None) -> JsonObject:
    """Return a value that cannot be computed, and why (WF-IND-0010)."""
    value: JsonObject = {"is_computable": False, "value": None, "reason": reason}
    if params is not None:
        value["params"] = params
    return value


def ratio(numerator: Decimal, denominator: Decimal, reason: str) -> JsonObject:
    """Return a ratio as the contract gives it (``share``), not computable without denominator."""
    if denominator == 0:
        return not_computable(reason)
    return computable(decimal(share(numerator / denominator)))


def index(numerator: Decimal, denominator: Decimal, reason: str, axis: str) -> JsonObject:
    """Return an index and its zone by the thresholds of the installation (WF-REF-0170).

    Below the threshold of alert, in alert; below that of watch, in watch; nominal otherwise.
    """
    value = ratio(numerator, denominator, reason)
    if not value["is_computable"]:
        return {"value": value, "zone": None}
    thresholds = fixture("reference_settings")["index_thresholds"]
    found = Decimal(cast("str", value["value"]))
    zone = "nominal"
    if found < Decimal(thresholds[f"{axis}_watch"]):
        zone = "watch"
    if found < Decimal(thresholds[f"{axis}_alert"]):
        zone = "alert"
    return {"value": value, "zone": zone}


# --- The indicators of the estimate -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Group:
    """Lines of an estimate gathered under a key: a nature, a subproject, an order item."""

    key: str
    label: str | None
    lines: list[mockcore.Row]


def missing_rates(
    reading: Reading, lines: Iterable[mockcore.Row], missing: frozenset[str]
) -> list[JsonValue]:
    """Return the categories some lines employ without a rate for the reference year."""
    named = labels()
    employed = {cast("str", reading.facet(line)["cost_category_id"]) for line in lines}
    return [
        {"cost_category_id": category, "label": named[category], "year": REFERENCE_YEAR}
        for category in sorted(employed & missing)
    ]


def _base(lines: Iterable[mockcore.Row]) -> Decimal:
    return sum((line.amounts.base for line in lines), Decimal(0))


def _amount(reading: Reading, lines: list[mockcore.Row], missing: frozenset[str]) -> JsonObject:
    """Return the amount of some lines, not computable if one misses its rate (WF-DEV-0010)."""
    absent = missing_rates(reading, lines, missing)
    if absent:
        return not_computable(_MISSING, {"missing_rates": absent})
    return computable(money(_base(lines)))


def _parts(
    reading: Reading,
    groups: list[Group],
    missing: frozenset[str],
    *,
    whole: bool = True,
) -> list[JsonValue]:
    """Return the amounts of some groups and their shares of the total (WF-DEV-0060).

    The shares of a partition of the total sum to one (``partition``); those of the order items,
    which hold a part of the lines only, are each the amount over the total (``share``). No share
    is computable when the total is not, nor without its amount.
    """
    absent = missing_rates(reading, reading.lines, missing)
    total = _base(reading.lines)
    amounts = [_base(group.lines) for group in groups]
    found = partition(amounts, total) if whole else [share(each / total) for each in amounts]
    parts: list[JsonValue] = []
    for group, part_share in zip(groups, found, strict=True):
        part: JsonObject = {"key": group.key}
        if group.label is not None:
            part["label"] = group.label
        amount = _amount(reading, group.lines, missing)
        part["amount"] = amount
        computed = not absent and amount["is_computable"] is True
        part["share"] = (
            computable(decimal(part_share))
            if computed
            else not_computable(_MISSING, {"missing_rates": absent})
        )
        parts.append(part)
    return parts


def natures(lines: list[mockcore.Row]) -> list[Group]:
    """Return some lines by nature of cost, in the order of the identifiers of the natures."""
    return [
        Group(key, label, [line for line in lines if mockhistory.nature(line) == key])
        for key, label in (
            (nature["cost_type_id"], nature["label"])
            for nature in by_identifier("cost_types", "cost_type_id")
        )
        if any(mockhistory.nature(line) == key for line in lines)
    ]


def subprojects(reading: Reading, lines: list[mockcore.Row]) -> list[Group]:
    """Return some lines by subproject, those of none last, each subproject that has some."""
    groups = [
        Group(scope, label, [line for line in lines if reading.in_scope(line, scope)])
        for scope, label in scopes()[1:]
    ]
    return [group for group in groups if group.lines]


def order_items(reading: Reading) -> list[Group]:
    """Return the lines under each task that bears an order item of the work breakdown."""
    groups: list[Group] = []
    for row in reading.rows:
        facet = reading.facet(row)
        if row.kind == mockcore.TASK and facet.get("order_item_id") is not None:
            below = reading.below(row.number)
            lines = [line for line in reading.lines if line.number in below]
            label = cast("str", facet["work_breakdown_label"])
            groups.append(Group(cast("str", facet["order_item_id"]), label, lines))
    return groups


def estimate(
    reading: Reading,
    *,
    against: Reading | None = None,
    previous: Reading | None = None,
    missing: frozenset[str] = frozenset(),
) -> JsonObject:
    """Return the indicators of the estimate of a revision (`EstimateIndicators`, WF-DEV-0060).

    Its total at the year of reference, by nature, by subproject and by order item; its
    provisions; its gaps to the estimate of the reference and of the previous marked revision,
    absent without them. That of a marked revision is the one its marking kept (WF-DAT-0040). A
    category in ``missing`` has no rate for the reference year: what its
    lines touch is not computed (WF-DEV-0010).
    """
    lines = reading.lines
    absent = missing_rates(reading, lines, missing)
    total = _base(lines)

    def gap(other: Reading | None) -> JsonObject | None:
        if other is None:
            return None
        if absent:
            return not_computable(_MISSING, {"missing_rates": absent})
        return computable(money(total - _base(other.lines)))

    items = order_items(reading)
    return {
        "context": context(reading, stored=reading.revision != mockhistory.CURRENT),
        "total": _amount(reading, lines, missing),
        "by_cost_type": _parts(reading, natures(lines), missing),
        "by_subproject": _parts(reading, subprojects(reading, lines), missing),
        "by_order_item": _parts(reading, items, missing, whole=False) if items else None,
        "provisions_identified": money(
            _base(line for line in lines if mockhistory.is_provision(line))
        ),
        "delta_to_reference": gap(against),
        "delta_to_previous_revision": gap(previous),
    }


def rate_update() -> JsonObject:
    """Return the rate update proposed when the revision 101 was created (WF-REV-0060).

    Opened on 12 January 2026 by the identification of the risks, its reference year is 2026,
    where the offer it copied had 2025: each labour category the offer employs is proposed at
    its rate of 2026 in the grid of the rates, its rate of 2025 beside.
    """
    kept, named, marked = mockhistory.offer_rates(), labels(), offer()
    employed = sorted(
        {cast("str", marked.facet(line)["cost_category_id"]) for line in marked.lines if line.hours}
    )
    return {
        "target_year": REFERENCE_YEAR,
        "categories": [
            {
                "cost_category_id": category,
                "label": named[category],
                "previous_amount": money(kept[category]),
                "proposed_amount": money(LABOUR_RATES[category]),
                "source": "reference_rate",
            }
            for category in employed
        ],
    }


# --- The remaining to commit --------------------------------------------------------------------


def balance(
    reading: Reading, base: Reading, costs: list[Cost], scope: str, label: str | None
) -> JsonObject:
    """Return the balance of a subproject: its budget against its cost and remaining (WF-RAE-0020).

    Its budget is that of its lines in the reference, as the indicators of the project read it;
    over it, it is in alert — a simplification of the scale of WF-IHM-0070, which says no
    threshold for it.
    """
    fixed, spent = budget(base, scope), actual(costs, reading.day, scope)
    left = remaining(reading, scope)
    variance = fixed - spent - left
    found: JsonObject = {"key": scope}
    if label is not None:
        found["label"] = label
    found.update(
        {
            "budget": money(fixed),
            "actual_cost": money(spent),
            "remaining": money(left),
            "variance": money(variance),
            "is_over_budget": variance < 0,
            "zone": "alert" if variance < 0 else "nominal",
        }
    )
    return found


def remaining_indicators(
    reading: Reading, base: Reading, previous: Reading | None, costs: list[Cost]
) -> JsonObject:
    """Return the indicators of the remaining to commit (`RemainingIndicators`, WF-RAE-0020).

    Its total, by nature and by subproject, each subproject balanced against its budget; its gap
    to the reference budget — the budget less the actual cost and the remaining, positive while
    a margin is left, in the one sense of the balances of the subprojects (#466) —, and to the
    remaining of the previous marked revision at its marking — the remaining less that one —,
    absent without one; the coverage of the risks (WF-RIS-0050).
    """
    total = remaining(reading)
    by_nature = [
        (group, sum((remaining_of(reading, line) for line in group.lines), Decimal(0)))
        for group in natures(reading.lines)
    ]
    by_nature = [(group, amount) for group, amount in by_nature if amount != 0]
    parts = partition([amount for _, amount in by_nature], total)
    coverage = mockhistory.coverage(list(reading.rows), list(base.rows))
    return {
        "context": context(reading),
        "total": money(total),
        "by_cost_type": [
            {
                "key": group.key,
                "label": group.label,
                "amount": money(amount),
                "share": decimal(part),
            }
            for (group, amount), part in zip(by_nature, parts, strict=True)
        ],
        "by_subproject": [
            balance(reading, base, costs, scope, label) for scope, label in scopes()[1:]
        ],
        "delta_to_reference": money(budget(base) - actual(costs, reading.day) - total),
        "delta_to_previous_revision": None
        if previous is None
        else money(total - remaining(previous)),
        "coverage": {key: value for key, value in coverage.items() if key != "context"},
    }


# --- The indicators of the project --------------------------------------------------------------


def project_indicators(
    reading: Reading,
    base: Reading,
    costs: list[Cost],
    scope: str = PROJECT,
) -> JsonObject:
    """Return the indicators of earned value of a scope (`ProjectIndicators`).

    Those of a marked revision are the ones its marking kept (WF-DAT-0040).

    At the day of the reading, on the reference ``base``: the reference budget, the planned and
    earned values, the actual cost and the remaining (WF-IND-0010 to WF-IND-0030), the progress
    (WF-IND-0040, WF-IND-0060), the indices and their gaps (WF-IND-0070, WF-IND-0080), and the
    three projections at completion (WF-IND-0050).
    """
    day = reading.day
    fixed, value = budget(base, scope), planned(base, day, scope)
    gained, spent = earned(reading, day, scope), actual(costs, day, scope)
    left = remaining(reading, scope)
    observed: JsonObject = computable("0")
    variance: str | None = None
    if spent == 0:
        observed = not_computable(_NO_ACTUAL)
    elif gained == 0:
        observed = not_computable(_NO_EARNED)
    else:
        at_rate = (fixed * spent / gained).quantize(CENT)
        observed, variance = computable(money(at_rate)), money(at_rate - fixed)
    return {
        "context": context(reading, stored=reading.revision != mockhistory.CURRENT),
        "reference_budget": money(fixed),
        "planned_value": money(value),
        "earned_value": money(gained),
        "actual_cost": money(spent),
        "remaining": money(left),
        "financial_progress": ratio(spent, spent + left, _NO_SPENDING),
        "budget_consumption": ratio(spent, fixed, _NO_BUDGET),
        "physical_progress": ratio(gained, fixed, _NO_BUDGET),
        "cost_index": index(gained, spent, _NO_ACTUAL, "cost"),
        "schedule_index": index(gained, value, _NO_PLANNED, "schedule"),
        "cost_variance": money(gained - spent),
        "schedule_variance": money(gained - value),
        "projections": {
            "at_budget": money(spent + fixed - gained),
            "project_manager": money(spent + left),
            "at_observed_rate": observed,
            "variance_at_budget": money(spent - gained),
            "variance_project_manager": money(spent + left - fixed),
            "variance_at_observed_rate": variance,
        },
    }


IN_PROGRESS = "in_progress"


def state_at(at: datetime, transitions: Sequence[JsonObject] | None = None) -> str | None:
    """Return the state of the project at an instant: that of its last transition by then.

    The transitions are those the project went through (``state_transitions``, written by hand):
    a transition at the very instant counts. None before the project was created.
    """
    found = fixture("state_transitions") if transitions is None else transitions
    state: str | None = None
    for transition in sorted(found, key=lambda each: cast("str", each["occurred_at"])):
        if cast("str", transition["occurred_at"]) <= mockhistory.stamp(at):
            state = cast("str", transition["to_state"])
    return state


@dataclass(frozen=True, slots=True)
class Point:
    """A revision at the instant its indicators are read: its marking, or today."""

    reading: Reading
    base: Reading
    version_name: str | None


def index_history(
    points: Sequence[Point], costs: list[Cost], only: str | None = None
) -> JsonObject:
    """Return the evolution of the indices of each scope (`IndexHistory`, WF-IND-0130).

    Of the one scope asked (`scope`), when one is, which the context names (WF-IND-0020).

    A point for each revision marked from the state In progress, at its marking, as it kept them
    — one marked while pricing kept the indicators of its estimate alone (WF-DAT-0040,
    WF-IND-0010) —; the last for the current revision, today; the thresholds of the installation
    beside. Whether a revision was marked In progress is read in the transitions of the state of
    the project (``state_transitions``), at the instant of its marking — not from its date. The
    Vérif of WF-IND-0130, a point for every marked revision, is questioned on #468.
    """
    current = points[-1]
    kept = [point for point in points if state_at(point.reading.at) == IN_PROGRESS]
    entries: list[JsonValue] = []
    for scope, label in scopes():
        if only is not None and scope != only:
            continue
        series: list[JsonValue] = []
        for point in kept:
            day = point.reading.day
            gained, spent = earned(point.reading, day, scope), actual(costs, day, scope)
            series.append(
                {
                    "at": mockhistory.stamp(point.reading.at),
                    "revision_id": point.reading.revision,
                    "version_name": point.version_name,
                    "cost_index": index(gained, spent, _NO_ACTUAL, "cost"),
                    "schedule_index": index(
                        gained, planned(point.base, day, scope), _NO_PLANNED, "schedule"
                    ),
                }
            )
        entries.append({"scope": scope, "label": label, "points": series})
    return {
        "context": context(current.reading, scope=PROJECT if only is None else only),
        "thresholds": fixture("reference_settings")["index_thresholds"],
        "scopes": entries,
    }


def milestone_tracking(marked: Sequence[Point], current: Point) -> JsonObject:
    """Return the time/time chart of the tracked milestones (`MilestoneTracking`, WF-IND-0090).

    For each milestone, the date each marked revision that bears it forecast, at its marking;
    the last point today, by the current revision — or, for a milestone completed, at its
    completion, on the diagonal, nothing after.
    """
    now = current.reading
    entries: list[JsonValue] = []
    for number in TRACKED:
        completed = now.completed_on(number)
        points: list[JsonValue] = [
            {
                "marked_at": mockhistory.stamp(point.reading.at),
                "forecast_date": point.reading.dated[number].finish.day.isoformat(),
            }
            for point in marked
            if number in point.reading.dated
            and (completed is None or point.reading.day <= completed)
        ]
        last = (
            (mockhistory.stamp(now.at), now.dated[number].finish.day)
            if completed is None
            else (f"{completed.isoformat()}T00:00:00Z", completed)
        )
        points.append({"marked_at": last[0], "forecast_date": last[1].isoformat()})
        entries.append(
            {
                "lineage_id": mockcore.lineage(number),
                "label": now.task(number)["label"],
                "completed_on": None if completed is None else completed.isoformat(),
                "points": points,
            }
        )
    return {"context": context(now), "milestones": entries}
