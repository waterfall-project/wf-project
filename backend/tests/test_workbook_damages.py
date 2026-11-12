# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A damaged workbook is refused by every reader of a workbook, by one list of exceptions (#2723).

The list of what openpyxl raises on a damaged file belongs to ``core/exchanges``; the reader of an
estimate and the reader of the actual costs both read it from there. One test tries a set of
damaged files on the two, so that a damage one of them let through would fail here.
"""

import zipfile
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pytest
from openpyxl import Workbook

from waterfall.core.costs import extraction
from waterfall.core.estimate.excel import reader
from waterfall.core.exchanges.interface import DAMAGES
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable


def _workbook() -> bytes:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(["Format", "Devis"])
    sheet.append(["Version", 1])
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def _truncated(part: str) -> bytes:
    """Give the workbook with a part of its zip cut in two: its XML is no longer well formed."""
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(_workbook())) as source, zipfile.ZipFile(out, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            target.writestr(item, data[: len(data) // 2] if item.filename == part else data)
    return out.getvalue()


def _altered() -> bytes:
    """Give the workbook with the middle of the deflate stream of its first tab overwritten."""
    raw = bytearray(_workbook())
    with zipfile.ZipFile(BytesIO(_workbook())) as source:
        info = source.getinfo("xl/worksheets/sheet1.xml")
    extra = int.from_bytes(raw[info.header_offset + 28 : info.header_offset + 30], "little")
    start = info.header_offset + 30 + len(info.filename.encode()) + extra
    middle = start + info.compress_size // 2
    raw[middle : middle + 4] = b"\xff\xff\xff\xff"
    return bytes(raw)


READERS: dict[str, Callable[[bytes], Any]] = {
    "estimate": reader.read_workbook,
    "actual costs": extraction.sheet_rows,
}


@pytest.mark.requirement("WF-INTF-0070-A")
def test_the_two_readers_of_a_workbook_read_one_list_of_damages() -> None:
    assert reader.DAMAGES is DAMAGES
    assert extraction.DAMAGES is DAMAGES


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("name", list(READERS))
@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"no workbook", id="no-zip"),
        pytest.param(_truncated("xl/worksheets/sheet1.xml"), id="sheet-cut"),
        pytest.param(_truncated("xl/workbook.xml"), id="workbook-cut"),
        pytest.param(_altered(), id="deflate-altered"),
    ],
)
def test_a_damaged_workbook_is_refused_as_unreadable_by_each_reader(
    name: str, content: bytes
) -> None:
    with pytest.raises(UnprocessableError) as raised:
        READERS[name](content)
    assert raised.value.code == "FILE_FORMAT_UNREADABLE"
