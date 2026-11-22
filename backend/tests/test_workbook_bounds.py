# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A workbook beyond the bounds is refused before it is opened, and a tab read within its bounds.

US-3190/L1: the opener of the exchanges (``opened_workbook``) judges the archive — its members,
their sizes declared, then what each inflates to — before openpyxl reads any of it, and each reader
materialises the tabs its format reads alone, each within its rows and columns (``bounded_rows``).
Tried here on the three readers of a workbook, by what the opening, the analysis and the
application call: the header, the whole reading, the preparation of the application. The refusals
through ``openImport`` are ``test_workbook_bounds_opening``'s; the round trips of the exports, and
the applications of the actual costs, ``test_estimate_export``'s, ``test_remaining_export``'s and
``test_actual_costs_apply``'s, which pass through the opener as every import does.
"""

import zipfile
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from actual_costs_import_support import extraction, line
from estimate_import_support import workbook as estimate_workbook
from remaining_import_support import workbook as remaining_workbook
from workbook_bombs import (
    CALM,
    GIBIBYTE,
    MEBIBYTE,
    announcing,
    compressed_by,
    crowded,
    duplicated,
    encrypted,
    grown,
    in_zip64,
    lying,
    measured,
    swollen,
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


@pytest.fixture
def unopened(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if openpyxl is asked to open a workbook."""

    def opened(*_: object, **__: object) -> None:
        msg = "the workbook was opened"
        raise AssertionError(msg)

    monkeypatch.setattr(workbooks, "load_workbook", opened)


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


@pytest.mark.story("US-3190")
@pytest.mark.parametrize("name", list(READINGS))
def test_a_tab_read_at_its_bounds_and_a_tab_not_read_past_them_are_read(name: str) -> None:
    reading = READINGS[name]
    read = reading.read[0]
    reading.whole(grown(_base(name), read, MOST_ROWS, 1))
    reading.prepare(grown(_base(name), read, 1, MOST_COLUMNS))
    for sheet in reading.unread:
        past = grown(_base(name), sheet, MOST_ROWS + 1, 1)
        reading.whole(grown(past, sheet, 1, MOST_COLUMNS + 1))
