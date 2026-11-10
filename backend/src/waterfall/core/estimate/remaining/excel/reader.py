# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the workbook « Reste à engager », pure (appendix B; US-1630/L2).

The header first (A1, B1, A2, B2 of the first tab: the format « Reste à engager » and a known
version), then the date of the review in « Synthèse », then every tab of a subproject and
« Hors sous-projet » — the tabs that are not the fixed ones — by its headers, whatever their rank:
the columns the format does not read and the empty lines are ignored, the line of total ends the
table (the note under it is no line), a number is read in a numeric cell and a number written as
text is rejected, each line read and each rejection named by its tab and its Excel row number
(WF-INTF-0070, WF-INTF-0120, WF-INTF-0130).
The reading of the cells is the estimate's (``waterfall.core.estimate.excel.reader``); the layout
is the writer's (``layout``), so that the workbook is read where it is written. openpyxl reads, in
``read_only`` mode and by values; nothing here touches a database or a session: the matching by
lineage, the analysis and the application are US-1630/L3.
"""

import zipfile
import zlib
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string
from openpyxl.utils.exceptions import InvalidFileException

from waterfall.core.estimate.excel.reader import (
    ENTRY_HEADER,
    FILE_FORMAT_UNREADABLE,
    FORMAT_LABEL,
    LABEL_HEADER,
    LINEAGE_HEADER,
    NUMBER_INVALID,
    ROLE_OR_CATEGORY_HEADER,
    TASK_HEADER,
    TASK_LINEAGE_HEADER,
    TOTAL_LABEL,
    VERSION_LABEL,
    Rejection,
    read_number,
)
from waterfall.core.estimate.remaining.excel.layout import (
    FIXED_TABS,
    FORMAT_NAME,
    FORMAT_VERSION,
    REVIEW_DATE_CELL,
    SUMMARY,
    TASKS,
)
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from decimal import Decimal

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

    ``review_date`` is none when « Synthèse » holds no date the reading understands (the policy is
    the analysis'). ``unread_sheets`` names the tabs that are not fixed ones and carry no headers
    of lines; ``missing_headers`` gives, by tab read, the headers of the columns read that the tab
    lacks (their cells read as none). ``tasks`` gives, by the entry « Tâches » lists, the lineage
    of its task: the analysis designates the task of a line by it.
    """

    review_date: date | None
    lines: tuple[ReadRemainingLine, ...]
    rejected: tuple[Rejection, ...]
    unread_sheets: tuple[str, ...] = ()
    missing_headers: Mapping[str, tuple[str, ...]] = MappingProxyType({})
    tasks: Mapping[str, str] = MappingProxyType({})


# What a damaged file raises as openpyxl opens or reads it: the estimate's reading keeps the same
# list private (``_DAMAGES``), as it does ``_text`` and ``_task_entries`` below, which pyright
# refuses to import.
_DAMAGES = (
    zipfile.BadZipFile,
    zlib.error,
    EOFError,
    RuntimeError,
    NotImplementedError,
    InvalidFileException,
    KeyError,
    ValueError,
    OSError,
    SyntaxError,
)


