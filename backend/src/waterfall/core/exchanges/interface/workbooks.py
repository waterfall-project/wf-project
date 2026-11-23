# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The opener of a workbook a user deposited: the only one every reader of a workbook employs.

A workbook is a zip, whose members openpyxl inflates whole — its theme, its styles, its shared
strings — before a single row is read: ten mebibytes deposited may hold gigabytes once inflated
(#4419). So the opener judges the archive before openpyxl sees it (US-3190; EP-33, "Les bornes
des classeurs"): first its directory, ``infolist()``, without inflating anything — more than
``MOST_MEMBERS`` members, or more than ``LARGEST_INFLATED`` bytes of sizes declared, is refused —,
then each member the size it declares. zipfile cuts a member at its declared size, but only once it
has inflated it: ``ZipFile.read`` inflates a member whole in one call, so a member that declares
7 000 bytes and inflates to 64 MiB holds 64 MiB before the cut — and passes, when its CRC is that
of its first 7 000 bytes. The opener inflates each member by bounded steps, never more than one
byte past what it declares, and refuses one that holds more; a member neither stored nor deflated,
whose inflation zipfile does not bound, or encrypted, is refused too (Excel writes none).

The sizes do not hold the memory: openpyxl materialises a row whole — an element, then a dict per
cell — before cutting it to the width ``<dimension>`` declares, and a workbook of 13 705 bytes
whose row holds 2 000 000 empty cells ``<c/>`` takes 583 MiB (#4734). So each step inflated is
fed, as it comes, to the hardened XML parser of the exchanges given a target that builds no tree
(US-3190/L1b; EP-33, "Les bornes des classeurs"): it counts the rows of each member and the
elements of each row — every element a row holds, empty or not, being a cell to openpyxl — and
refuses past ``MOST_ROWS`` rows or ``MOST_COLUMNS`` cells in a row. Every member is read so, and
not the tabs a format reads alone: openpyxl reaches a tab by the relations the file itself names,
which the opener would have to resolve as openpyxl does, and its opening parses every tab, read
or not, up to its ``<dimension>`` or to its end when it has none. A member libxml2 cannot start
reading is read no further when it does not start as XML does (an image, a binary); one that
starts as XML and is not well formed, or that the hardened parser refuses (a value of more than
10 MB in an attribute, which openpyxl's parser reads past), is refused. Only then is the workbook
opened, read-only and by values.

An archive in ZIP64 — the sizes and the offsets of its members in their extra field, the end of its
directory in a record of 64 bits — is judged as any other, and none is refused for it: zipfile reads
the sizes its directory declares there, which the bounds judge, and the opener steps over the
extra field of each local header. Excel writes none under 4 GiB; a member that announces beyond the
bound through its ZIP64 field is refused by the bound.

The cost, accepted: the check inflates once each deflated member, which openpyxl may inflate again
if it reads it, and it is replayed at each judgment of a file (the header, the analysis, the
application), so a workbook at the bound, 200 MiB declared, inflates up to 200 MiB per judgment, a
step of a mebibyte at a time and never held (a member of spaces, which inflates fast, costs a
fraction of a second, as ``tests/workbook_bombs.py`` builds them; #4740), and it reads each XML
member once more than openpyxl does: some 150 ms for an extraction of 18 000 lines of cost that
openpyxl reads in 650 ms, some three million cells a second (measured on rows of 500 empty
``<c/>``, 13 MiB a second), so some fifteen seconds a judgment, three judgments an import, for
200 MiB of empty cells. The bound of the sizes is a worst case, which a user may reach only by
depositing a file that is refused anyway, and no bound could be had without inflating.

A reader then materialises the tabs its format reads, and those alone, by ``bounded_rows``: a tab
of more than ``MOST_ROWS`` rows or ``MOST_COLUMNS`` columns, as openpyxl gives them — the rows a
gap leaves, and the width the places of the cells give —, is refused.

Every refusal raises ``WorkbookOutOfBoundsError``, which ``DAMAGES`` lists: each reader turns it
into the refusal of its format, ``FILE_FORMAT_UNREADABLE``, as it does a damaged file.
"""

import zipfile
import zlib
from contextlib import contextmanager
from io import BytesIO
from typing import TYPE_CHECKING, Any

from lxml import etree
from openpyxl import load_workbook

from waterfall.core.exchanges.interface.xml import hardened_target_parser

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Iterator

    from lxml.etree._parser import CustomTargetParser
    from openpyxl.workbook.workbook import Workbook

# The bounds of the design (EP-33, "Les bornes des classeurs"): 200 MiB declared, twenty times the
# largest file deposited; 200 000 rows, ten times the 18 000 lines of cost of §4.6.2; 500 columns,
# for the columns kept of an extraction.
LARGEST_INFLATED = 200 * 1024 * 1024
MOST_MEMBERS = 1_000
MOST_ROWS = 200_000
MOST_COLUMNS = 500

# The steps of the inflation of a member: what is fed, and the most that one step gives.
_FED = 64 * 1024
_STEP = 1024 * 1024
# The local header of a member (APPNOTE 4.3.7): its signature, its fixed length, and where the
# lengths of its name and of its extra field are.
_LOCAL_SIGNATURE = b"PK\x03\x04"
_LOCAL_LENGTH = 30
_NAME_LENGTH_AT = 26
_EXTRA_LENGTH_AT = 28
_ENCRYPTED = 0x1
# The row of SpreadsheetML, as openpyxl finds it wherever it lies (ECMA-376, §18.3.1.73).
_ROW = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"
# How an XML document starts, past a UTF-8 byte order mark and blanks: its first tag, or the byte
# order mark or the first tag of UTF-16 (XML 1.0, appendix F). What the head of a member that
# libxml2 cannot start reading is judged on, as far as its first bytes go.
_UTF8_MARK = b"\xef\xbb\xbf"
_BLANKS = b" \t\r\n"
_XML_STARTS = (b"<", b"\xff\xfe", b"\xfe\xff", b"\x00<")
_HEAD = 4096
_VML = ".vml"


class WorkbookOutOfBoundsError(ValueError):
    """A workbook, or a tab of it, beyond a bound: refused as a damaged workbook is."""


class _Tally:
    """The target of the reading of a member: counts its rows, and the cells of each row.

    A row may lie in a row, as openpyxl reads it: each row open keeps its depth and its cells. The
    target answers every call of a parser target (lxml's ``ParserTarget``); it keeps no text, no
    comment, no instruction.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.started = False
        self.depth = 0
        self.rows = 0
        self.open_rows: list[list[int]] = []

    def start(self, tag: str, _attributes: dict[str, str], /) -> None:
        """Count an element: a cell of the row it lies in, if any, and a row if it is one."""
        self.started = True
        self.depth += 1
        if self.open_rows and self.open_rows[-1][0] == self.depth - 1:
            self.open_rows[-1][1] += 1
            if self.open_rows[-1][1] > MOST_COLUMNS:
                msg = f"{self.name!r} holds a row of more than {MOST_COLUMNS} cells"
                raise WorkbookOutOfBoundsError(msg)
        if tag == _ROW:
            self.rows += 1
            if self.rows > MOST_ROWS:
                msg = f"{self.name!r} holds more than {MOST_ROWS} rows"
                raise WorkbookOutOfBoundsError(msg)
            self.open_rows.append([self.depth, 0])

    def end(self, _tag: str, /) -> None:
        """Close an element, and the row it is."""
        if self.open_rows and self.open_rows[-1][0] == self.depth:
            self.open_rows.pop()
        self.depth -= 1

    def close(self) -> None:
        """End the reading: nothing to give, the counts having refused as they came."""

    def data(self, _text: str, /) -> None:
        """Leave a text: no cell of openpyxl's lies in one."""

    def comment(self, _text: str, /) -> None:
        """Leave a comment: openpyxl's parser of a tab reads none."""

    def pi(self, _target: str, _data: str, /) -> None:
        """Leave a processing instruction: openpyxl's parser of a tab reads none."""

    def start_ns(self, _prefix: str, _uri: str, /) -> None:
        """Leave the declaration of a namespace: the tags come already qualified."""

    def end_ns(self, _prefix: str, /) -> None:
        """Leave the end of a namespace."""

    def doctype(self, _root: str | None, _public_id: str | None, _system_id: str | None, /) -> None:
        """Leave a document type: the hardened parser loads none."""


class _Reading:
    """The reading of a member, fed step by step, without a tree.

    A syntax error is no refusal in a VML drawing, which openpyxl does not parse; its rows and
    cells, if it has any, are counted until the error. The head is kept until the parser has started
    the document: a member libxml2 cannot start is read no further when its head does not start as
    XML does, and refused when it does.
    """

    def __init__(self, name: str) -> None:
        self.tally = _Tally(name)
        # openpyxl opens a workbook read-only without ever parsing a VML drawing, and Excel writes
        # legacy ones that are not well-formed XML (a ``<br>`` unclosed): its syntax is no refusal.
        self.is_parsed = not name.lower().endswith(_VML)
        self.parser: CustomTargetParser[None] | None = hardened_target_parser(self.tally)
        self.head = b""

    def feed(self, step: bytes) -> None:
        """Feed a step inflated of the member, unless its reading has been left."""
        if self.parser is None:
            return
        if not self.tally.started and len(self.head) < _HEAD:
            self.head += step[: _HEAD - len(self.head)]
        try:
            self.parser.feed(step)
        except etree.XMLSyntaxError as error:
            self._leave_or_refuse(error)

    def close(self) -> None:
        """End the reading of the member."""
        if self.parser is None:
            return
        try:
            self.parser.close()
        except etree.XMLSyntaxError as error:
            self._leave_or_refuse(error)

    def _leave_or_refuse(self, error: etree.XMLSyntaxError) -> None:
        """Leave a member that is no XML; refuse one begun, or that starts as XML does.

        A head of blanks alone, as long as the head kept, is refused too: what follows is unseen.
        """
        if not self.is_parsed:
            self.parser = None
            return
        head = self.head.removeprefix(_UTF8_MARK).lstrip(_BLANKS)
        blank = not head and len(self.head) == _HEAD
        if self.tally.started or blank or head.startswith(_XML_STARTS):
            raise error
        self.parser = None


def _judge_directory(members: list[zipfile.ZipInfo]) -> None:
    """Refuse a directory of too many members, or whose declared sizes add up beyond the bound."""
    if len(members) > MOST_MEMBERS:
        msg = f"{len(members)} members, more than {MOST_MEMBERS}"
        raise WorkbookOutOfBoundsError(msg)
    declared = sum(member.file_size for member in members)
    if declared > LARGEST_INFLATED:
        msg = f"{declared} bytes declared, more than {LARGEST_INFLATED}"
        raise WorkbookOutOfBoundsError(msg)


def _stream_of(content: bytes, member: zipfile.ZipInfo) -> memoryview:
    """Give the compressed bytes of a member, after its local header (APPNOTE 4.3.7)."""
    at = member.header_offset
    if content[at : at + len(_LOCAL_SIGNATURE)] != _LOCAL_SIGNATURE:
        msg = f"no local header for {member.filename!r}"
        raise zipfile.BadZipFile(msg)
    name = int.from_bytes(content[at + _NAME_LENGTH_AT : at + _NAME_LENGTH_AT + 2], "little")
    extra = int.from_bytes(content[at + _EXTRA_LENGTH_AT : at + _EXTRA_LENGTH_AT + 2], "little")
    start = at + _LOCAL_LENGTH + name + extra
    return memoryview(content)[start : start + member.compress_size]


def _beyond(member: zipfile.ZipInfo) -> WorkbookOutOfBoundsError:
    """Give the refusal of a member that inflates to more than it declares."""
    msg = f"{member.filename!r} inflates beyond the {member.file_size} bytes it declares"
    return WorkbookOutOfBoundsError(msg)


def _inflated(content: bytes, member: zipfile.ZipInfo) -> Iterator[bytes | memoryview]:
    """Give a member inflated, a step at most at a time, refused once past what it declares."""
    if member.flag_bits & _ENCRYPTED:
        msg = f"{member.filename!r} is encrypted"
        raise WorkbookOutOfBoundsError(msg)
    if member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
        msg = f"{member.filename!r} is compressed by method {member.compress_type}"
        raise WorkbookOutOfBoundsError(msg)
    stream = _stream_of(content, member)
    if member.compress_type == zipfile.ZIP_STORED:
        # A stored member is read as it lies in the file, cut by zipfile to the size it declares.
        stored = stream[: member.file_size]
        for start in range(0, len(stored), _STEP):
            yield stored[start : start + _STEP]
        return
    inflater = zlib.decompressobj(-zlib.MAX_WBITS)
    inflated = 0
    for start in range(0, len(stream), _FED):
        pending: bytes | memoryview = stream[start : start + _FED]
        while pending and not inflater.eof:
            step = inflater.decompress(pending, min(_STEP, member.file_size + 1 - inflated))
            inflated += len(step)
            if inflated > member.file_size:
                raise _beyond(member)
            yield step
            pending = inflater.unconsumed_tail
        if inflater.eof:
            return
    # What a step left inflated with no input to feed: the end of the last match.
    while not inflater.eof:
        step = inflater.decompress(b"", min(_STEP, member.file_size + 1 - inflated))
        if not step:
            return
        inflated += len(step)
        if inflated > member.file_size:
            raise _beyond(member)
        yield step


def _judge_member(content: bytes, member: zipfile.ZipInfo) -> None:
    """Refuse a member beyond its declared size, or whose XML holds a row past a bound."""
    reading = _Reading(member.filename)
    for step in _inflated(content, member):
        reading.feed(bytes(step))
    reading.close()


def _judge_archive(content: bytes) -> None:
    """Refuse a workbook whose archive is beyond the bounds, before openpyxl reads any of it.

    Raises ``WorkbookOutOfBoundsError`` for the bounds, ``zipfile.BadZipFile`` or ``zlib.error``
    for a file that is no zip or whose member is damaged, ``etree.XMLSyntaxError`` for a member
    whose XML is damaged: all of them in ``DAMAGES``.
    """
    with zipfile.ZipFile(BytesIO(content)) as archive:
        members = archive.infolist()
    _judge_directory(members)
    for member in members:
        _judge_member(content, member)


@contextmanager
def opened_workbook(content: bytes) -> Generator[Workbook]:
    """Open a workbook deposited, read-only and by values, once its archive is judged; close it.

    Whatever the judgment or openpyxl raises is the caller's to turn into its refusal, by
    ``DAMAGES``: in read-only mode the XML of a tab is parsed while iterating, so the reading of the
    rows belongs inside the ``with``.
    """
    _judge_archive(content)
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        yield workbook
    finally:
        workbook.close()


def bounded_rows(rows: Iterable[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    """Materialise the rows of a tab, refused past ``MOST_ROWS`` rows or ``MOST_COLUMNS`` columns.

    The rows are those openpyxl gives (``iter_rows(values_only=True)``), each as wide as the tab
    says it is: a row past a bound is refused as it comes, before the next is read.
    """
    kept: list[tuple[Any, ...]] = []
    for row in rows:
        if len(kept) == MOST_ROWS:
            msg = f"a tab of more than {MOST_ROWS} rows"
            raise WorkbookOutOfBoundsError(msg)
        if len(row) > MOST_COLUMNS:
            msg = f"a tab of more than {MOST_COLUMNS} columns"
            raise WorkbookOutOfBoundsError(msg)
        kept.append(row)
    return kept
