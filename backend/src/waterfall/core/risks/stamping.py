# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The stamp of the risks of a project, which the key of the cache of the indicators reads.

Private to the module; ``interface.risks`` offers it.

The number of the risks of the project and the sum of their counters: a risk declared or deleted
moves the first, a review, an occurrence, a change of its identity or of its provision the second
(``Risk.lock_version`` advances at each, under the lock of the risk). The indicators read the lines
and the structures the risks write, and these two numbers say that a risk changed even where no
line did (EP-08, "Les indicateurs et le cache"; US-2630/L1, #3629).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.risks.tables import Risk

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class RisksStamp:
    """How many risks a project holds, and the sum of their counters."""

    count: int
    versions: int


def stamp_of_risks(session: Session, project_id: UUID) -> RisksStamp:
    """Give the number of the risks of a project and the sum of their counters, in one statement."""
    count, versions = session.execute(
        select(func.count(), func.coalesce(func.sum(Risk.lock_version), 0)).where(
            Risk.project_id == project_id
        )
    ).one()
    return RisksStamp(count, int(versions))
