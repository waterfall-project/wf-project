# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the workbook of an estimate, pure (appendix B; US-1550/L2).

The header first (A1, B1, A2, B2 of the first tab: the format "Devis" and a known version), then
every tab of lines by its headers, whatever their rank: the columns the format does not read, the
empty lines and the line of total of the table are ignored, a number is read in a numeric cell and
a number written as text is rejected (``NUMBER_INVALID``), each line read and each rejection named
by its tab and its Excel row number (WF-INTF-0070, WF-INTF-0080, WF-INTF-0100). openpyxl reads, in
``read_only`` mode and by values; nothing here touches a database or a session.
"""

import math
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING, Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
NUMBER_INVALID = "NUMBER_INVALID"

# What the header of the workbook says (appendix B); the exporter writes the same.
FORMAT_KIND = "estimate"
FORMAT_NAME = "Devis"
FORMAT_VERSION = 1
FORMAT_LABEL = "Format"
VERSION_LABEL = "Version"

# The tabs that are not tabs of lines: written for the reading, never read as lines.
PRESENTATION_SHEET = "Présentation"
SUMMARY_SHEET = "Devis"
TASKS_SHEET = "Tâches"
PARAMETERS_SHEET = "Paramètres"
NOT_LINE_SHEETS = frozenset({PRESENTATION_SHEET, SUMMARY_SHEET, TASKS_SHEET, PARAMETERS_SHEET})

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

_TEXT_HEADERS = (
    TASK_HEADER,
    ROLE_OR_CATEGORY_HEADER,
    LABEL_HEADER,
    SUBPROJECT_HEADER,
    LINEAGE_HEADER,
)
_NUMBER_HEADERS = (QUANTITY_HEADER, HOURS_HEADER, DISBURSEMENT_HEADER, PAYMENT_DELAY_HEADER)
_READ_HEADERS = frozenset(_TEXT_HEADERS + _NUMBER_HEADERS)
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
    """A cell the reading refuses, at its tab and its Excel row, with its reason and parameters."""

    sheet: str
    row: int
    code: str
    params: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class WorkbookRead:
    """What a workbook says: the lines read, tab by tab and row by row, and the rejections."""

    lines: tuple[ReadLine, ...]
    rejected: tuple[Rejection, ...]


def _unreadable() -> UnprocessableError:
    return UnprocessableError(
        FILE_FORMAT_UNREADABLE,
        {"expected_format": FORMAT_KIND, "expected_version": str(FORMAT_VERSION)},
    )


def _text(value: object) -> str | None:
    """Read a cell as text: blank is none, a whole number loses its ``.0``."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _is_version(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return value == FORMAT_VERSION
    return isinstance(value, str) and value.strip() == str(FORMAT_VERSION)


def _check_header(rows: Sequence[Sequence[object]]) -> None:
    """Refuse a first tab that does not say "Devis" and a known version in A1, B1, A2, B2."""
    first, second = ([(*row, None, None)[:2] for row in rows[:2]] + [(None, None)] * 2)[:2]
    if (
        _text(first[0]) != FORMAT_LABEL
        or _text(first[1]) != FORMAT_NAME
        or _text(second[0]) != VERSION_LABEL
        or not _is_version(second[1])
    ):
        raise _unreadable()


def _number(value: object) -> tuple[Decimal | None, bool]:
    """Read a cell as a decimal; the flag is false for a text, or any value but a number."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, True
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None, False
    if isinstance(value, float) and not math.isfinite(value):
        return None, False
    return Decimal(repr(value)), True


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


def _is_ignored(texts: Mapping[str, str | None], raws: Mapping[str, object]) -> bool:
    """Tell an empty line, or the line of total of the table (``Total`` and nothing else read)."""
    if any(_number(raw) != (None, True) for raw in raws.values()):
        return False
    others = [value for header, value in texts.items() if header != TASK_HEADER]
    if any(value is not None for value in others):
        return False
    return texts[TASK_HEADER] in {None, TOTAL_LABEL}


def _read_sheet(
    name: str, rows: Sequence[Sequence[object]]
) -> tuple[list[ReadLine], list[Rejection]]:
    """Read the lines of a tab: none if no row carries the headers of a tab of lines."""
    lines: list[ReadLine] = []
    rejected: list[Rejection] = []
    columns: dict[str, int] | None = None
    for number, row in enumerate(rows, start=1):
        if columns is None:
            found = _header_columns(row)
            columns = found if _KEY_HEADERS <= found.keys() else None
            continue
        texts = {header: _text(_at(row, columns, header)) for header in _TEXT_HEADERS}
        raws = {header: _at(row, columns, header) for header in _NUMBER_HEADERS}
        if _is_ignored(texts, raws):
            continue
        numbers = {header: _number(raw) for header, raw in raws.items()}
        refusals = [
            Rejection(name, number, NUMBER_INVALID, {"column": header, "value": str(raws[header])})
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
    return lines, rejected


def read_workbook(content: bytes) -> WorkbookRead:
    """Read the workbook of an estimate: its header, then every tab of lines.

    Raises ``FILE_FORMAT_UNREADABLE`` (``expected_format``, ``expected_version``) for a file that
    is no workbook, or whose first tab does not say the format "Devis" and a known version.
    """
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except (zipfile.BadZipFile, InvalidFileException, KeyError, ValueError, OSError) as error:
        raise _unreadable() from error
    try:
        sheets = [(sheet.title, list(sheet.iter_rows(values_only=True))) for sheet in workbook]
    finally:
        workbook.close()
    if not sheets:
        raise _unreadable()
    _check_header(sheets[0][1])
    lines: list[ReadLine] = []
    rejected: list[Rejection] = []
    for name, rows in sheets:
        if name in NOT_LINE_SHEETS:
            continue
        sheet_lines, sheet_rejected = _read_sheet(name, rows)
        lines += sheet_lines
        rejected += sheet_rejected
    return WorkbookRead(tuple(lines), tuple(rejected))
