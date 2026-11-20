# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scope of a view of the portfolio: its states, its date, its period, its node (US-2670).

What every view is asked, as the query of the contract says it, and the scope it retains
(``PortfolioScope``), which each answer gives back (WF-PTF-0010): the states asked or, without
them, the projects In progress, a state the view does not count being without effect, never
refused; the date of calculation, the current day of the time zone of the installation without
``as_of``; the period, the default one — the twelve months that end at the date — included, null
for a view that retains none, and its refusal (``PortfolioPeriodRefused``, 422); the node and its
label, an unknown node refused (422 on ``/query/org_node_id``); the number of projects retained.
One function resolves it for the eight views, the state of a project at a date being that of its
last transition dated that day or before (WF-CYC-0130).

It gives each view, besides that scope, the projects it retains (``ResolvedScope``): those whose
state at the date is both asked and one the view counts, which the view names (``counted``) — a
project Completed by its completion in the period (``PortfolioStates``) —, so that
``project_count`` is their number for every view (EP-11, "Les vues"); and, for each, its
state, the revision it contributes by and its weight (EP-11, "La contribution d'un projet"). A view
reads the contributions of these projects and of no other, and does not resolve them again.

Declared by US-2670/L1, the socle of EP-11; filled by US-2670/L3.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.portfolio.aggregation import weight_of
from waterfall.core.portfolio.states import COMPLETED, PRICING
from waterfall.core.projects.interface import current_day, projects_in_states_on
from waterfall.core.resource_settings.interface import node_labels
from waterfall.core.revisions.interface import last_marked_at_instant
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, UnprocessableError
from waterfall.platform.installation import TIME_ZONE

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import ProjectAtDate, ProjectState
    from waterfall.core.revisions.interface import RetainedRevisions
    from waterfall.platform.cache import IndicatorsCache

# The states retained when none is asked: the projects In progress (``PortfolioStates``).
DEFAULT_STATES: tuple[ProjectState, ...] = ("in_progress",)
UNKNOWN_ORG_NODE = "UNKNOWN_ORG_NODE"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
FROM_POINTER = "/query/from"
TO_POINTER = "/query/to"
ORG_NODE_POINTER = "/query/org_node_id"
NOUGHT = Decimal(0)


@dataclass(frozen=True, slots=True)
class PortfolioAsked:
    """What a view is asked: ``states``, ``from``, ``to``, ``as_of`` and ``org_node_id``.

    Each absent when the query leaves it out: ``states`` empty for the default, ``as_of`` ``None``
    for the current day.
    """

    states: tuple[ProjectState, ...] = ()
    period_from: date | None = None
    period_to: date | None = None
    as_of: date | None = None
    org_node_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class PortfolioReading:
    """When a view is read, and what the indicators of the day are read from.

    ``at`` is the instant of the reading, read once by the caller, never by the view; ``cache`` is
    the cache of the indicators of the day of the process, none for a process that computes them at
    each reading (EP-10, "Le cache"). A date asked (``as_of``) reads the markings, never the cache.
    """

    at: datetime
    cache: IndicatorsCache | None = None


@dataclass(frozen=True, slots=True)
class PortfolioScope:
    """The scope a view retains (``PortfolioScope``).

    ``period_from`` and ``period_to`` are both null for a view that retains no period,
    ``org_node_label`` without a node.
    """

    states: tuple[ProjectState, ...]
    as_of: date
    period_from: date | None
    period_to: date | None
    org_node_id: UUID | None
    org_node_label: str | None
    project_count: int


