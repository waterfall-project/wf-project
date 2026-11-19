# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of several projects the portfolio retains at an instant (EP-11, US-2670).

At a past date, a project contributes by its last revision marked before the end of that day, in
the time zone of the installation; on the current day, by its current revision or, without one, by
its last marked (WF-PTF-0010, WF-IND-0010). Both are read for every project of a scope in one query
(EP-11, "La contribution d'un projet"), with the probability of winning the last marked kept, the
weight of an offer at a past date (EP-07).

Declared by US-2670/L1, the socle of EP-11; filled by US-2670/L3.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from waterfall.core.revisions.tables import Revision

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class RetainedRevisions:
    """The last revision of a project marked before an instant, its marking, and its current one.

    ``last_marked_id``, ``marked_at`` and ``win_probability`` — the probability of winning that
    marking kept (``Revision.win_probability``) — are null for a project none of whose revisions
    was marked before the instant; ``current_id`` for one that has no current revision.
    ``win_probability`` is null too for a revision marked before EP-07, which kept none.
    """

    last_marked_id: UUID | None
    marked_at: datetime | None
    win_probability: Decimal | None
    current_id: UUID | None


def last_marked_at_instant(
    session: Session, project_ids: Collection[UUID], before: datetime
) -> dict[UUID, RetainedRevisions]:
    """Give, for each project, its last revision marked before ``before`` and its current one.

    Every project asked has its entry, empty for one that has neither. Two markings of one instant
    are ordered by identifier, as the indicators order them. One query for all the projects: their
    current revisions and their revisions marked before the instant, the latest kept.
    """
    if not project_ids:
        return {}
    rows = session.execute(
        select(
            Revision.project_id,
            Revision.id,
            Revision.status,
            Revision.marked_at,
            Revision.win_probability,
        )
        .where(
            Revision.project_id.in_(list(project_ids)),
            or_(
                Revision.status == "draft",
                (Revision.status == "marked") & (Revision.marked_at < before),
            ),
        )
        .order_by(Revision.marked_at.asc().nulls_first(), Revision.id.asc())
    )
    current: dict[UUID, UUID] = {}
    # Ascending: the last marked row of a project is its latest.
    marked: dict[UUID, tuple[UUID, datetime | None, Decimal | None]] = {}
    for row in rows:
        if row.status == "draft":
            current[row.project_id] = row.id
        else:
            marked[row.project_id] = (row.id, row.marked_at, row.win_probability)
    return {
        project_id: RetainedRevisions(
            *marked.get(project_id, (None, None, None)), current.get(project_id)
        )
        for project_id in project_ids
    }
