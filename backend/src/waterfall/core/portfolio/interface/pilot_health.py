# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The health of the control of the projects (``getPortfolioPilotHealth``; US-2750).

Four signals on the projects In progress: the review overdue on the delay of the reference
settings, the risks not reviewed (``not_reviewed_since``), no cost imported since the last marked
revision (``last_imports``), the tracked milestone overdue (``portfolio_milestones``); their zone,
their parameters and ``can_open`` (WF-PTF-0110, WF-REF-0180).

Only the projects In progress contribute: another state a request names, Completed included, has no
effect, and the view retains no period (``resolve_scope``, #1714). The delay is that of the
reference settings at the instant of the reading, a delay changed changing the signals at the next
one. The
risks and the costs are judged over the interval of the last marked revision of each project: from
the marking before it, or from the passage to In progress without one, to that marking (WF-PTF-0110,
specification 1.0.7). A past date reads the last marking by the end of that day, and the milestones
the marking kept.

Declared by US-2670/L1, the socle of EP-11; filled by US-2750.
"""

from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.costs.interface import last_imports
from waterfall.core.portfolio.contributing import MILESTONES
from waterfall.core.portfolio.documents import documents_of
from waterfall.core.portfolio.interface.scope import resolve_scope
from waterfall.core.portfolio.shaping import scope_document
from waterfall.core.portfolio.signalling import (
    MILESTONE_OVERDUE,
    NO_ACTUAL_COST,
    REVIEW_OVERDUE,
    RISKS_NOT_REVIEWED,
    overdue_milestones,
    review_interval,
    signal,
    weeks_overdue,
)
from waterfall.core.portfolio.states import IN_PROGRESS
from waterfall.core.projects.interface import openable, projects_named
from waterfall.core.revisions.interface import marked_revisions_of
from waterfall.core.risks.interface import ReviewWindow, not_reviewed_since

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked, PortfolioReading
    from waterfall.core.portfolio.signalling import ReviewInterval
    from waterfall.core.projects.interface import ProjectState, Viewer

COUNTED: frozenset[ProjectState] = frozenset({IN_PROGRESS})


def read_pilot_health(
    session: Session, asked: PortfolioAsked, reading: PortfolioReading, viewer: Viewer
) -> Document:
    """Give the signals of the projects of the scope read by ``reading``, by project then by code.

    The projects in the order of their identifier, each one's signals in the order of the contract:
    the review overdue, the risks not reviewed, no actual cost imported, then its overdue milestones
    in the order of the plan. A project with no marked revision by the date gives none: there is no
    last marking to judge. Refuses an unknown node as every view of the portfolio does (422).
    """
    resolved = resolve_scope(session, asked, reading.at, counted=COUNTED, period=False)
    as_of = resolved.scope.as_of
    identifiers = sorted(resolved.projects)
    names = projects_named(session, identifiers)
    can_open = openable(session, identifiers, viewer)
    delay = read_reference_settings(session).max_weeks_between_reviews
    markings = marked_revisions_of(session, identifiers)
    intervals: dict[UUID, ReviewInterval] = {}
    for project_id in identifiers:
        retained = resolved.projects[project_id]
        interval = review_interval(markings[project_id], retained.marked_at, retained.entered_at)
        if interval is not None:
            intervals[project_id] = interval
    unreviewed = not_reviewed_since(
        session, {each: ReviewWindow(it.revision_id, it.start) for each, it in intervals.items()}
    )
    imported = last_imports(session, {each: it.end for each, it in intervals.items()})
    documents = documents_of(session, resolved, reading, (MILESTONES,))
    signals: list[Document] = []
    for project_id in identifiers:
        if project_id not in names:
            continue
        label = names[project_id][1]
        interval = intervals.get(project_id)
        if interval is None:
            continue

        raised: list[tuple[str, Document | None]] = []
        weeks = weeks_overdue(interval.end, as_of, delay)
        if weeks is not None:
            raised.append((REVIEW_OVERDUE, {"weeks_since_last_mark": weeks}))
        if project_id in unreviewed:
            raised.append((RISKS_NOT_REVIEWED, None))
        last = imported.get(project_id)
        if last is None or last < interval.start:
            raised.append((NO_ACTUAL_COST, None))
        held = documents.get(project_id, {}).get(MILESTONES)
        raised.extend((MILESTONE_OVERDUE, each) for each in overdue_milestones(held, as_of))
        signals.extend(
            signal(project_id, label, can_open=project_id in can_open, code=code, params=params)
            for code, params in raised
        )
    return {"scope": scope_document(resolved.scope), "signals": signals}