@dataclass(frozen=True, slots=True)
class RetainedProject:
    """A project a view retains: its state at the date, the revision it contributes by, its weight.

    ``revision_id`` is, on the current day, the current revision of the project — the revision in
    progress or, without one, the last marked —, and at a past date its last revision marked by the
    end of that day; it is null for a project none of whose revisions was marked by then, which is
    retained by its state and contributes to no sum. ``weight`` is one for a project In progress or
    Completed; for an offer, the probability of winning its revision kept at the marking, or that of
    the project on the current day; null when ``revision_id`` is, and also for an offer whose
    revision retained, marked before EP-07, kept no probability: nothing is taken up nor
    recalculated. ``marked_at`` is the instant of the last marking before the end of the date, null
    for a project none of whose revisions was marked by then: the column ``last_marked_at`` of the
    list (WF-PTF-0040), which is not that of ``revision_id``, a revision in progress on the day.
    ``entered_at`` is the instant of the transition that brought the project to its state at the
    date: for a project In progress, its passage to In progress, where the health of the control
    starts an interval when no revision was marked before the last (WF-PTF-0110).
    """

    state: ProjectState
    revision_id: UUID | None
    weight: Decimal | None
    marked_at: datetime | None = None
    entered_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ResolvedScope:
    """The scope a view gives back, and the projects it retains, by their identifier.

    ``scope.project_count`` is the number of ``projects``; ``on_current_day`` says whether the
    contributions are read for the current day (``day_documents_of``) or kept by the revisions
    retained (``kept_documents_of``). It is true only without ``as_of``: an ``as_of`` equal to the
    current day is a date asked, read by the markings (``AsOf``) — each project by its last revision
    marked by the end of the day, an offer weighing the probability that marking kept, a revision
    in progress ignored.
    """

    scope: PortfolioScope
    projects: Mapping[UUID, RetainedProject]
    on_current_day: bool


def _day_start(day: date) -> datetime:
    """Give the instant a day starts at in the time zone of the installation, in universal time.

    The end of a day is the start of the next: an instant belongs to the day when it is not before
    its start and before its end, as ``current_day`` reads it.
    """
    return datetime.combine(day, time(), tzinfo=TIME_ZONE.zone()).astimezone(UTC)


def period_instants(scope: PortfolioScope) -> tuple[datetime, datetime] | None:
    """Give the instants of the period of a scope: its first day's start, its last day's end.

    What a statistic of the period reads its transitions between, its bounds included
    (WF-CYC-0130): a transition of the last day of the period falls in it, one of the next day not.
    ``None`` for a scope that retains no period.
    """
    if scope.period_from is None or scope.period_to is None:
        return None
    return _day_start(scope.period_from), _day_start(scope.period_to + timedelta(days=1))


def _default_start(as_of: date) -> date:
    """Give the start of the default period: the date minus twelve months, then the next day.

    The 28 February stands in for a 29 February the year before lacks: 4 June 2025 for 3 June
    2026, 1 March 2027 for 29 February 2028 (``PortfolioTo``).
    """
    try:
        year_before = as_of.replace(year=as_of.year - 1)
    except ValueError:
        year_before = as_of.replace(year=as_of.year - 1, day=28)
    return year_before + timedelta(days=1)


def _period(asked: PortfolioAsked, as_of: date) -> tuple[date, date] | FieldError:
    """Give the period asked, each bound absent completed by the default one; or its refusal.

    One rule for every view that takes a period (``PortfolioPeriodRefused``): an end before the
    start given, ``/query/to`` with that start; a start after the end completed — the date of
    calculation —, ``/query/from`` with that end; an end before the start completed, ``/query/to``
    with that start. The bound sent is the one designated, the completed one named.
    """
    start = _default_start(as_of) if asked.period_from is None else asked.period_from
    end = as_of if asked.period_to is None else asked.period_to
    if end >= start:
        return start, end
    if asked.period_from is not None and asked.period_to is None:
        return FieldError(FROM_POINTER, VALUE_OUT_OF_RANGE, {"maximum": end.isoformat()})
    return FieldError(TO_POINTER, VALUE_OUT_OF_RANGE, {"minimum": start.isoformat()})


def _in_period(found: ProjectAtDate, period: tuple[date, date] | None) -> bool:
    """Tell whether a project is retained by the period: Completed, only by a completion in it."""
    if period is None or found.state != COMPLETED:
        return True
    return period[0] <= current_day(found.entered_at) <= period[1]


