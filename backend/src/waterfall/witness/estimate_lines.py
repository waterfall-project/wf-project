# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the revisions of the witness: the estimate of each revision, after its tasks.

Registered by ``register_revision_filler`` (``chronology``), after the tasks: once the slice of the
revisions opens a revision of PRJ-001 — 100, 101, 102 — and its tasks are written, before the next
event marks it, it reconciles by lineage the lines the copy gave the revision with those
``witness_lines.json`` describes for it — created, changed, deleted — through the interface of the
estimate, at the identifiers and the instant imposed (EP-07, "Le chargeur du témoin"). The amounts
are those the service computes.

Declared by US-1490/L1, it writes nothing; US-1570 fills it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness
    from waterfall.witness.revisions import OpenedRevision


def fill(session: Session, witness: Witness, opened: OpenedRevision) -> None:
    """Write the lines the witness describes for a revision just opened: none yet."""
    del session, witness, opened
