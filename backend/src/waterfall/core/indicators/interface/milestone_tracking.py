# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time/time diagram of a project (``getMilestoneTracking``; US-1710).

For each milestone inscribed in the tracking, the finish each revision that kept the indicators of
the project forecast, by its marking, up to its completion, then the point of the current day or of
its completion (WF-IND-0090). A project before In progress is refused (409).

Declared by US-1660/L1, the socle of EP-10; ``at`` is the instant of the computation, read by the
caller.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document


def milestone_tracking(session: Session, project_id: UUID, at: datetime) -> Document:
    """Give the forecast finishes of the tracked milestones of a project, by marking."""
    msg = "milestone_tracking is filled by US-1710"
    raise NotImplementedError(msg)
