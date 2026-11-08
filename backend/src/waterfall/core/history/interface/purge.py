# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge of the history: the entries of the old sessions, and the plans of a paste expired.

``waterfall-worker purge`` calls it in its transaction (EP-06, "La purge"): it removes the entries
of a session older than ``WATERFALL_UNDO_RETENTION_HOURS`` and the plans past their hour. A session
of the realm lives twelve hours at most: an entry written before ``before`` is of a session over,
whose ``sid`` no request carries any more, and the stack it belongs to is wholly of that session.

Declared by US-1380/L1; filled by US-1450/L1.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete

from waterfall.core.history.tables import PastePlan, UndoEntry

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


def purge(session: Session, *, before: datetime, now: datetime) -> None:
    """Remove the entries written before ``before``, and the plans expired at ``now``.

    Both moments are named at the call: two dates of one type, which an order would let swap.
    """
    session.execute(delete(UndoEntry).where(UndoEntry.created_at < before))
    session.execute(delete(PastePlan).where(PastePlan.expires_at <= now))
