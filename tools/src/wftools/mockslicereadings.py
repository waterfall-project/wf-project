# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The readings of the eight views of the portfolio on the witness and its slice (EP-11/US-2770).

What the service must answer once ``waterfall-api load-witness`` has loaded PRJ-001, PRJ-002 and
the ten projects of the slice (``mockslice``), each view read at the date of the witness, 3 June
2026, by ``as_of``: a past date to the service, whose clock runs on, so that every project
contributes by what its last revision marked by then kept, and is retained by the state it had
that day (WF-PTF-0010, WF-DAT-0040). The computation is this module's own: it imports nothing of
the back, ``aggregation/`` included, and reads PRJ-001 by the readings of the tools
(``mockindicators``, ``mockcurves``, ``mockwitnessrisks``), on its reference 101 as marked on
1 February 2026.

The rules it follows, where the design of EP-11 leaves the lot of a view to decide:

- a project contributes by its last revision marked by the end of the day; one marked while in
  pricing kept an estimate and no indicator of a project (EP-10), and one with no marked revision
  contributes nothing — listed by its state, without an amount, its probability of winning
  included, none being kept (US-2670);
- the scope counts the projects the view retains: those of the states asked that it counts —
  in progress and in pricing for the workload, in progress alone for the performance and the
  health of the steering —, the completed ones being those of the default period;
- a series kept at a marking is read at a day by its last point on or before that day: the actual
  cost stays at what was known at the marking, the projection starts there (WF-IND-0100);
- a weighted part of an offer is rounded once, by project, to the cent — to the hundredth of an
  hour for its load —, before the sum (EP-11, « Ce que le cadrage décide »);
- the matrix of the portfolio, its totals included, is a ``RiskMatrix`` read from the risks the
  marked revisions kept (US-2730): its ``ProvisionTotals`` count each risk once, in the state the
  marking kept — an identified one for its provision, an occurred or dismissed one for the one it
  held in the reference revision —; the outcomes of the period alone, ``period_outcome``, are read
  by the date of the review that changed the state of a risk, after the marking or not (US-2730),
  so that they may overlap the identified total: they are two readings, not one;
- a review of a risk is any row of its history, its declaration the first: the declaration writes
  « un premier réexamen daté du jour », and ``listRiskReviews`` renders each review,
  « l'identification le premier » (EP-08, US-2570 and US-2590), which the signal
  ``risks_not_reviewed`` counts like the others;
- an import of actual costs at or before the instant of a marking is known to it: the actual cost
  kept and the signal ``no_actual_cost_since_last_review`` take the same bound, the marking
  included;
- the reader is the manager, who opens every project (WF-INTF-0020): ``can_open`` is true.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING, cast

from wftools import mockindicators, mockportfolio, mocktoday
from wftools.mockcurves import Era, cost_curve, workload
from wftools.mockhistory import is_provision, nature, stamp
from wftools.mockids import universe
from wftools.mockslice import (
    COMPLETED,
    IDENTIFIED,
    IN_PROGRESS,
    PRICING,
    SLICE,
    Project,
)
from wftools.mockstructure import (
    LABOR,
    NON_LABOR,
    PROVISION,
    JsonObject,
    JsonValue,
)
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    COST_IMPORTS,
    CREATED,
    OFFER_MARKED,
    OFFER_OPENED,
    ORDER_RECEIVED,
    fixture,
)
from wftools.mockwitnessrisks import REGISTER, reference_provision

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

AS_OF = date(2026, 6, 3)
"""The date of the witness the views are read at, by ``as_of``."""

STATES = (IN_PROGRESS, PRICING, COMPLETED)
"""The states every view is asked with: what each counts of them is its own."""

PERIOD_FROM = mockportfolio.period_from(AS_OF)
HORIZON = 6
MAX_WEEKS = cast("int", fixture("reference_settings")["max_weeks_between_reviews"])
"""The delay between two reviews the reference sets (WF-REF-0180)."""

ZERO = Decimal("0.00")

type Curve = Callable[[date], Decimal]


def _flat(_day: date) -> Decimal:
    return ZERO


@dataclass(frozen=True, slots=True)
class KeptRisk:
    """A risk as a marking kept it, with the base of its project that classes its severity."""

    risk_id: str
    label: str
    probability: Decimal
    severity: Decimal
    provision: Decimal
    state: str
    held: Decimal = ZERO
    """The provision it held in the reference revision, which ``ProvisionTotals`` counts for an
    occurred or dismissed risk."""


