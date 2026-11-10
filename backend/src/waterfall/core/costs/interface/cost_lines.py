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

Declared by US-1580/L1; filled by US-1620/L1 and US-1610/L3.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from waterfall.core.costs.reading import read_lines
from waterfall.core.costs.scoping import ScopeChange, judge_exclusion, set_scope
from waterfall.core.costs.writing import Placed, held_lines, write_line
from waterfall.core.projects.interface import lock_project, subprojects_coded

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.reading import (
        CostLineFilters,
        CostLineList,
        CostLinePage,
        CostLineSort,
        CostLineView,
    )
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


def list_actual_costs(
    session: Session,
    project_id: UUID,
    filters: CostLineFilters,
    sort: CostLineSort,
    page: CostLinePage,
) -> CostLineList:
    """Give a page of the lines of the actual costs of a project, and the totals of all retained.

    Filtered by subproject, by period on the date of the document and by scope; the totals, the
    instant of the last import and the columns kept are those of the whole set retained, not of the
    page (``listActualCosts``, WF-CRE-0040). A period reversed or a subproject the project does not
    have is refused (422).
    """
    return read_lines(session, project_id, filters, sort, page)


def set_tracked_scope(
    session: Session, project_id: UUID, cost_line_id: UUID, change: ScopeChange, act: Act
) -> CostLineView:
    """Exclude a line from the scope tracked, or reinstate it (``setActualCostTrackedScope``).

    Idempotent, under the lock of the project, once its command ``exclude_cost_lines`` is judged:
    409 ``project_not_terminal``, then ``project_in_progress``. The change is inscribed in the
    journal of audit (``cost_line_exclude``, ``cost_line_reinstate``); a line already in the state
    aimed at, with the same reason, is left as it is and inscribes nothing (WF-CRE-0030).
    """
    judge_exclusion(session, project_id)
    return set_scope(session, project_id, cost_line_id, change, act)


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
    by_document = held_lines(session, project_id, {line.document_number for line in lines})
    for line in lines:
        key = (line.document_number, line.document_item)
        code = line.subproject_code
        placed = Placed(
            project_id,
            line.cost_line_id,
            None if code is None else codes.get(code),
            cost_import_id,
        )
        by_document[key] = write_line(session, by_document.get(key), line, placed, act)
    session.flush()


def load_exclusion(
    session: Session, project_id: UUID, cost_line_id: UUID, reason: str | None, act: Act
) -> None:
    """Exclude a line of the witness at the instant its chronology imposes, for ``reason``.

    As the service excludes it, the journal of audit included, but for the conditions of the
    command: the witness writes the past, whatever the state of the project it reaches.
    """
    change = ScopeChange(is_in_tracked_scope=False, reason=reason)
    set_scope(session, project_id, cost_line_id, change, act)
