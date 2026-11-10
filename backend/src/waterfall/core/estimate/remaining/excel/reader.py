# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the workbook « Reste à engager », pure (appendix B; US-1630/L2).

The header first (A1, B1, A2, B2 of the first tab: the format « Reste à engager » and a known
version), then the date of the review in « Synthèse », then every tab of a subproject and
« Hors sous-projet » — the tabs that are not the fixed ones — by its headers, whatever their rank:
the columns the format does not read and the empty lines are ignored, so are the line of total
and the note the writer sets under the table, and whatever else is typed under them is read as a
line; a number is read in a numeric cell and a number written as text is rejected, each line read
and each rejection named by its tab and its Excel row number (WF-INTF-0070, WF-INTF-0120,
WF-INTF-0130).
The reading of the cells is the estimate's (``waterfall.core.estimate.excel.reader``); the layout
is the writer's (``layout``), so that the workbook is read where it is written. openpyxl reads, in
``read_only`` mode and by values; nothing here touches a database or a session: the matching by
lineage, the analysis and the application are US-1630/L3.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import TYPE_CHECKING

from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

from waterfall.core.estimate.excel.reader import (
    FILE_FORMAT_UNREADABLE,
    LABEL_HEADER,
    LINEAGE_HEADER,
    NUMBER_INVALID,
    ROLE_OR_CATEGORY_HEADER,
    TASK_HEADER,
    TOTAL_LABEL,
    Rejection,
    at,
    check_header_rows,
    header_columns,
    load_sheets,
    read_number,
    task_entries,
    text,
    unreadable,
)
from waterfall.core.estimate.remaining.excel.layout import (
    FIXED_TABS,
    FORMAT_NAME,
    FORMAT_VERSION,
    REVIEW_DATE_CELL,
    SUMMARY,
    TASKS,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "FILE_FORMAT_UNREADABLE",
    "NUMBER_INVALID",
    "ReadRemainingLine",
    "Rejection",
    "RemainingRead",
    "read_remaining_workbook",
]

# What the header of the workbook says: the format, in the slot of a remaining to commit.
FORMAT_KIND = "remaining"

# The headers of the columns read; the other columns are written for the reader and ignored.
DAYS_HEADER = "Jours restants"
DISBURSEMENT_HEADER = "Débours restant"

_TEXT_HEADERS = (TASK_HEADER, ROLE_OR_CATEGORY_HEADER, LABEL_HEADER, LINEAGE_HEADER)
_NUMBER_HEADERS = (DAYS_HEADER, DISBURSEMENT_HEADER)
_ALL_HEADERS = _TEXT_HEADERS + _NUMBER_HEADERS
_READ_HEADERS = frozenset(_ALL_HEADERS)
# A tab of lines is the one that carries both of these, on whichever row.
_KEY_HEADERS = frozenset({TASK_HEADER, ROLE_OR_CATEGORY_HEADER})
_NOT_LINE_SHEETS = frozenset(FIXED_TABS)


@dataclass(frozen=True, slots=True)
class ReadRemainingLine:
    """A line of a remaining to commit as the workbook says it, at its tab and its Excel row.

    ``days`` the days left of a line of labour, ``disbursement`` the amount left of a line of
    disbursement: the workbook asks one of them of a line, the analysis decides.
    """

    sheet: str
    row: int
    task: str | None
    role_or_category: str | None
    label: str | None
    days: Decimal | None
    disbursement: Decimal | None
    lineage: str | None


@dataclass(frozen=True, slots=True)
class RemainingRead:
    """What a workbook says: the date of the review, the lines read, and the rejections.

    ``review_date`` is none when « Synthèse » holds no date the reading understands: an absent
    date and an unreadable one are not told apart here. The policy is US-1630/L3's (#2410): the
    date of completion is never null, so it decides their fate, and it reads the raw cell again
    if it must name the value read. ``unread_sheets`` names the tabs that are not fixed ones and
    carry no headers of lines; ``missing_headers`` gives, by tab read, the headers of the columns
    read that the tab lacks (their cells read as none). ``tasks`` gives, by the entry « Tâches »
    lists, the lineage of its task: the analysis designates the task of a line by it.
    """

    review_date: date | None
    lines: tuple[ReadRemainingLine, ...]
    rejected: tuple[Rejection, ...]
    unread_sheets: tuple[str, ...] = ()
    missing_headers: Mapping[str, tuple[str, ...]] = MappingProxyType({})
    tasks: Mapping[str, str] = MappingProxyType({})


def _check_header(rows: Sequence[Sequence[object]]) -> None:
    """Refuse a first tab that does not say « Reste à engager » and a known version."""
    check_header_rows(rows, FORMAT_NAME, FORMAT_VERSION, FORMAT_KIND)


def _review_date(rows: Sequence[Sequence[object]]) -> date | None:
    """Read the date of the review in the cell of « Synthèse » the writer holds it in.

    A date cell (openpyxl reads it as a ``datetime``) and the ISO text the writer writes are
    understood; anything else is none.
    """
    column, row = coordinate_from_string(REVIEW_DATE_CELL)
    cells = tuple(rows[row - 1]) if row <= len(rows) else ()
    rank = column_index_from_string(column) - 1
    value = cells[rank] if rank < len(cells) else None
    if isinstance(value, datetime):
        return value.date()
    written = text(value)
    if written is None:
        return None
    try:
        return date.fromisoformat(written)
    except ValueError:
        return None


