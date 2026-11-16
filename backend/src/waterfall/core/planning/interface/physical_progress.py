# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The physical progress of the summary tasks, which the planning asks the indicators (US-1680).

A registry of this module (EP-10, "Les points d'extension"), filled by the indicators at the import
of their interface: the reading of the facet task asks it, at once, for the summaries it gives, and
sets ``TaskFacet.physical_progress``; none while nothing answers.

Declared by US-1660/L3, the only lot of EP-10 that writes the ``__init__`` of the planning; filled
by US-1680.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

# What gives, of the summary tasks of a revision named, the physical progress of each, none for one
# whose subtree bears no budgeted amount.
type PhysicalProgress = Callable[[Session, UUID, Collection[UUID]], Mapping[UUID, Decimal | None]]


def register_physical_progress(progress: PhysicalProgress) -> Callable[[], None]:
    """Add what gives the physical progress of the summary tasks; give its withdrawal."""
    msg = "register_physical_progress is filled by US-1680"
    raise NotImplementedError(msg)
