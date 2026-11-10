# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the workbook of an estimate, pure (appendix B; US-1550/L2).

The header first (A1, B1, A2, B2 of the first tab: the format "Devis" and a known version), then
every tab of lines by its headers, whatever their rank: the columns the format does not read, the
empty lines and the line of total of the table are ignored, a number is read in a numeric cell and
a number written as text is rejected (``NUMBER_INVALID``), each line read and each rejection named
by its tab and its Excel row number (WF-INTF-0070, WF-INTF-0080, WF-INTF-0100); « Tâches » gives
the lineage of the task each entry names, and the header alone is read at the opening of an import
(``check_header``, US-1550/L3). openpyxl reads, in
``read_only`` mode and by values; nothing here touches a database or a session.
"""

import math
import zipfile
import zlib
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from waterfall.core.estimate.excel.writer import (
    FIXED_TABS,
    FORMAT_NAME,
    FORMAT_VERSION,
    TASKS,
)
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
NUMBER_INVALID = "NUMBER_INVALID"

# What the header of the workbook says (appendix B): the name and the version are the writer's
# (US-1550/L1), which exports no constant for the two labels of A1 and A2.
FORMAT_KIND = "estimate"
FORMAT_LABEL = "Format"
VERSION_LABEL = "Version"

# The tabs that are not tabs of lines are the writer's fixed tabs: written for the reading, never
# read as lines.
NOT_LINE_SHEETS = frozenset(FIXED_TABS)

# The headers of the columns read; the other columns are written for the reader and ignored.
TASK_HEADER = "Tâche"
ROLE_OR_CATEGORY_HEADER = "Rôle ou catégorie"
LABEL_HEADER = "Désignation"
QUANTITY_HEADER = "Quantité"
HOURS_HEADER = "Heures"
DISBURSEMENT_HEADER = "Débours unitaire"
PAYMENT_DELAY_HEADER = "Délai de paiement (j)"
SUBPROJECT_HEADER = "Sous-projet"
LINEAGE_HEADER = "ID ligne"
TOTAL_LABEL = "Total"
# The headers of « Tâches » the reading knows a task by: the entry a line names, and its lineage.
ENTRY_HEADER = "Entrée"
TASK_LINEAGE_HEADER = "ID tâche"

_TEXT_HEADERS = (
    TASK_HEADER,
    ROLE_OR_CATEGORY_HEADER,
    LABEL_HEADER,
    SUBPROJECT_HEADER,
    LINEAGE_HEADER,
)
_NUMBER_HEADERS = (QUANTITY_HEADER, HOURS_HEADER, DISBURSEMENT_HEADER, PAYMENT_DELAY_HEADER)
_ALL_HEADERS = _TEXT_HEADERS + _NUMBER_HEADERS
_READ_HEADERS = frozenset(_ALL_HEADERS)
# A tab of lines is the one that carries both of these, on whichever row.
_KEY_HEADERS = frozenset({TASK_HEADER, ROLE_OR_CATEGORY_HEADER})


@dataclass(frozen=True, slots=True)
class ReadLine:
    """A line of an estimate as the workbook wrote it, at its tab and its Excel row."""

    sheet: str
    row: int
    task: str | None
    role_or_category: str | None
    label: str | None
    quantity: Decimal | None
    hours: Decimal | None
    disbursement: Decimal | None
    payment_delay: Decimal | None
    subproject: str | None
    lineage: str | None


@dataclass(frozen=True, slots=True)
class Rejection:
    """A cell the reading refuses, at its tab and its Excel row, with its reason and parameters.

    ``lineage`` is the one of the row refused, so that the analysis does not take it for absent.
    """

    sheet: str
    row: int
    code: str
    params: Mapping[str, Any]
    lineage: str | None = None

    def __post_init__(self) -> None:
        """Freeze the parameters: a frozen report must not be changed through them."""
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))


@dataclass(frozen=True, slots=True)
class WorkbookRead:
    """What a workbook says: the lines read, tab by tab and row by row, and the rejections.

    ``unread_sheets`` names the tabs that are not tabs of lines and are not fixed ones (no
    "Tâche" and "Rôle ou catégorie" headers); ``missing_headers`` gives, by tab read, the headers
    of the columns read that the tab lacks (their cells read as none). The policy is the analysis'.
    ``tasks`` gives, by the entry « Tâches » lists, the lineage of its task, as the workbook
    writes them (US-1550/L3): the analysis designates the task of a line by it.
    """

    lines: tuple[ReadLine, ...]
    rejected: tuple[Rejection, ...]
    unread_sheets: tuple[str, ...] = ()
    missing_headers: Mapping[str, tuple[str, ...]] = MappingProxyType({})
    tasks: Mapping[str, str] = MappingProxyType({})


# What a damaged file raises as openpyxl opens or reads it. SyntaxError is the parent of
# ElementTree.ParseError and of lxml's XMLSyntaxError; zlib.error and EOFError are a cut deflate
# stream, RuntimeError and NotImplementedError a member that zipfile cannot decode (encrypted,
# unknown compression): none of them is an OSError.
DAMAGES = (
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


def unreadable(
    expected_format: str = FORMAT_KIND, expected_version: int = FORMAT_VERSION
) -> UnprocessableError:
    """Build the refusal of a file that is no workbook of the format: the format is the slot's."""
    return UnprocessableError(
        FILE_FORMAT_UNREADABLE,
        {"expected_format": expected_format, "expected_version": str(expected_version)},
    )


