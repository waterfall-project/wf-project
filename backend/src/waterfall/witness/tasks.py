# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of the revisions of the witness: the content of each revision, between its events.

Registered by ``register_revision_filler`` (``chronology``): after the slice of the revisions opens
a revision of PRJ-001 — 100, 101, 102 — and before the next event marks it, it reconciles by
lineage the tasks the copy gave the revision with those ``witness_tasks.json`` describes for it —
created, changed, deleted, their links, their states, their inscriptions, the date the planning of
the structure starts on — through the interface of the planning, at the identifiers and the instant
imposed (EP-06, "Le chargeur du témoin"). The dates are those the engine computes.

Declared by US-1380/L1, it writes nothing; US-1400/L2 fills the inscriptions, US-1480/L2 the rest.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness
    from waterfall.witness.revisions import OpenedRevision


def fill(session: Session, witness: Witness, opened: OpenedRevision) -> None:
    """Write the tasks the witness describes for a revision just opened: none yet."""
    del session, witness, opened
