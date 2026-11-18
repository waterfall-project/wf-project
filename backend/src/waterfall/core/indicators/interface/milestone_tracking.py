# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time/time diagram of a project (``getMilestoneTracking``; US-1710).

For each milestone inscribed in the tracking, the finish each revision that kept the indicators of
the project forecast, by its marking, up to its completion, then the point of the current day or of
its completion (WF-IND-0090). A project before In progress is refused (409).

Nothing is kept for the diagram: the dates of a milestone in a marked revision are lines of ``task``
that do not change (WF-DAT-0030), read by lineage (``milestone_forecasts``). The revision of the
day — the current one, else the last marked — gives the milestones, their ``label`` and their
``completed_on``: a lineage inscribed that is no milestone there (a duration given since, subtasks)
is not rendered, its inscription left as it is (#2498); a milestone completed then reopened is not
completed, and receives the point of the day again (WF-RAE-0030). A revision marked is read when it
kept the indicators of the project, which only a project In progress does (US-1670/L1), and up to
the completion of the milestone: the point of a marking on the day of the completion or after it
would stand to the right of the last point, which is that day at midnight, in universal time.

Declared by US-1660/L1, the socle of EP-10; ``at`` is the instant of the computation, read by the
caller.
"""

from datetime import UTC, date, datetime, time
from typing import TYPE_CHECKING, Any

from waterfall.core.indicators.interface.project_indicators import current_day_reading
from waterfall.core.indicators.interface.stored_documents import kept_revisions
from waterfall.core.indicators.shaping import context_document, instant
from waterfall.core.planning.interface import (
    milestone_forecasts,
    tasks_for_indicators,
    tracked_milestones,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.planning.interface import IndicatorTask

COMPLETED = "completed"


def _point(marked_at: datetime, forecast: date) -> dict[str, str]:
    return {"marked_at": instant(marked_at), "forecast_date": forecast.isoformat()}


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _milestone(
    task: IndicatorTask,
    kept: list[tuple[UUID, datetime]],
    forecasts: Mapping[UUID, Mapping[UUID, date]],
    at: datetime,
) -> dict[str, Any]:
    """Draw a milestone: a point by marking that holds it, then its completion or the day."""
    done = task.completed_on if task.progress == COMPLETED else None
    points: list[dict[str, str]] = []
    for revision_id, marked_at in kept:
        if done is not None and marked_at >= _midnight(done):
            break
        found = forecasts.get(revision_id, {}).get(task.lineage_id)
        if found is not None:
            points.append(_point(marked_at, found))
    if done is not None:
        points.append(_point(_midnight(done), done))
    else:
        points.append(_point(at, task.finish.day))
    return {
        "lineage_id": str(task.lineage_id),
        "label": task.label,
        "completed_on": None if done is None else done.isoformat(),
        "points": points,
    }


def milestone_tracking(session: Session, project_id: UUID, at: datetime) -> Document:
    """Give the forecast finishes of the tracked milestones of a project, by marking."""
    reading = current_day_reading(session, project_id, at)
    tracked = set(tracked_milestones(session, project_id))
    tasks = [
        each
        for each in tasks_for_indicators(session, project_id, reading.basis.revision_id)
        if each.is_milestone and each.lineage_id in tracked
    ]
    kept = kept_revisions(session, project_id)
    forecasts = milestone_forecasts(
        session, project_id, [each.lineage_id for each in tasks], [each for each, _ in kept]
    )
    return {
        "context": context_document(reading.context),
        "milestones": [_milestone(each, kept, forecasts, at) for each in tasks],
    }
