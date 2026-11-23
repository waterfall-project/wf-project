# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The other vectors of a workbook, each at its bound read and past it refused (US-3190/L2b).

The bounds the author set on 2026-11-23 (EP-33, "Les bornes des classeurs"), on the measures of
``measure/workbooks.py``: the shared strings — their number, the elements of one, their text —, the
lists of ``styles.xml`` and the defined names are counted by the reading ahead of the opener, and a
workbook past one of them is refused before openpyxl opens it; the tabs read are counted in cumul,
200 000 rows and 10 000 000 cells, as the rows come, and refused past them after the opening.
Each refusal is ``FILE_FORMAT_UNREADABLE``, the format named, by each of the three readers.

The memory is the resident size of the process, measured in a fresh one (``resident``):
``tracemalloc`` does not see what libxml2 allocates, and underestimates the styles and the names up
to 2.4 times. One process for the vectors refused before the opening and read at their bounds, one
for each reader of the cumul: their peak only rises, so the refusals come first.

A part openpyxl rejects by a ``TypeError`` — a ``<fill/>`` without a pattern — is a damaged
workbook, refused by each reader as one (#4848); a ``TypeError`` of the code that reads the rows is
not.
"""

import zipfile
from functools import cache
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pytest
from openpyxl.packaging.workbook import WorkbookPackage
from openpyxl.styles.stylesheet import Stylesheet
from openpyxl.xml.functions import fromstring
from test_workbook_bounds import READINGS, UNREADABLE
from workbook_bombs import (
    CALM,
    MEBIBYTE,
    SPACINGS,
    STYLES,
    WORKBOOK,
    edited,
    named,
    resident,
    respaced,
    shared_strings,
    shared_text,
    styled,
    tab,
    tabulated,
    with_bare_hyperlink,
    with_empty_fill,
    with_member,
)

from waterfall.core.exchanges.interface import (
    LONGEST_TEXT,
    MOST_CELLS,
    MOST_COLUMNS,
    MOST_NAMES,
    MOST_ROWS,
    MOST_STRING_ELEMENTS,
    MOST_STRINGS,
    STYLE_LISTS,
    OpenedWorkbook,
    WorkbookDamagedError,
    opened_workbook,
    workbooks,
)
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# The most the resident size may rise to reading a workbook at a bound, or past the cumul of the
# tabs read: the design holds each vector under 135 MiB, every bound reached at once under 330 MiB.
WITHIN = 192 * MEBIBYTE

# Each vector refused before the opening, by what makes a workbook of a format hold ``count`` of it,
# and its bound: the workbook at the bound is read, the one past it refused.
type Swelling = Callable[[bytes, str, int], bytes]
VECTORS: dict[str, tuple[Swelling, int]] = {
    "strings": (lambda base, _, count: shared_strings(base, count), MOST_STRINGS),
    "elements-of-a-string": (
        lambda base, _, count: shared_strings(base, 1, count),
        MOST_STRING_ELEMENTS,
    ),
    "text": (lambda base, _, count: shared_text(base, count, astral=True), LONGEST_TEXT),
    "defined-names": (lambda base, sheet, count: named(base, count, sheet), MOST_NAMES),
    **{
        f"styles-{listing}": (
            lambda base, _, count, listing=listing: styled(base, listing, count),
            most,
        )
        for listing, most in STYLE_LISTS.items()
    },
}


# What the refusal of each vector says the member holds more than of.
REFUSED_AS: dict[str, str] = {
    "strings": "shared strings",
    "elements-of-a-string": "elements in a shared string",
    "text": "characters of text in shared strings",
    "defined-names": "items in definedNames",
    **{f"styles-{listing}": f"items in {listing}" for listing in STYLE_LISTS},
}


@cache
def _base(name: str) -> bytes:
    return READINGS[name].base()


@cache
def _swollen(name: str, vector: str, count: int) -> bytes:
    swelling, _ = VECTORS[vector]
    return swelling(_base(name), READINGS[name].read[0], count)


def _never_opened(*_: object, **__: object) -> None:
    msg = "the workbook was opened"
    raise AssertionError(msg)


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("vector", list(VECTORS))
@pytest.mark.parametrize("name", list(READINGS))
def test_a_workbook_past_the_bound_of_a_vector_is_refused_before_the_opening_naming_its_format(
    name: str, vector: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « les chaînes partagées (leur nombre, leurs runs, leur texte), les listes de `styles.xml` et
    # les noms définis d'un classeur ont chacun la borne de la conception, au-delà de laquelle
    # l'import échoue avant l'ouverture sur `FILE_FORMAT_UNREADABLE` »
    reading, most = READINGS[name], VECTORS[vector][1]
    content = _swollen(name, vector, most + 1)
    monkeypatch.setattr(workbooks, "load_workbook", _never_opened)
    with pytest.raises(UnprocessableError) as raised:
        reading.whole(content)
    assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
    assert f"holds more than {most} {REFUSED_AS[vector]}" in str(raised.value.__cause__)


@pytest.mark.story("US-3190")
def test_each_vector_at_its_bound_is_read_and_past_it_refused_the_memory_within_the_bound() -> None:
    # « … sans que la mémoire réelle du processus ne passe la borne que le test fixe » : one fresh
    # process, the refusals first, each under what a refusal before any inflation allocates.
    past = [_swollen("estimate", vector, most + 1) for vector, (_, most) in VECTORS.items()]
    at = [_swollen("estimate", vector, most) for vector, (_, most) in VECTORS.items()]
    found = resident("estimate", _base("estimate"), [*past, *at])
    refused, read = found[: len(past)], found[len(past) :]
    assert [each.outcome for each in refused] == [UNREADABLE] * len(VECTORS)
    assert [each.outcome for each in read] == ["read"] * len(VECTORS)
    assert max(each.rise for each in refused) < CALM
    assert max(each.rise for each in read) < WITHIN


# --- The lists as openpyxl reads them: by their local names, their comments among their items ----

# The member each list lies in, and the items openpyxl builds of it, as it reads the member alone.
LISTED: dict[str, str] = {
    "defined-names": WORKBOOK,
    **{f"styles-{name}": STYLES for name in STYLE_LISTS},
}
_ITEMS: dict[str, Callable[[Any], int]] = {
    "numFmts": lambda styles: len(styles.numFmts.numFmt),
    "fonts": lambda styles: len(styles.fonts),
    "fills": lambda styles: len(styles.fills),
    "borders": lambda styles: len(styles.borders),
    "cellStyleXfs": lambda styles: len(styles.cellStyleXfs.xf),
    "cellXfs": lambda styles: len(styles.cellXfs.xf),
    "cellStyles": lambda styles: len(styles.cellStyles.cellStyle),
    "dxfs": lambda styles: len(styles.dxfs),
    "tableStyles": lambda styles: len(styles.tableStyles.tableStyle),
    # The ``indexedColors`` that holds the colours is counted with them.
    "colors": lambda styles: len(styles.colors.indexedColors) + 1,
}


def _built(vector: str, content: bytes) -> int:
    """Give the items openpyxl builds of the list of ``vector`` in ``content``."""
    with zipfile.ZipFile(BytesIO(content)) as archive:
        # The element of openpyxl's lxml, which its stubs type as the standard library's.
        node: Any = fromstring(archive.read(LISTED[vector]))
    if vector == "defined-names":
        package = WorkbookPackage.from_tree(node)
        names = None if package is None else package.definedNames
        return 0 if names is None else len(names.definedName)
    return _ITEMS[vector.removeprefix("styles-")](Stylesheet.from_tree(node))


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
@pytest.mark.parametrize("spacing", SPACINGS)
@pytest.mark.parametrize("vector", list(LISTED))
def test_a_list_in_any_namespace_is_read_at_its_bound_and_refused_past_it_before_the_opening(
    vector: str, spacing: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # openpyxl reads ``styles.xml`` and ``workbook.xml`` by the local names of their elements: a
    # list in no namespace, in another, or prefixed, is built as one of SpreadsheetML is, and
    # counted so. Past the bound, openpyxl would build each item of it.
    most = VECTORS[vector][1]
    at, past = (
        respaced(_swollen("estimate", vector, count), LISTED[vector], spacing)
        for count in (most, most + 1)
    )
    assert _built(vector, past) == most + 1
    READINGS["estimate"].whole(at)
    refused = _refused_unopened(past, monkeypatch)
    assert f"holds more than {most} {REFUSED_AS[vector]}" in refused


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("node", [b"<!--a font-->", b"<?a font?>"])
def test_a_comment_or_an_instruction_in_a_list_is_counted_as_the_item_openpyxl_builds_of_it(
    node: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    # openpyxl's lxml gives a comment, and an instruction, as a child of the list, of which it
    # builds a font: the list at its bound and one more is refused.
    most = STYLE_LISTS["fonts"]
    past = edited(
        _swollen("estimate", "styles-fonts", most),
        STYLES,
        lambda xml: xml.replace(b"</fonts>", node + b"</fonts>"),
    )
    assert _built("styles-fonts", past) == most + 1
    assert f"holds more than {most} items in fonts" in _refused_unopened(past, monkeypatch)


@pytest.mark.story("US-3190")
def test_a_document_type_is_refused_in_a_part_openpyxl_parses_and_left_in_another(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Under a document type it does not load, openpyxl's lxml keeps an entity it leaves unresolved
    # as a child, of which it builds a font, where the reading sees nothing: a part openpyxl may
    # parse that declares one is refused; Excel writes none.
    base = _base("estimate")
    fonts = _built("styles-fonts", base)
    typed = edited(
        base,
        STYLES,
        lambda xml: (
            b'<!DOCTYPE styleSheet SYSTEM "s.dtd">' + xml.replace(b"</fonts>", b"&e;</fonts>")
        ),
    )
    assert _built("styles-fonts", typed) == fonts + 1
    assert "'xl/styles.xml' declares a document type" in _refused_unopened(typed, monkeypatch)
    READINGS["estimate"].whole(
        with_member(base, "customXml/item1.xml", b'<!DOCTYPE a SYSTEM "a.dtd"><a/>')
    )


# --- The cumul of the tabs read, counted as the rows come ----------------------------------------


def _counted(call: Callable[[bytes], Any], content: bytes) -> OpenedWorkbook:
    """Give the workbook a reading of ``content`` opened, its rows and cells counted in all."""
    opened: list[OpenedWorkbook] = []
    counted = OpenedWorkbook.bounded_rows

    def spied(self: OpenedWorkbook, rows: Any) -> list[tuple[Any, ...]]:
        opened.append(self)
        return counted(self, rows)

    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(OpenedWorkbook, "bounded_rows", spied)
        call(content)
    assert len({id(each) for each in opened}) == 1
    return opened[0]


def _two_tabs(rows: int) -> bytes:
    """Give the estimate whose two tabs read hold ``rows`` rows read in all, half each."""
    base = _base("estimate")
    first, second = (tab(base, title) for title in READINGS["estimate"].read)
    width = MOST_COLUMNS // 50

    def grown(first_rows: int, second_rows: int) -> bytes:
        return tabulated(tabulated(base, first, first_rows, width), second, second_rows, width)

    others = _counted(READINGS["estimate"].whole, grown(100, 100)).rows - 200
    half = (rows - others) // 2
    return grown(half, rows - others - half)


@cache
def _wide(rows: int) -> bytes:
    """Give the extraction whose tab holds ``rows`` rows of ``MOST_COLUMNS`` cells each."""
    base = _base("actual_costs")
    return tabulated(base, tab(base, "Extraction"), rows, MOST_COLUMNS)


@pytest.mark.story("US-3190")
def test_the_tabs_read_are_bounded_in_cumul_each_within_its_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « le cumul des onglets lus, 200 000 lignes et 10 000 000 de cellules, se compte à la lecture
    # et fait échouer l'import de même, après l'ouverture » : two tabs of 100 000 rows, each within
    # the bound of a tab, are read at the bound and refused one row past it, once opened.
    at, past = _two_tabs(MOST_ROWS), _two_tabs(MOST_ROWS + 1)
    reading = READINGS["estimate"]
    assert _counted(reading.whole, at).rows == MOST_ROWS
    opened: list[bytes] = []
    load = workbooks.load_workbook

    def loaded(source: Any, **options: Any) -> Any:
        opened.append(b"")
        return load(source, **options)

    monkeypatch.setattr(workbooks, "load_workbook", loaded)
    for call in (reading.whole, reading.prepare):
        with pytest.raises(UnprocessableError) as raised:
            call(past)
        assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
    assert len(opened) == 2


@pytest.mark.story("US-3190")
def test_the_cumul_of_rows_and_of_cells_is_held_within_the_memory_bound() -> None:
    # The rows of the two tabs, then the cells of rows 500 wide: read at the bound, refused past it,
    # the resident size of the process under the bound the test fixes, in a fresh process each.
    rows = resident("estimate", _base("estimate"), [_two_tabs(MOST_ROWS), _two_tabs(MOST_ROWS + 1)])
    assert [each.outcome for each in rows] == ["read", UNREADABLE]
    at, past = MOST_CELLS // MOST_COLUMNS, MOST_CELLS // MOST_COLUMNS + 1
    assert _counted(READINGS["actual_costs"].whole, _wide(10)).cells == 10 * MOST_COLUMNS
    cells = resident("actual_costs", _base("actual_costs"), [_wide(at), _wide(past)])
    assert [each.outcome for each in cells] == ["read", UNREADABLE]
    assert max(each.rise for each in (*rows, *cells)) < WITHIN


# --- A part openpyxl rejects by a TypeError (#4848) -----------------------------------------------


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_fill_without_a_pattern_is_refused_as_a_damaged_workbook_by_each_reader(
    name: str,
) -> None:
    # openpyxl rejects ``<fill/>`` by a TypeError at the opening: the import failed on
    # INTERNAL_ERROR instead of the refusal of its format (#4848).
    reading = READINGS[name]
    for call in (reading.header, reading.whole, reading.prepare):
        with pytest.raises(UnprocessableError) as raised:
            call(with_empty_fill(_base(name)))
        assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
        assert isinstance(raised.value.__cause__, WorkbookDamagedError)


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_type_error_amid_the_rows_of_a_tab_read_is_refused_as_a_damaged_workbook_by_each_reader(
    name: str,
) -> None:
    # A hyperlink without a cell among the rows of a tab read: openpyxl rejects it by a TypeError
    # once the first row is given and before the next, in the midst of the reading (#4848).
    reading, base = READINGS[name], _base(name)
    member = tab(base, reading.read[0])
    content = with_bare_hyperlink(base, member)
    with zipfile.ZipFile(BytesIO(content)) as archive:
        xml = archive.read(member)
    assert xml.index(b"<hyperlinks>") < xml.rindex(b"<row")
    for call in (reading.whole, reading.prepare):
        with pytest.raises(UnprocessableError) as raised:
            call(content)
        assert (raised.value.code, dict(raised.value.params)) == (UNREADABLE, reading.params)
        assert isinstance(raised.value.__cause__, WorkbookDamagedError)
        assert isinstance(raised.value.__cause__.__cause__, TypeError)


def _rejected() -> Iterator[tuple[Any, ...]]:
    yield ("a row",)
    msg = "expected <class 'openpyxl.styles.fills.Fill'>"
    raise TypeError(msg)


def _misread(rows: list[tuple[Any, ...]]) -> None:
    msg = f"a reader that misreads its {len(rows)} rows"
    raise TypeError(msg)


@pytest.mark.story("US-3190")
def test_a_type_error_of_the_reading_of_the_rows_is_damage_and_one_of_the_reader_is_not() -> None:
    # The TypeError is caught at the opening and at the reading of the rows alone: an error of the
    # code that reads them stays a TypeError, not a refusal of the file.
    with opened_workbook(_base("actual_costs")) as opened:
        with pytest.raises(WorkbookDamagedError):
            opened.bounded_rows(_rejected())
        rows = opened.bounded_rows(opened.worksheets[0].iter_rows(values_only=True))
        with pytest.raises(TypeError) as raised:
            _misread(rows)
    assert not isinstance(raised.value, WorkbookDamagedError)
