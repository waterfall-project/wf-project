# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The plans of a paste: kept by ``previewPaste``, read and dropped by ``applyPaste``.

A plan keeps the block judged, the target and the counter of the structure, for an hour (EP-06,
"L'historique annulable et le collage"); the planning judges and applies it, the history keeps it
without reading any table of the planning.

Declared by US-1380/L1; US-1450/L1 fills it, and gives each its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def keep_plan(session: Session, revision_id: UUID, user_account_id: UUID) -> None:
    """Keep the plan of a paste of an account in a revision, and give it its identifier."""
    msg = "keep_plan is filled by US-1450/L1"
    raise NotImplementedError(msg)


def read_plan(session: Session, plan_id: UUID, user_account_id: UUID) -> None:
    """Read the plan of a paste its account kept, unless it expired."""
    msg = "read_plan is filled by US-1450/L1"
    raise NotImplementedError(msg)


def drop_plan(session: Session, plan_id: UUID) -> None:
    """Drop the plan of a paste once applied."""
    msg = "drop_plan is filled by US-1450/L1"
    raise NotImplementedError(msg)
