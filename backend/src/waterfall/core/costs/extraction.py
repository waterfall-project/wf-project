# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of an extraction of the actual costs, private to the module (FLX-07; US-1610).

An extraction is the first tab of a workbook, its headers in row 1, read by openpyxl in values — a
column computed by the value it saved (EP-09, "Les coûts réels"). Its headers are compared to the
labels of the mapping by the folding of the cost settings (WF-REF-0190): without case, accents nor
spaces at their ends. A header names a column read, or a column kept, or neither — ignored, and
named by the report (``ImportIgnored``, ``columns``). Two headers of a file that name the same
column, the first is read or kept and the second ignored, as the reader of an estimate takes the
first of two equal headers. A column without a header is no column: neither read nor named.

What the header gives (``Reading``) is kept with the report, so that the application reads the file
as the analysis read it, even if the mapping changes in between: the rank of each column read and
of each column kept, and the label a kept column bears in the file, which names it in the lines
(``ActualCostLine.passthrough``).

Each row below is then read (``read_lines``): an empty row is skipped; the WBS element is a text —
empty or beginning with a slash, ``WBS_ELEMENT_INVALID`` —, whose part before the first slash is the
code of the project, dots included, and the part after it the code of a subproject (C-373); a code
of project that is not that of the project is ``WBS_ELEMENT_OUTSIDE_PROJECT``. The document is a
text or a whole number read as text; its item a text, or none; the date a cell of date or a text
``AAAA-MM-JJ`` (``DATE_INVALID``); the amount a number, signed, rounded to the cent — half a cent
away from zero, ``ROUND_HALF_UP`` of ``decimal`` (0.005 gives 0.01 and -0.005 gives -0.01), a
choice the spec leaves to settle (#2721) — a number written as a text is ``NUMBER_INVALID``, one
beyond the bound of the column ``VALUE_OUT_OF_RANGE``. A required cell empty is
``VALUE_REQUIRED``. A line is rejected for its first fault, in the order of its columns,
``params.column`` naming the column by its identifier (``ActualCostSourceColumn``), and
``params.value`` the cell as the file carries it.
The columns kept are read as texts, an empty one left out.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import TYPE_CHECKING, Any

from openpyxl import load_workbook

from waterfall.core.cost_settings.interface import (
    fold_labels,
    read_actual_cost_mapping,
    read_folded_labels,
)
from waterfall.core.costs.tables import DOCUMENT_NUMBER_LENGTH, SUBPROJECT_CODE_LENGTH
from waterfall.core.exchanges.interface import DAMAGES
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.orm import Session

FORMAT_KIND = "actual_costs"
FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
WBS_ELEMENT_INVALID = "WBS_ELEMENT_INVALID"
WBS_ELEMENT_OUTSIDE_PROJECT = "WBS_ELEMENT_OUTSIDE_PROJECT"
VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
NUMBER_INVALID = "NUMBER_INVALID"
DATE_INVALID = "DATE_INVALID"
# The columns read (``ActualCostSourceColumn``), in the fixed order of the mapping.
WBS_ELEMENT = "wbs_element"
DOCUMENT_NUMBER = "document_number"
DOCUMENT_ITEM = "document_item"
DOCUMENT_DATE = "document_date"
AMOUNT = "amount"
# What separates the code of the project from that of the subproject in a WBS element (C-373).
SLASH = "/"
# The row of the headers, the first of the first tab; the lines follow it.
HEADER_ROW = 1
# An amount is kept to the cent, below the bound of its column (``numeric(14,2)``).
CENT = Decimal("0.01")
LARGEST_AMOUNT = Decimal("999999999999.99")
_BOUNDS = {"column": "amount", "minimum": str(-LARGEST_AMOUNT), "maximum": str(LARGEST_AMOUNT)}
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def unreadable(params: Mapping[str, Any] | None = None) -> UnprocessableError:
    """Refuse a file that is no extraction of the actual costs (422), naming the format expected.

    An extraction has no version: ``expected_version`` is never given (WF-INTF-0070).
    """
    return UnprocessableError(
        FILE_FORMAT_UNREADABLE, {"expected_format": FORMAT_KIND, **(params or {})}
    )


def sheet_rows(content: bytes, max_row: int | None = None) -> list[tuple[Any, ...]]:
    """Read the rows of the first tab of a workbook, in values, up to ``max_row`` if given.

    In ``read_only`` mode the XML of a tab is parsed while iterating: both steps are guarded, and
    any damage of the file, or a workbook without a tab, is ``FILE_FORMAT_UNREADABLE``.
    """
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            sheets = workbook.worksheets
            if not sheets:
                raise unreadable()
            return list(sheets[0].iter_rows(max_row=max_row, values_only=True))
        finally:
            workbook.close()
    except DAMAGES as error:
        raise unreadable() from error


def text_of(value: object) -> str | None:
    """Read a cell as text: blank is none, a whole number loses its ``.0``, a date its time."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime) and value.time() == datetime.min.time():
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class Kept:
    """A column kept: its rank in the row, and the label the file gives it, which names it."""

    rank: int
    label: str


@dataclass(frozen=True, slots=True)
class Reading:
    """The header of an extraction read against the mapping.

    ``columns`` the rank of each column read the file carries, by its identifier; ``kept`` the
    columns kept, in the order of the file; ``ignored`` the labels of the columns neither read nor
    kept, in the order of the file.
    """

    columns: Mapping[str, int]
    kept: tuple[Kept, ...]
    ignored: tuple[str, ...] = ()

    def kept_with_report(self) -> dict[str, Any]:
        """Give what the report keeps of the reading, for the application to read as it did."""
        return {
            "columns": dict(self.columns),
            "kept": [{"rank": each.rank, "label": each.label} for each in self.kept],
        }

    @staticmethod
    def from_report(kept: Mapping[str, Any]) -> Reading:
        """Give back the reading a report keeps (``kept_with_report``)."""
        columns = {str(name): int(rank) for name, rank in kept["columns"].items()}
        return Reading(
            columns, tuple(Kept(int(each["rank"]), str(each["label"])) for each in kept["kept"])
        )


def read_header(session: Session, row: Sequence[object]) -> Reading:
    """Read the headers of an extraction against the mapping of the installation.

    A required column of the mapping that no header names refuses the file (422
    ``FILE_FORMAT_UNREADABLE``, ``missing_columns``: each, in the order of the mapping, with the
    labels the mapping declares for it).
    """
    headers = [(rank, label) for rank, cell in enumerate(row) if (label := text_of(cell))]
    forms = fold_labels(session, [label for _, label in headers])
    known = read_folded_labels(session)
    columns: dict[str, int] = {}
    kept: list[Kept] = []
    ignored: list[str] = []
    kept_forms: set[str] = set()
    for (rank, label), form in zip(headers, forms, strict=True):
        named = known.get(form, "")
        if named is None and form not in kept_forms:
            kept_forms.add(form)
            kept.append(Kept(rank, label))
        elif named and named not in columns:
            columns[named] = rank
        else:
            ignored.append(label)
    mapping = read_actual_cost_mapping(session)
    missing = [
        {"column": column.column, "labels": list(column.labels)}
        for column in mapping.columns
        if column.required and column.column not in columns
    ]
    if missing:
        raise unreadable({"missing_columns": missing})
    return Reading(columns, tuple(kept), tuple(ignored))


@dataclass(frozen=True, slots=True)
class Line:
    """A line of an extraction read and accepted, by its row; its subproject by its code alone."""

    row: int
    subproject_code: str | None
    document_number: str
    document_item: str | None
    document_date: date
    amount: Decimal
    passthrough: Mapping[str, str]

    @property
    def key(self) -> tuple[str, str | None]:
        """The document and its item, which identify the line in its project (WF-INTF-0140)."""
        return self.document_number, self.document_item


@dataclass(frozen=True, slots=True)
class Rejection:
    """A line of an extraction rejected, by its row, its reason and the parameters of it.

    ``key`` its document and its item when the file gives a document that can be read: the
    analysis rejects a line another of the file shares them with, whatever else it lacks.
    """

    row: int
    code: str
    params: Mapping[str, Any] = field(default_factory=dict[str, Any])
    key: tuple[str, str | None] | None = None

    def reported(self) -> dict[str, Any]:
        """Give the rejection as the report gives it (``ImportRejection``): one tab, no sheet."""
        return {"sheet": None, "row": self.row, "code": self.code, "params": dict(self.params)}


@dataclass(frozen=True, slots=True)
class LinesRead:
    """The lines of an extraction: those accepted, those rejected, and how many were read."""

    lines: tuple[Line, ...]
    rejected: tuple[Rejection, ...]
    read_count: int


class _LineRejectedError(Exception):
    """A cell refuses its line: the reason, and its parameters."""

    def __init__(self, code: str, params: Mapping[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


def _cell(row: Sequence[object], rank: int | None) -> object:
    return row[rank] if rank is not None and rank < len(row) else None


def _shown(value: object) -> str:
    """Give a cell as the file carries it, for ``params.value``."""
    return text_of(value) or ""


def _raw(value: object) -> str:
    """Give a cell as the file carries it, spaces included (``params.wbs_element``)."""
    return "" if value is None else str(value)


def _subproject_code(value: object, project_code: str | None) -> str | None:
    """Read the WBS element: the code of the subproject it names after the slash, or none.

    The element is read without its spaces at the ends, and reported as the file carries it. A
    slash with nothing after it (``A.ABC.26001/``) is ``WBS_ELEMENT_INVALID`` (#2721).
    """
    element = text_of(value) or ""
    carried = _raw(value)
    if not element or element.startswith(SLASH):
        raise _LineRejectedError(WBS_ELEMENT_INVALID, {"wbs_element": carried})
    code, slash, subproject = element.partition(SLASH)
    if slash and not subproject:
        raise _LineRejectedError(WBS_ELEMENT_INVALID, {"wbs_element": carried})
    if code != project_code:
        raise _LineRejectedError(
            WBS_ELEMENT_OUTSIDE_PROJECT, {"wbs_element": carried, "project_code": code}
        )
    if len(subproject) > SUBPROJECT_CODE_LENGTH:
        too_long = {"column": WBS_ELEMENT, "max_length": SUBPROJECT_CODE_LENGTH}
        raise _LineRejectedError(VALUE_TOO_LONG, too_long)
    return subproject or None


def _document_number(value: object) -> str:
    number = text_of(value)
    if number is None:
        raise _LineRejectedError(VALUE_REQUIRED, {"column": DOCUMENT_NUMBER})
    if len(number) > DOCUMENT_NUMBER_LENGTH:
        raise _LineRejectedError(
            VALUE_TOO_LONG, {"column": DOCUMENT_NUMBER, "max_length": DOCUMENT_NUMBER_LENGTH}
        )
    return number


def _document_date(value: object) -> date:
    if text_of(value) is None:
        raise _LineRejectedError(VALUE_REQUIRED, {"column": DOCUMENT_DATE})
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and ISO_DATE.fullmatch(value.strip()):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise _LineRejectedError(DATE_INVALID, {"column": DOCUMENT_DATE, "value": _shown(value)})


def _amount(value: object) -> Decimal:
    """Read the amount: a signed number, to the cent, half a cent away from zero (#2721)."""
    if text_of(value) is None:
        raise _LineRejectedError(VALUE_REQUIRED, {"column": AMOUNT})
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or (isinstance(value, float) and not math.isfinite(value))
    ):
        raise _LineRejectedError(NUMBER_INVALID, {"column": AMOUNT, "value": _shown(value)})
    exact = Decimal(repr(value))
    # Before the rounding: a quantize beyond the precision of the context raises.
    if abs(exact) > LARGEST_AMOUNT + CENT:
        raise _LineRejectedError(VALUE_OUT_OF_RANGE, _BOUNDS)
    amount = exact.quantize(CENT, rounding=ROUND_HALF_UP)
    if abs(amount) > LARGEST_AMOUNT:
        raise _LineRejectedError(VALUE_OUT_OF_RANGE, _BOUNDS)
    return amount


def _line(row: Sequence[object], number: int, reading: Reading, project_code: str | None) -> Line:
    """Read a row of the file as a line, or raise the first fault of its cells."""
    columns = reading.columns
    subproject_code = _subproject_code(_cell(row, columns.get(WBS_ELEMENT)), project_code)
    document_number = _document_number(_cell(row, columns.get(DOCUMENT_NUMBER)))
    document_item = text_of(_cell(row, columns.get(DOCUMENT_ITEM)))
    document_date = _document_date(_cell(row, columns.get(DOCUMENT_DATE)))
    amount = _amount(_cell(row, columns.get(AMOUNT)))
    passthrough = {
        each.label: text
        for each in reading.kept
        if (text := text_of(_cell(row, each.rank))) is not None
    }
    return Line(
        number, subproject_code, document_number, document_item, document_date, amount, passthrough
    )


def _key(row: Sequence[object], reading: Reading) -> tuple[str, str | None] | None:
    """Read the document and the item of a row, or none when its document cannot be read."""
    columns = reading.columns
    try:
        number = _document_number(_cell(row, columns.get(DOCUMENT_NUMBER)))
    except _LineRejectedError:
        return None
    return number, text_of(_cell(row, columns.get(DOCUMENT_ITEM)))


def read_lines(
    rows: Sequence[Sequence[object]], reading: Reading, project_code: str | None
) -> LinesRead:
    """Read the rows below the headers as lines of the project of ``project_code``.

    ``rows`` are those of the tab after the row of the headers; an empty row is not read.
    """
    lines: list[Line] = []
    rejected: list[Rejection] = []
    read_count = 0
    for number, row in enumerate(rows, start=HEADER_ROW + 1):
        if all(text_of(cell) is None for cell in row):
            continue
        read_count += 1
        try:
            lines.append(_line(row, number, reading, project_code))
        except _LineRejectedError as fault:
            rejected.append(Rejection(number, fault.code, fault.params, _key(row, reading)))
    return LinesRead(tuple(lines), tuple(rejected), read_count)
