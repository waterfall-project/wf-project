# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The matrix of the risks of a project, private to the module (US-2600/L2).

``getProjectRiskMatrix``.

The risks of a revision, read as the register reads them — one context for all of them, so that the
matrix costs the same statements whatever their number —, placed on the bounds of the matrix of the
reference settings (WF-REF-0160, WF-RIS-0040):

- each risk is a point at its exact values, in the zone of its cell; its severity share is that of
  the base of the project, none on a base of nought, which relates no severity to anything (#1240);
- each of the sixteen cells counts the identified risks it holds, and only them (#1395): an
  occurred or a dismissed risk stays a point and is counted in no cell;
- the totals are the register's, over all the risks of the revision, the reserve beside them;
- a project with no revision to read holds no risk: its matrix is empty, its levels still those of
  the settings, which an installation not bootstrapped does not have (503).
"""

from typing import TYPE_CHECKING

from waterfall.core.risk_settings.interface import LEVELS
from waterfall.core.risks.reading import (
    NOUGHT,
    read_context,
    risk_view,
    severity_share,
)
from waterfall.core.risks.registering import found_in, provision_totals, revision_read
from waterfall.core.risks.views import (
    MatrixCell,
    MatrixLevel,
    MatrixPoint,
    ProvisionTotals,
    RiskMatrix,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.reading import ReadContext
    from waterfall.core.risks.views import RiskView


def _levels(bounds: Sequence[Decimal]) -> tuple[MatrixLevel, ...]:
    """Give the levels of an axis: the lower bound included, the upper excluded, none last."""
    lowers = (NOUGHT, *bounds)
    uppers = (*bounds, None)
    return tuple(
        MatrixLevel(rank, lower, upper)
        for rank, (lower, upper) in enumerate(zip(lowers, uppers, strict=True), start=1)
    )


def _cells(context: ReadContext, views: Sequence[RiskView]) -> tuple[MatrixCell, ...]:
    """Give the sixteen cells, by probability then severity, each with its identified risks."""
    counts: dict[tuple[int, int], int] = {}
    for view in views:
        if view.state == "identified":
            cell = view.matrix_cell
            key = (cell.probability_level, cell.severity_level)
            counts[key] = counts.get(key, 0) + 1
    return tuple(
        MatrixCell(
            row,
            column,
            context.matrix.zones[LEVELS * (row - 1) + (column - 1)],
            counts.get((row, column), 0),
        )
        for row in range(1, LEVELS + 1)
        for column in range(1, LEVELS + 1)
    )


def _point(context: ReadContext, view: RiskView) -> MatrixPoint:
    """Place a risk at its exact values, its severity as a share of the base of its revision."""
    return MatrixPoint(
        view.risk_id,
        view.label,
        view.probability,
        view.severity,
        severity_share(context, view.revision_id, view.severity),
        view.provision_amount,
        view.state,
        view.matrix_cell.zone,
    )


def read_matrix(
    session: Session, project_id: UUID, revision_id: UUID | None, viewer: Viewer
) -> RiskMatrix:
    """Fill the matrix of a project with the risks of a revision.

    The one named, else the current, else the last marked (404 for one of another project).
    """
    read = revision_read(session, project_id, revision_id)
    founds = [] if read is None else found_in(session, project_id, read, None)
    context = read_context(session, project_id, founds)
    views = [risk_view(session, project_id, found, viewer, context) for found in founds]
    totals = (
        ProvisionTotals(NOUGHT, NOUGHT, NOUGHT, NOUGHT, NOUGHT)
        if read is None
        else provision_totals(views, session, project_id, context.facts.reference_revision_id)
    )
    return RiskMatrix(
        _levels(context.matrix.probability_bounds),
        _levels(context.matrix.severity_bounds),
        _cells(context, views),
        tuple(_point(context, view) for view in views),
        totals,
    )
