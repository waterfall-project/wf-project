# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The natures of cost of the witness.

``cost_types.json``; the nature of provision of the bootstrap stays, those of the witness are
added.

Empty until US-0820 fills it: it writes nothing.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    del session, witness
    return False
