# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The analysis of an extraction of the actual costs against a project, private to the module.

The extraction is read (``extraction``), its header against the mapping as it stands at the
analysis; its lines are then judged together and against those of the project, writing nothing
(EP-09, "Les coûts réels"):

- two lines of the file of the same document and the same item, no item included, are rejected
  each (``DUPLICATE_COST_LINE``, ``params.rows`` the rows of the others, in the order of the file):
  neither can be told from the other (WF-INTF-0140, D-4). Every line of the project whose document
  can be read is compared, whatever else it lacks — the contract's letter: that reason replaces its
  others —; a line rejected for its WBS element is not of the project, and is compared with none
  (BRC-04; #3966);
- a line accepted is imputed to the subproject of its project whose code its WBS element is,
  compared whole, or to the project alone, its element the code of the project; any other element
  rejects its line (``WBS_ELEMENT_OUTSIDE_PROJECT``), and the report names each such element once,
  with the number of its lines (``unknown_wbs_elements``, WF-CRE-0020);
- it is then matched with the line of the project of its document and its item: none, it is
  ``added``; one, it is ``updated`` on the columns that change — its date, its amount, its
  subproject, each column kept (``passthrough.<label>``), whether the file gives it or the line
  had it —, or unchanged (WF-INTF-0140). The exclusion of a line is not a column of the file.

The report is the contract's (``ImportReport``): no version, the lines read, those unchanged,
rejected, the differences in the order of the file, the columns ignored, the reason to confirm
(``lines_outside_project``) and the unknown elements. Beside it, under ``READING``, the
reading of the header — the ranks of the columns read and kept, and the label of each kept —, which
the application reads the file by (EP-09, "Les coûts réels"); the contract's reading of an import
does not return it.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from waterfall.core.costs.extraction import (
    HEADER_ROW,
    Known,
    Line,
    LinesRead,
    Rejection,
    read_header,
    read_lines,
    sheet_rows,
)
from waterfall.core.costs.writing import held_lines
from waterfall.core.projects.interface import compared_code, project_code, subprojects_by_code

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.tables import CostLine

DUPLICATE_COST_LINE = "DUPLICATE_COST_LINE"
LINES_OUTSIDE_PROJECT = "lines_outside_project"
# The object of a difference (``ImportDifference.target``).
ACTUAL_COST_LINE = "actual_cost_line"
# Where the report keeps the reading of the header, beside what the contract reads of it.
READING = "actual_cost_reading"
# The prefix of a column kept, among the fields of a difference (``ActualCostColumn``).
PASSTHROUGH = "passthrough."


def doubled_lines(read: LinesRead) -> tuple[list[Line], list[Rejection], list[Rejection]]:
    """Split the rows: the lines alone on their key, the other rejections, the doubled.

    Every row of the project whose document and item can be read is compared, accepted or not: a
    line another of the file shares them with is rejected, whatever else either lacks. A row
    rejected for its WBS element has no key, and is compared with none (BRC-04).
    """
    keyed = sorted(
        ((each.row, each.key) for each in (*read.lines, *read.rejected) if each.key is not None),
        key=lambda pair: pair[0],
    )
    rows: dict[tuple[str, str | None], list[int]] = defaultdict(list)
    for row, key in keyed:
        rows[key].append(row)
    doubled = [
        Rejection(
            row, DUPLICATE_COST_LINE, {"rows": [other for other in rows[key] if other != row]}
        )
        for row, key in keyed
        if len(rows[key]) > 1
    ]
    taken = {each.row for each in doubled}
    alone = [line for line in read.lines if line.row not in taken]
    others = [each for each in read.rejected if each.row not in taken]
    return alone, others, doubled


@dataclass(frozen=True, slots=True)
class Held:
    """A line of the project as a line of the file is compared to it.

    Its subproject by its code and its own: a line imputed again changes its subproject.
    """

    document_date: date
    amount: Decimal
    subproject: tuple[str | None, UUID | None]
    passthrough: Mapping[str, Any]

    @staticmethod
    def of(row: CostLine) -> Held:
        """Give a line of the project, as it is held, to compare."""
        return Held(
            row.document_date,
            row.amount,
            (row.subproject_code, row.subproject_id),
            row.passthrough,
        )


def changed(held: Held, line: Line, subproject_id: UUID | None) -> list[str]:
    """Name the columns a line of the file changes of the line of the project, in their order."""
    fields: list[str] = []
    if held.document_date != line.document_date:
        fields.append("document_date")
    if held.amount != line.amount:
        fields.append("amount")
    if held.subproject != (line.subproject_code, subproject_id):
        fields.append("subproject")
    labels = list(line.passthrough) + [
        label for label in held.passthrough if label not in line.passthrough
    ]
    fields.extend(
        f"{PASSTHROUGH}{label}"
        for label in labels
        if held.passthrough.get(label) != line.passthrough.get(label)
    )
    return fields


def _difference(change: str, line: Line, fields: list[str]) -> dict[str, Any]:
    return {
        "change": change,
        "target": ACTUAL_COST_LINE,
        "lineage_id": None,
        "label": line.document_number,
        "document_item": line.document_item,
        "fields": fields,
    }


def known_elements(session: Session, project_id: UUID) -> Known:
    """Give the elements a project knows: its code, and its subprojects by their codes, as stored.

    Every subproject of the project is read, whatever the file carries: a project has few, and a
    file may carry as many elements as rows.
    """
    return Known(project_code(session, project_id), subprojects_by_code(session, project_id))


def imputed(line: Line, known: Known) -> UUID | None:
    """Give the subproject a line is imputed to: the one its code is, or none for the project."""
    return None if line.subproject_code is None else known.subprojects.get(line.subproject_code)


def unknown_elements(read: Iterable[Rejection]) -> list[dict[str, Any]]:
    """Name each WBS element a line is rejected for, once, with its lines, as the file first has it.

    ``ImportReport.unknown_wbs_elements``: the subprojects to declare before importing again
    (WF-CRE-0020; #3966). Two elements that differ by their blanks at the ends alone are one, as
    they are compared to the codes: one subproject to declare. The rejections are in the order of
    the file.
    """
    shown: dict[str, str] = {}
    counted: dict[str, int] = {}
    for each in read:
        element = each.unknown_element
        if element is not None:
            compared = compared_code(element)
            shown.setdefault(compared, element)
            counted[compared] = counted.get(compared, 0) + 1
    return [
        {"wbs_element": shown[compared], "line_count": count} for compared, count in counted.items()
    ]


def analyse(session: Session, project_id: UUID, content: bytes) -> dict[str, Any]:
    """Give the report of an extraction against the lines of a project, writing nothing.

    A line rejected for its WBS element asks for confirmation (``lines_outside_project``, #2724):
    the confirmation guards against a file of the wrong project.
    """
    rows = sheet_rows(content)
    reading = read_header(session, rows[0] if rows else ())
    known = known_elements(session, project_id)
    read = read_lines(rows[HEADER_ROW:], reading, known)
    lines, others, doubled = doubled_lines(read)
    held = held_lines(session, project_id, {line.document_number for line in lines})
    differences: list[dict[str, Any]] = []
    for line in lines:
        before = held.get(line.key)
        if before is None:
            differences.append(_difference("added", line, []))
        elif fields := changed(Held.of(before), line, imputed(line, known)):
            differences.append(_difference("updated", line, fields))
    rejected = sorted((*others, *doubled), key=lambda each: each.row)
    unknown = unknown_elements(read.rejected)
    ignored = reading.ignored
    return {
        "format_version": None,
        "read_count": read.read_count,
        "unchanged_count": read.read_count - len(rejected) - len(differences),
        "rejected": [each.reported() for each in rejected],
        "refusals": [],
        "differences": differences,
        "ignored": [{"kind": "columns", "count": len(ignored), "labels": list(ignored)}]
        if ignored
        else [],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": [LINES_OUTSIDE_PROJECT] if unknown else [],
        "unknown_wbs_elements": unknown,
        READING: reading.kept_with_report(),
    }
