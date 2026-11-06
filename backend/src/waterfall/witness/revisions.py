# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of the projects of the witness, and the events of their chronology.

``revisions.json``, in the order and at the instants of the chronology: the revision 100
opened (Created to Pricing), its marking, the 101 opened, the designation of 100 tried and
refused, the code entered, the 101 marked, the 102 opened.

Empty until US-0960, US-0970 and US-0980 fills it: it writes nothing.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    del session, witness
    return False
