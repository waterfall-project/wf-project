# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parts openpyxl holds whole, bounded in elements (US-3190b, #4862) and in bytes (US-3190/L3).

openpyxl parses ``styles.xml``, ``workbook.xml``, the content types, the relations, the properties,
a chartsheet and its drawings and charts whole, into a tree: each element costs it a node, in a list
bounded by US-3190/L2b or out of any — 25 kB of ``<b/>`` in a font held 543 MiB. The reading ahead
of the opener counts them, and their attributes, one an element — 28 000 ``<b/>`` of 52 empty
attributes held 342 MiB more (US-3190/L3) —: past 1 100 000 in all the workbook is refused before it
is opened, ``FILE_FORMAT_UNREADABLE``. What a node costs grows with the length of its attributes and
of its text, which the count does not see: 900 000 ``<b a="…"/>`` held 660 MiB more (#4914). So the
bytes these parts declare, and the theme's, which openpyxl keeps as bytes, are bounded too, at 7.5
MiB in all, and each list of ``styles.xml`` with items as Excel writes them is read at its bound,
which the bytes lowered for three of them. The tabs and the shared strings, which openpyxl reads as
a stream, are left to their own bounds (``test_workbook_bounds_vectors``,
``test_workbook_bounds_foreign``).

The memory is the peak resident size of a fresh process, ``VmHWM`` (``resident``), as for the other
vectors.
"""

import zipfile
from functools import cache
from io import BytesIO

import pytest
from lxml import etree
from test_workbook_bounds import PROTOTYPES, READINGS, UNREADABLE
from test_workbook_bounds_vectors import WITHIN
from workbook_bombs import (
    ATTRIBUTED,
    CALM,
    MEBIBYTE,
    STYLES,
    THEME,
    WORKBOOK,
    charted,
    linked_externally,
    referring,
    resident,
    stuffed,
    styled_in_full,
    styled_richly,
)

from waterfall.core.estimate.excel import reader as estimate_reader
from waterfall.core.estimate.remaining.excel import reader as remaining_reader
from waterfall.core.exchanges.interface import (
    LARGEST_TREES,
    MOST_ELEMENTS,
    STYLE_LISTS,
    workbooks,
)
from waterfall.platform.errors import UnprocessableError

REFUSAL = f"the parts openpyxl parses into a tree hold more than {MOST_ELEMENTS} elements"
# The workbooks of #4862: elements out of any list, in a font of ``styles.xml`` or under the root
# of ``workbook.xml``; each member, and where they go in it. Refused: 5 000 000 of them, and
# 1 200 000, which put the total just past the bound, and the 28 000 ``<b/>`` of 52 attributes,
# counted with them (US-3190/L3, decided by the author on 2026-11-25). Read: 1 000 000, which the
# bound of 1 100 000 (decided on 2026-11-25, option a1) holds.
FONT_B = (STYLES, b"</font>", b"<b/>")
WORKBOOK_X = (WORKBOOK, b"</workbook>", b"<x/>")
SWOLLEN: dict[str, tuple[str, bytes, bytes, int]] = {
    "b-in-a-font-5M": (*FONT_B, 5_000_000),
    "b-in-a-font-just-past": (*FONT_B, 1_200_000),
    "x-under-the-workbook-5M": (*WORKBOOK_X, 5_000_000),
    "x-under-the-workbook-just-past": (*WORKBOOK_X, 1_200_000),
    "attributes-in-a-font": (STYLES, b"</font>", ATTRIBUTED, 28_000),
}
HELD: dict[str, tuple[str, bytes, bytes, int]] = {
    "b-in-a-font-1M": (*FONT_B, 1_000_000),
    "x-under-the-workbook-1M": (*WORKBOOK_X, 1_000_000),
}
# The workbooks of #4914: elements in a font, under ``MOST_ELEMENTS``, each with an attribute of 190
# characters, or a text of as many: 900 000 of a text, 180 MB, under the 200 MiB declared; 500 000
# of an attribute, 100 MB, the 900 000 of #4914 counting their attributes past the elements.
BYTES_SWOLLEN: dict[str, tuple[str, bytes, bytes, int]] = {
    "attribute-in-a-font": (STYLES, b"</font>", b'<b a="' + b"a" * 190 + b'"/>', 500_000),
    "text-in-a-font": (STYLES, b"</font>", b"<b>" + b"a" * 190 + b"</b>", 900_000),
}
BYTES_REFUSAL = f"the parts openpyxl holds whole declare more than {LARGEST_TREES} bytes"
# The lists of ``styles.xml`` with items as Excel writes them, each at its bound, each read alone in
# a fresh process: ``python -m measure.workbooks counts`` (``rich-<list>``, VmHWM) measured the
# heaviest, ``dxfs`` at 22 000, at 158 MiB; ``cellXfs`` at 40 000, 150; ``cellStyleXfs`` at
# 60 000, 135; ``cellStyles`` at 65 490, 53; the others under 2. Their attributes counted as
# elements, ``dxfs`` count the most, 572 282 of the 1 100 000. Read one after the other in one
# process, they rose to 200 MiB with ``dxfs`` at 25 000, what the earlier reads leave held: each is
# read alone. The plafond is the objective of the design, some 192 MiB of peak by vector bounded,
# some 20 % over the heaviest. These 192 MiB, and the figures measured, are the rise above the
# process warmed on the base (``resident``), which starts at some 123 MiB: not its VmHWM in absolute
# terms.
RICH_ORDER = (
    "colors",
    "numFmts",
    "fills",
    "fonts",
    "tableStyles",
    "borders",
    "cellStyles",
    "cellStyleXfs",
    "cellXfs",
    "dxfs",
)
RICH_WITHIN = 192 * MEBIBYTE
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
LINKED_RELATIONS = "xl/externalLinks/_rels/linked.xml.rels"
# The external link of the review of US-3190b: 3 000 000 elements, named by a bare ``id``, which
# held 612 MiB when only ``r:id`` was kept.
LINKED_SWOLLEN = 3_000_000


@cache
def _base(name: str) -> bytes:
    return READINGS[name].base()


@cache
def _swollen(name: str, swelling: str) -> bytes:
    return stuffed(_base(name), *{**SWOLLEN, **HELD}[swelling])


@cache
def _bytes_swollen(name: str, swelling: str) -> bytes:
    return stuffed(_base(name), *BYTES_SWOLLEN[swelling])


def _held_bytes(content: bytes, parts: tuple[str, ...]) -> int:
    """Give the bytes ``parts`` and the theme declare, as openpyxl holds them whole."""
    with zipfile.ZipFile(BytesIO(content)) as archive:
        held = {*parts, THEME}
        return sum(item.file_size for item in archive.infolist() if item.filename in held)


def _never_opened(*_: object, **__: object) -> None:
    msg = "the workbook was opened"
    raise AssertionError(msg)


def _nodes(content: bytes, parts: tuple[str, ...], *, attributes: bool = True) -> int:
    """Give the nodes of the trees lxml builds of ``parts``: elements, comments, instructions.

    And the attributes of their elements, one a node, as the bound counts them, unless not
    ``attributes``.
    """
    with zipfile.ZipFile(BytesIO(content)) as archive:
        return sum(
            sum(
                1 + (len(node.attrib) if attributes and isinstance(node.tag, str) else 0)
                for node in etree.fromstring(archive.read(part)).iter()
            )
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
def test_the_workbooks_of_4862_are_refused_within_the_memory() -> None:
    # « … sans que la mémoire réelle du processus ne passe la borne que le test fixe » : one fresh
    # process, the refusals, each under what a refusal before any inflation allocates.
    swollen = [_swollen("estimate", swelling) for swelling in SWOLLEN]
    found = resident("estimate", _base("estimate"), swollen)
    assert [each.outcome for each in found] == [UNREADABLE] * len(SWOLLEN)
    assert max(each.rise for each in found) < CALM


@pytest.mark.story("US-3190")
def test_every_list_of_styles_full_and_the_workbooks_of_4862_at_a_million_are_read_within() -> None:
    # « … chaque liste de styles.xml à sa borne, avec des items comme Excel les écrit, passe » : in
    # one fresh process, from the lightest, the workbooks of #4862 at 1 000 000 elements and every
    # list of ``styles.xml`` full at once with empty items (some 200 000 elements), read within
    # the memory of the other vectors (``WITHIN``, 192 MiB): 124 MiB measured (VmHWM), the workbooks
    # of #4862 each alone as all three in one process, the full lists alone 110.
    full = styled_in_full(_base("estimate"), STYLE_LISTS)
    held = [_swollen("estimate", swelling) for swelling in HELD]
    found = resident("estimate", _base("estimate"), [*held, full])
    assert [each.outcome for each in found] == ["read"] * len(found)
    assert max(each.rise for each in found) < WITHIN


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("listing", RICH_ORDER)
def test_each_list_of_styles_with_items_as_excel_writes_them_is_read_at_its_bound_and_past_refused(
    listing: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « … chaque liste de styles.xml à sa borne, avec des items comme Excel les écrit, passe »,
    # amended by US-3190/L3 (#4914): each at its bound, lowered for the bytes, under both bounds of
    # the parts held whole, is read in a fresh process, within the memory; one item past it,
    # refused on the bound of the list.
    most = STYLE_LISTS[listing]
    at = styled_richly(_base("estimate"), listing, most)
    assert _nodes(at, PARTS) < MOST_ELEMENTS
    assert _held_bytes(at, PARTS) < LARGEST_TREES
    (found,) = resident("estimate", _base("estimate"), [at])
    assert found.outcome == "read"
    assert found.rise < RICH_WITHIN
    past = styled_richly(_base("estimate"), listing, most + 1)
    assert f"holds more than {most} items in {listing}" in _refused_unopened(past, monkeypatch)


@pytest.mark.story("US-3190")
def test_the_dxfs_of_excel_at_their_bound_take_the_most_of_the_bytes() -> None:
    # The bound of ``dxfs``, lowered from 65 490 to some 25 000 for the 7.5 MiB, then to 22 000
    # (decided by the author on 2026-11-25): 22 000 dxf of 16 elements and 10 attributes hold the
    # most of the bytes and the most of the elements of any list, under both bounds; 4 000 more pass
    # the bytes.
    rich = styled_richly(_base("estimate"), "dxfs", STYLE_LISTS["dxfs"])
    assert STYLE_LISTS["dxfs"] == 22_000
    assert LARGEST_TREES * 0.85 < _held_bytes(rich, PARTS) < LARGEST_TREES
    assert MOST_ELEMENTS / 2 < _nodes(rich, PARTS) < MOST_ELEMENTS
    richer = styled_richly(_base("estimate"), "dxfs", STYLE_LISTS["dxfs"] + 4_000)
    assert _held_bytes(richer, PARTS) > LARGEST_TREES


@pytest.mark.story("US-3190")
def test_the_attributes_of_an_element_count_as_elements(monkeypatch: pytest.MonkeyPatch) -> None:
    # « … au-delà de laquelle l'import échoue avant l'ouverture sur `FILE_FORMAT_UNREADABLE` » :
    # 28 000 ``<b/>`` of 52 empty attributes, under the bytes and under the elements bare of their
    # attributes, are refused on the elements, their attributes counted one an element.
    content = _swollen("estimate", "attributes-in-a-font")
    assert _nodes(content, PARTS, attributes=False) < MOST_ELEMENTS // 30
    assert _held_bytes(content, PARTS) < LARGEST_TREES
    assert _nodes(content, PARTS) > MOST_ELEMENTS
    assert REFUSAL in _refused_unopened(content, monkeypatch)


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("swelling", list(BYTES_SWOLLEN))
@pytest.mark.parametrize("name", list(READINGS))
def test_the_workbooks_of_4914_are_refused_before_the_opening_naming_their_format(
    name: str, swelling: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « … au-delà de laquelle l'import échoue avant l'ouverture sur `FILE_FORMAT_UNREADABLE` » :
    # elements under the bound of their count, whose attributes or text openpyxl would hold.
    reading = READINGS[name]
    content = _bytes_swollen(name, swelling)
    assert _nodes(content, PARTS) < MOST_ELEMENTS
    monkeypatch.setattr(workbooks, "load_workbook", _never_opened)
    with pytest.raises(UnprocessableError) as raised:
        reading.whole(content)
    assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
    assert BYTES_REFUSAL in str(raised.value.__cause__)


@pytest.mark.story("US-3190")
def test_the_workbooks_of_4914_are_refused_within_the_memory() -> None:
    # « … sans que la mémoire réelle du processus ne passe la borne que le test fixe » : one fresh
    # process, the refusals, each under what a refusal before any inflation allocates.
    swollen = [_bytes_swollen("estimate", swelling) for swelling in BYTES_SWOLLEN]
    found = resident("estimate", _base("estimate"), swollen)
    assert [each.outcome for each in found] == [UNREADABLE] * len(BYTES_SWOLLEN)
    assert max(each.rise for each in found) < CALM


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("chartsheet", [False, True], ids=["tabs", "chartsheet"])
def test_the_bytes_counted_are_those_of_the_parts_openpyxl_holds_whole(
    chartsheet: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The bound set at the bytes the parts openpyxl parses into a tree declare, and the theme's,
    # the workbook is read; one below, refused: the tabs, the package's relations are not counted,
    # the theme, a chartsheet, its drawing and its chart are.
    content = charted(_base("estimate"), "Graphique") if chartsheet else _base("estimate")
    held = _held_bytes(content, PARTS + CHARTSHEET if chartsheet else PARTS)
    monkeypatch.setattr(workbooks, "LARGEST_TREES", held)
    READINGS["estimate"].whole(content)
    monkeypatch.setattr(workbooks, "LARGEST_TREES", held - 1)
    assert f"declare more than {held - 1} bytes" in _refused_unopened(content, monkeypatch)


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("swelling", list(HELD))
def test_the_workbooks_of_4862_at_a_million_elements_are_read(swelling: str) -> None:
    # The bound at 1 100 000 holds the workbooks of #4862 swollen by 1 000 000 elements.
    content = _swollen("estimate", swelling)
    assert _nodes(content, PARTS) < MOST_ELEMENTS
    READINGS["estimate"].whole(content)


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
@pytest.mark.parametrize("bare", [False, True], ids=["r-id", "bare-id"])
def test_a_part_the_workbook_names_an_external_link_is_counted_whatever_its_relation(
    bare: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # openpyxl parses into a tree the target of the relation an external reference names by its
    # id, ``r:id`` or a bare ``id`` (``Serialisable.from_tree`` keeps an attribute of no
    # namespace), whatever its type: a part named so by a relation typed a tab is counted, with its
    # relations; named by the relation alone, which no sheet names, openpyxl never reads it, and it
    # is not.
    data = b"<externalLink>" + b"<x/>" * 100 + b"</externalLink>"
    ignored = linked_externally(_base("estimate"), LINKED, data, referred=False)
    referred = linked_externally(_base("estimate"), LINKED, data, referred=True, bare=bare)
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", _nodes(ignored, PARTS))
    READINGS["estimate"].whole(ignored)
    nodes = _nodes(referred, (*PARTS, LINKED, LINKED_RELATIONS))
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", nodes)
    READINGS["estimate"].whole(referred)
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", nodes - 1)
    assert f"hold more than {nodes - 1} elements" in _refused_unopened(referred, monkeypatch)


@pytest.mark.story("US-3190")
def test_an_external_link_named_by_a_bare_id_is_refused_within_the_memory() -> None:
    # « … sans que la mémoire réelle du processus ne passe la borne que le test fixe » : the
    # external link of the review, 3 000 000 elements named by a bare ``id``, is refused in a fresh
    # process under what a refusal before any inflation allocates.
    data = b"<externalLink>" + b"<x/>" * LINKED_SWOLLEN + b"</externalLink>"
    content = linked_externally(_base("estimate"), LINKED, data, referred=True, bare=True)
    (found,) = resident("estimate", _base("estimate"), [content])
    assert found.outcome == UNREADABLE
    assert found.rise < CALM


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
    # the writers reproduce, and the workbooks of the tests, are read under a thousandth of the
    # elements, and a hundredth of the bytes (the witness holds some 41 kB of them).
    monkeypatch.setattr(workbooks, "MOST_ELEMENTS", MOST_ELEMENTS // 1_000)
    monkeypatch.setattr(workbooks, "LARGEST_TREES", LARGEST_TREES // 100)
    estimate = estimate_reader.read_workbook((PROTOTYPES / "devis-prototype.xlsx").read_bytes())
    remaining = remaining_reader.read_remaining_workbook(
        (PROTOTYPES / "rae-prototype.xlsx").read_bytes()
    )
    assert (len(estimate.lines), len(remaining.lines)) > (0, 0)
    for name, reading in READINGS.items():
        reading.whole(_base(name))
