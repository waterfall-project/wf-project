# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The timelines of the project of the witness, before its revisions.

``timelines.json``: the two timelines of PRJ-001, under the identifiers the examples give them,
loaded after the work breakdown and before the revisions, so that the inscriptions of the tasks
find them (EP-06, "Le chargeur du témoin").

Declared by US-1380/L1, an empty slice that writes nothing; US-1400/L1 fills it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it: nothing yet, so ``False``."""
    del session, witness
    return False