@dataclass(frozen=True, slots=True)
class Kept:
    """What the marking of a revision kept for the portfolio (US-2680), at its instant.

    For a revision marked in pricing, an offer: its estimate, without and with its provisions, its
    load, its natures and its curves, and the probability it kept (EP-07). For one marked in
    progress, the indicators of the project besides (EP-10).
    """

    marked: datetime
    offer: bool
    probability: Decimal
    budget: Decimal
    estimate: Decimal
    planned: Decimal = ZERO
    earned: Decimal = ZERO
    actual: Decimal = ZERO
    remaining: Decimal = ZERO
    budget_by_nature: dict[str, Decimal] = field(default_factory=dict[str, Decimal])
    remaining_by_nature: dict[str, Decimal] = field(default_factory=dict[str, Decimal])
    labour_by_role: dict[str, Decimal] = field(default_factory=dict[str, Decimal])
    hours: dict[tuple[str, str], Decimal] = field(default_factory=dict[tuple[str, str], Decimal])
    budget_curve: Curve = _flat
    actual_curve: Curve = _flat
    projection_curve: Curve = _flat
    risks: tuple[KeptRisk, ...] = ()
    reserve: Decimal = ZERO

    @property
    def projection(self) -> Decimal:
        """The projection of the project manager: the actual cost and the remaining to commit."""
        return self.actual + self.remaining


@dataclass(frozen=True, slots=True)
class Member:
    """A project of the portfolio as the views read it: its history, its markings, its risks."""

    project_id: str
    label: str
    code: str
    history: tuple[tuple[datetime, str], ...]
    markings: tuple[Kept, ...]
    outcomes: tuple[tuple[datetime, str, Decimal], ...] = ()
    reviews: tuple[tuple[str, datetime], ...] = ()
    """Each review of each risk, its declaration included: the first review of its history
    (EP-08, US-2570, « un premier réexamen daté du jour »)."""
    imports: tuple[datetime, ...] = ()
    milestones: tuple[tuple[str, str, date, date | None], ...] = ()

    def state_on(self, day: date) -> str | None:
        """Return its state on a day: its last transition dated that day or before (WF-CYC-0130)."""
        held = [state for instant, state in self.history if instant.date() <= day]
        return held[-1] if held else None

    def kept_on(self, day: date) -> list[Kept]:
        """Return its revisions marked by the end of a day, the last one last."""
        return [kept for kept in self.markings if kept.marked.date() <= day]

    def last_on(self, day: date) -> Kept | None:
        """Return its last revision marked by the end of a day, if any."""
        found = self.kept_on(day)
        return found[-1] if found else None

    def project_on(self, day: date) -> Kept | None:
        """Return its last kept indicators of a project on a day: none after an offer's marking."""
        last = self.last_on(day)
        return None if last is None or last.offer else last

    def offer_on(self, day: date) -> Kept | None:
        """Return the offer its last marking on a day kept: none after a project's marking."""
        last = self.last_on(day)
        return last if last is not None and last.offer else None

    def completed_in(self, start: date, end: date) -> bool:
        """Whether it passed to Completed in a period, bounds included (WF-CYC-0130)."""
        return any(
            state == COMPLETED and start <= instant.date() <= end for instant, state in self.history
        )


# --- The slice: what each marking kept --------------------------------------------------------


def _month(day: date) -> str:
    return day.strftime("%Y-%m")


