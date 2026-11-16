# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The dates of the milestones as the time/time diagram reads them (WF-IND-0090; US-1710).

The lineages inscribed in the time/time tracking (``tracked_milestones``, US-1400/L2), and the
finish of each lineage in each revision named (``milestone_forecasts``): the lines of ``task`` of a
marked revision do not change (WF-DAT-0030), so nothing is kept for the diagram (EP-10, "Ce que le
cadrage décide"). A lineage absent from a revision has no date there.

Declared by US-1660/L3, the only lot of EP-10 that writes the ``__init__`` of the planning; filled
by US-1710.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session


def tracked_milestones(session: Session, project_id: UUID) -> tuple[UUID, ...]:
    """Give the lineages of the milestones of a project inscribed in the time/time tracking."""
    msg = "tracked_milestones is filled by US-1710"
    raise NotImplementedError(msg)


def milestone_forecasts(
    session: Session,
    project_id: UUID,
    lineage_ids: Collection[UUID],
    revision_ids: Collection[UUID],
) -> Mapping[UUID, Mapping[UUID, date]]:
    """Give, by revision named, the finish of each lineage named that the revision holds."""
    msg = "milestone_forecasts is filled by US-1710"
    raise NotImplementedError(msg)
