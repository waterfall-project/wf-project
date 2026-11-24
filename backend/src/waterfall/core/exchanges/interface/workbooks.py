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
10 MB in an attribute, which openpyxl's parser reads past), is refused — but a VML drawing, which
Excel writes not well formed and openpyxl does not parse where Excel names it, in the relations of a
worksheet or of a chartsheet. Its error is kept, not judged on its name: openpyxl reads a tab
wherever the relations of the workbook put it, ``sheet3.vml`` as ``sheet3.xml``. Once every member
is read, the parts openpyxl may parse are found as it finds them — the content types, the relations
of the workbook and those of each part they name, the drawings of a chartsheet and what their
relations name, their targets resolved as ``get_dependents`` does and compared as zipfile names its
members —, the parts naming others read by the hardened parser without a tree, keeping only names
of members; a VML drawing among them is refused on its error. Only then is the workbook opened,
read-only and by values.

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

The same reading counts the other vectors a workbook amplifies by (US-3190/L2b; EP-33, "Les bornes
des classeurs"), each bounded by the author on the measures of ``measure/workbooks.py``: the shared
strings — their number, the elements of one, the characters of their text —, wherever they lie, as
openpyxl's reader of them finds them; the items of each list of ``styles.xml``, which openpyxl
builds an object of each; the defined names of ``workbook.xml``. openpyxl reads these two parts by
the local names of their elements, whatever their namespace, and builds an item of a comment or an
instruction a list holds, or of an entity a document type leaves unresolved: the lists are counted
by their local names, where it reads them, comments and instructions included, and a part it may
parse that declares a document type is refused. Past a bound, the workbook is refused before it is
opened.

The items bounded are not all openpyxl builds: it parses ``styles.xml``, ``workbook.xml``, the
content types, the relations, the properties, a chartsheet and its drawings and charts whole, into a
tree, and each element costs it a node, in an item or out of any list — 25 kB of ``<b/>`` in a font
held 543 MiB (#4862). So the reading counts the elements of every member, comments and instructions
included, and once the parts openpyxl parses into a tree are found as it finds them, their elements
are added up: past ``MOST_ELEMENTS`` in all, the workbook is refused before it is opened
(US-3190b). The tabs and the shared strings, which openpyxl reads as a stream and the other bounds
hold, are left out, unless openpyxl parses them into a tree by another way; the theme too, which it
keeps as bytes.

A reader then materialises the tabs its format reads, and those alone, by the ``bounded_rows`` of
the workbook opened: a row of more than ``MOST_COLUMNS`` columns, as openpyxl gives them — the width
the places of the cells give —, is refused, and so are the tabs read past ``MOST_ROWS`` rows or
``MOST_CELLS`` cells in all, the rows a gap leaves included, counted as they come. That refusal
comes after the opening: the rows are those openpyxl gives, which the reading ahead would have to
reproduce, and none is held past the bounds.

Every refusal raises ``WorkbookOutOfBoundsError``, which ``DAMAGES`` lists: each reader turns it
into the refusal of its format, ``FILE_FORMAT_UNREADABLE``, as it does a damaged file. A
``TypeError`` openpyxl raises at the opening or at the reading of the rows, for a part of the wrong
kind, raises ``WorkbookDamagedError``, a ``ValueError`` that ``DAMAGES`` lists too (#4848).
"""

import posixpath
import zipfile
import zlib
from contextlib import contextmanager
from enum import Enum
from io import BytesIO
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Never

from lxml import etree
from openpyxl import load_workbook
from openpyxl.xml.constants import (
    ARC_CONTENT_TYPES,
    ARC_CORE,
    ARC_CUSTOM,
    ARC_STYLE,
    ARC_THEME,
    ARC_WORKBOOK,
    REL_NS,
    SHARED_STRINGS,
    XLSM,
    XLSX,
    XLTM,
    XLTX,
)

from waterfall.core.exchanges.interface.xml import hardened_target_parser

if TYPE_CHECKING:
    from collections.abc import Callable, Container, Generator, Iterable, Iterator, Mapping

    from lxml.etree._parser import CustomTargetParser
    from openpyxl.workbook.workbook import Workbook

# The bounds of the design (EP-33, "Les bornes des classeurs"): 200 MiB declared, twenty times the
# largest file deposited; 200 000 rows, ten times the 18 000 lines of cost of §4.6.2; 500 columns,
# for the columns kept of an extraction.
LARGEST_INFLATED = 200 * 1024 * 1024
MOST_MEMBERS = 1_000
MOST_ROWS = 200_000
MOST_COLUMNS = 500
# The other vectors, measured by US-3190/L2b and bounded by the author on 2026-11-23 (EP-33, "Les
# bornes des classeurs"). The tabs read, in cumul: 200 000 rows, and 10 000 000 cells, 8.3 bytes
# each to openpyxl. The shared strings: their number, the elements of one (its runs and what they
# hold), and their text, which Python holds up to four bytes a character, counted in characters.
MOST_CELLS = 10_000_000
MOST_STRINGS = 1_000_000
MOST_STRING_ELEMENTS = 65_536
LONGEST_TEXT = 32 * 1024 * 1024
# The items of each list of ``styles.xml``: the limits of Excel, so that a workbook Excel writes is
# never refused; ``colors``, the colours its lists hold, counted with them. The defined names of
# ``workbook.xml``.
STYLE_LISTS: Mapping[str, int] = MappingProxyType(
    {
        "numFmts": 1_000,
        "fonts": 1_024,
        "fills": 1_024,
        "borders": 1_024,
        "tableStyles": 1_024,
        "colors": 1_024,
        "cellStyleXfs": 65_490,
        "cellXfs": 65_490,
        "cellStyles": 65_490,
        "dxfs": 65_490,
    }
)
MOST_NAMES = 10_000
# The elements of the parts openpyxl parses into a tree, in all (US-3190b, decided by the author on
# 2026-11-24, #4862): some 110 bytes a node to openpyxl, some 110 MiB at the bound.
MOST_ELEMENTS = 1_000_000

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
# The row of SpreadsheetML, as openpyxl finds it wherever it lies (ECMA-376, §18.3.1.73); a shared
# string (§18.4.8), which it finds so too, by its tag, namespace included. The lists whose items are
# bounded, by their local name, where openpyxl reads them — a child of the root of the member, in
# any namespace or none, as ``Serialisable.from_tree`` reads ``styles.xml`` and ``workbook.xml`` —:
# their bound, and whether all they hold is counted (``colors``) or their children alone.
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_ROW = f"{_MAIN}row"
_STRING = f"{_MAIN}si"
_COLORS = "colors"
_LISTS = {
    name: (most, name == _COLORS)
    for name, most in {**STYLE_LISTS, "definedNames": MOST_NAMES}.items()
}
# The depth of a list openpyxl reads, the root of the member being at depth 1: a child of the root.
_LISTED_AT = 2
# How an XML document starts, past a UTF-8 byte order mark and blanks: its first tag, or the byte
# order mark or the first tag of UTF-16 (XML 1.0, appendix F). What the head of a member that
# libxml2 cannot start reading is judged on, as far as its first bytes go.
_UTF8_MARK = b"\xef\xbb\xbf"
_BLANKS = b" \t\r\n"
_XML_STARTS = (b"<", b"\xff\xfe", b"\xfe\xff", b"\x00<")
_HEAD = 4096
_VML = ".vml"
# What openpyxl's opening finds a part by (``openpyxl.reader.excel``): the content types, the fixed
# names it reads, the content types it looks the workbook and its shared strings up by, and the
# word that makes a relation of the workbook a chartsheet, and the type of the relations of a
# chartsheet it reads, its drawings (``SpreadsheetDrawing._rel_type``), whose charts it reads.
_CONTENT_TYPES = ARC_CONTENT_TYPES
_WORKBOOK = ARC_WORKBOOK
_FIXED = frozenset({ARC_CONTENT_TYPES, ARC_CORE, ARC_CUSTOM, ARC_STYLE, ARC_THEME, ARC_WORKBOOK})
_WORKBOOKS = frozenset({XLSX, XLSM, XLTX, XLTM})
_LOOKED_UP = _WORKBOOKS | {SHARED_STRINGS}
_CHARTSHEET = "chartsheet"
_DRAWING = f"{REL_NS}/drawing"
# The fixed names openpyxl parses into a tree: all but the theme, which it keeps as bytes. The list
# of the workbook whose children name, by the id of a relation, the external links it parses into a
# tree (``WorkbookParser.parse``), a child of the root in any namespace, as ``from_tree`` reads it;
# the attributes it takes their id from, that of the relationships' namespace before the bare one
# (``Serialisable.from_tree`` keeps an attribute of no namespace, and sets the namespaced over it).
_TREES = _FIXED - {ARC_THEME}
_REFERENCES = "externalReferences"
_RELATION_IDS = (f"{{{REL_NS}}}id", "id")


class _Relations(Enum):
    """Whose relations a part's are, as openpyxl's opening follows them.

    Those of a workbook name the parts it parses, and the chartsheets whose relations it follows;
    those of a chartsheet, its drawings alone, whose relations it follows; those of a drawing, the
    charts and images it reads, whose relations it parses and does not follow.
    """

    WORKBOOK = "workbook"
    CHARTSHEET = "chartsheet"
    DRAWING = "drawing"


type _Named = Callable[[dict[str, str]], tuple[str, _Relations | None, bool] | None]


class WorkbookOutOfBoundsError(ValueError):
    """A workbook, or a tab of it, beyond a bound: refused as a damaged workbook is."""


class WorkbookDamagedError(ValueError):
    """A workbook whose parts openpyxl rejects by a ``TypeError``: refused as a damaged one is.

    openpyxl's descriptors raise it for an element of the wrong kind, a ``<fill/>`` that holds no
    pattern (#4848). It is caught at the opening and at the reading of the rows alone, so that an
    error of a reader's own code is not taken for a damaged file.
    """


class _Target:
    """A target of the hardened parser that keeps nothing.

    It answers every call of lxml's ``ParserTarget``, and keeps no element, no text, no comment, no
    instruction.
    """

    def start(self, _tag: str, _attributes: dict[str, str], /) -> None:
        """Leave an element."""

    def end(self, _tag: str, /) -> None:
        """Leave the end of an element."""

    def close(self) -> None:
        """End the reading: nothing to give."""

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


class _Listing:
    """A list of bounded items open: its name, its depth, its bound, what it counts."""

    __slots__ = ("deep", "depth", "most", "name")

    def __init__(self, name: str, depth: int, most: int, *, deep: bool) -> None:
        self.name = name
        self.depth = depth
        self.most = most
        self.deep = deep


def _local(tag: str) -> str:
    """Give the local name of a tag, past its namespace, as openpyxl's ``localname`` does."""
    return tag.rpartition("}")[2]


class _Tally(_Target):
    """The target of the reading of a member: counts what a bound is judged on.

    Its rows, and the cells of each row: a row may lie in a row, as openpyxl reads it, so each row
    open keeps its depth and its cells. Its shared strings, wherever they lie, as openpyxl finds
    them; the elements of each, those of a string in it included; and the characters of their text.
    The items of a list bounded — of ``styles.xml``, the defined names —, a child of the root of
    whatever member, by its local name: its children, or all it holds for ``colors``, its comments
    and its processing instructions among them, which openpyxl's lxml gives as children and builds
    an item of (``NestedSequence``); a list in a list is an item of the first. The items of a list
    met twice add up. Whether the member declares a document type, under which an entity left
    unresolved is one more child to openpyxl and none to the reading. Its elements, comments and
    instructions included, each a node of the tree openpyxl may parse of it.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.started = False
        self.elements = 0
        self.depth = 0
        self.rows = 0
        self.open_rows: list[list[int]] = []
        self.strings = 0
        # The depth of the outermost string open, 0 out of any.
        self.string_at = 0
        self.string_elements = 0
        self.text = 0
        self.listing: _Listing | None = None
        self.items: dict[str, int] = {}
        self.typed = False

    def _refuse(self, what: str, most: int) -> Never:
        """Refuse the member past a bound: it holds more than ``most`` of ``what``."""
        msg = f"{self.name!r} holds more than {most} {what}"
        raise WorkbookOutOfBoundsError(msg)

    def start(self, tag: str, _attributes: dict[str, str], /) -> None:
        """Count an element: as a cell, a row, a string, an element of one, an item of a list."""
        self.started = True
        self.elements += 1
        self.depth += 1
        if self.open_rows and self.open_rows[-1][0] == self.depth - 1:
            self.open_rows[-1][1] += 1
            if self.open_rows[-1][1] > MOST_COLUMNS:
                msg = f"{self.name!r} holds a row of more than {MOST_COLUMNS} cells"
                raise WorkbookOutOfBoundsError(msg)
        if tag == _ROW:
            self.rows += 1
            if self.rows > MOST_ROWS:
                self._refuse("rows", MOST_ROWS)
            self.open_rows.append([self.depth, 0])
        if self.string_at or tag == _STRING:
            self._count_strings(tag)
        if self.listing is not None:
            self._count_item(self.depth - 1)
        elif self.depth == _LISTED_AT and (bounded := _LISTS.get(_local(tag))) is not None:
            self.listing = _Listing(_local(tag), self.depth, bounded[0], deep=bounded[1])

    def _count_item(self, parent: int) -> None:
        """Count a node of the list open whose parent lies at ``parent``, if it is an item."""
        listing = self.listing
        if listing is not None and (listing.deep or listing.depth == parent):
            count = self.items.get(listing.name, 0) + 1
            self.items[listing.name] = count
            if count > listing.most:
                self._refuse(f"items in {listing.name}", listing.most)

    def _count_strings(self, tag: str) -> None:
        """Count a shared string, and an element of the string open."""
        if tag == _STRING:
            self.strings += 1
            if self.strings > MOST_STRINGS:
                self._refuse("shared strings", MOST_STRINGS)
        if self.string_at:
            self.string_elements += 1
            if self.string_elements > MOST_STRING_ELEMENTS:
                self._refuse("elements in a shared string", MOST_STRING_ELEMENTS)
        elif tag == _STRING:
            self.string_at = self.depth
            self.string_elements = 0

    def data(self, text: str, /) -> None:
        """Count the characters of the text of a shared string; leave any other."""
        if self.string_at:
            self.text += len(text)
            if self.text > LONGEST_TEXT:
                self._refuse("characters of text in shared strings", LONGEST_TEXT)

    def comment(self, _text: str, /) -> None:
        """Count a comment as an element, and as an item of the list open: openpyxl builds one."""
        self.elements += 1
        self._count_item(self.depth)

    def pi(self, _target: str, _data: str, /) -> None:
        """Count a processing instruction as a comment is counted."""
        self.elements += 1
        self._count_item(self.depth)

    def doctype(self, _root: str | None, _public_id: str | None, _system_id: str | None, /) -> None:
        """Keep that the member declares a document type."""
        self.typed = True

    def end(self, _tag: str, /) -> None:
        """Close an element, and the row, the string or the list it is."""
        if self.open_rows and self.open_rows[-1][0] == self.depth:
            self.open_rows.pop()
        if self.string_at == self.depth:
            self.string_at = 0
        if self.listing is not None and self.listing.depth == self.depth:
            self.listing = None
        self.depth -= 1


class _Naming(_Target):
    """The target of the reading of a part that names others: keeps the members it names.

    ``named`` gives, from the attributes of an element, the member it names, as openpyxl finds it,
    and whose relations those of that member are when openpyxl follows them, ``None`` when it does
    not, and whether openpyxl parses it into a tree; ``None`` for an element that names no member
    openpyxl parses. A name no member bears is not kept: what is kept is at most the archive.
    """

    def __init__(self, named: _Named, members: Container[str]) -> None:
        self.named = named
        self.members = members
        self.parts: set[str] = set()
        self.trees: set[str] = set()
        self.followed: set[tuple[str, _Relations]] = set()

    def start(self, _tag: str, attributes: dict[str, str], /) -> None:
        """Keep the member an element names, if any, and whose relations it has if followed."""
        found = self.named(attributes)
        if found is not None and found[0] in self.members:
            self.parts.add(found[0])
            if found[2]:
                self.trees.add(found[0])
            if found[1] is not None:
                self.followed.add((found[0], found[1]))


class _Referring(_Target):
    """The target of the reading of a workbook part: keeps the relations its external links name.

    The ids of the children of ``externalReferences``, a child of the root, whatever their tag, as
    ``NestedSequence`` reads them, in the relationships' namespace or in none: both are kept, a
    superset of the one openpyxl takes. Each child is an element of a part openpyxl parses into a
    tree: past ``MOST_ELEMENTS`` of them, the workbook is refused before it holds more ids than
    twice as many.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.depth = 0
        self.within = False
        self.children = 0
        self.ids: set[str] = set()

    def start(self, tag: str, attributes: dict[str, str], /) -> None:
        """Keep the id of a child of the external references."""
        self.depth += 1
        if self.depth == _LISTED_AT:
            self.within = _local(tag) == _REFERENCES
        elif self.within and self.depth == _LISTED_AT + 1:
            self.children += 1
            if self.children > MOST_ELEMENTS:
                msg = f"{self.name!r} holds more than {MOST_ELEMENTS} elements"
                raise WorkbookOutOfBoundsError(msg)
            self.ids.update(attributes[key] for key in _RELATION_IDS if key in attributes)

    def end(self, _tag: str, /) -> None:
        """Close an element."""
        self.depth -= 1


class _Reading:
    """The reading of a member, fed step by step, without a tree.

    A syntax error in a VML drawing is left aside, its rows and cells, if it has any, counted until
    the error: the judgment of the archive refuses it only if openpyxl parses the member. The head
    is kept until the parser has started the document: a member libxml2 cannot start is read no
    further when its head does not start as XML does, and refused when it does.
    """

    def __init__(self, name: str) -> None:
        self.tally = _Tally(name)
        # Excel writes legacy VML drawings that are not well-formed XML (a ``<br>`` unclosed), which
        # openpyxl opens a workbook read-only without parsing: their syntax is judged by the parts.
        self.tolerant = name.lower().endswith(_VML)
        self.left: etree.XMLSyntaxError | None = None
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
        A VML drawing is left, its error kept for the judgment of the parts.
        """
        if self.tolerant:
            self.left = error
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


def _judge_member(content: bytes, member: zipfile.ZipInfo) -> _Reading:
    """Refuse a member beyond its declared size, or whose XML holds a row past a bound.

    Gives its reading: the syntax error a VML drawing was left on, if any, and whether it declares
    a document type.
    """
    reading = _Reading(member.filename)
    for step in _inflated(content, member):
        reading.feed(bytes(step))
    reading.close()
    return reading


def _relations_of(part: str) -> str:
    """Give the relations of a part, as openpyxl names them (``get_rels_path``)."""
    folder, name = posixpath.split(part)
    return posixpath.join(folder, "_rels", f"{name}.rels")


def _content_type(attributes: dict[str, str]) -> tuple[str, _Relations | None, bool] | None:
    """Give the part an override of the content types names, if openpyxl looks it up by its type.

    openpyxl takes its name past its first character, and follows the relations of a workbook,
    which it parses into a tree; its shared strings, it reads as a stream.
    """
    kind, part = attributes.get("ContentType"), attributes.get("PartName")
    if kind not in _LOOKED_UP or part is None:
        return None
    workbook = kind in _WORKBOOKS
    return part[1:], _Relations.WORKBOOK if workbook else None, workbook


def _followed(kind: str, of: _Relations) -> tuple[bool, _Relations | None]:
    """Give whether openpyxl parses the target of a relation of ``kind``, and follows its relations.

    It parses every target the relations of a workbook or of a drawing name, and follows the
    relations of a chartsheet; of the relations of a chartsheet, it parses and follows its drawings
    alone, as ``read_chartsheet`` does, and not its VML drawings (``legacyDrawing``,
    ``legacyDrawingHF``).
    """
    match of:
        case _Relations.WORKBOOK:
            return True, _Relations.CHARTSHEET if _CHARTSHEET in kind else None
        case _Relations.CHARTSHEET:
            drawing = kind == _DRAWING
            return drawing, _Relations.DRAWING if drawing else None
        case _Relations.DRAWING:
            return True, None


def _relation(relations: str, of: _Relations, linked: Container[str] = ()) -> _Named:
    """Give how an element of ``relations`` names a member, as openpyxl's ``get_dependents`` does.

    A target is taken as it is when external, past its slash when absolute, and joined to the folder
    of the part otherwise, then normalised; it is named when openpyxl parses it (``_followed``).
    Of the targets of a workbook, openpyxl parses into a tree its chartsheets, and the external
    links its ids ``linked`` name, whatever their type; its tabs, its shared strings, it reads as a
    stream, and the rest not at all. It parses into a tree every target it parses of the others.
    """
    folder = posixpath.dirname(posixpath.dirname(relations))

    def named(attributes: dict[str, str]) -> tuple[str, _Relations | None, bool] | None:
        target = attributes.get("Target")
        kind = attributes.get("Type", "")
        parsed, followed = _followed(kind, of)
        if target is None or not parsed:
            return None
        external = attributes.get("TargetMode") == "External"
        if not external and target.startswith("/"):
            target = target[1:]
        elif not external:
            target = posixpath.normpath(posixpath.join(folder, target))
        linking = attributes.get("Id", "") in linked
        return target, followed, of != _Relations.WORKBOOK or _CHARTSHEET in kind or linking

    return named


def _parsed_parts(content: bytes, members: list[zipfile.ZipInfo]) -> tuple[set[str], set[str]]:
    """Give the members openpyxl's opening, read-only, may parse, and those it parses into a tree.

    Each a superset of those it parses so. openpyxl finds them by fixed names, by the content types
    (the workbook and its shared strings), by the relations of the workbook (its tabs, read as tabs
    whatever their name, the relations of each, the other parts it names, the external links it
    names by their ids) and, from a chartsheet, by its drawings and what their relations name; the
    relations of a worksheet and of a chartsheet, where Excel names its VML drawings, it parses
    without parsing those. Each part that names others is read by the hardened parser, without a
    tree, at most once for each kind of relations it may hold.
    """
    by_name = {member.filename: member for member in members}

    def read(part: str, target: _Target) -> None:
        member = by_name.get(part)
        if member is not None:
            parser = hardened_target_parser(target)
            for step in _inflated(content, member):
                parser.feed(bytes(step))
            parser.close()

    def named_by(part: str, named: _Named) -> _Naming:
        naming = _Naming(named, by_name)
        read(part, naming)
        return naming

    found = named_by(_CONTENT_TYPES, _content_type)
    parsed = {*_FIXED, *found.parts}
    trees = {*_TREES, *found.trees}
    pending = [*found.followed, (_WORKBOOK, _Relations.WORKBOOK)]
    seen: set[tuple[str, _Relations]] = set()
    while pending:
        part, of = pending.pop()
        relations = _relations_of(part)
        if (relations, of) in seen:
            continue
        seen.add((relations, of))
        referring = _Referring(part)
        if of == _Relations.WORKBOOK:
            read(part, referring)
        found = named_by(relations, _relation(relations, of, referring.ids))
        parsed |= {relations, *found.parts, *map(_relations_of, found.parts)}
        trees |= {relations, *found.trees, *map(_relations_of, found.parts)}
        pending.extend(found.followed)
    return parsed, trees


def _judge_archive(content: bytes) -> None:
    """Refuse a workbook whose archive is beyond the bounds, before openpyxl reads any of it.

    Raises ``WorkbookOutOfBoundsError`` for the bounds, ``zipfile.BadZipFile`` or ``zlib.error``
    for a file that is no zip or whose member is damaged, ``etree.XMLSyntaxError`` for a member
    whose XML is damaged, a VML drawing included when openpyxl may parse it: all of them in
    ``DAMAGES``. A part openpyxl may parse that declares a document type is refused by the bounds:
    Excel writes none, and an entity it leaves unresolved, which the reading does not see, is an
    item to openpyxl's lxml in a list of ``styles.xml``. So are the parts it parses into a tree
    whose elements add up past ``MOST_ELEMENTS``, those of two members of one name included.
    """
    with zipfile.ZipFile(BytesIO(content)) as archive:
        members = archive.infolist()
    _judge_directory(members)
    left: dict[str, etree.XMLSyntaxError] = {}
    typed: set[str] = set()
    elements: dict[str, int] = {}
    for member in members:
        reading = _judge_member(content, member)
        if reading.left is not None:
            left.setdefault(member.filename, reading.left)
        if reading.tally.typed:
            typed.add(member.filename)
        elements[member.filename] = elements.get(member.filename, 0) + reading.tally.elements
    # The parts of fixed names first, so that the parts naming others are not read past the bound.
    _judge_elements(elements, _TREES)
    parsed, trees = _parsed_parts(content, members)
    for name in left.keys() & parsed:
        raise left[name]
    for name in typed & parsed:
        msg = f"{name!r} declares a document type"
        raise WorkbookOutOfBoundsError(msg)
    _judge_elements(elements, trees)


def _judge_elements(elements: Mapping[str, int], trees: Iterable[str]) -> None:
    """Refuse the parts ``trees`` openpyxl parses into a tree, past ``MOST_ELEMENTS`` in all."""
    if sum(elements.get(name, 0) for name in trees) > MOST_ELEMENTS:
        msg = f"the parts openpyxl parses into a tree hold more than {MOST_ELEMENTS} elements"
        raise WorkbookOutOfBoundsError(msg)


class OpenedWorkbook:
    """A workbook ``opened_workbook`` opened: its tabs, and the rows read of them, in cumul."""

    def __init__(self, workbook: Workbook) -> None:
        self._workbook = workbook
        self.rows = 0
        self.cells = 0

    @property
    def worksheets(self) -> list[Any]:
        """Give the tabs of the workbook, in their order: openpyxl's read-only worksheets."""
        return self._workbook.worksheets

    def bounded_rows(self, rows: Iterable[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
        """Materialise the rows of a tab, refused past a row of ``MOST_COLUMNS`` columns.

        The rows are those openpyxl gives (``iter_rows(values_only=True)``), each as wide as the tab
        says it is. They are counted with those of every tab read before them from this workbook:
        past ``MOST_ROWS`` rows or ``MOST_CELLS`` cells in all, the row is refused as it comes,
        before the next is read, so that what is held stays within the bounds (EP-33, "Les bornes
        des classeurs"). A ``TypeError`` of openpyxl while it reads them is a damaged workbook.
        """
        kept: list[tuple[Any, ...]] = []
        try:
            for row in rows:
                if len(row) > MOST_COLUMNS:
                    msg = f"a row of more than {MOST_COLUMNS} cells in a tab read"
                    raise WorkbookOutOfBoundsError(msg)
                self.rows += 1
                self.cells += len(row)
                if self.rows > MOST_ROWS:
                    msg = f"the tabs read hold more than {MOST_ROWS} rows in cumul"
                    raise WorkbookOutOfBoundsError(msg)
                if self.cells > MOST_CELLS:
                    msg = f"the tabs read hold more than {MOST_CELLS} cells in cumul"
                    raise WorkbookOutOfBoundsError(msg)
                kept.append(row)
        except TypeError as error:
            msg = f"openpyxl rejects a row: {error}"
            raise WorkbookDamagedError(msg) from error
        return kept


@contextmanager
def opened_workbook(content: bytes) -> Generator[OpenedWorkbook]:
    """Open a workbook deposited, read-only and by values, once its archive is judged; close it.

    Whatever the judgment or openpyxl raises is the caller's to turn into its refusal, by
    ``DAMAGES``: in read-only mode the XML of a tab is parsed while iterating, so the reading of the
    rows, by ``bounded_rows``, belongs inside the ``with``. A ``TypeError`` of openpyxl at the
    opening is a damaged workbook (#4848).
    """
    _judge_archive(content)
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except TypeError as error:
        msg = f"openpyxl rejects a part: {error}"
        raise WorkbookDamagedError(msg) from error
    try:
        yield OpenedWorkbook(workbook)
    finally:
        workbook.close()