def _kept(project: Project, marked: datetime) -> Kept:
    """Return what the marking of a revision of a project of the slice kept, at its instant.

    Every task lies within a month, completed at its finish or ahead of the marking, but the one
    left started past its finish, whose remaining is whole at the day (WF-IND-0100).
    """
    day, year = marked.date(), project.year
    offer = project.state_before(marked) == PRICING
    remaining_lines: list[tuple[date, str, Decimal]] = []
    budget_by, remaining_by = defaultdict[str, Decimal](Decimal), defaultdict[str, Decimal](Decimal)
    labour: defaultdict[str, Decimal] = defaultdict(Decimal)
    hours: defaultdict[tuple[str, str], Decimal] = defaultdict(Decimal)
    budget = planned = earned = Decimal(0)
    for task in project.tasks:
        open_ = offer or not task.completed_by(day)
        for line in task.lines:
            amount, kind = line.amount(year), LABOR if line.hours is not None else NON_LABOR
            budget += amount
            budget_by[kind] += amount
            if line.role is not None:
                labour[line.role] += amount
            planned += amount if task.finish <= day else 0
            earned += amount if task.completed_by(day) else 0
            if open_:
                remaining_by[kind] += amount
                remaining_lines.append((max(task.finish, day), kind, amount))
                if line.role is not None and line.hours is not None:
                    hours[line.role, _month(task.start)] += line.hours
    for risk in project.risks:
        provision = risk.provision_at(marked)
        if provision:
            remaining_by[PROVISION] += provision
            remaining_lines.append(
                (max(project.tasks[risk.task - 1].finish, day), PROVISION, provision)
            )
    costs = [
        (on, amount)
        for imported in project.imports
        if imported.at <= marked
        for on, amount in imported.costs
        if on <= day
    ]
    actual = sum((amount for _, amount in costs), Decimal(0))
    provisions = remaining_by.get(PROVISION, Decimal(0))
    finishes = [(task.finish, line.amount(year)) for task in project.tasks for line in task.lines]

    def budget_curve(at: date) -> Decimal:
        return sum((amount for finish, amount in finishes if finish <= at), Decimal(0))

    def actual_curve(at: date) -> Decimal:
        return sum((amount for on, amount in costs if on <= min(at, day)), Decimal(0))

    def projection_curve(at: date) -> Decimal:
        if offer:
            return budget_curve(at) + sum(
                (
                    amount
                    for finish, kind, amount in remaining_lines
                    if kind == PROVISION and finish <= at
                ),
                Decimal(0),
            )
        if at < day:
            return ZERO
        return actual + sum(
            (amount for finish, _, amount in remaining_lines if finish <= at), Decimal(0)
        )

    reference = project.revisions[0].marked
    risks = tuple(
        KeptRisk(
            project.risk_id(number),
            risk.label,
            known.probability,
            risk.severity,
            risk.provision_at(marked),
            known.state,
            risk.provision_at(reference) if reference else ZERO,
        )
        for number, risk in enumerate(project.risks, start=1)
        if (known := risk.known_at(marked)) is not None
    )
    return Kept(
        marked=marked,
        offer=offer,
        probability=project.probability if offer else Decimal(1),
        budget=budget,
        estimate=budget + provisions,
        planned=planned,
        earned=earned,
        actual=actual,
        remaining=sum(remaining_by.values(), Decimal(0)),
        budget_by_nature=dict(budget_by),
        remaining_by_nature=dict(remaining_by),
        labour_by_role=dict(labour),
        hours=dict(hours),
        budget_curve=budget_curve,
        actual_curve=actual_curve,
        projection_curve=projection_curve,
        risks=risks,
        reserve=sum(
            (risk.provision_at(reference) for risk in project.risks if reference), Decimal(0)
        ),
    )


def member(project: Project) -> Member:
    """Return a project of the slice as the views read it."""
    outcomes = tuple(
        (review.at, review.state, risk.provision_at(review.at - timedelta(seconds=1)))
        for risk in project.risks
        for review in risk.reviews[1:]
        if review.state != IDENTIFIED
    )
    return Member(
        project.project_id,
        project.label,
        project.code,
        tuple((instant, state) for instant, _, state in project.history()),
        tuple(_kept(project, revision.marked) for revision in project.revisions if revision.marked),
        outcomes,
        tuple(
            (project.risk_id(number), review.at)
            for number, risk in enumerate(project.risks, start=1)
            for review in risk.reviews
        ),
        tuple(imported.at for imported in project.imports),
    )


# --- PRJ-001 and PRJ-002, by the readings of the tools ------------------------------------------


def _series(points: list[JsonValue]) -> Curve:
    """Read a kept series at a day: its last point on or before it, nought before the first."""
    found = [
        (date.fromisoformat(cast("str", point["date"])), Decimal(cast("str", point["amount"])))
        for point in cast("list[JsonObject]", points)
    ]

    def at(day: date) -> Decimal:
        before = [amount for on, amount in found if on <= day]
        return before[-1] if before else ZERO

    return at


def _by_nature(rows: Iterable[tuple[str, Decimal]]) -> dict[str, Decimal]:
    found: defaultdict[str, Decimal] = defaultdict(Decimal)
    for key, amount in rows:
        found[key] += amount
    return dict(found)


