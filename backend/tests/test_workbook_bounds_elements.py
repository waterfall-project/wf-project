# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The elements of the parts openpyxl parses into a tree, bounded in all (US-3190b, #4862).

openpyxl parses ``styles.xml``, ``workbook.xml``, the content types, the relations, the properties,
a chartsheet and its drawings and charts whole, into a tree: each element costs it a node, in a list
bounded by US-3190/L2b or out of any — 25 kB of ``<b/>`` in a font held 543 MiB. The reading ahead
of the opener counts them, and past 1 000 000 in all the workbook is refused before it is opened,
``FILE_FORMAT_UNREADABLE``. The tabs and the shared strings, which openpyxl reads as a stream, are
left to their own bounds (``test_workbook_bounds_vectors`` reads them at those bounds); the theme,
which it keeps as bytes, too.

The memory is the resident size of a fresh process (``resident``), as for the other vectors.
"""

import zipfile
from functools import cache
from io import BytesIO

import pytest
from lxml import etree
from test_workbook_bounds import PROTOTYPES, READINGS, UNREADABLE
from test_workbook_bounds_vectors import WITHIN
from workbook_bombs import (
    CALM,
    STYLES,
    WORKBOOK,
    charted,
    linked_externally,
    referring,
    resident,
    stuffed,
    styled_in_full,
)

from waterfall.core.estimate.excel import reader as estimate_reader
from waterfall.core.estimate.remaining.excel import reader as remaining_reader
from waterfall.core.exchanges.interface import MOST_ELEMENTS, STYLE_LISTS, workbooks
from waterfall.platform.errors import UnprocessableError

REFUSAL = f"the parts openpyxl parses into a tree hold more than {MOST_ELEMENTS} elements"
# The workbooks of #4862: elements out of any list, in a font of ``styles.xml`` or under the root
# of ``workbook.xml``, 1 000 000 or 5 000 000 of them; each member, and where they go in it.
SWOLLEN: dict[str, tuple[str, bytes, bytes, int]] = {
    "b-in-a-font-1M": (STYLES, b"</font>", b"<b/>", 1_000_000),
    "b-in-a-font-5M": (STYLES, b"</font>", b"<b/>", 5_000_000),
    "x-under-the-workbook-1M": (WORKBOOK, b"</workbook>", b"<x/>", 1_000_000),
    "x-under-the-workbook-5M": (WORKBOOK, b"</workbook>", b"<x/>", 5_000_000),
}
# The parts an openpyxl workbook holds that openpyxl parses into a tree, and those of a chartsheet.
PARTS = (
    "[Content_Types].xml",
    "docProps/core.xml",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
)
CHARTSHEET = (
    "xl/chartsheets/sheet1.xml",
    "xl/chartsheets/_rels/sheet1.xml.rels",
    "xl/drawings/drawing1.xml",
    "xl/drawings/_rels/drawing1.xml.rels",
    "xl/charts/chart1.xml",
)
LINKED = "xl/externalLinks/linked.xml"


@cache
def _base(name: str) -> bytes:
    return READINGS[name].base()


@cache
def _swollen(name: str, swelling: str) -> bytes:
    return stuffed(_base(name), *SWOLLEN[swelling])


def _never_opened(*_: object, **__: object) -> None:
    msg = "the workbook was opened"
    raise AssertionError(msg)


def _nodes(content: bytes, parts: tuple[str, ...]) -> int:
    """Give the nodes of the trees lxml builds of ``parts``: elements, comments, instructions."""
    with zipfile.ZipFile(BytesIO(content)) as archive:
        return sum(
            sum(1 for _ in etree.fromstring(archive.read(part)).iter())
            for part in parts
            if part in archive.namelist()
        )


def _refused_unopened(content: bytes, monkeypatch: pytest.MonkeyPatch) -> str:
    """Give what the estimate is refused on, before the opening."""
    reading = READINGS["estimate"]
    with monkeypatch.context() as patched:
        patched.setattr(workbooks, "load_workbook", _never_opened)
        with pytest.raises(UnprocessableError) as raised:
            reading.whole(content)
    assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
    return str(raised.value.__cause__)


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("swelling", list(SWOLLEN))
@pytest.mark.parametrize("name", list(READINGS))
def test_the_workbooks_of_4862_are_refused_before_the_opening_naming_their_format(
    name: str, swelling: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « … au-delà de laquelle l'import échoue avant l'ouverture sur `FILE_FORMAT_UNREADABLE` » :
    # elements out of any list bounded, which openpyxl would build a node of each.
    reading = READINGS[name]
    monkeypatch.setattr(workbooks, "load_workbook", _never_opened)
    with pytest.raises(UnprocessableError) as raised:
        reading.whole(_swollen(name, swelling))
    assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
    assert REFUSAL in str(raised.value.__cause__)


@pytest.mark.story("US-3190")
def test_the_workbooks_of_4862_are_refused_within_the_memory_and_styles_in_full_read() -> None:
    # « … sans que la mémoire réelle du processus ne passe la borne que le test fixe » : one fresh
    # process, the refusals first, each under what a refusal before any inflation allocates; then
    # ``styles.xml`` as full as Excel writes it, every list at its bound at once, read.
    full = styled_in_full(_base("estimate"), STYLE_LISTS)
    swollen = [_swollen("estimate", swelling) for swelling in SWOLLEN]
    found = resident("estimate", _base("estimate"), [*swollen, full])
    assert [each.outcome for each in found] == [UNREADABLE] * len(SWOLLEN) + ["read"]
    assert max(each.rise for each in found[:-1]) < CALM
    assert found[-1].rise < WITHIN


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("chartsheet", [False, True], ids=["tabs", "chartsheet"])
def test_the_elements_counted_are_those_of_the_parts_openpyxl_parses_into_a_tree(
    chartsheet: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The bound set at the nodes lxml builds of the parts openpyxl parses into a tree, the workbook
    # is read; one below, refused: the tabs, the theme, the package's relations are not counted, a
    # chartsheet, its drawing and its chart are.
    content = charted(_base("estimate"), "Graphique") if chartsheet else _base("estimate")
    nodes = _nodes(content, PARTS + CHARTSHEET if chartsheet else PARTS)
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", nodes)
    READINGS["estimate"].whole(content)
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", nodes - 1)
    refused = _refused_unopened(content, monkeypatch)
    assert f"hold more than {nodes - 1} elements" in refused


@pytest.mark.story("US-3190")
def test_a_part_the_workbook_names_an_external_link_is_counted_whatever_its_relation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # openpyxl parses into a tree the target of the relation an external reference names by its
    # id, whatever its type: a part named so by a relation typed a tab is counted; named by the
    # relation alone, which no sheet names, openpyxl never reads it, and it is not.
    data = b"<externalLink>" + b"<x/>" * 100 + b"</externalLink>"
    ignored = linked_externally(_base("estimate"), LINKED, data, referred=False)
    referred = linked_externally(_base("estimate"), LINKED, data, referred=True)
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", _nodes(ignored, PARTS))
    READINGS["estimate"].whole(ignored)
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", _nodes(referred, (*PARTS, LINKED)) - 1)
    assert "elements" in _refused_unopened(referred, monkeypatch)


@pytest.mark.story("US-3190")
def test_the_external_links_a_workbook_part_names_are_kept_within_the_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The ids of the external links are kept to find their relations, each an element of a part
    # openpyxl parses into a tree: a workbook part at another name than the fixed one, which the
    # parts of fixed names do not count, is refused once it names more than the bound.
    content = referring(_base("estimate"), "xl/book.xml", 0)
    fixed = _nodes(content, ("[Content_Types].xml", "docProps/core.xml", STYLES))
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", fixed)
    refused = _refused_unopened(referring(_base("estimate"), "xl/book.xml", fixed + 1), monkeypatch)
    assert f"'xl/book.xml' holds more than {fixed} elements" in refused


@pytest.mark.requirement("WF-INTF-0070-A")
def test_the_workbooks_waterfall_exports_and_writes_stay_far_below_the_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « les classeurs que Waterfall exporte et ceux du témoin passent la borne » : the prototypes
    # the writers reproduce, and the workbooks of the tests, are read under a thousandth of it.
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", MOST_ELEMENTS // 1_000)
    estimate = estimate_reader.read_workbook((PROTOTYPES / "devis-prototype.xlsx").read_bytes())
    remaining = remaining_reader.read_remaining_workbook(
        (PROTOTYPES / "rae-prototype.xlsx").read_bytes()
    )
    assert (len(estimate.lines), len(remaining.lines)) > (0, 0)
    for name, reading in READINGS.items():
        reading.whole(_base(name))
