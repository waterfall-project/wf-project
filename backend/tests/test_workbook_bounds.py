# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A workbook beyond the bounds is refused before it is opened, and a tab read within its bounds.

US-3190/L1: the opener of the exchanges (``opened_workbook``) judges the archive — its members,
their sizes declared, then what each inflates to — before openpyxl reads any of it, and each reader
materialises the tabs its format reads alone, each within its rows and columns (``bounded_rows``).
US-3190/L1b: the opener reads ahead the XML of every member, without a tree, and refuses a member of
more rows, or a row of more cells, empty or not, than the bounds, before openpyxl opens it (#4734).
Tried here on the three readers of a workbook, by what the opening, the analysis and the
application call: the header, the whole reading, the preparation of the application. The refusals
through ``openImport`` are ``test_workbook_bounds_opening``'s; the round trips of the exports, and
the applications of the actual costs, ``test_estimate_export``'s, ``test_remaining_export``'s and
``test_actual_costs_apply``'s, which pass through the opener as every import does.
"""

import warnings
import zipfile
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from actual_costs_import_support import extraction, line
from estimate_import_support import workbook as estimate_workbook
from lxml import etree
from openpyxl import load_workbook
from openpyxl.chartsheet import Chartsheet
from openpyxl.xml.constants import SHARED_STRINGS
from remaining_import_support import workbook as remaining_workbook
from workbook_bombs import (
    CALM,
    GIBIBYTE,
    MEBIBYTE,
    Rows,
    announcing,
    appended,
    charted,
    compressed_by,
    crowded,
    duplicated,
    encrypted,
    grown,
    in_zip64,
    lying,
    measured,
    relocated,
    swollen,
    tab,
    with_member,
    with_relations,
)

from waterfall.core.costs import extraction as costs_reader
from waterfall.core.costs.interface import ACTUAL_COSTS_FORMAT
from waterfall.core.estimate.excel import reader as estimate_reader
from waterfall.core.estimate.interface import ESTIMATE_FORMAT, REMAINING_FORMAT
from waterfall.core.estimate.remaining.excel import reader as remaining_reader
from waterfall.core.exchanges.interface import (
    LARGEST_INFLATED,
    MOST_COLUMNS,
    MOST_MEMBERS,
    MOST_ROWS,
    workbooks,
    xml,
)
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[2]
PROTOTYPES = ROOT / "docs" / "spec" / "exemples"
UNREADABLE = "FILE_FORMAT_UNREADABLE"


@dataclass(frozen=True)
class Reading:
    """A format, as its readers read a workbook: the header, the whole, the preparation."""

    params: dict[str, str]
    base: Callable[[], bytes]
    header: Callable[[bytes], Any]
    whole: Callable[[bytes], Any]
    prepare: Callable[[bytes], Any]
    # The tabs the format reads whole, and those it does not materialise.
    read: tuple[str, ...]
    unread: tuple[str, ...]


READINGS = {
    "estimate": Reading(
        {"expected_format": "estimate", "expected_version": "1"},
        lambda: estimate_workbook([]),
        estimate_reader.check_header,
        estimate_reader.read_workbook,
        ESTIMATE_FORMAT.prepare,
        ("1 Études", "Tâches"),
        ("Présentation", "Devis", "Paramètres"),
    ),
    "remaining": Reading(
        {"expected_format": "remaining", "expected_version": "1"},
        lambda: remaining_workbook({"Hors sous-projet": []}),
        remaining_reader.check_header,
        remaining_reader.read_remaining_workbook,
        REMAINING_FORMAT.prepare,
        ("Hors sous-projet", "Synthèse", "Tâches"),
        ("Paramètres",),
    ),
    "actual_costs": Reading(
        {"expected_format": "actual_costs"},
        lambda: extraction([line()]),
        lambda content: costs_reader.sheet_rows(content, max_row=costs_reader.HEADER_ROW),
        costs_reader.sheet_rows,
        ACTUAL_COSTS_FORMAT.prepare,
        ("Extraction",),
        ("Notes",),
    ),
}
BOMBS: dict[str, Callable[[bytes], bytes]] = {
    "inflates-64-MiB-declares-7-kB": lying,
    "announces-1-GiB": announcing,
    "declares-past-200-MiB": lambda base: swollen(base, LARGEST_INFLATED + MEBIBYTE),
    "1001-members": lambda base: crowded(base, MOST_MEMBERS + 1),
    "bzip2-member": lambda base: compressed_by(base, zipfile.ZIP_BZIP2),
    "encrypted-member": encrypted,
    "lzma-member": lambda base: compressed_by(base, zipfile.ZIP_LZMA),
    "zip64-announces-5-GiB": lambda base: in_zip64(base, 5 * GIBIBYTE),
}


@cache
def _base(name: str) -> bytes:
    return READINGS[name].base()


@cache
def _bomb(name: str, bomb: str) -> bytes:
    return BOMBS[bomb](_base(name))


def _refused(call: Callable[[bytes], Any], content: bytes) -> dict[str, Any]:
    """Give the parameters of the refusal of ``content``: ``FILE_FORMAT_UNREADABLE``, asserted."""
    with pytest.raises(UnprocessableError) as raised:
        call(content)
    assert raised.value.code == UNREADABLE
    return dict(raised.value.params)


def _never_opened(*_: object, **__: object) -> None:
    msg = "the workbook was opened"
    raise AssertionError(msg)


@pytest.fixture
def unopened(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if openpyxl is asked to open a workbook."""
    monkeypatch.setattr(workbooks, "load_workbook", _never_opened)


# --- The archive, judged before any opening ------------------------------------------------------


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.usefixtures("unopened")
@pytest.mark.parametrize("bomb", list(BOMBS))
@pytest.mark.parametrize("name", list(READINGS))
def test_a_workbook_beyond_the_bounds_is_refused_naming_its_format_without_being_opened(
    name: str, bomb: str
) -> None:
    # « pour les trois formats Excel, un classeur dont la somme des tailles décompressées que ses
    # membres déclarent, ou le nombre de ses membres, passe la borne de la conception est refusé
    # […] 422 FILE_FORMAT_UNREADABLE, le format attendu nommé, sans avoir été ouvert par le
    # lecteur de classeurs » : at the opening (the header), at the analysis and at the
    # application (the preparation).
    reading, content = READINGS[name], _bomb(name, bomb)
    for call in (reading.header, reading.whole, reading.prepare):
        assert _refused(call, content) == reading.params


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.usefixtures("unopened")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_member_inflating_to_64_mebibytes_is_refused_without_the_memory_rising(
    name: str,
) -> None:
    # « éprouvé sur un classeur de 68 515 octets dont un membre se décompresse en 64 Mio […] la
    # mémoire du processus ne montant pas » : zipfile would inflate the whole member, then cut it
    # at the 7 000 bytes it declares and find their CRC right.
    content = _bomb(name, "inflates-64-MiB-declares-7-kB")
    assert len(content) < 80_000
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert sum(item.file_size for item in archive.infolist()) < LARGEST_INFLATED
    with measured() as peak:
        _refused(READINGS[name].header, content)
    assert peak.allocated < CALM


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.usefixtures("unopened")
def test_a_member_announcing_one_gibibyte_is_refused_without_the_memory_rising() -> None:
    content = _bomb("estimate", "announces-1-GiB")
    with measured() as peak:
        _refused(estimate_reader.check_header, content)
    assert peak.allocated < CALM


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_member_inflating_one_byte_past_what_it_declares_is_refused() -> None:
    content = lying(_base("estimate"), MEBIBYTE, MEBIBYTE - 1)
    assert _refused(estimate_reader.read_workbook, content) == READINGS["estimate"].params


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_member_whose_local_header_is_missing_is_refused() -> None:
    # The directory names a member where the archive holds no local header: nothing to inflate.
    raw = bytearray(_base("estimate"))
    with zipfile.ZipFile(BytesIO(bytes(raw))) as archive:
        at = archive.getinfo("xl/workbook.xml").header_offset
    raw[at : at + 4] = b"XXXX"
    assert _refused(estimate_reader.read_workbook, bytes(raw)) == READINGS["estimate"].params


@pytest.mark.requirement("WF-INTF-0070-A")
def test_an_archive_at_the_bounds_of_its_members_and_their_sizes_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The bounds are inclusive: a thousand members pass, and sizes declared that add up to the
    # bound exactly (the bound lowered to the size of the workbook, rather than a file of 200 MiB).
    assert estimate_reader.read_workbook(crowded(_base("estimate"), MOST_MEMBERS)).lines == ()
    base = _base("estimate")
    with zipfile.ZipFile(BytesIO(base)) as archive:
        declared = sum(item.file_size for item in archive.infolist())
    monkeypatch.setattr(workbooks, "LARGEST_INFLATED", declared)
    assert estimate_reader.read_workbook(base).lines == ()
    monkeypatch.setattr(workbooks, "LARGEST_INFLATED", declared - 1)
    _refused(estimate_reader.read_workbook, base)


@pytest.mark.requirement("WF-INTF-0070-A")
def test_an_honest_stored_member_is_read() -> None:
    content = duplicated(_base("estimate"), 1024, copies=1)
    assert estimate_reader.read_workbook(content).lines == ()


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_workbook_in_zip64_within_the_bounds_is_read(name: str) -> None:
    # « Un fichier conforme à chacun des formats […] est accepté » : ZIP64 is no refusal of its own
    # (#4740); its sizes, read in the ZIP64 field, are judged as any other (the 5 GiB it may
    # announce are refused with the bombs).
    reading, content = READINGS[name], in_zip64(_base(name))
    assert b"PK\x06\x06" in content
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert all(item.extra[:2] == b"\x01\x00" for item in archive.infolist())
    assert reading.header(content) == reading.header(_base(name))
    assert reading.prepare(content) == reading.prepare(_base(name))


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("method", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_members_of_one_name_are_all_counted_in_the_sizes_declared(
    monkeypatch: pytest.MonkeyPatch, method: int
) -> None:
    base = _base("estimate")
    with zipfile.ZipFile(BytesIO(base)) as archive:
        declared = sum(item.file_size for item in archive.infolist())
    # Two members of 1 KiB under one name: the bound holds both, or refuses the pair.
    content = duplicated(base, 1024, method=method)
    monkeypatch.setattr(workbooks, "LARGEST_INFLATED", declared + 2048)
    assert estimate_reader.read_workbook(content).lines == ()
    monkeypatch.setattr(workbooks, "LARGEST_INFLATED", declared + 2047)
    _refused(estimate_reader.read_workbook, content)


@pytest.mark.requirement("WF-INTF-0070-A")
def test_the_prototypes_of_the_specification_pass_the_bounds() -> None:
    # « les classeurs que Waterfall exporte et ceux du témoin passent la borne » : the prototypes
    # the writers reproduce, read whole.
    estimate = estimate_reader.read_workbook((PROTOTYPES / "devis-prototype.xlsx").read_bytes())
    remaining = remaining_reader.read_remaining_workbook(
        (PROTOTYPES / "rae-prototype.xlsx").read_bytes()
    )
    assert (len(estimate.lines), len(remaining.lines)) > (0, 0)
    assert estimate.unread_sheets == remaining.unread_sheets == ()


# --- The tabs read, and their bounds -------------------------------------------------------------


@pytest.mark.story("US-3190")
def test_the_readers_materialise_the_tabs_their_format_reads_alone() -> None:
    # The first tab of an estimate is read in its header; « Devis » and « Paramètres » are not
    # read, nor « Paramètres » of a remaining to commit.
    prototype = (PROTOTYPES / "devis-prototype.xlsx").read_bytes()
    sheets = dict(estimate_reader.load_sheets(prototype))
    assert "Devis" not in sheets
    assert "Paramètres" not in sheets
    assert (len(sheets["Présentation"]), "Tâches" in sheets) == (2, True)
    rae = (PROTOTYPES / "rae-prototype.xlsx").read_bytes()
    read = dict(
        remaining_reader.load_sheets(
            rae, unread=("Paramètres",), expected_format="remaining", expected_version=1
        )
    )
    assert list(read) == ["Synthèse", "SP-PRE", "SP-MAT", "Hors sous-projet", "Tâches"]


@pytest.mark.story("US-3190")
@pytest.mark.parametrize(
    ("row", "column"),
    [(MOST_ROWS + 1, 1), (1, MOST_COLUMNS + 1)],
    ids=["rows", "columns"],
)
@pytest.mark.parametrize("name", list(READINGS))
def test_a_tab_read_past_its_rows_or_its_columns_fails_the_analysis_and_the_application(
    name: str, row: int, column: int
) -> None:
    reading = READINGS[name]
    for sheet in reading.read:
        content = grown(_base(name), sheet, row, column)
        assert _refused(reading.whole, content) == reading.params
        assert _refused(reading.prepare, content) == reading.params


def _rows_read(
    call: Callable[[bytes], Any], content: bytes, monkeypatch: pytest.MonkeyPatch
) -> int:
    """Give the rows a reading of ``content`` counted, in all the tabs it read."""
    opened: list[workbooks.OpenedWorkbook] = []
    counted = workbooks.OpenedWorkbook.bounded_rows

    def spied(self: workbooks.OpenedWorkbook, rows: Any) -> list[tuple[Any, ...]]:
        opened.append(self)
        return counted(self, rows)

    with monkeypatch.context() as patched:
        patched.setattr(workbooks.OpenedWorkbook, "bounded_rows", spied)
        call(content)
    assert len({id(each) for each in opened}) == 1
    return opened[0].rows


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_tab_read_at_its_bounds_and_a_tab_not_read_past_them_are_read(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The rows of the tabs read are bounded in cumul (US-3190/L2b): the first tab read grown so
    # that, with those the others read, they are as many as the bound.
    reading = READINGS[name]
    read = reading.read[0]
    others = _rows_read(reading.whole, grown(_base(name), read, 1_000, 1), monkeypatch) - 1_000
    reading.whole(grown(_base(name), read, MOST_ROWS - others, 1))
    reading.prepare(grown(_base(name), read, 1, MOST_COLUMNS))
    for sheet in reading.unread:
        past = grown(_base(name), sheet, MOST_ROWS + 1, 1)
        reading.whole(grown(past, sheet, 1, MOST_COLUMNS + 1))


# --- The XML of the members, read ahead of the opening (US-3190/L1b) -----------------------------

# The workbook of #4734: a row of 2 000 000 empty cells, 8 MB of XML declared honestly.
CELLS_OF_4734 = 2_000_000


@cache
def _with_row(name: str, cells: int, cell: bytes = b"<c/>") -> bytes:
    """Give the workbook of a format whose first tab read ends with a row of ``cells`` cells."""
    base = _base(name)
    return appended(base, tab(base, READINGS[name].read[0]), Rows(cells=cells, cell=cell))


@pytest.mark.story("US-3190")
@pytest.mark.usefixtures("unopened")
@pytest.mark.parametrize("name", list(READINGS))
def test_the_workbook_of_4734_is_refused_before_the_opening_without_the_memory_rising(
    name: str,
) -> None:
    # « lignes et cellules, vides comprises, se comptent avant l'ouverture, et un classeur de
    # 13 705 octets dont une ligne porte 2 000 000 de cellules vides est refusé sans que la mémoire
    # du processus ne monte » : openpyxl took 583 MiB to read it (#4734); at the opening (the
    # header), at the analysis and at the application, the format named.
    reading, content = READINGS[name], _with_row(name, CELLS_OF_4734)
    assert len(content) < 16_000
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert sum(item.file_size for item in archive.infolist()) > 4 * CELLS_OF_4734
    for call in (reading.header, reading.whole, reading.prepare):
        with measured() as peak:
            assert _refused(call, content) == reading.params
        assert peak.allocated < CALM


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_row_of_501_empty_cells_is_refused_before_the_opening_and_one_of_500_read(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every element a row holds is a cell to openpyxl, an empty one as another, whatever its tag.
    reading = READINGS[name]
    reading.whole(_with_row(name, MOST_COLUMNS))
    reading.prepare(_with_row(name, MOST_COLUMNS, b"<x/>"))
    monkeypatch.setattr(workbooks, "load_workbook", _never_opened)
    for cell in (b"<c/>", b"<x/>"):
        content = _with_row(name, MOST_COLUMNS + 1, cell)
        assert _refused(reading.whole, content) == reading.params
        assert _refused(reading.prepare, content) == reading.params


@pytest.mark.story("US-3190")
def test_a_tab_of_more_rows_than_the_bound_is_refused_before_the_opening(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Its rows counted as they lie in the XML, empty ones included: at the bound, the tab is read.
    base = _base("actual_costs")
    member = tab(base, "Extraction")
    with zipfile.ZipFile(BytesIO(base)) as archive:
        held = archive.read(member).count(b"<row ")
    at_bound = appended(base, member, Rows(MOST_ROWS - held, dimension=False))
    assert len(costs_reader.sheet_rows(at_bound)) == MOST_ROWS
    monkeypatch.setattr(workbooks, "load_workbook", _never_opened)
    past = appended(base, member, Rows(MOST_ROWS - held + 1, dimension=False))
    assert _refused(costs_reader.sheet_rows, past) == READINGS["actual_costs"].params


@pytest.mark.story("US-3190")
@pytest.mark.usefixtures("unopened")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_row_past_its_cells_in_a_tab_the_format_does_not_read_is_refused_too(
    name: str,
) -> None:
    # openpyxl, opening a workbook, parses every tab up to its dimension, to its end when it has
    # none: a tab the format does not read took 154 MiB at the reading of the header alone.
    reading, base = READINGS[name], grown(_base(name), "Annexe", 1, 1)
    content = appended(base, tab(base, "Annexe"), Rows(cells=CELLS_OF_4734, dimension=False))
    with measured() as peak:
        assert _refused(reading.header, content) == reading.params
    assert peak.allocated < CALM


@pytest.mark.story("US-3190")
def test_a_member_that_is_no_xml_is_left_and_a_member_of_damaged_xml_refused() -> None:
    base, read = _base("estimate"), estimate_reader.read_workbook
    for other in (b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 64, b"", b" \n" * 100):
        assert read(with_member(base, "xl/media/image1.png", other)).lines == ()
    for damaged in (b"<a><b></a>", b"\xef\xbb\xbf  <a>", b"\xff\xfe<\x00a\x00", b" " * 5000):
        assert _refused(read, with_member(base, "xl/media/x.xml", damaged))


# What Excel writes for the comments of a legacy workbook: not well-formed XML.
EXCEL_VML = (
    b'<xml xmlns:v="urn:schemas-microsoft-com:vml"><v:shape id=_x0000_s1025 type="#_x0000_t202">'
    b"<v:textbox><div style='text-align:left'>Note<br></div></v:textbox></v:shape></xml>"
)


@pytest.mark.story("US-3190")
def test_a_vml_drawing_not_well_formed_is_no_refusal_but_is_still_counted() -> None:
    # openpyxl, read-only, never parses a VML drawing: its syntax is no refusal of the workbook,
    # while a member openpyxl does parse (an .xml one, as the test above) is refused.
    base, read = _base("estimate"), estimate_reader.read_workbook
    assert read(with_member(base, "xl/drawings/vmlDrawing1.vml", EXCEL_VML)).lines == ()
    assert _refused(read, with_member(base, "xl/drawings/drawing1.xml", EXCEL_VML))
    main = b"http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    cells = b'<row xmlns="' + main + b'">' + b"<c/>" * (MOST_COLUMNS + 1) + b"</row><br>"
    assert _refused(read, with_member(base, "xl/drawings/vmlDrawing2.vml", cells))


VML = "xl/drawings/vmlDrawing1.vml"


@pytest.mark.story("US-3190")
def test_a_vml_drawing_not_well_formed_is_read_where_excel_names_it_and_refused_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Excel names a VML drawing in the relations of a worksheet, which openpyxl parses read-only
    # without following them; the relations of the workbook it follows, whatever their type, and
    # from a chartsheet every relation of the drawings it reaches.
    base, read = _base("estimate"), estimate_reader.read_workbook
    sheet = tab(base, "1 Études")
    worksheet = {sheet: "vmlDrawing ../drawings/vmlDrawing1.vml"}
    assert read(with_relations(base, {VML: EXCEL_VML}, worksheet)).lines == ()
    monkeypatch.setattr(workbooks, "load_workbook", _never_opened)
    for relation in ("vmlDrawing drawings/vmlDrawing1.vml", f"worksheet {VML} External"):
        workbook = {"xl/workbook.xml": relation}
        assert _refused(read, with_relations(base, {VML: EXCEL_VML}, workbook))
    chart = "xl/chartsheets/sheet1.xml"
    charted = with_relations(
        base,
        {chart: b"<chartsheet/>", "xl/drawings/drawing1.xml": b"<wsDr/>", VML: EXCEL_VML},
        {"xl/workbook.xml": f"chartsheet /{chart}", chart: "drawing ../drawings/drawing1.xml"},
    )
    charted = with_relations(charted, {}, {"xl/drawings/drawing1.xml": "chart vmlDrawing1.vml"})
    assert _refused(read, charted)


def _strings_at_a_vml(base: bytes) -> bytes:
    """Give the workbook whose content types name its shared strings at a VML drawing ill formed.

    openpyxl looks the shared strings up by their content type, and parses them whatever their name.
    """
    with zipfile.ZipFile(BytesIO(base)) as archive:
        types = archive.read("[Content_Types].xml")
    override = f'<Override PartName="/xl/sharedStrings.vml" ContentType="{SHARED_STRINGS}"/>'
    named = types.replace(b"</Types>", override.encode() + b"</Types>")
    members = {"[Content_Types].xml": named, "xl/sharedStrings.vml": EXCEL_VML}
    return with_relations(base, members, {})


def _a_tab_twice(base: bytes, *, ill_formed_first: bool) -> bytes:
    """Give the workbook whose tab lies twice at a ``.vml``, one of its copies ill formed.

    zipfile, as openpyxl, reads the last copy of a name; the reading ahead keeps the error of the
    first copy that has one.
    """
    sheet, member = tab(base, "1 Études"), "xl/worksheets/sheet3.vml"
    with zipfile.ZipFile(BytesIO(base)) as archive:
        well_formed = archive.read(sheet)
    ill_formed = well_formed.replace(b"</sheetData>", b"<br></sheetData>")
    first = relocated(base, sheet, member, f"/{member}", [b"<br>"] if ill_formed_first else [])
    with warnings.catch_warnings():
        # zipfile warns of a name written twice, which is the point here.
        warnings.simplefilter("ignore", UserWarning)
        return with_member(first, member, well_formed if ill_formed_first else ill_formed)


VML_PARSED: dict[str, Callable[[bytes], bytes]] = {
    "named-by-the-content-types": _strings_at_a_vml,
    "twice-ill-formed-first": lambda base: _a_tab_twice(base, ill_formed_first=True),
    "twice-ill-formed-last": lambda base: _a_tab_twice(base, ill_formed_first=False),
}


@pytest.mark.story("US-3190")
@pytest.mark.usefixtures("unopened")
@pytest.mark.parametrize("swollen_by", list(VML_PARSED))
def test_a_vml_ill_formed_that_openpyxl_parses_is_refused(swollen_by: str) -> None:
    # The tolerance of an ill-formed VML drawing holds only where openpyxl does not parse it: not
    # where the content types name it, nor at a name a member of the archive bears twice (#4838).
    content = VML_PARSED[swollen_by](_base("estimate"))
    assert _refused(estimate_reader.read_workbook, content) == READINGS["estimate"].params


RELATIONS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("element", ["legacyDrawing", "legacyDrawingHF"])
def test_a_vml_drawing_not_well_formed_of_a_chartsheet_is_read(element: str) -> None:
    # Excel names in the relations of a chartsheet the VML drawing of its form controls
    # (legacyDrawing) and of its header and footer (legacyDrawingHF); of those relations, openpyxl
    # parses the drawings alone, and the VML drawing is no refusal (#4837). Its chart is still read.
    base = charted(_base("estimate"), "Graphique")
    chart = "xl/chartsheets/sheet1.xml"
    with zipfile.ZipFile(BytesIO(base)) as archive:
        xml = archive.read(chart)
    legacy = f'<{element} xmlns:r="{RELATIONS}" r:id="rIdAdded"/></chartsheet>'
    content = with_relations(
        base,
        {chart: xml.replace(b"</chartsheet>", legacy.encode()), VML: EXCEL_VML},
        {chart: "vmlDrawing ../drawings/vmlDrawing1.vml"},
    )
    assert isinstance(load_workbook(BytesIO(content), read_only=True)["Graphique"], Chartsheet)
    assert estimate_reader.read_workbook(content).lines == ()


@pytest.mark.story("US-3190")
def test_the_two_hardened_parsers_take_the_same_options(monkeypatch: pytest.MonkeyPatch) -> None:
    taken: list[dict[str, Any]] = []
    parser = etree.XMLParser

    def spy(**options: Any) -> etree.XMLParser:
        taken.append(options)
        return parser()

    monkeypatch.setattr(etree, "XMLParser", spy)
    xml.hardened_parser()
    xml.hardened_target_parser(cast("Any", object()))
    first, second = taken
    assert second.pop("target") is not None
    assert first == second
    assert first["resolve_entities"] is False
    assert first["no_network"] is True


@pytest.mark.story("US-3190")
@pytest.mark.usefixtures("unopened")
def test_a_tab_the_hardened_parser_refuses_is_refused_though_openpyxl_reads_it() -> None:
    # openpyxl's parser reads past a value of 11 MB in an attribute, which the hardened parser
    # refuses: the reading ahead cannot leave the tab there, and let what follows pass unread.
    content = _with_row("estimate", 1, b'<c a="' + b"a" * 11_000_000 + b'"/>')
    assert _refused(estimate_reader.read_workbook, content) == READINGS["estimate"].params


# A row openpyxl reads past and the hardened parser refuses, then blanks past a step of the
# reading ahead, then a row past its cells.
PAST_THE_ERROR = (
    b'<row><c a="' + b"a" * 11_000_000 + b'"/></row>',
    *(b" " * MEBIBYTE for _ in range(3)),
    b"<row>" + b"<c/>" * 600 + b"</row>",
)


@pytest.mark.story("US-3190")
@pytest.mark.usefixtures("unopened")
@pytest.mark.parametrize(
    ("member", "target"),
    [
        ("xl/worksheets/sheet3.vml", "/xl/worksheets/sheet3.vml"),
        ("xl/worksheets/sheet3.vml", "./worksheets/../worksheets/sheet3.vml"),
        ("xl/worksheets/sheet3.VML", "../xl/worksheets/sheet3.VML"),
        ("xl/worksheets\\sheet3.vml", "worksheets\\sheet3.vml"),
    ],
)
def test_a_tab_named_as_a_vml_drawing_is_refused_past_an_error_of_its_syntax(
    member: str, target: str
) -> None:
    # openpyxl reads a tab wherever the relations of the workbook put it, whatever its name, and
    # finds it as zipfile names it, the target joined to its folder and normalised: a syntax error
    # leaves no tab unread, VML or not, and the row of 600 cells it reads after is refused.
    base = _base("estimate")
    content = relocated(base, tab(base, "1 Études"), member, target, PAST_THE_ERROR)
    sheet = load_workbook(BytesIO(content), read_only=True)["1 Études"]
    assert max(len(row) for row in sheet.iter_rows(values_only=True)) == 600
    assert _refused(estimate_reader.read_workbook, content) == READINGS["estimate"].params
