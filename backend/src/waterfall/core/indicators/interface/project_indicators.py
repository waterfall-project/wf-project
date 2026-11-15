# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The earned value indicators of a project, on a scope (``getProjectIndicators``; US-1660).

The reference budget, the planned value, the earned value, the actual cost and the remaining to
commit at the date of the computation, the progresses and the consumption, the two indices and
their variances, the three projections (WF-IND-0010 to WF-IND-0080): computed on the current day
(US-1660/L3), or read as a marking kept them, for a marked revision named or at a date
(US-1670/L2). The zones are classified at the reading, on the thresholds of the day; a project
before In progress is refused (409).

Declared by US-1660/L1, the socle of EP-10.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.interface.reading import IndicatorsReading


def project_indicators(session: Session, project_id: UUID, asked: IndicatorsReading) -> Document:
    """Give the indicators of a project on the scope and for the revision a reading asks."""
    msg = "project_indicators is filled by US-1660/L3"
    raise NotImplementedError(msg)