@cache
def witness() -> Member:
    """Return PRJ-001 as its reference 101 kept it on 1 February 2026, read by the tools.

    Its indicators as ``project_indicators_marked``; its load as ``workload_marked_remaining``; its
    curve as its marking computed it, nothing spent yet; its risks as they stood that day; its
    tracked milestones as the reference dated them, none completed yet.
    """
    base, found = mockindicators.reference(), mocktoday.witness()
    indicators = cast("dict[str, str]", mockindicators.project_indicators(base, base, found.costs))
    curve = cost_curve(
        base, [Era(ORDER_RECEIVED.on, found.offer), Era(AMENDMENT_MERGED.on, base)], []
    )
    series = {
        cast("str", each["name"]): cast("list[JsonValue]", each["points"])
        for each in cast("list[JsonObject]", curve["series"])
    }
    plan = workload(base, "marked_remaining")
    lines = base.lines
    roles = {
        line.number: cast(
            "str | None", cast("JsonObject", line.node["estimate_line"])["resource_role_id"]
        )
        for line in lines
    }
    labour = _by_nature(
        (role, line.amounts.budgeted)
        for line in lines
        if not is_provision(line) and (role := roles[line.number]) is not None
    )
    on = AMENDMENT_MERGED.on
    kept = Kept(
        marked=AMENDMENT_MERGED.instant,
        offer=False,
        probability=Decimal(1),
        budget=Decimal(indicators["reference_budget"]),
        estimate=Decimal(indicators["reference_budget"]),
        planned=Decimal(indicators["planned_value"]),
        earned=Decimal(indicators["earned_value"]),
        actual=Decimal(indicators["actual_cost"]),
        remaining=Decimal(indicators["remaining"]),
        budget_by_nature=_by_nature(
            (nature(line), line.amounts.budgeted) for line in lines if not is_provision(line)
        ),
        remaining_by_nature=_by_nature(
            (nature(line), mockindicators.remaining_of(base, line)) for line in lines
        ),
        labour_by_role=labour,
        hours={
            (cast("str", role["resource_role_id"]), cast("str", month["month"])): Decimal(
                cast("str", month["hours"])
            )
            for role in cast("list[JsonObject]", plan["roles"])
            for month in cast("list[JsonObject]", role["months"])
        },
        budget_curve=_series(series["reference_budget"]),
        actual_curve=_series(series["actual_cost"]),
        projection_curve=_series(series["project_manager_projection"]),
        risks=tuple(
            KeptRisk(
                universe(risk.number),
                risk.label,
                known.probability,
                known.severity,
                reference_provision(risk),
                known.state,
                reference_provision(risk),
            )
            for risk in REGISTER
            if (known := risk.known_on(on)) is not None
        ),
        reserve=sum((reference_provision(risk) for risk in REGISTER), Decimal(0)),
    )
    # The offer 100, marked in pricing: the views of 3 June read nothing of it but its instant, the
    # previous review of the reference (WF-PTF-0110).
    offer = Kept(
        OFFER_MARKED.instant, offer=True, probability=Decimal(1), budget=ZERO, estimate=ZERO
    )
    tracking = mockindicators.milestone_tracking(found.points()[:-1], found.points()[-1])
    marked = stamp(AMENDMENT_MERGED.instant)
    milestones = tuple(
        (
            cast("str", milestone["lineage_id"]),
            cast("str", milestone["label"]),
            date.fromisoformat(cast("str", point["forecast_date"])),
            None,
        )
        for milestone in cast("list[JsonObject]", tracking["milestones"])
        for point in cast("list[JsonObject]", milestone["points"])
        if point["marked_at"] == marked
    )
    project = fixture("project")
    outcomes = tuple(
        (review.at, review.state, reference_provision(risk))
        for risk in REGISTER
        for review in risk.reviews
        if review.state != IDENTIFIED
    )
    return Member(
        cast("str", project["project_id"]),
        cast("str", project["label"]),
        cast("str", project["code"]),
        (
            (CREATED.instant, "created"),
            (OFFER_OPENED.instant, PRICING),
            (ORDER_RECEIVED.instant, IN_PROGRESS),
        ),
        (offer, kept),
        outcomes,
        tuple((universe(risk.number), review.at) for risk in REGISTER for review in risk.reviews),
        tuple(each.instant for each in COST_IMPORTS),
        milestones,
    )


def pricing_offer() -> Member:
    """Return PRJ-002, in pricing since its creation, without a revision marked."""
    offer = fixture("project_pricing")
    created = datetime.fromisoformat(cast("str", offer["audit"]["created_at"]))
    return Member(
        cast("str", offer["project_id"]),
        cast("str", offer["label"]),
        cast("str", offer["code"]),
        ((created, cast("str", offer["state"])),),
        (),
    )


def members() -> list[Member]:
    """Return every project the witness loads, PRJ-001 and PRJ-002 first, then the slice."""
    return [witness(), pricing_offer(), *(member(project) for project in SLICE)]
