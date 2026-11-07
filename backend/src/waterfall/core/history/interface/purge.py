# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge of the history: the entries of the old sessions, and the plans of a paste expired.

``waterfall-worker purge`` calls it in its transaction (EP-06, "La purge"): it removes the entries
of a session older than ``WATERFALL_UNDO_RETENTION_HOURS`` and the plans past their hour.

Declared by US-1380/L1, without effect until US-1450/L1 keeps entries and plans.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


def purge(session: Session, before: datetime) -> None:
    """Remove the entries of the sessions begun before ``before``, and the plans expired.

    Nothing is kept before US-1450/L1.
    """
    del session, before
