# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge of the exchanges: the imports expired, the deposits expired, the exports old.

``waterfall-worker purge`` calls it in its transaction (EP-06, "La purge"): it moves to ``expired``
the imports ``analysed`` whose report expired, deletes the deposits expired and the exports of more
than twenty-four hours, their objects deleted after the transaction.

Declared by US-1380/L1, without effect until US-1420/L2 fills it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


def purge(session: Session, now: datetime) -> None:
    """Purge what expired at ``now``: nothing until US-1420/L2."""
    del session, now
