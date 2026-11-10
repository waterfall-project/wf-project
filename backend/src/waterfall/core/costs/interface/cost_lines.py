# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the actual costs of a project: read, excluded, written for the witness (US-1620).

``list_actual_costs`` reads the lines of a project, filtered, sorted and paginated, with their three
totals, the instant of the last import and the columns kept (``listActualCosts``);
``set_tracked_scope`` excludes a line from the scope tracked, or reinstates it, idempotent and
without a counter (``setActualCostTrackedScope``, WF-CRE-0030) — both US-1620/L1's, with
``load_exclusion``, the exclusion of the witness at its instant. ``load_cost_lines`` writes the
lines an import of the witness creates or updates, at the identifiers and the instant it imposes
(US-1610/L3).

Declared by US-1580/L1; each raises ``NotImplementedError`` naming the story that fills it, which
gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def list_actual_costs(session: Session, project_id: UUID) -> None:
    """Give a page of the lines of the actual costs of a project, and their totals."""
    msg = "list_actual_costs is filled by US-1620/L1"
    raise NotImplementedError(msg)


def set_tracked_scope(session: Session, project_id: UUID, cost_line_id: UUID) -> None:
    """Exclude a line from the scope tracked, or reinstate it (``setActualCostTrackedScope``)."""
    msg = "set_tracked_scope is filled by US-1620/L1"
    raise NotImplementedError(msg)


def load_cost_lines(session: Session, project_id: UUID) -> None:
    """Write the lines an import of the witness writes, at the identifiers and instant imposed."""
    msg = "load_cost_lines is filled by US-1610/L3"
    raise NotImplementedError(msg)


def load_exclusion(session: Session, project_id: UUID, cost_line_id: UUID) -> None:
    """Exclude a line of the witness at the instant its chronology imposes."""
    msg = "load_exclusion is filled by US-1620/L1"
    raise NotImplementedError(msg)
