# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbooks beyond the bounds of the opener, written by the tests, not versioned (US-3190).

A workbook of the format given, swollen afterwards: a member that inflates to 64 MiB while it
declares 7 000 bytes, its CRC that of its first 7 000 bytes, as the workbook of #4419 holds 64 MiB
of spaces in its theme in some 68 kB; a member that announces 1 GiB; an archive of too many
members; a member compressed by another method than deflate; an archive in ZIP64, honest or
announcing 5 GiB through its ZIP64 field. A tab grown past its rows or columns, and a tab that ends
with rows of empty cells, as the workbook of #4734 holds a row of 2 000 000 ``<c/>`` in some 13 kB;
a member added, with relations naming it; a tab moved to another name. Each is written by streams
of a mebibyte at most, so that writing one does not take the memory the test then measures. And
the measure: the peak of what Python allocates during a call.
"""

import re
import tracemalloc
import warnings
import zipfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from openpyxl import load_workbook

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

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


def encrypted(base: bytes) -> bytes:
    """Give the workbook with one member more, whose "encrypted" bit is set (APPNOTE 4.4.4)."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        _copied(base, target)
        target.writestr(HUGE, b" " * 1024)
    raw = bytearray(out.getvalue())
    with zipfile.ZipFile(BytesIO(bytes(raw))) as archive:
        local = archive.getinfo(HUGE).header_offset
    raw[local + 6] |= 1
    at = raw.find(b"PK\x01\x02")
    while at >= 0:
        length = int.from_bytes(raw[at + 28 : at + 30], "little")
        if bytes(raw[at + 46 : at + 46 + length]) == HUGE.encode():
            raw[at + 8] |= 1
        at = raw.find(b"PK\x01\x02", at + 4)
    return bytes(raw)


def in_zip64(base: bytes, announced: int | None = None) -> bytes:
    """Give the workbook written again in ZIP64, its first member announcing ``announced`` if given.

    zipfile writes ZIP64 past its limit alone: the limit lowered to nothing, every member carries
    its sizes and its offset in the ZIP64 field of its extra (APPNOTE 4.5.3), the directory holds
    0xFFFFFFFF in their place, and the end of the directory has its record of 64 bits. The size
    announced replaces the first eight bytes of the ZIP64 field of the first directory entry, its
    size inflated.
    """
    out = BytesIO()
    limit = zipfile.ZIP64_LIMIT
    zipfile.ZIP64_LIMIT = 0
    try:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
            _copied(base, target)
    finally:
        zipfile.ZIP64_LIMIT = limit
    raw = bytearray(out.getvalue())
    if announced is not None:
        at = raw.find(b"PK\x01\x02")
        field = at + 46 + int.from_bytes(raw[at + 28 : at + 30], "little")
        assert raw[field : field + 2] == b"\x01\x00"
        raw[field + 4 : field + 12] = announced.to_bytes(8, "little")
    return bytes(raw)


