# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbooks beyond the bounds of the opener, written by the tests, not versioned (US-3190).

A workbook of the format given, swollen afterwards: a member that inflates to 64 MiB while it
declares 7 000 bytes, its CRC that of its first 7 000 bytes, as the workbook of #4419 holds 64 MiB
of spaces in its theme in some 68 kB; a member that announces 1 GiB; an archive of too many
members; a member compressed by another method than deflate; an archive in ZIP64, honest or
announcing 5 GiB through its ZIP64 field. A tab grown past its rows or columns, and a tab that ends
with rows of empty cells, as the workbook of #4734 holds a row of 2 000 000 ``<c/>`` in some 13 kB;
a member added, with relations naming it; a tab moved to another name; a chartsheet added. Each is
written by streams of a mebibyte at most, so that writing one does not take the memory the test then
measures. And the measure: the peak of what Python allocates during a call.

The other vectors of amplification, which US-3190/L2b measured, then bounded: shared strings by
their number, by the elements of one, by their text; the lists of ``styles.xml``; the defined names
of ``workbook.xml``; a tab of rows as wide as its ``<dimension>`` says. Each gives exactly the
count it is asked, so that a test sets a workbook just at a bound, or one past it. The elements of
the parts openpyxl parses into a tree (US-3190b): a member stuffed with elements out of any list,
every list of ``styles.xml`` at once, a part named an external link by the workbook. And their
measure: the peak resident size of a fresh process, which sees what libxml2 allocates and
``tracemalloc`` does not (``resident``), the one the measure of the workbooks takes too
(``measure/workbooks.py``).
"""

import gc
import multiprocessing
import re
import resource
import time
import tracemalloc
import warnings
import zipfile
import zlib
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, Any, cast

from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter

from waterfall.core.costs import extraction as costs_reader
from waterfall.core.estimate.excel import reader as estimate_reader
from waterfall.core.estimate.remaining.excel import reader as remaining_reader
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Mapping, Sequence

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


def charted(base: bytes, title: str) -> bytes:
    """Give the workbook with a chartsheet more, ``title``, as openpyxl writes one.

    Its chart, drawn from the first cells of the first tab, lies in a drawing its relations name:
    ``xl/chartsheets/sheet1.xml``, ``xl/drawings/drawing1.xml``, ``xl/charts/chart1.xml``.
    """
    book = load_workbook(BytesIO(base))
    # The stubs of openpyxl leave the chart a method takes untyped.
    chart = cast("Any", BarChart())
    chart.add_data(Reference(book.worksheets[0], min_col=1, min_row=1, max_row=2))
    cast("Any", book.create_chartsheet(title)).add_chart(chart)
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


# --- The other vectors of amplification (US-3190/L2b) --------------------------------------------

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
STRINGS = "xl/sharedStrings.xml"
STYLES = "xl/styles.xml"
WORKBOOK = "xl/workbook.xml"
CONTENT_TYPES = "[Content_Types].xml"
STRINGS_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"
# The lists of ``styles.xml`` in the order of ECMA-376 (§18.8.39), and an item of each that openpyxl
# reads; the item of ``colors`` is a colour of its ``indexedColors``, which it holds with them.
STYLE_ORDER = (
    "numFmts",
    "fonts",
    "fills",
    "borders",
    "cellStyleXfs",
    "cellXfs",
    "cellStyles",
    "dxfs",
    "tableStyles",
    "colors",
)
_STYLE_ITEMS: dict[str, Callable[[int], bytes]] = {
    "numFmts": lambda rank: b'<numFmt numFmtId="%d" formatCode="0.%d"/>' % (164 + rank, rank),
    "fonts": lambda _: b"<font/>",
    "fills": lambda _: b"<fill><patternFill/></fill>",
    "borders": lambda _: b"<border/>",
    "cellStyleXfs": lambda _: b"<xf/>",
    "cellXfs": lambda _: b"<xf/>",
    "cellStyles": lambda rank: b'<cellStyle name="s%d" xfId="0"/>' % rank,
    "dxfs": lambda _: b"<dxf/>",
    "tableStyles": lambda rank: b'<tableStyle name="t%d"/>' % rank,
    "colors": lambda _: b'<rgbColor rgb="FF000000"/>',
}
# A ``dxf`` as Excel writes it: a font with ``b`` and a colour, a fill with the ``bgColor`` of its
# pattern, a border of four sides each with a style and a colour: 16 elements.
RICH_DXF = (
    b'<dxf><font><b/><color rgb="FF9C0006"/></font>'
    b'<fill><patternFill><bgColor rgb="FFFFC7CE"/></patternFill></fill>'
    b"<border>"
    b'<left style="thin"><color auto="1"/></left>'
    b'<right style="thin"><color auto="1"/></right>'
    b'<top style="thin"><color auto="1"/></top>'
    b'<bottom style="thin"><color auto="1"/></bottom>'
    b"</border></dxf>"
)
RICH_DXF_ELEMENTS = 16
# The longest text of one string of ``shared_text``: the text is written by streams of a MiB.
_LONGEST_STRING = 8 * MEBIBYTE
_ASTRAL = "\U0001f600".encode()


def _member(base: bytes, name: str) -> bytes:
    """Give a member of a workbook."""
    with zipfile.ZipFile(BytesIO(base)) as archive:
        return archive.read(name)


def _rewritten(base: bytes, members: dict[str, bytes]) -> bytes:
    """Give the workbook whose ``members`` replace those of the same name, or are added."""
    out = BytesIO()
    with (
        zipfile.ZipFile(BytesIO(base)) as source,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as target,
    ):
        for item in source.infolist():
            if item.filename not in members:
                target.writestr(item, source.read(item.filename))
        for name, data in members.items():
            target.writestr(name, data)
    return out.getvalue()


def _typed_strings(base: bytes) -> bytes:
    """Give the content types of a workbook, its shared strings named, as openpyxl finds them."""
    types = _member(base, CONTENT_TYPES)
    if STRINGS_TYPE.encode() in types:
        return types
    override = f'<Override PartName="/{STRINGS}" ContentType="{STRINGS_TYPE}"/>'
    return types.replace(b"</Types>", override.encode() + b"</Types>")


def shared_strings(base: bytes, count: int, elements: int = 0) -> bytes:
    """Give the workbook of ``count`` shared strings, each holding ``elements`` elements.

    A string of no element is ``<si/>``; the elements of one are runs ``<r><t>a</t></r>``, two
    elements each, and a ``<t>a</t>`` when their count is odd.
    """
    one = b"<si>" + b"<r><t>a</t></r>" * (elements // 2) + b"<t>a</t>" * (elements % 2) + b"</si>"
    if not elements:
        one = b"<si/>"
    head = f'<sst xmlns="{MAIN}" count="{count}" uniqueCount="{count}">'.encode()
    return _rewritten(
        base, {STRINGS: head + one * count + b"</sst>", CONTENT_TYPES: _typed_strings(base)}
    )


def shared_text(base: bytes, characters: int, *, astral: bool = False) -> bytes:
    """Give the workbook whose shared strings hold ``characters`` characters of text in all.

    Strings of 8 Mi characters at most, written by streams; each ends with an astral character when
    ``astral``, which makes Python hold its text four bytes a character.
    """
    tail = _ASTRAL if astral else b""
    out = BytesIO()
    with (
        zipfile.ZipFile(BytesIO(base)) as source,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as target,
    ):
        for item in source.infolist():
            if item.filename not in {STRINGS, CONTENT_TYPES}:
                target.writestr(item, source.read(item.filename))
        target.writestr(CONTENT_TYPES, _typed_strings(base))
        with target.open(STRINGS, "w") as written:
            written.write(f'<sst xmlns="{MAIN}">'.encode())
            left = characters
            while left > 0:
                plain = min(left, _LONGEST_STRING) - (1 if astral else 0)
                written.write(b"<si><t>")
                for start in range(0, plain, MEBIBYTE):
                    written.write(b"a" * min(MEBIBYTE, plain - start))
                written.write(tail + b"</t></si>")
                left -= min(left, _LONGEST_STRING)
            written.write(b"</sst>")
    return out.getvalue()


def styled(
    base: bytes, listing: str, count: int, item: Callable[[int], bytes] | None = None
) -> bytes:
    """Give the workbook whose list ``listing`` of ``styles.xml`` holds ``count`` items exactly.

    ``item`` writes an item of the list, ``_STYLE_ITEMS`` the empty one by default.

    The list replaces the one the workbook has, or is added at its place in the order of the
    stylesheet; ``colors`` holds its ``indexedColors``, then ``count - 1`` colours in it: ``count``
    elements in all.
    """
    item = item or _STYLE_ITEMS[listing]
    tag = listing.encode()
    if listing == "colors":
        block = b"<colors><indexedColors>" + item(0) * (count - 1) + b"</indexedColors></colors>"
    else:
        block = b"<" + tag + b">" + b"".join(map(item, range(count))) + b"</" + tag + b">"
    xml = _member(base, STYLES)
    held = re.search(b"<" + tag + rb"(?: [^>]*)?(?:/>|>.*?</" + tag + b">)", xml, re.DOTALL)
    if held is not None:
        xml = xml[: held.start()] + block + xml[held.end() :]
    else:
        later = [
            found.start()
            for name in STYLE_ORDER[STYLE_ORDER.index(listing) + 1 :]
            if (found := re.search(b"<" + name.encode() + rb"[ />]", xml)) is not None
        ]
        at = later[0] if later else xml.index(b"</styleSheet>")
        xml = xml[:at] + block + xml[at:]
    return _rewritten(base, {STYLES: xml})


# The forms a part may name its elements in, which openpyxl reads alike by their local names: in no
# namespace, in another than SpreadsheetML, or each prefixed by a prefix bound to SpreadsheetML.
SPACINGS = ("none", "other", "prefixed")
_DEFAULT_SPACE = f'xmlns="{MAIN}"'.encode()
_UNPREFIXED = re.compile(rb"<(/?)([A-Za-z_][\w.-]*)(?=[\s/>])")


def edited(base: bytes, member: str, edit: Callable[[bytes], bytes]) -> bytes:
    """Give the workbook whose ``member`` is edited by ``edit``."""
    return _rewritten(base, {member: edit(_member(base, member))})


def respaced(base: bytes, member: str, spacing: str) -> bytes:
    """Give the workbook whose ``member``, of SpreadsheetML by default, names it by ``spacing``."""
    xml = _member(base, member)
    if xml.count(_DEFAULT_SPACE) != 1:
        msg = f"{member!r} declares SpreadsheetML by default other than once"
        raise ValueError(msg)
    match spacing:
        case "none":
            xml = xml.replace(_DEFAULT_SPACE, b"")
        case "other":
            xml = xml.replace(_DEFAULT_SPACE, b'xmlns="urn:x"')
        case _:
            xml = _UNPREFIXED.sub(rb"<\1x:\2", xml).replace(
                _DEFAULT_SPACE, f'xmlns:x="{MAIN}"'.encode()
            )
    return _rewritten(base, {member: xml})


def with_bare_hyperlink(base: bytes, member: str) -> bytes:
    """Give the workbook whose tab ``member`` holds, after its first row, a bare hyperlink.

    openpyxl reads it as it comes among the rows, and rejects it by a ``TypeError`` (#4848): the
    reading of the rows fails in their midst, a row following it, empty, if the tab has no other.
    """
    xml = _member(base, member)
    at = xml.index(b"</row>") + len(b"</row>")
    xml = xml[:at] + b"<hyperlinks><hyperlink/></hyperlinks><row/>" + xml[at:]
    return _rewritten(base, {member: xml})


def with_empty_fill(base: bytes) -> bytes:
    """Give the workbook whose fills end with ``<fill/>``, which openpyxl rejects (#4848)."""
    xml = _member(base, STYLES).replace(b"</fills>", b"<fill/></fills>", 1)
    return _rewritten(base, {STYLES: xml})


def named(base: bytes, count: int, sheet: str) -> bytes:
    """Give the workbook of ``count`` defined names, each a cell of the tab ``sheet``."""
    names = "".join(
        f"<definedName name=\"n{rank}\">'{sheet}'!$A$1</definedName>" for rank in range(count)
    )
    xml = re.sub(rb"<definedNames>.*?</definedNames>|<definedNames/>", b"", _member(base, WORKBOOK))
    xml = xml.replace(b"</sheets>", f"</sheets><definedNames>{names}</definedNames>".encode(), 1)
    return _rewritten(base, {WORKBOOK: xml})


def stuffed(base: bytes, member: str, before: bytes, element: bytes, count: int) -> bytes:
    """Give the workbook whose ``member`` holds ``count`` elements ``element`` more (US-3190b).

    They come before the first ``before`` the member holds, written by streams of a MiB: the
    workbooks of #4862, a ``<b/>`` in a font of ``styles.xml`` or a ``<x/>`` under the root of
    ``workbook.xml``, which openpyxl parses into a tree, out of any list bounded.
    """
    head, tail = _member(base, member).split(before, 1)
    per_write = max(1, MEBIBYTE // len(element))
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        _copied(base, target, but=member)
        with target.open(member, "w") as written:
            written.write(head)
            for start in range(0, count, per_write):
                written.write(element * min(per_write, count - start))
            written.write(before + tail)
    return out.getvalue()


def styled_richly(base: bytes, count: int) -> bytes:
    """Give the workbook whose ``dxfs`` hold ``count`` dxf as Excel writes them (``RICH_DXF``)."""
    return styled(base, "dxfs", count, lambda _: RICH_DXF)


def styled_in_full(base: bytes, lists: Mapping[str, int]) -> bytes:
    """Give the workbook whose lists of ``styles.xml`` each hold the items ``lists`` gives."""
    for listing, count in lists.items():
        base = styled(base, listing, count)
    return base


def linked_externally(
    base: bytes, member: str, data: bytes, *, referred: bool, bare: bool = False
) -> bytes:
    """Give the workbook with ``member`` more, named by a relation of its workbook typed a tab.

    The relation is ``rIdLinked``; when ``referred``, ``workbook.xml`` names it as an external link
    too, of which openpyxl parses the target into a tree whatever the type of the relation, by an
    ``r:id`` or, when ``bare``, an ``id`` of no namespace, which openpyxl takes as well; the target
    then has its relations, the path of the linked workbook, which openpyxl reads too.
    """
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    relations = "xl/_rels/workbook.xml.rels"
    relation = f'<Relationship Id="rIdLinked" Type="{office}/worksheet" Target="/{member}"/>'
    held = _member(base, relations).replace(
        b"</Relationships>", relation.encode() + b"</Relationships>"
    )
    xml = _member(base, WORKBOOK)
    written = {member: data, relations: held, WORKBOOK: xml}
    if referred:
        named = 'id="rIdLinked"' if bare else f'xmlns:r="{office}" r:id="rIdLinked"'
        reference = f"<externalReferences><externalReference {named}/>"
        written[WORKBOOK] = xml.replace(
            b"</sheets>", f"</sheets>{reference}</externalReferences>".encode(), 1
        )
        folder, name = member.rsplit("/", 1)
        path = (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1"'
            f' Type="{office}/externalLinkPath" Target="linked.xlsx" TargetMode="External"/>'
            "</Relationships>"
        )
        written[f"{folder}/_rels/{name}.rels"] = path.encode()
    return _rewritten(base, written)


def referring(base: bytes, member: str, references: int) -> bytes:
    """Give the workbook whose workbook part lies at ``member``, naming ``references`` links.

    The content types name it there, its relations follow it; it names the external links by ids
    no relation bears.
    """
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    folder, name = member.rsplit("/", 1)
    links = "".join(f'<externalReference r:id="rIdLink{rank}"/>' for rank in range(references))
    xml = _member(base, WORKBOOK).replace(
        b"</sheets>",
        f'</sheets><externalReferences xmlns:r="{office}">{links}</externalReferences>'.encode(),
        1,
    )
    relations = "xl/_rels/workbook.xml.rels"
    types = _member(base, CONTENT_TYPES).replace(f'"/{WORKBOOK}"'.encode(), f'"/{member}"'.encode())
    moved = {member: xml, f"{folder}/_rels/{name}.rels": _member(base, relations)}
    out = BytesIO()
    with (
        zipfile.ZipFile(BytesIO(base)) as source,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for item in source.infolist():
            if item.filename not in {WORKBOOK, relations, CONTENT_TYPES}:
                target.writestr(item, source.read(item.filename))
        for written, data in {**moved, CONTENT_TYPES: types}.items():
            target.writestr(written, data)
    return out.getvalue()


def tabulated(base: bytes, member: str, rows: int, columns: int) -> bytes:
    """Give the workbook whose tab ``member`` holds ``rows`` rows, ``columns`` wide.

    Its ``<dimension>`` says so, and empty rows ``<row/>`` follow its own up to ``rows``: openpyxl
    gives a row present, even empty, as a tuple as wide as the dimension, and stops at the last.
    """
    xml = _member(base, member).replace(b"<sheetData/>", b"<sheetData></sheetData>")
    reach = f'<dimension ref="A1:{get_column_letter(columns)}{rows}"/>'.encode()
    xml = re.sub(rb"<dimension [^>]*/>", reach, xml)
    added = rows - len(re.findall(rb"<row[ />]", xml))
    xml = xml.replace(b"</sheetData>", b"<row/>" * added + b"</sheetData>")
    return _rewritten(base, {member: xml})


# --- The resident size of a fresh process --------------------------------------------------------

# The readers a measure in a fresh process calls, by the name it is given across the processes.
READERS: dict[str, Callable[[bytes], Any]] = {
    "estimate": estimate_reader.read_workbook,
    "remaining": remaining_reader.read_remaining_workbook,
    "actual_costs": costs_reader.sheet_rows,
}


@dataclass(frozen=True)
class Resident:
    """What reading a workbook in a fresh process gave.

    ``outcome`` is ``read`` or the code of the refusal; ``rise``, in bytes, what the peak resident
    size of the process rose to since the reader was warmed, this read and those before it
    included; ``seconds``, its duration; ``traced``, the peak ``tracemalloc`` saw of this read
    alone, when asked.
    """

    outcome: str
    rise: int
    seconds: float
    traced: int | None = None


def _peak() -> int:
    """Give the peak resident size of this process, in bytes (Linux gives it in kibibytes)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _read_each(
    reader: str, base: bytes, contents: Sequence[bytes], *, traced: bool
) -> list[Resident]:
    """Read ``base`` to warm the reader, then each content: what each gave."""
    call = READERS[reader]
    call(base)
    gc.collect()
    before = _peak()
    found: list[Resident] = []
    for content in contents:
        if traced:
            tracemalloc.start()
        start = time.perf_counter()
        outcome = "read"
        try:
            call(content)
        except UnprocessableError as error:
            outcome = error.code
        seconds = time.perf_counter() - start
        peak = tracemalloc.get_traced_memory()[1] if traced else None
        tracemalloc.stop()
        found.append(Resident(outcome, _peak() - before, seconds, peak))
    return found


def resident(
    reader: str, base: bytes, contents: Sequence[bytes], *, traced: bool = False
) -> list[Resident]:
    """Read each content by ``reader`` in one fresh process, in order: what each gave.

    The process is spawned, not forked, so that it holds nothing of the caller's but its arguments;
    the reader is warmed on ``base`` before the peak is taken. The peak only rises: a content read
    after a heavier one is seen through it, so a caller orders them from the lightest.
    """
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        return pool.submit(_read_each, reader, base, tuple(contents), traced=traced).result()
