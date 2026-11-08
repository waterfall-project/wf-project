# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge of the exchanges: the imports expired, the deposits expired, the exports old.

``waterfall-worker purge`` calls ``purge`` in its transaction (EP-06, "La purge"): it moves to
``expired`` the imports ``analysed`` whose report expired, deletes the rows of the deposits expired
— those of EP-03 included — and marks consumed the results of the exports of more than twenty-four
hours, and gives what the storage must lose. The worker hands it to ``remove_purged`` once the
transaction is validated, as EP-03 deletes its deposits: an object is never deleted for a row a
failed transaction keeps.

Declared by US-1380/L1, without effect until US-1420/L2 fills it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.platform.storage import Bucket


@dataclass(frozen=True, slots=True)
class Purged:
    """What the storage loses once a purge is validated.

    ``objects`` the keys of the files of the imports and of the exports, and of the deposits
    completed; ``deposits`` the key and the deposit of each deposit left in parts, to abort.
    """

    objects: tuple[str, ...] = ()
    deposits: tuple[tuple[str, str], ...] = ()


def purge(session: Session, now: datetime) -> Purged:
    """Purge the rows that expired at ``now``, and give what the storage must lose.

    Nothing until US-1420/L2.
    """
    del session, now
    return Purged()


def remove_purged(bucket: Bucket, purged: Purged) -> None:
    """Delete from the storage what a purge validated gave, after its transaction.

    Nothing until US-1420/L2, which gives the worker the bucket.
    """
    del bucket, purged
