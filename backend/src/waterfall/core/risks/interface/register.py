# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The register of the risks of a project (``listRisks``; US-2600).

The risks as a revision freezes them (WF-RIS-0030), filtered, sorted and paginated by the server,
with the provision totals of all those the filters retain, whatever the page (WF-RIS-0040,
WF-IHM-0130, #1367): the identified at their current provision, the occurred and the dismissed at
the share they held in the reference, and the reserve beside them (WF-RIS-0050).

Declared by US-2550/L1, the socle of EP-08; filled by US-2600/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.interface.risks import RiskState, RiskView

# The columns the register sorts on (``listRisks``, ``sort_by``).
type RiskColumn = Literal[
    "label",
    "probability",
    "severity",
    "provision_amount",
    "occurrence_cost",
    "occurred_reestimated_amount",
    "state",
    "last_review_on",
]


@dataclass(frozen=True, slots=True)
class Bounds[T]:
    """The two bounds of a column, each included, ``None`` when not given."""

    least: T | None = None
    most: T | None = None


@dataclass(frozen=True, slots=True)
class RiskFilters:
    """What the register keeps (``listRisks``): each column by its list, its search or its bounds.

    ``revision_id`` the revision read: the current one, or the last marked, when ``None``.
    """

    revision_id: UUID | None = None
    states: tuple[RiskState, ...] | None = None
    zones: tuple[str, ...] | None = None
    search: str | None = None
    probability: Bounds[Decimal] = Bounds()
    severity: Bounds[Decimal] = Bounds()
    provision_amount: Bounds[Decimal] = Bounds()
    occurrence_cost: Bounds[Decimal] = Bounds()
    occurred_reestimated_amount: Bounds[Decimal] = Bounds()
    last_review_on: Bounds[date] = Bounds()


@dataclass(frozen=True, slots=True)
class RiskSort:
    """How the register is sorted: by a column, or in the order of declaration when ``None``."""

    key: RiskColumn | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class RiskPage:
    """Which risks of the register are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ProvisionTotals:
    """The provision totals of the risks retained, by state, their sum, and the reserve."""

    identified: Decimal
    occurred: Decimal
    dismissed: Decimal
    total: Decimal
    reserve: Decimal


@dataclass(frozen=True, slots=True)
class RiskList:
    """A page of the register, how many risks the filters retain, and their totals."""

    risks: list[RiskView]
    total: int
    totals: ProvisionTotals


def list_risks(
    session: Session,
    project_id: UUID,
    query: tuple[RiskFilters, RiskSort, RiskPage],
    viewer: Viewer,
) -> RiskList:
    """Read a page of the register of a project in a revision, and the totals of those retained."""
    msg = "list_risks is filled by US-2600/L1"
    raise NotImplementedError(msg)
