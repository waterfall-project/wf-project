# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projects of the witness, and the local accounts of their contributors.

``projects.json`` and ``project.json``: the local accounts of Waterfall alone, which never
sign in, then PRJ-002 and PRJ-001 with their client, at the instants of the chronology.

Empty until US-0920/L1 fills it: it writes nothing.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    del session, witness
    return False