def duplicated(
    base: bytes, size: int, *, copies: int = 2, method: int = zipfile.ZIP_STORED
) -> bytes:
    """Give the workbook with ``copies`` members of the same name, each of ``size`` bytes."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        _copied(base, target)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            for _ in range(copies):
                target.writestr(HUGE, b" " * size, compress_type=method)
    return out.getvalue()


def tab(base: bytes, title: str) -> str:
    """Give the member of the tab ``title`` of a workbook openpyxl wrote: sheetN, N its rank."""
    return f"xl/worksheets/sheet{load_workbook(BytesIO(base)).sheetnames.index(title) + 1}.xml"


@dataclass(frozen=True)
class Rows:
    """Rows appended to a tab: ``count`` rows of ``cells`` cells each, every cell ``cell``.

    The rows have no number: openpyxl numbers them after the last. The tab keeps its
    ``<dimension>``, which openpyxl cuts the rows and the width to, unless ``dimension`` is false.
    """

    count: int = 1
    cells: int = 0
    cell: bytes = b"<c/>"
    dimension: bool = True


def appended(base: bytes, member: str, rows: Rows) -> bytes:
    """Give the workbook whose tab ``member`` ends with ``rows``, written by streams of a MiB."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        _copied(base, target, but=member)
        with zipfile.ZipFile(BytesIO(base)) as source:
            xml = source.read(member).replace(b"<sheetData/>", b"<sheetData></sheetData>")
        if not rows.dimension:
            xml = re.sub(rb"<dimension [^>]*/>", b"", xml)
        before, after = xml.split(b"</sheetData>")
        per_write = max(1, MEBIBYTE // len(rows.cell))
        with target.open(member, "w") as written:
            written.write(before)
            if rows.cells > per_write:
                for _ in range(rows.count):
                    written.write(b"<row>")
                    for start in range(0, rows.cells, per_write):
                        written.write(rows.cell * min(per_write, rows.cells - start))
                    written.write(b"</row>")
            else:
                row = b"<row>" + rows.cell * rows.cells + b"</row>"
                rows_per_write = max(1, MEBIBYTE // len(row))
                for start in range(0, rows.count, rows_per_write):
                    written.write(row * min(rows_per_write, rows.count - start))
            written.write(b"</sheetData>" + after)
    return out.getvalue()


def relocated(base: bytes, member: str, to: str, target: str, tail: Iterable[bytes]) -> bytes:
    """Give the workbook whose tab ``member`` lies at ``to``, its rows ending with ``tail``.

    The content types name it at ``to``, the relations of the workbook by ``target``, as openpyxl
    finds a tab; it loses its ``<dimension>``, and ``tail`` is written piece by piece.
    """
    workbook_relations = "xl/_rels/workbook.xml.rels"
    out = BytesIO()
    with (
        zipfile.ZipFile(BytesIO(base)) as source,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as written,
    ):
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(f'"/{member}"'.encode(), f'"/{to}"'.encode())
            elif item.filename == workbook_relations:
                data = data.replace(f'"/{member}"'.encode(), f'"{target}"'.encode())
            if item.filename != member:
                written.writestr(item, data)
        xml = source.read(member).replace(b"<sheetData/>", b"<sheetData></sheetData>")
        before, after = re.sub(rb"<dimension [^>]*/>", b"", xml).split(b"</sheetData>")
        with written.open(to, "w") as moved:
            moved.write(before)
            for piece in tail:
                moved.write(piece)
            moved.write(b"</sheetData>" + after)
    return out.getvalue()


def with_member(base: bytes, name: str, data: bytes) -> bytes:
    """Give the workbook with one member more, ``name``, holding ``data``."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        _copied(base, target)
        target.writestr(name, data)
    return out.getvalue()


def with_relations(base: bytes, members: dict[str, bytes], relations: dict[str, str]) -> bytes:
    """Give the workbook with ``members`` more, and relations: of each part, a type to a target.

    A relation is written ``"<type> <target>"``, or ``"<type> <target> <mode>"``; it is added to
    the relations the part holds, or makes them.
    """
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    out = BytesIO()
    with (
        zipfile.ZipFile(BytesIO(base)) as source,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        written = dict(members)
        for part, relation in relations.items():
            folder, name = part.rsplit("/", 1)
            path = f"{folder}/_rels/{name}.rels"
            kind, to, *mode = relation.split(" ")
            element = f'<Relationship Id="rIdAdded" Type="{office}/{kind}" Target="{to}"'
            element += f' TargetMode="{mode[0]}"/>' if mode else "/>"
            end = "</Relationships>"
            held = source.read(path).decode() if path in source.namelist() else ""
            held = held or f'<Relationships xmlns="{package}">{end}'
            written[path] = held.replace(end, element + end).encode()
        for item in source.infolist():
            if item.filename not in written:
                target.writestr(item, source.read(item.filename))
        for name, data in written.items():
            target.writestr(name, data)
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