def _is_total(
    texts: Mapping[str, str | None],
    numbers: Mapping[str, tuple[Decimal | None, bool]],
    sums: Mapping[str, Decimal],
) -> bool:
    """Tell the line of total of the table: ``Total`` under the task, nothing else read.

    A role, a label or a lineage make it a line. Its numbers are the sums of the columns, empty,
    zero (the sums the writer leaves uncomputed) or the sums of the lines above; any other number
    is a line a person typed.
    """
    others = [value for header, value in texts.items() if header != TASK_HEADER]
    if texts[TASK_HEADER] != TOTAL_LABEL or any(value is not None for value in others):
        return False
    return all(
        valid and value in {None, Decimal(0), sums[header]}
        for header, (value, valid) in numbers.items()
    )


def _is_note(texts: Mapping[str, str | None], raws: Mapping[str, object]) -> bool:
    """Tell a row of which nothing is read outside the task column: the note under the table."""
    others = [value for header, value in texts.items() if header != TASK_HEADER]
    return (
        texts[TASK_HEADER] is not None
        and all(value is None for value in others)
        and all(read_number(raw) == (None, True) for raw in raws.values())
    )


def _is_empty(texts: Mapping[str, str | None], raws: Mapping[str, object]) -> bool:
    """Tell an empty line: no text read, no number."""
    return all(value is None for value in texts.values()) and all(
        read_number(raw) == (None, True) for raw in raws.values()
    )


def _read_sheet(
    name: str, rows: Sequence[Sequence[object]]
) -> tuple[list[ReadRemainingLine], list[Rejection], dict[str, int] | None]:
    """Read the lines of a tab, below the row of its headers; the columns found, none without."""
    lines: list[ReadRemainingLine] = []
    rejected: list[Rejection] = []
    columns: dict[str, int] | None = None
    sums = {header: Decimal(0) for header in _NUMBER_HEADERS}
    total_seen = note_seen = False
    for number, row in enumerate(rows, start=1):
        if columns is None:
            found = header_columns(row, _READ_HEADERS)
            columns = found if found.keys() >= _KEY_HEADERS else None
            continue
        texts = {header: text(at(row, columns, header)) for header in _TEXT_HEADERS}
        raws = {header: at(row, columns, header) for header in _NUMBER_HEADERS}
        numbers = {header: read_number(raw) for header, raw in raws.items()}
        if _is_empty(texts, raws):
            continue
        if _is_total(texts, numbers, sums):
            total_seen = True
            continue
        if total_seen and not note_seen and _is_note(texts, raws):
            # The note the writer sets under the table, once; any other row is a row of the tab.
            note_seen = True
            continue
        refusals = [
            Rejection(
                name,
                number,
                NUMBER_INVALID,
                {"header": header, "value": str(raws[header])},
                texts[LINEAGE_HEADER],
            )
            for header, (_, valid) in numbers.items()
            if not valid
        ]
        if refusals:
            rejected += refusals
            continue
        for header, (value, _) in numbers.items():
            sums[header] += value or Decimal(0)
        lines.append(
            ReadRemainingLine(
                sheet=name,
                row=number,
                task=texts[TASK_HEADER],
                role_or_category=texts[ROLE_OR_CATEGORY_HEADER],
                label=texts[LABEL_HEADER],
                days=numbers[DAYS_HEADER][0],
                disbursement=numbers[DISBURSEMENT_HEADER][0],
                lineage=texts[LINEAGE_HEADER],
            )
        )
    return lines, rejected, columns


def read_remaining_workbook(content: bytes) -> RemainingRead:
    """Read the workbook of a remaining to commit: its header, its review date, its tabs of lines.

    Raises ``FILE_FORMAT_UNREADABLE`` (``expected_format`` at ``remaining``, ``expected_version``)
    for a file that is no workbook, whose XML is damaged, or whose first tab does not say the
    format « Reste à engager » and a known version.
    """
    sheets = load_sheets(content, FORMAT_KIND, FORMAT_VERSION)
    if not sheets:
        raise unreadable(FORMAT_KIND, FORMAT_VERSION)
    _check_header(sheets[0][1])
    review_date: date | None = None
    lines: list[ReadRemainingLine] = []
    rejected: list[Rejection] = []
    unread: list[str] = []
    missing: dict[str, tuple[str, ...]] = {}
    tasks: dict[str, str] = {}
    for name, rows in sheets:
        if name == SUMMARY:
            review_date = _review_date(rows)
        elif name == TASKS:
            tasks = task_entries(rows)
        if name in _NOT_LINE_SHEETS:
            continue
        sheet_lines, sheet_rejected, columns = _read_sheet(name, rows)
        lines += sheet_lines
        rejected += sheet_rejected
        if columns is None:
            unread.append(name)
            continue
        absent = tuple(header for header in _ALL_HEADERS if header not in columns)
        if absent:
            missing[name] = absent
    return RemainingRead(
        review_date,
        tuple(lines),
        tuple(rejected),
        tuple(unread),
        MappingProxyType(missing),
        MappingProxyType(tasks),
    )
