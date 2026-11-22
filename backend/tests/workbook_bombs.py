# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbooks beyond the bounds of the opener, written by the tests, not versioned (US-3190).

A workbook of the format given, swollen afterwards: a member that inflates to 64 MiB while it
declares 7 000 bytes, its CRC that of its first 7 000 bytes, as the workbook of #4419 holds 64 MiB
of spaces in its theme in some 68 kB; a member that announces 1 GiB; an archive of too many
members; a member compressed by another method than deflate. And a tab grown past its rows or
columns. Each is written by streams of a mebibyte at most, so that writing one does not take the
memory the test then measures. And the measure: the peak of what Python allocates during a call.
"""

import tracemalloc
import zipfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from openpyxl import load_workbook

if TYPE_CHECKING:
    from collections.abc import Generator

MEBIBYTE = 1024 * 1024
GIBIBYTE = 1024 * MEBIBYTE
THEME = "xl/theme/theme1.xml"
HUGE = "xl/media/huge.bin"
# The member of #4419: 64 MiB of spaces, declared 7 000 bytes.
INFLATED = 64 * MEBIBYTE
DECLARED = 7_000
# What a refusal before any inflation allocates at most, far below what a bomb inflates.
CALM = 16 * MEBIBYTE


def _copied(base: bytes, target: zipfile.ZipFile, *, but: str | None = None) -> None:
    """Copy every member of a workbook into an archive being written, but ``but``."""
    with zipfile.ZipFile(BytesIO(base)) as source:
        for item in source.infolist():
            if item.filename != but:
                target.writestr(item, source.read(item.filename))


def _declare(raw: bytearray, name: str, size: int, crc: int) -> None:
    """Make the local header and the directory entry of ``name`` declare a size and a CRC.

    The local header (APPNOTE 4.3.7) holds the CRC at 14 and the size at 22; the directory entry
    (4.3.12), at 16 and 24, its name at 46: the fields keep their width, the archive its offsets.
    """
    with zipfile.ZipFile(BytesIO(bytes(raw))) as archive:
        local = archive.getinfo(name).header_offset
    raw[local + 14 : local + 18] = crc.to_bytes(4, "little")
    raw[local + 22 : local + 26] = size.to_bytes(4, "little")
    at = raw.find(b"PK\x01\x02")
    while at >= 0:
        length = int.from_bytes(raw[at + 28 : at + 30], "little")
        if bytes(raw[at + 46 : at + 46 + length]) == name.encode():
            raw[at + 16 : at + 20] = crc.to_bytes(4, "little")
            raw[at + 24 : at + 28] = size.to_bytes(4, "little")
        at = raw.find(b"PK\x01\x02", at + 4)


def lying(base: bytes, inflated: int = INFLATED, declared: int = DECLARED) -> bytes:
    """Give the workbook whose theme inflates to ``inflated`` spaces but declares ``declared``.

    Its CRC is that of the ``declared`` first spaces: zipfile, which cuts the member there, finds
    it whole — once it has inflated all of it.
    """
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        _copied(base, target, but=THEME)
        with target.open(THEME, "w") as member:
            for _ in range(inflated // MEBIBYTE):
                member.write(b" " * MEBIBYTE)
    raw = bytearray(out.getvalue())
    _declare(raw, THEME, declared, zlib.crc32(b" " * declared))
    return bytes(raw)


def swollen(base: bytes, inflated: int) -> bytes:
    """Give the workbook whose theme holds ``inflated`` spaces, as it declares."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        _copied(base, target, but=THEME)
        with target.open(THEME, "w") as member:
            for _ in range(inflated // MEBIBYTE):
                member.write(b" " * MEBIBYTE)
    return out.getvalue()


def announcing(base: bytes, size: int = GIBIBYTE) -> bytes:
    """Give the workbook with one member more, of a kibibyte, that announces ``size`` bytes."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        _copied(base, target)
        target.writestr(HUGE, b" " * 1024)
    raw = bytearray(out.getvalue())
    _declare(raw, HUGE, size, zlib.crc32(b" " * 1024))
    return bytes(raw)


def crowded(base: bytes, members: int) -> bytes:
    """Give the workbook padded with empty members up to ``members`` in all."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        _copied(base, target)
        for rank in range(members - len(target.infolist())):
            target.writestr(f"xl/media/pad{rank}.bin", b"")
    return out.getvalue()


def compressed_by(base: bytes, method: int) -> bytes:
    """Give the workbook with one member more, compressed by ``method``."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        _copied(base, target)
        target.writestr(HUGE, b" " * 1024, compress_type=method)
    return out.getvalue()


def grown(base: bytes, sheet: str, row: int, column: int) -> bytes:
    """Give the workbook whose tab ``sheet`` (added last if missing) holds a cell at a place."""
    book = load_workbook(BytesIO(base))
    tab = book[sheet] if sheet in book.sheetnames else book.create_sheet(sheet)
    tab.cell(row=row, column=column, value="x")
    out = BytesIO()
    book.save(out)
    return out.getvalue()


@dataclass
class Peak:
    """The most Python allocated within a ``measured`` block, in bytes, once the block is left."""

    allocated: int = 0


@contextmanager
def measured() -> Generator[Peak]:
    """Measure the most Python allocates within the block, whatever the block raises."""
    peak = Peak()
    tracemalloc.start()
    try:
        yield peak
    finally:
        peak.allocated = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
