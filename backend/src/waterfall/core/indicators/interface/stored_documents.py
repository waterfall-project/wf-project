# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A document a marked revision kept, read as it was kept (WF-DAT-0040; US-1670/L2).

What the readings of a marked revision answer: those of EP-10, and those of the indicators of the
estimate (EP-07) and of the remaining to commit (EP-09), which keep their computation for the
current revision (EP-10, "La conservation au marquage"). None for a kind and a scope the marking
did not keep: the indicators of the project, for a revision marked before In progress.

Declared by US-1660/L1, the socle of EP-10.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.interface.documents import Document, IndicatorKind


def stored_document(
    session: Session, revision_id: UUID, kind: IndicatorKind, scope: CostScope
) -> Document | None:
    """Give the document of a kind and a scope a revision kept at its marking, or none."""
    msg = "stored_document is filled by US-1670/L2"
    raise NotImplementedError(msg)
