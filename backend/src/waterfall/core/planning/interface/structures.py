# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The dates of a structure: the engine replayed on it, its start date and its label written.

``reschedule`` runs the engine (``scheduling``, pure) on a whole structure under its lock, writes
the dates and the floats that change and moves ``scheduled_at`` on (EP-06, "Modules"): every write
of a node calls it (US-1380/L2). ``update_cost_structure`` writes the date the planning of a
structure starts on and its label (``updateCostStructure``, #2170; US-1390/L2).

Declared by US-1380/L1; each story gives its function its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def reschedule(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Replay the engine on a structure locked, and write what changes."""
    msg = "reschedule is filled by US-1380/L2"
    raise NotImplementedError(msg)


def update_cost_structure(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Write the start date and the label of a structure, and redate it."""
    msg = "update_cost_structure is filled by US-1390/L2"
    raise NotImplementedError(msg)