def _retained(
    found: ProjectAtDate, kept: RetainedRevisions, *, on_current_day: bool
) -> RetainedProject:
    """Give a project retained, with the revision it contributes by and its weight.

    On the current day, its current revision or, without one, its last marked, and, for an offer,
    its probability of winning now; at a past date, its last revision marked by the end of that
    day, and the probability that marking kept (EP-07), never the project's of today (#4025). The
    weight is that of the aggregation (``weight_of``): one for a project In progress or Completed.
    """
    if on_current_day:
        revision_id = kept.current_id or kept.last_marked_id
        probability = found.win_probability
    else:
        revision_id = kept.last_marked_id
        probability = kept.win_probability
    if revision_id is None:
        return RetainedProject(found.state, None, None, kept.marked_at, found.entered_at)
    if probability is None:
        # A marking before EP-07 kept no probability: an offer by it weighs nothing known.
        weight = None if found.state == PRICING else weight_of(found.state, NOUGHT)
    else:
        weight = weight_of(found.state, probability)
    return RetainedProject(found.state, revision_id, weight, kept.marked_at, found.entered_at)


def resolve_scope(
    session: Session,
    asked: PortfolioAsked,
    at: datetime,
    *,
    counted: frozenset[ProjectState],
    period: bool,
) -> ResolvedScope:
    """Resolve what a view is asked at the instant ``at``, with a period if the view retains one.

    ``counted`` is the states the view counts: a state asked outside it stays in ``scope.states``
    and retains no project. Refuses a period inverted or that starts after its default end (422),
    and an unknown node (422), each designated in one refusal.

    The date of calculation is ``as_of``, or the current day of ``at`` in the time zone of the
    installation; without ``as_of`` the contributions are those of the current day, with it those
    the markings kept by the end of that day, the current day included (``AsOf``). A project is
    retained when its state at the date — that of its last transition before the end of the day —
    is both asked and counted. ``period`` false, the view retains no period: ``from`` and ``to``
    are not read, and the scope gives none. A project Completed at the date is then retained if
    and only if ``completed`` is both counted and asked: whether a view without a period — the list
    read without ``from`` nor ``to`` — counts it is the view's choice, by ``counted``; the list
    does not (#4020, decided on 2026-11-19 by the author: no period in which it would have been
    completed). With a period, it is retained only when its completion falls in the period,
    its bounds included (``PortfolioStates``, G-05).
    """
    as_of = current_day(at) if asked.as_of is None else asked.as_of
    on_current_day = asked.as_of is None
    states: tuple[ProjectState, ...] = tuple(dict.fromkeys(asked.states)) or DEFAULT_STATES
    faults: list[FieldError] = []
    bounds = _period(asked, as_of) if period else None
    if isinstance(bounds, FieldError):
        faults.append(bounds)
        bounds = None
    node_id = asked.org_node_id
    label = None if node_id is None else node_labels(session, {node_id}).get(node_id)
    if node_id is not None and label is None:
        faults.append(FieldError(ORG_NODE_POINTER, UNKNOWN_ORG_NODE))
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    end = _day_start(as_of + timedelta(days=1))
    wanted: list[ProjectState] = [state for state in states if state in counted]
    found = projects_in_states_on(session, wanted, None if on_current_day else end)
    found = {key: each for key, each in found.items() if _in_period(each, bounds)}
    kept = last_marked_at_instant(session, list(found), end)
    projects = {
        key: _retained(each, kept[key], on_current_day=on_current_day)
        for key, each in found.items()
    }
    scope = PortfolioScope(
        states=states,
        as_of=as_of,
        period_from=None if bounds is None else bounds[0],
        period_to=None if bounds is None else bounds[1],
        org_node_id=node_id,
        org_node_label=label,
        project_count=len(projects),
    )
    return ResolvedScope(scope, projects, on_current_day)
