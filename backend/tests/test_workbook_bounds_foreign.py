# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The elements of the tabs and of the shared strings out of place, bounded (US-3190/L3, #4915).

openpyxl reads a tab, and the shared strings, as a stream that frees a row, a string, once read,
and keeps the rest: 3 000 000 ``<x/>`` under the root of a tab, or under ``<sst>``, held some
250 MiB more, a row bounded, a string bounded, none of them past a bound. The reading ahead of the
opener counts the elements of every tab, read or not — openpyxl's opening parses a tab of no
``<dimension>`` to the end of its rows —, out of the rows of its ``sheetData`` and their cells, and
those of the shared strings out of their strings: past 100 000 in all, the workbook is refused
before it is opened, ``FILE_FORMAT_UNREADABLE``. The elements the cells of a row hold are freed
with the row: they are bounded by row, at 65 536, as the elements of a string are, for ``v`` and
``f`` reach 20 000 000 at the bound of the cells.

The memory is the peak resident size of a fresh process, ``VmHWM`` (``resident``).
"""

import re
import zipfile
from functools import cache
from io import BytesIO

import pytest
from lxml import etree
from test_workbook_bounds import PROTOTYPES, READINGS, UNREADABLE
from workbook_bombs import (
    CALM,
    STRINGS,
    Rows,
    appended,
    edited,
    grown,
    relocated,
    resident,
    shared_strings,
    stuffed,
    tab,
    with_relations,
)

from waterfall.core.estimate.excel import reader as estimate_reader
from waterfall.core.estimate.remaining.excel import reader as remaining_reader
from waterfall.core.exchanges.interface import MOST_CELL_ELEMENTS, MOST_FOREIGN, workbooks
from waterfall.platform.errors import UnprocessableError

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
FOREIGN = b"<x/>"
REFUSAL = f"hold more than {MOST_FOREIGN} elements out of place"
CELLS_REFUSAL = f"holds more than {MOST_CELL_ELEMENTS} elements in the cells of a row"
# The workbooks of #4915: 3 000 000 ``<x/>``, under the root of a tab read, under ``<sst>``, in a
# cell of a tab read, under the root of a tab not read, of no ``<dimension>``, before its rows.
SWOLLEN = 3_000_000
SWELLINGS = ("under-a-tab-read", "under-the-strings", "in-a-cell", "under-a-tab-not-read")
# The rows nested of the review of US-3190/L3: 100 rows, each in a cell of the one before, each
# cell holding 65 000 ``<x/>``, which held 540 MiB more when each row had a bound of its own.
NESTED = (100, 65_000)
# The tabs found by their relation alone: of a type openpyxl does not know, by a target relative to
# the folder of the workbook, by an absolute one; each the member it names, and the target.
UNKNOWN_TYPE = "http://example.com/relationships/unknown"
RELATED = {
    "of-a-type-unknown": ("xl/worksheets/x.xml", "/xl/worksheets/x.xml"),
    "by-a-relative-target": ("worksheets/x.xml", "../worksheets/x.xml"),
    "by-an-absolute-target": ("xl/worksheets/x.xml", "/xl/worksheets/x.xml"),
}
# A chain of calculation, which the relations of a workbook name and openpyxl does not read.
CHAIN = (
    b'<calcChain xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    + b'<c r="A1" i="1"/>' * 1_000
    + b"</calcChain>"
)


@cache
def _base(name: str) -> bytes:
    return READINGS[name].base()


def _unread(name: str) -> tuple[bytes, str]:
    """Give the base with a tab its format does not read, of no ``<dimension>``, and its member."""
    title = READINGS[name].unread[-1]
    content = grown(_base(name), title, 1, 1)
    member = tab(content, title)
    return edited(content, member, lambda xml: re.sub(rb"<dimension [^>]*/>", b"", xml)), member


@cache
def _swollen(name: str, swelling: str, count: int = SWOLLEN) -> bytes:
    base = _base(name)
    read = tab(base, READINGS[name].read[0])
    match swelling:
        case "under-a-tab-read":
            return stuffed(base, read, b"</worksheet>", FOREIGN, count)
        case "under-the-strings":
            return stuffed(shared_strings(base, 1), STRINGS, b"</sst>", FOREIGN, count)
        case "in-a-cell":
            return stuffed(base, read, b"</c>", FOREIGN, count)
        case _:
            content, member = _unread(name)
            return stuffed(content, member, b"<sheetData", FOREIGN, count)


def _never_opened(*_: object, **__: object) -> None:
    msg = "the workbook was opened"
    raise AssertionError(msg)


def _refused_unopened(
    content: bytes, monkeypatch: pytest.MonkeyPatch, name: str = "estimate"
) -> str:
    """Give what a format refuses ``content`` on, before the opening."""
    reading = READINGS[name]
    with monkeypatch.context() as patched:
        patched.setattr(workbooks, "load_workbook", _never_opened)
        with pytest.raises(UnprocessableError) as raised:
            reading.whole(content)
    assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
    return str(raised.value.__cause__)


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("swelling", SWELLINGS)
@pytest.mark.parametrize("name", list(READINGS))
def test_the_workbooks_of_4915_are_refused_before_the_opening_naming_their_format(
    name: str, swelling: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « … au-delà de laquelle l'import échoue avant l'ouverture sur `FILE_FORMAT_UNREADABLE` » :
    # elements openpyxl's stream would keep, or hold with a row, out of any other bound.
    refused = _refused_unopened(_swollen(name, swelling), monkeypatch, name)
    assert (CELLS_REFUSAL if swelling == "in-a-cell" else REFUSAL) in refused


@pytest.mark.story("US-3190")
def test_the_workbooks_of_4915_are_refused_within_the_memory() -> None:
    # « … sans que la mémoire réelle du processus ne passe la borne que le test fixe » : one fresh
    # process, the refusals, each under what a refusal before any inflation allocates.
    swollen = [_swollen("estimate", swelling) for swelling in SWELLINGS]
    found = resident("estimate", _base("estimate"), swollen)
    assert [each.outcome for each in found] == [UNREADABLE] * len(SWELLINGS)
    assert max(each.rise for each in found) < CALM


def _out_of(member: bytes, place: str) -> int:
    """Give the elements of ``member`` neither a ``place`` nor in one, as lxml builds them."""
    return sum(
        1
        for element in etree.fromstring(member).iter(etree.Element)
        if next(element.iterancestors(place), None) is None and element.tag != place
    )


def _out_of_place(content: bytes, tabs: tuple[str, ...]) -> int:
    """Give the elements of ``tabs`` out of their rows, and of the shared strings out of theirs."""
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = archive.namelist()
        found = sum(_out_of(archive.read(member), f"{_MAIN}row") for member in tabs)
        if STRINGS in names:
            found += _out_of(archive.read(STRINGS), f"{_MAIN}si")
    return found


@pytest.mark.story("US-3190")
def test_the_elements_counted_out_of_place_are_those_of_every_tab_and_of_the_shared_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The bound set at the elements out of place, the workbook is read; one below, refused: every
    # tab is counted, a tab not read among them, and the shared strings; the cells and what they
    # hold are not, nor a part the workbook names without a sheet naming it, which openpyxl does not
    # read as a tab (a chain of calculation of 1 000 cells, out of any row).
    content, unread = _unread("estimate")
    content = stuffed(shared_strings(content, 2), STRINGS, b"</sst>", FOREIGN, 10)
    content = with_relations(
        content, {"xl/calcChain.xml": CHAIN}, {"xl/workbook.xml": "calcChain calcChain.xml"}
    )
    tabs = (*(tab(content, title) for title in ("Présentation", "Tâches", "1 Études")), unread)
    counted = _out_of_place(content, tabs)
    monkeypatch.setattr(workbooks, "MOST_FOREIGN", counted)
    READINGS["estimate"].whole(content)
    monkeypatch.setattr(workbooks, "MOST_FOREIGN", counted - 1)
    assert f"hold more than {counted - 1} elements out of place" in _refused_unopened(
        content, monkeypatch
    )


def _rows_holding(elements: int, rows: int = 1) -> bytes:
    """Give the estimate whose tab of lines ends with ``rows`` rows of a cell of ``elements``."""
    base = _base("estimate")
    cell = b"<c>" + FOREIGN * elements + b"</c>"
    return appended(base, tab(base, "1 Études"), Rows(count=rows, cells=1, cell=cell))


@pytest.mark.story("US-3190")
def test_the_elements_the_cells_of_a_row_hold_are_bounded_by_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The cells of a row may hold ``MOST_CELL_ELEMENTS`` elements, and every row as many, which
    # openpyxl frees with the row; one more in a row is refused before the opening.
    READINGS["estimate"].whole(_rows_holding(MOST_CELL_ELEMENTS, rows=2))
    refused = _refused_unopened(_rows_holding(MOST_CELL_ELEMENTS + 1), monkeypatch)
    assert CELLS_REFUSAL in refused


def _related(relation: str, count: int = SWOLLEN) -> bytes:
    """Give the estimate whose tab of lines lies where ``relation`` puts it, ``count`` ``<x/>`` in.

    They lie in its ``sheetData``, out of any row; the relation keeps its id, which a sheet names.
    """
    base = _base("estimate")
    member = tab(base, "1 Études")
    to, target = RELATED[relation]
    content = relocated(base, member, to, target, (FOREIGN * (count // 30) for _ in range(30)))
    if relation != "of-a-type-unknown":
        return content
    return edited(
        content,
        "xl/_rels/workbook.xml.rels",
        lambda xml: re.sub(
            rb'Type="[^"]*"( Target="' + re.escape(target.encode()) + rb'")',
            b'Type="' + UNKNOWN_TYPE.encode() + rb'"\1',
            xml,
        ),
    )


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("relation", list(RELATED))
def test_a_tab_a_sheet_names_is_counted_wherever_its_relation_puts_it(
    relation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # openpyxl reads as a tab the target of every relation a sheet names, whatever its type, the
    # target joined to the folder of the workbook or taken past its slash: 3 000 000 ``<x/>`` out
    # of its rows are refused before the opening, wherever the relation puts the tab.
    content = _related(relation)
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert RELATED[relation][0] in archive.namelist()
        relations = archive.read("xl/_rels/workbook.xml.rels").decode()
    assert (UNKNOWN_TYPE in relations) == (relation == "of-a-type-unknown")
    assert REFUSAL in _refused_unopened(content, monkeypatch)


@pytest.mark.story("US-3190")
def test_a_tab_no_sheet_names_is_left_out_of_the_bound() -> None:
    # A worksheet the relations of the workbook name, but no sheet: openpyxl does not read it, and
    # twice ``MOST_FOREIGN`` elements out of its rows leave the workbook read.
    worksheet = (
        f'<worksheet xmlns="{_MAIN[1:-1]}"><sheetData>'.encode()
        + FOREIGN * (2 * MOST_FOREIGN)
        + b"</sheetData></worksheet>"
    )
    content = with_relations(
        _base("estimate"),
        {"xl/worksheets/x.xml": worksheet},
        {"xl/workbook.xml": "worksheet worksheets/x.xml"},
    )
    READINGS["estimate"].whole(content)


def _nested(levels: int, each: int, more: int = 0) -> bytes:
    """Give the estimate whose tab of lines, of no ``<dimension>``, ends with rows nested.

    ``levels`` rows, each in the cell of the one before, every cell holding ``each`` ``<x/>``, the
    first ``more`` more: the cells of the first row hold ``levels * each + more`` of them, and the
    ``2 * (levels - 1)`` rows and cells nested in it.
    """
    body = b"".join(
        b"<row><c>" + FOREIGN * (each + (more if level == 0 else 0)) for level in range(levels)
    )
    body += b"</c></row>" * levels

    def nest(xml: bytes) -> bytes:
        xml = re.sub(rb"<dimension [^>]*/>", b"", xml)
        xml = xml.replace(b"<sheetData/>", b"<sheetData></sheetData>")
        return xml.replace(b"</sheetData>", body + b"</sheetData>")

    base = _base("estimate")
    return edited(base, tab(base, "1 Études"), nest)


@pytest.mark.story("US-3190")
def test_nested_rows_share_the_bound_of_the_outermost_row(monkeypatch: pytest.MonkeyPatch) -> None:
    # openpyxl frees a row with what it holds once that row closes: what the cells of a row hold
    # stays held while the rows nested in it are read. Three rows nested, their cells holding
    # 30 000 ``<x/>`` each, are refused on the bound of the cells of a row, which each would pass
    # alone; at the bound, the rows and cells nested counted, the estimate is read; one more,
    # refused.
    assert CELLS_REFUSAL in _refused_unopened(_nested(3, 30_000), monkeypatch)
    each, rest = divmod(MOST_CELL_ELEMENTS - 2 * (3 - 1), 3)
    READINGS["estimate"].whole(_nested(3, each, rest))
    assert CELLS_REFUSAL in _refused_unopened(_nested(3, each, rest + 1), monkeypatch)


@pytest.mark.story("US-3190")
def test_rows_nested_a_hundred_deep_are_refused_within_the_memory() -> None:
    # « … sans que la mémoire réelle du processus ne passe la borne que le test fixe » : the rows
    # nested of the review, 6 500 000 ``<x/>`` in all, refused in a fresh process before any
    # inflation.
    (found,) = resident("estimate", _base("estimate"), [_nested(*NESTED)])
    assert found.outcome == UNREADABLE
    assert found.rise < CALM


@pytest.mark.requirement("WF-INTF-0070-A")
def test_the_workbooks_waterfall_exports_and_writes_stay_far_below_the_bound_out_of_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « les classeurs que Waterfall exporte et ceux du témoin passent la borne » : the prototypes
    # the writers reproduce, and the workbooks of the tests, are read under a hundredth of it (the
    # witness holds under 900 elements out of place, some 36 a tab).
    monkeypatch.setattr(workbooks, "MOST_FOREIGN", MOST_FOREIGN // 100)
    estimate = estimate_reader.read_workbook((PROTOTYPES / "devis-prototype.xlsx").read_bytes())
    remaining = remaining_reader.read_remaining_workbook(
        (PROTOTYPES / "rae-prototype.xlsx").read_bytes()
    )
    assert (len(estimate.lines), len(remaining.lines)) > (0, 0)
    for name, reading in READINGS.items():
        reading.whole(_base(name))
