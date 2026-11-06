# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The categories of cost of the witness, each under its nature.

``volume/cost_categories.json``; the category of provision of the bootstrap stays.

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
