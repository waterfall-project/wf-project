# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk deleted (``deleteRisk``; US-2590).

A risk no marked revision cites yet is deleted with its own estimate and its provision line, in
the current revision, created if need be, at the counter read; one a marked revision cites is
dismissed by a review instead, and an occurred one is never deleted (WF-RIS-0020).

Declared by US-2550/L1, the socle of EP-08; filled by US-2590/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer


@dataclass(frozen=True, slots=True)
class RiskDeletion:
    """A risk to delete, and the counter its caller read (``deleteRisk``)."""

    risk_id: UUID
    lock_version: int


def delete_risk(
    session: Session, project_id: UUID, deletion: RiskDeletion, writer: Writer, viewer: Viewer
) -> None:
    """Delete a risk no marked revision cites, with its own estimate and its provision line."""
    msg = "delete_risk is filled by US-2590/L1"
    raise NotImplementedError(msg)
