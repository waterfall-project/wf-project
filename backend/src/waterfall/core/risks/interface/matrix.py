# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The matrix of the risks of a project (``getProjectRiskMatrix``; US-2600).

The identified risks counted by cell, and every risk read placed at its exact values, on the bounds
of the matrix of the reference settings (WF-RIS-0040, WF-REF-0160): its probability, its severity
as a share of the base of the project — its reference budget, or before it the total of the
estimate of its current revision, provisions left out —, and the zone of its cell, which the risk
settings give (``zone_of``). The portfolio matrix of EP-11 reads its points.

Declared by US-2550/L1, the socle of EP-08; filled by US-2600/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.interface.register import ProvisionTotals
    from waterfall.core.risks.interface.risks import RiskState


@dataclass(frozen=True, slots=True)
class MatrixLevel:
    """A level of an axis and its bounds (``RiskMatrixLevel``), the upper ``None`` at the last."""

    level: int
    lower: Decimal
    upper: Decimal | None


@dataclass(frozen=True, slots=True)
class MatrixCell:
    """A cell of the matrix, its zone, and how many identified risks it holds."""

    probability_level: int
    severity_level: int
    zone: str
    count: int


@dataclass(frozen=True, slots=True)
class MatrixPoint:
    """A risk the matrix places (``RiskMatrixPoint``), at the values of the risk read.

    ``severity_ratio`` its severity as a share of the base of the project, ``None`` on a base of
    nought, which relates it to nothing (#1240).
    """

    risk_id: UUID
    label: str
    probability: Decimal
    severity_amount: Decimal
    severity_ratio: Decimal | None
    provision_amount: Decimal
    state: RiskState
    zone: str


@dataclass(frozen=True, slots=True)
class RiskMatrix:
    """The matrix of a project in a revision (``RiskMatrix``): its levels, cells, points, totals."""

    probability_levels: tuple[MatrixLevel, ...]
    severity_levels: tuple[MatrixLevel, ...]
    cells: tuple[MatrixCell, ...]
    points: tuple[MatrixPoint, ...]
    totals: ProvisionTotals


def risk_matrix(
    session: Session, project_id: UUID, revision_id: UUID | None, viewer: Viewer
) -> RiskMatrix:
    """Fill the matrix of a project with its risks read in a revision, by default the current."""
    msg = "risk_matrix is filled by US-2600/L2"
    raise NotImplementedError(msg)
