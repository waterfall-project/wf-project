# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The inscriptions of a task, by its lineage, to the timelines and to the time/time tracking.

``setNodeTracking`` replaces the inscriptions of a task, kept by its lineage so that they follow it
from revision to revision (WF-PLA-0060, WF-PLA-0140; EP-06, US-1400).

Declared by US-1380/L1; US-1400/L2 fills it, and gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def set_node_tracking(session: Session, project_id: UUID, node_id: UUID, act: Act) -> None:
    """Replace the inscriptions of a task (``setNodeTracking``)."""
    msg = "set_node_tracking is filled by US-1400/L2"
    raise NotImplementedError(msg)
