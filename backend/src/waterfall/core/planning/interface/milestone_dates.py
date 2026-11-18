# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The dates of the milestones as the time/time diagram reads them (WF-IND-0090; US-1710).

The lineages inscribed in the time/time tracking (``tracked_milestones``, US-1400/L2), and the
finish of each lineage in each revision named (``milestone_forecasts``): the lines of ``task`` of a
marked revision do not change (WF-DAT-0030), so nothing is kept for the diagram (EP-10, "Ce que le
cadrage décide"). A lineage absent from a revision has no date there.

Declared by US-1660/L3, the only lot of EP-10 that writes the ``__init__`` of the planning; filled
by US-1710. An inscription stays on a task that has ceased to be a milestone (a duration given
since, subtasks), ``setNodeTracking`` judging it at its entry alone (#2498): nothing is purged
here, the diagram keeps the inscriptions of the milestones as the revision of the day reads them.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.planning.tables import Node, Task, TrackingEntry
from waterfall.core.revisions.interface import aimed_structure

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

MILESTONE_TRACKING = "milestone_tracking"
TASK = "task"


def tracked_milestones(session: Session, project_id: UUID) -> tuple[UUID, ...]:
    """Give the lineages of the project inscribed in the time/time tracking, in a stable order.

    The inscriptions are kept by lineage (WF-PLA-0060): none says whether the task is a milestone
    now; the reader keeps those that are, in the revision it reads.
    """
    return tuple(
        session.scalars(
            select(TrackingEntry.lineage_id)
            .where(TrackingEntry.project_id == project_id, TrackingEntry.kind == MILESTONE_TRACKING)
            .order_by(TrackingEntry.created_at, TrackingEntry.id)
        )
    )


def milestone_forecasts(
    session: Session,
    project_id: UUID,
    lineage_ids: Collection[UUID],
    revision_ids: Collection[UUID],
) -> Mapping[UUID, Mapping[UUID, date]]:
    """Give, by revision named, the finish of each lineage named that the revision holds.

    Read on the main structure of each revision; a revision without one, and a lineage a revision
    does not hold, have no entry.
    """
    forecasts: dict[UUID, dict[UUID, date]] = defaultdict(dict)
    if not lineage_ids:
        return forecasts
    for revision_id in revision_ids:
        structure_id = aimed_structure(session, project_id, revision_id, None)
        if structure_id is None:
            continue
        rows = session.execute(
            select(Node.lineage_id, Task.finish_date)
            .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
            .where(
                Node.project_id == project_id,
                Node.revision_id == revision_id,
                Node.structure_id == structure_id,
                Node.kind == TASK,
                Node.lineage_id.in_(lineage_ids),
            )
        )
        for lineage_id, finish in rows:
            forecasts[revision_id][lineage_id] = finish
    return forecasts
