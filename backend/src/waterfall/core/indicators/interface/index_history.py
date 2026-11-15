# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evolution of the indices of a project (``getIndexHistory``; US-1700).

For each scope, or the one asked for, a point by revision that kept the indicators of the project
at its marking, by its marking, then the point of the current day; the thresholds of the day
(WF-IND-0130, WF-REF-0170). A project before In progress is refused (409).

Declared by US-1660/L1, the socle of EP-10; ``scope`` none gives every scope, ``at`` is the instant
of the computation, read by the caller.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.interface.documents import Document


def index_history(
    session: Session, project_id: UUID, scope: CostScope | None, at: datetime
) -> Document:
    """Give the evolution of the cost and schedule indices of a project, by scope."""
    msg = "index_history is filled by US-1700"
    raise NotImplementedError(msg)
