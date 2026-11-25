# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the refusal of a workbook with a column missing share (US-3200).

A header of a workbook rewritten or blanked, and a snapshot of the lines of estimate the platform
holds, to tell that a refused file changed none.
"""

from io import BytesIO
from typing import TYPE_CHECKING, Any

from openpyxl import load_workbook
from sqlalchemy import inspect, select

from waterfall.core.estimate.tables import EstimateLine

if TYPE_CHECKING:
    from waterfall.platform.database import Database


def rewritten(content: bytes, sheet: str, header: str, new: str | None = None) -> bytes:
    """Give the workbook with the header of a tab renamed to ``new``, or cleared when none."""
    book = load_workbook(BytesIO(content))
    tab = book[sheet]
    places = [cell.coordinate for row in tab.iter_rows() for cell in row if cell.value == header]
    assert len(places) == 1, (sheet, header)
    tab[places[0]] = new
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def lines_held(database: Database) -> list[tuple[Any, ...]]:
    """Read every line of estimate of the platform, all its columns, in a stable order."""
    names = [column.key for column in inspect(EstimateLine).mapper.column_attrs]
    with database.transaction() as session:
        return sorted(
            tuple(str(getattr(line, name)) for name in names)
            for line in session.scalars(select(EstimateLine))
        )