def text(value: object) -> str | None:
    """Read a cell as text: blank is none, a whole number loses its ``.0``."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    stripped = str(value).strip()
    return stripped or None


def is_version(value: object, version: int = FORMAT_VERSION) -> bool:
    """Tell a cell that says the version of the format: a number or its text."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return value == version
    return isinstance(value, str) and value.strip() == str(version)


def cells_of(rows: Sequence[Sequence[object]], rank: int) -> tuple[object, object]:
    """Give the cells A and B of a row, none where the row or the cell is missing."""
    cells = tuple(rows[rank]) if rank < len(rows) else ()
    return (cells[0] if cells else None, cells[1] if len(cells) > 1 else None)


def check_header_rows(
    rows: Sequence[Sequence[object]],
    format_name: str = FORMAT_NAME,
    version: int = FORMAT_VERSION,
    expected_format: str = FORMAT_KIND,
) -> None:
    """Refuse a first tab that does not say the format and a known version in A1, B1, A2, B2.

    The name and the version are the slot's; ``expected_format`` is the kind the refusal names.
    """
    first, second = cells_of(rows, 0), cells_of(rows, 1)
    if (
        text(first[0]) != FORMAT_LABEL
        or text(first[1]) != format_name
        or text(second[0]) != VERSION_LABEL
        or not is_version(second[1], version)
    ):
        raise unreadable(expected_format, version)


def check_header(content: bytes) -> None:
    """Refuse a file that is not a workbook saying "Devis" and a known version (US-1550/L3).

    What the opening of an import reads, before any analysis: only the first two rows of the first
    tab, the file opened as ``read_workbook`` opens it.
    """
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            sheets = workbook.worksheets
            rows = list(sheets[0].iter_rows(max_row=2, values_only=True)) if sheets else None
        finally:
            workbook.close()
    except DAMAGES as error:
        raise unreadable() from error
    if rows is None:
        raise unreadable()
    check_header_rows(rows)


def task_entries(rows: Sequence[Sequence[object]]) -> dict[str, str]:
    """Read « Tâches »: the lineage of each entry, below the row of its headers; none without it."""
    entries: dict[str, str] = {}
    columns: tuple[int, int] | None = None
    for row in rows:
        texts = [text(cell) for cell in row]
        if columns is None:
            if ENTRY_HEADER in texts and TASK_LINEAGE_HEADER in texts:
                columns = (texts.index(ENTRY_HEADER), texts.index(TASK_LINEAGE_HEADER))
            continue
        entry, lineage = (texts[rank] if rank < len(texts) else None for rank in columns)
        if entry is not None and lineage is not None:
            entries.setdefault(entry, lineage)
    return entries


