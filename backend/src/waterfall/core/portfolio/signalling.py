# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rules of the four signals of the health of the control, without a database (WF-PTF-0110).

Not a part of the interface of the portfolio: the view reads through it. A rule is a function of
what the view has read — the markings of a project, a document of milestones, the delay of the
reference settings — and of the date of calculation, passed in, never read from a clock.
"""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from waterfall.core.portfolio.aggregation import ALERT, WATCH
from waterfall.core.projects.interface import current_day

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from uuid import UUID

    from waterfall.core.indicators.interface import Document

REVIEW_OVERDUE = "review_overdue"
RISKS_NOT_REVIEWED = "risks_not_reviewed"
NO_ACTUAL_COST = "no_actual_cost_since_last_review"
MILESTONE_OVERDUE = "contractual_milestone_overdue"
DAYS_IN_A_WEEK = 7


@dataclass(frozen=True, slots=True)
class ReviewInterval:
    """The interval the risks and the costs of a project are judged over: its last marked revision.

    From the marking before the last, or from the passage to In progress without one, to the last
    marking (WF-PTF-0110, specification 1.0.7).
    """

    revision_id: UUID
    start: datetime
    end: datetime


def review_interval(
    markings: Sequence[tuple[UUID, datetime]],
    marked_at: datetime | None,
    entered_at: datetime | None,
) -> ReviewInterval | None:
    """Give the interval of the last marked revision of a project, or none if it has no marking.

    ``markings`` are the marked revisions of the project, the oldest first; those after
    ``marked_at``, the last marking at the date of calculation, are not read. None too for a project
    with a single marking whose passage to In progress is not known.
    """
    if marked_at is None:
        return None
    seen = [each for each in markings if each[1] <= marked_at]
    if not seen:
        return None
    revision_id, end = seen[-1]
    start = seen[-2][1] if len(seen) > 1 else entered_at
    return None if start is None else ReviewInterval(revision_id, start, end)


def weeks_overdue(marked_at: datetime, as_of: date, delay_weeks: int) -> int | None:
    """Give the whole weeks elapsed since a marking if they exceed the delay, else none.

    The delay is exceeded when the days elapsed — from the day of the marking, in the time zone of
    the installation, to the date of calculation — are more than that many weeks of seven days.
    """
    days = (as_of - current_day(marked_at)).days
    return days // DAYS_IN_A_WEEK if days > delay_weeks * DAYS_IN_A_WEEK else None


def overdue_milestones(document: Document | None, as_of: date) -> list[Document]:
    """Give the milestones of a document whose reference date is passed and that is not completed.

    In the order of the document, the plan's: each with its lineage, its label and its reference
    date. A milestone the reference does not date is none that is overdue.
    """
    if document is None:
        return []
    return [
        {
            "lineage_id": each["lineage_id"],
            "milestone_label": each["label"],
            "reference_date": each["reference_date"],
        }
        for each in document["milestones"]
        if each["reference_date"] is not None
        and each["completed_on"] is None
        and date.fromisoformat(each["reference_date"]) < as_of
    ]


def signal(
    project_id: UUID, label: str, *, can_open: bool, code: str, params: Document | None = None
) -> Document:
    """Write a signal of the contract: its project, its zone by its code, its parameters if any.

    The zone is alert for an overdue milestone, watch for the three others (WF-PTF-0110).
    """
    written: Document = {
        "project_id": str(project_id),
        "project_label": label,
        "can_open": can_open,
        "zone": ALERT if code == MILESTONE_OVERDUE else WATCH,
        "code": code,
    }
    if params is not None:
        written["params"] = params
    return written
