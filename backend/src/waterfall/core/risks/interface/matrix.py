# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The matrix of the risks of a project (``getProjectRiskMatrix``; US-2600).

The identified risks counted by cell, and every risk read placed at its exact values, on the bounds
of the matrix of the reference settings (WF-RIS-0040, WF-REF-0160): its probability, its severity
as a share of the base of the project — its reference budget, or before it the total of the
estimate of its current revision, provisions left out —, and the zone of its cell, which the risk
settings give (``zone_of``). The portfolio matrix of EP-11 reads its points.

Declared by US-2550/L1, the socle of EP-08; filled by US-2600/L2. What it gives lives in ``views``
(``RiskMatrix``, ``MatrixLevel``, ``MatrixCell``, ``MatrixPoint``), which the interface of the
module names.
"""

from typing import TYPE_CHECKING

from waterfall.core.risks.matrixing import read_matrix

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.views import RiskMatrix


def risk_matrix(
    session: Session, project_id: UUID, revision_id: UUID | None, viewer: Viewer
) -> RiskMatrix:
    """Fill the matrix of a project with its risks read in a revision.

    The revision named, else the current, else the last marked; one of another project is not
    found (404). The levels are those of the reference settings, refused while they are not
    written (503). A risk is read as ``read_risk`` reads it, so its cell and its zone are the ones
    the register gives.
    """
    return read_matrix(session, project_id, revision_id, viewer)
