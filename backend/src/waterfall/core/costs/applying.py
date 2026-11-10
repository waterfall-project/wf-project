# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of an extraction of the actual costs to a project, private to the module.

In the transaction of the task of the exchanges, under the lock of the project, once they judged
the import again (EP-09, "Les coûts réels"): the file is read as the analysis read it — by the
reading of its header the report keeps, whatever the mapping became —, its lines judged together
again, then against those of the project as they stand under the lock:

- a line accepted whose document and item no line of the project bears is inserted, tracked;
- one that matches a line of the project and changes its date, its amount, its subproject or a
  column kept updates it — its imputation computed again from its WBS element, its columns kept
  replaced, its exclusion intact (WF-INTF-0140, WF-CRE-0020) —; one that changes nothing leaves it
  as it is, written by the import that last changed it;
- each line written names the import, and the account that confirmed it as its author
  (WF-DAT-0070).

The entry of the log is written first, the lines name it: the author who confirmed, the period of
the opening, the columns kept of the file in its order, and the four counts of what the application
did (WF-CRE-0050). The inscription ``import_apply`` in the journal is the exchanges'; nothing enters
the undo history.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from waterfall.core.costs.analysing import (
    READING,
    Held,
    changed,
    doubled_lines,
    imputed,
    subprojects_of,
)
from waterfall.core.costs.extraction import HEADER_ROW, Reading, read_lines, sheet_rows
from waterfall.core.costs.tables import CostImport
from waterfall.core.costs.writing import Placed, held_lines, write_line
from waterfall.core.projects.interface import lock_project, project_code
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.extraction import Line
    from waterfall.core.costs.tables import CostLine
    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class Applied:
    """An import to apply: its project, its import of the exchanges, its author, its period."""

    project_id: UUID
    import_report_id: UUID
    requested_by: UUID
    period_from: date | None
    period_to: date | None


def apply(
    session: Session, applied: Applied, content: bytes, report: Mapping[str, Any], act: Act
) -> UUID:
    """Write an extraction into its project: the entry of the log, then the lines; give it."""
    project_id = applied.project_id
    lock_project(session, project_id)
    reading = Reading.from_report(report[READING])
    rows = sheet_rows(content)
    read = read_lines(rows[HEADER_ROW:], reading, project_code(session, project_id))
    lines, others, doubled = doubled_lines(read)
    codes = subprojects_of(session, project_id, lines)
    held = held_lines(session, project_id)
    written: list[tuple[Line, CostLine | None]] = []
    unchanged = 0
    for line in lines:
        before = held.get(line.key)
        if before is None or changed(Held.of(before), line, imputed(line, codes)):
            written.append((line, before))
        else:
            unchanged += 1
    created = sum(1 for _, before in written if before is None)
    entry = CostImport(
        id=new_id(),
        project_id=project_id,
        import_report_id=applied.import_report_id,
        imported_at=act.at,
        requested_by=applied.requested_by,
        period_from=applied.period_from,
        period_to=applied.period_to,
        created_count=created,
        updated_count=len(written) - created,
        unchanged_count=unchanged,
        rejected_count=len(others) + len(doubled),
        passthrough_columns=[each.label for each in reading.kept],
    )
    session.add(entry)
    session.flush()
    for line, before in written:
        placed = Placed(project_id, new_id(), imputed(line, codes), entry.id)
        write_line(session, before, line, placed, act)
    session.flush()
    return entry.id
