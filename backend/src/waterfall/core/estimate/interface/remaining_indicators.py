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

Declared by US-1580/L1 with their arguments and their results, the coverage served from then on;
``remaining_of_revision`` filled by US-1580/L2 (EP-09, "Ce que le cadrage laisse à EP-10"; #2708),
``remaining_indicators`` raising ``NotImplementedError`` naming US-1600, which fills it.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.remaining.reviewing import revision_remaining
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.estimate.indicating import AmountByKey


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


@dataclass(frozen=True, slots=True)
class SubprojectBalance:
    """The margin of a subproject, or of the lines of the project alone (``SubprojectBalance``).

    ``key`` is the identifier of the subproject, or ``unassigned``; ``budget`` the budgeted amounts
    of the reference, none without one; ``variance`` the budget minus the actual cost and the
    remaining, none with the budget; ``zone`` ``alert`` or ``nominal``.
    """

    key: str
    label: str | None
    budget: Decimal | None
    actual_cost: Decimal
    remaining: Decimal
    variance: Decimal | None
    is_over_budget: bool
    zone: str


@dataclass(frozen=True, slots=True)
class CalculationContext:
    """The context of a computation, as the screens display it (``CalculationContext``).

    ``revision_status`` is the status of the revision as the contract writes it; ``scope`` is
    ``project``, ``unassigned`` or a subproject, the ``CostScope`` of the actual
    costs; ``is_stored`` is false until EP-10 keeps the indicators.
    """

    revision_id: UUID
    revision_status: str
    computed_at: datetime
    scope: CostScope
    is_stored: bool


@dataclass(frozen=True, slots=True)
class RemainingIndicators:
    """The indicators of the remaining to commit of a revision (``RemainingIndicators``).

    Computed at the reading, never stored (``context.is_stored`` false until EP-10 keeps them);
    the deltas none without a reference, or without a revision marked after the passage In progress.
    """

    context: CalculationContext
    total: Decimal
    by_cost_type: tuple[AmountByKey, ...]
    by_subproject: tuple[SubprojectBalance, ...]
    coverage: Coverage
    delta_to_reference: Decimal | None
    delta_to_previous_revision: Decimal | None


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


def remaining_of_revision(
    session: Session, project_id: UUID, revision_id: UUID
) -> RevisionRemaining:
    """Give the remaining to commit of a revision, total and by line, at the state of its tasks.

    The re-estimated amounts of the lines, provisions left out, of the tasks not completed of its
    main structure — started or not, re-estimated or not —, the current revision or a marked one,
    as its tasks stand in it (WF-RAE-0010); none for a revision without a main structure.
    """
    total, by_line = revision_remaining(session, project_id, revision_id)
    return RevisionRemaining(total, by_line)


def remaining_indicators(
    session: Session, project_id: UUID, revision_id: UUID
) -> RemainingIndicators:
    """Give the indicators of the remaining to commit of a revision (``getRemainingIndicators``)."""
    msg = "remaining_indicators is filled by US-1600"
    raise NotImplementedError(msg)
