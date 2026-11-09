# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit, and the coverage of the risks they show (US-1600).

``remaining_of_revision`` sums the reestimated amounts of the lines, not provisions, of the tasks
not completed of the main structure of a revision, at the state of its tasks, and gives each line's
— what the indicators read, and EP-10 for the projection of the project manager and the index of
cost. ``remaining_indicators`` reads the indicators of a revision (``getRemainingIndicators``),
their coverage of the risks by ``risk_coverage`` (EP-09, "Les indicateurs du reste à engager").

The coverage is a registry the estimate declares and the risks fill (``register_coverage``, EP-08):
until then none is registered, and the coverage is zero — no reserve, no provision left, no cost of
a risk occurred, no variance —, what is true of a project without risk.

Declared by US-1580/L1, the coverage served from then on; the two functions raise
``NotImplementedError`` naming US-1600, which fills them and gives ``remaining_indicators`` its
result.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class RevisionRemaining:
    """The remaining to commit of a revision: its total, and each line's, by its node."""

    total: Decimal
    by_line: Mapping[UUID, Decimal]


@dataclass(frozen=True, slots=True)
class Coverage:
    """The coverage of the risks of a revision (``RiskCoverageTotals``, WF-RIS-0050)."""

    reserve: Decimal
    remaining_provisions: Decimal
    occurred_cost: Decimal
    occurred_reestimated: Decimal
    coverage_variance: Decimal


ZERO = Decimal("0.00")
NO_COVERAGE = Coverage(ZERO, ZERO, ZERO, ZERO, ZERO)

# What answers the coverage of the risks of a revision of a project: one at most, the risks'.
_COVERAGE: Registry[Callable[[Session, UUID, UUID], Coverage]] = Registry("estimate.coverage")


def register_coverage(cover: Callable[[Session, UUID, UUID], Coverage]) -> Callable[[], None]:
    """Add what answers the coverage of the risks; give its withdrawal; refused if one answers."""
    if _COVERAGE.entries():
        msg = "the coverage of the risks has its answer already"
        raise ValueError(msg)
    return _COVERAGE.register(cover)


def risk_coverage(session: Session, project_id: UUID, revision_id: UUID) -> Coverage:
    """Give the coverage of the risks of a revision of a project: zero while nothing answers."""
    held = _COVERAGE.entries()
    return held[0](session, project_id, revision_id) if held else NO_COVERAGE


def remaining_of_revision(session: Session, revision_id: UUID) -> RevisionRemaining:
    """Give the remaining to commit of a revision, total and by line, at the state of its tasks."""
    msg = "remaining_of_revision is filled by US-1600"
    raise NotImplementedError(msg)


def remaining_indicators(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Give the indicators of the remaining to commit of a revision (``getRemainingIndicators``)."""
    msg = "remaining_indicators is filled by US-1600"
    raise NotImplementedError(msg)
