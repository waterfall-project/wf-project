# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the actual costs of a project: read, excluded, written for the witness (US-1620).

``list_actual_costs`` reads the lines of a project, filtered, sorted and paginated, with their three
totals, the instant of the last import and the columns kept (``listActualCosts``);
``set_tracked_scope`` excludes a line from the scope tracked, or reinstates it, idempotent and
without a counter (``setActualCostTrackedScope``, WF-CRE-0030) — both US-1620/L1's, with
``load_exclusion``, the exclusion of the witness at its instant. ``load_cost_lines`` writes the
lines an import of the witness creates or updates, at the identifiers and the instant it imposes
(US-1610/L3): as the application writes them, on their document and item — a line held updated,
its exclusion kept, another inserted —, each imputed by its code to the subproject of the project
that bears it, or to the project alone (WF-CRE-0020, WF-INTF-0140).

Declared by US-1580/L1; each raises ``NotImplementedError`` naming the story that fills it, which
gives it its arguments and its result.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.costs.tables import CostLine
from waterfall.core.projects.interface import lock_project, subprojects_coded

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class CostLineLoad:
    """A line an import of the witness writes: the identifier it takes if it is created.

    Its document and its item, which identify it in its project (WF-DAT-0110); its date, its signed
    amount, the code of subproject its WBS element bears, none without a subproject part; its
    columns kept, texts by their label.
    """

    cost_line_id: UUID
    document_number: str
    document_item: str | None
    document_date: date
    amount: Decimal
    subproject_code: str | None
    passthrough: Mapping[str, str] = field(default_factory=dict[str, str])


def list_actual_costs(session: Session, project_id: UUID) -> None:
    """Give a page of the lines of the actual costs of a project, and their totals."""
    msg = "list_actual_costs is filled by US-1620/L1"
    raise NotImplementedError(msg)


def set_tracked_scope(session: Session, project_id: UUID, cost_line_id: UUID) -> None:
    """Exclude a line from the scope tracked, or reinstate it (``setActualCostTrackedScope``)."""
    msg = "set_tracked_scope is filled by US-1620/L1"
    raise NotImplementedError(msg)


def load_cost_lines(
    session: Session,
    project_id: UUID,
    cost_import_id: UUID,
    lines: Collection[CostLineLoad],
    act: Act,
) -> None:
    """Write the lines an import of the witness writes, at the identifiers and instant imposed.

    Under the lock of the project, as the application: a line of the same document and item, no
    item included, is updated — its date, its amount, its code and its imputation computed again,
    its columns kept replaced, its exclusion intact —, another inserted at its identifier, tracked;
    each names the import that wrote it last, the author and the instant of ``act`` its audit.
    """
    if not lines:
        return
    lock_project(session, project_id)
    codes = subprojects_coded(
        session, project_id, {line.subproject_code for line in lines if line.subproject_code}
    )
    held = session.scalars(
        select(CostLine).where(
            CostLine.project_id == project_id,
            CostLine.document_number.in_({line.document_number for line in lines}),
        )
    ).all()
    by_document = {(row.document_number, row.document_item): row for row in held}
    for line in lines:
        row = by_document.get((line.document_number, line.document_item))
        if row is None:
            row = CostLine(
                id=line.cost_line_id,
                project_id=project_id,
                document_number=line.document_number,
                document_item=line.document_item,
                is_in_tracked_scope=True,
                excluded_reason=None,
                created_at=act.at,
                created_by=act.author,
            )
            session.add(row)
            by_document[line.document_number, line.document_item] = row
        row.document_date = line.document_date
        row.amount = line.amount
        row.subproject_code = line.subproject_code
        code = line.subproject_code
        row.subproject_id = None if code is None else codes.get(code)
        row.passthrough = dict(line.passthrough)
        row.last_import_id = cost_import_id
        row.updated_at = act.at
        row.updated_by = act.author
    session.flush()


def load_exclusion(session: Session, project_id: UUID, cost_line_id: UUID) -> None:
    """Exclude a line of the witness at the instant its chronology imposes."""
    msg = "load_exclusion is filled by US-1620/L1"
    raise NotImplementedError(msg)