def _text(value: object) -> str | None:
    """Read a cell as text: blank is none, a whole number loses its ``.0``."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _task_entries(rows: Sequence[Sequence[object]]) -> dict[str, str]:
    """Read « Tâches »: the lineage of each entry, below the row of its headers; none without it."""
    entries: dict[str, str] = {}
    columns: tuple[int, int] | None = None
    for row in rows:
        texts = [_text(cell) for cell in row]
        if columns is None:
            if ENTRY_HEADER in texts and TASK_LINEAGE_HEADER in texts:
                columns = (texts.index(ENTRY_HEADER), texts.index(TASK_LINEAGE_HEADER))
            continue
        entry, lineage = (texts[rank] if rank < len(texts) else None for rank in columns)
        if entry is not None and lineage is not None:
            entries.setdefault(entry, lineage)
    return entries


def _unreadable() -> UnprocessableError:
    return UnprocessableError(
        FILE_FORMAT_UNREADABLE,
        {"expected_format": FORMAT_KIND, "expected_version": str(FORMAT_VERSION)},
    )


def _is_version(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return value == FORMAT_VERSION
    return isinstance(value, str) and value.strip() == str(FORMAT_VERSION)


def _cells_of(rows: Sequence[Sequence[object]], rank: int) -> tuple[object, object]:
    """Give the cells A and B of a row, none where the row or the cell is missing."""
    cells = tuple(rows[rank]) if rank < len(rows) else ()
    return (cells[0] if cells else None, cells[1] if len(cells) > 1 else None)


def _check_header(rows: Sequence[Sequence[object]]) -> None:
    """Refuse a first tab that does not say « Reste à engager » and a known version."""
    first, second = _cells_of(rows, 0), _cells_of(rows, 1)
    if (
        _text(first[0]) != FORMAT_LABEL
        or _text(first[1]) != FORMAT_NAME
        or _text(second[0]) != VERSION_LABEL
        or not _is_version(second[1])
    ):
        raise _unreadable()


def _review_date(rows: Sequence[Sequence[object]]) -> date | None:
    """Read the date of the review in the cell of « Synthèse » the writer holds it in.

    A date cell and the ISO text the writer writes are understood; anything else is none.
    """
    column, row = coordinate_from_string(REVIEW_DATE_CELL)
    cells = tuple(rows[row - 1]) if row <= len(rows) else ()
    rank = column_index_from_string(column) - 1
    value = cells[rank] if rank < len(cells) else None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _header_columns(row: Sequence[object]) -> dict[str, int]:
    """Give the rank of each column read, by its header (the first of two equal headers)."""
    columns: dict[str, int] = {}
    for rank, cell in enumerate(row):
        header = _text(cell)
        if header in _READ_HEADERS and header not in columns:
            columns[header] = rank
    return columns


def _at(row: Sequence[object], columns: Mapping[str, int], header: str) -> object:
    rank = columns.get(header)
    return row[rank] if rank is not None and rank < len(row) else None


def _is_total(texts: Mapping[str, str | None]) -> bool:
    """Tell the line of total of the table: ``Total`` under the task and nothing else read.

    Its sums, in the columns of the amounts, are not looked at.
    """
    others = [value for header, value in texts.items() if header != TASK_HEADER]
    return texts[TASK_HEADER] == TOTAL_LABEL and all(value is None for value in others)


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
    for number, row in enumerate(rows, start=1):
        if columns is None:
            found = _header_columns(row)
            columns = found if found.keys() >= _KEY_HEADERS else None
            continue
        texts = {header: _text(_at(row, columns, header)) for header in _TEXT_HEADERS}
        raws = {header: _at(row, columns, header) for header in _NUMBER_HEADERS}
        if _is_total(texts):
            # The table ends with its line of total; the note under it is not a line.
            break
        if _is_empty(texts, raws):
            continue
        numbers = {header: read_number(raw) for header, raw in raws.items()}
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


def _load_sheets(content: bytes) -> list[tuple[str, list[tuple[Any, ...]]]]:
    """Open the workbook and read every tab; any damage of the file is ``FILE_FORMAT_UNREADABLE``.

    In ``read_only`` mode the XML of a tab is parsed while iterating, so both steps are guarded.
    """
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            return [(sheet.title, list(sheet.iter_rows(values_only=True))) for sheet in workbook]
        finally:
            workbook.close()
    except _DAMAGES as error:
        raise _unreadable() from error


def read_remaining_workbook(content: bytes) -> RemainingRead:
    """Read the workbook of a remaining to commit: its header, its review date, its tabs of lines.

    Raises ``FILE_FORMAT_UNREADABLE`` (``expected_format`` at ``remaining``, ``expected_version``)
    for a file that is no workbook, whose XML is damaged, or whose first tab does not say the
    format « Reste à engager » and a known version.
    """
    sheets = _load_sheets(content)
    if not sheets:
        raise _unreadable()
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
            tasks = _task_entries(rows)
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