def read_number(value: object) -> tuple[Decimal | None, bool]:
    """Read a cell as a decimal; the flag is false for a text, or any value but a number."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, True
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None, False
    if isinstance(value, float) and not math.isfinite(value):
        return None, False
    return Decimal(repr(value)), True


def header_columns(row: Sequence[object], wanted: Collection[str]) -> dict[str, int]:
    """Give the rank of each column wanted, by its header (the first of two equal headers)."""
    columns: dict[str, int] = {}
    for rank, cell in enumerate(row):
        header = text(cell)
        if header is not None and header in wanted and header not in columns:
            columns[header] = rank
    return columns


def at(row: Sequence[object], columns: Mapping[str, int], header: str) -> object:
    """Give the cell of a row under a header, none where the column or the cell is missing."""
    rank = columns.get(header)
    return row[rank] if rank is not None and rank < len(row) else None


def _is_ignored(texts: Mapping[str, str | None], raws: Mapping[str, object]) -> bool:
    """Tell an empty line, or the line of total of the table (``Total`` and nothing else read)."""
    if any(read_number(raw) != (None, True) for raw in raws.values()):
        return False
    others = [value for header, value in texts.items() if header != TASK_HEADER]
    if any(value is not None for value in others):
        return False
    return texts[TASK_HEADER] in {None, TOTAL_LABEL}


def _read_sheet(
    name: str, rows: Sequence[Sequence[object]]
) -> tuple[list[ReadLine], list[Rejection], dict[str, int] | None]:
    """Read the lines of a tab: none if no row carries the headers of a tab of lines.

    The last item is the columns found, none for a tab that has no headers of lines.
    """
    lines: list[ReadLine] = []
    rejected: list[Rejection] = []
    columns: dict[str, int] | None = None
    for number, row in enumerate(rows, start=1):
        if columns is None:
            found = header_columns(row, _READ_HEADERS)
            columns = found if found.keys() >= _KEY_HEADERS else None
            continue
        texts = {header: text(at(row, columns, header)) for header in _TEXT_HEADERS}
        raws = {header: at(row, columns, header) for header in _NUMBER_HEADERS}
        if _is_ignored(texts, raws):
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
            ReadLine(
                sheet=name,
                row=number,
                task=texts[TASK_HEADER],
                role_or_category=texts[ROLE_OR_CATEGORY_HEADER],
                label=texts[LABEL_HEADER],
                quantity=numbers[QUANTITY_HEADER][0],
                hours=numbers[HOURS_HEADER][0],
                disbursement=numbers[DISBURSEMENT_HEADER][0],
                payment_delay=numbers[PAYMENT_DELAY_HEADER][0],
                subproject=texts[SUBPROJECT_HEADER],
                lineage=texts[LINEAGE_HEADER],
            )
        )
    return lines, rejected, columns


def load_sheets(
    content: bytes, expected_format: str = FORMAT_KIND, expected_version: int = FORMAT_VERSION
) -> list[tuple[str, list[tuple[Any, ...]]]]:
    """Open the workbook and read every tab; any damage of the file is ``FILE_FORMAT_UNREADABLE``.

    In ``read_only`` mode the XML of a tab is parsed while iterating, so both steps are guarded.
    """
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            return [(sheet.title, list(sheet.iter_rows(values_only=True))) for sheet in workbook]
        finally:
            workbook.close()
    except DAMAGES as error:
        raise unreadable(expected_format, expected_version) from error


def read_workbook(content: bytes) -> WorkbookRead:
    """Read the workbook of an estimate: its header, then every tab of lines.

    Raises ``FILE_FORMAT_UNREADABLE`` (``expected_format``, ``expected_version``) for a file that
    is no workbook, whose XML is damaged, or whose first tab does not say the format "Devis" and a
    known version.
    """
    sheets = load_sheets(content)
    if not sheets:
        raise unreadable()
    check_header_rows(sheets[0][1])
    lines: list[ReadLine] = []
    rejected: list[Rejection] = []
    unread: list[str] = []
    missing: dict[str, tuple[str, ...]] = {}
    tasks: dict[str, str] = {}
    for name, rows in sheets:
        if name == TASKS:
            tasks = task_entries(rows)
        if name in NOT_LINE_SHEETS:
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
    return WorkbookRead(
        tuple(lines),
        tuple(rejected),
        tuple(unread),
        MappingProxyType(missing),
        MappingProxyType(tasks),
    )
