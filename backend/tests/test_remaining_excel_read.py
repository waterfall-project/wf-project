# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbook « Reste à engager », read (US-1630/L2).

The pure reading, on workbooks built cell by cell and on the ones the writer of US-1630/L1 makes:
no database, no analysis (US-1630/L3). The round trip of the export itself is US-1630/L4's.
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook, load_workbook

from waterfall.core.estimate.remaining.excel.layout import (
    FORMAT_NAME,
    FORMAT_VERSION,
    HEADERS,
    OUTSIDE,
    PREPARED,
    REVIEW_DATE_CELL,
    SUMMARY,
    TABLE_ROW,
    TASKS,
)
from waterfall.core.estimate.remaining.excel.model import (
    Category,
    Nature,
    RemainingLine,
    RemainingTab,
    RemainingTask,
    RemainingWorkbook,
    Role,
    remaining_days,
)
from waterfall.core.estimate.remaining.excel.reader import (
    DAYS_HEADER,
    DISBURSEMENT_HEADER,
    read_remaining_workbook,
)
from waterfall.core.estimate.remaining.excel.writer import write_workbook
from waterfall.platform.errors import UnprocessableError

D = Decimal
ARCH = "Architecte logiciel (ARCH-LOG)"
PURCHASE = "Appareillage (fo-APPA)"
SMALL = ["Tâche", "Rôle ou catégorie", "Désignation", DAYS_HEADER, DISBURSEMENT_HEADER, "ID ligne"]


def workbook(
    sheets: dict[str, list[list[Any]]],
    header: tuple[Any, Any, Any, Any] = ("Format", FORMAT_NAME, "Version", FORMAT_VERSION),
    review: Any = date(2027, 2, 15),
) -> bytes:
    """Write a workbook: « Synthèse » first, with the header and the review, then the tabs."""
    book = Workbook()
    summary = book.active
    assert summary is not None
    summary.title = SUMMARY
    summary.append(list(header[:2]))
    summary.append(list(header[2:]))
    summary[REVIEW_DATE_CELL] = review
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def refusal(content: bytes) -> UnprocessableError:
    with pytest.raises(UnprocessableError) as raised:
        read_remaining_workbook(content)
    return raised.value


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_workbook_of_the_format_and_a_known_version_is_accepted() -> None:
    read = read_remaining_workbook(workbook({"SP-1": [SMALL]}))

    assert read.lines == ()
    assert read.rejected == ()


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize(
    "header",
    [
        pytest.param(("Format", FORMAT_NAME, "Version", None), id="no-version"),
        pytest.param(("Format", FORMAT_NAME, "Version", 2), id="unknown-version"),
        pytest.param(("Format", FORMAT_NAME, "Version", "v1"), id="text-version"),
        pytest.param(("Format", "Devis", "Version", 1), id="other-format"),
        pytest.param((None, None, None, None), id="no-header"),
        pytest.param(("Format", FORMAT_NAME, None, 1), id="no-version-label"),
    ],
)
def test_a_workbook_without_a_version_or_of_an_unknown_one_is_refused_naming_the_expected_ones(
    header: tuple[Any, Any, Any, Any],
) -> None:
    error = refusal(workbook({}, header))

    assert error.status == 422
    assert error.code == "FILE_FORMAT_UNREADABLE"
    assert error.params == {"expected_format": "remaining", "expected_version": "1"}


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("content", [b"", b"not a workbook", b"PK\x03\x04broken"])
def test_a_file_that_is_no_workbook_is_refused_as_unreadable(content: bytes) -> None:
    error = refusal(content)

    assert error.code == "FILE_FORMAT_UNREADABLE"
    assert error.params == {"expected_format": "remaining", "expected_version": "1"}


@pytest.mark.requirement("WF-INTF-0120-A")
@pytest.mark.parametrize(
    "review",
    [
        pytest.param(date(2027, 2, 15), id="date"),
        pytest.param("2027-02-15", id="iso-text"),
    ],
)
def test_the_review_date_is_read_in_the_summary_cell_the_writer_holds_it_in(review: Any) -> None:
    assert read_remaining_workbook(workbook({}, review=review)).review_date == date(2027, 2, 15)


@pytest.mark.requirement("WF-INTF-0120-A")
@pytest.mark.parametrize("review", [None, "demain", 42])
def test_a_review_date_that_is_no_date_is_none(review: Any) -> None:
    assert read_remaining_workbook(workbook({}, review=review)).review_date is None


@pytest.mark.requirement("WF-INTF-0120-A")
def test_the_tabs_are_read_by_their_headers_and_the_fixed_tabs_are_not() -> None:
    read = read_remaining_workbook(
        workbook(
            {
                "SP-1": [SMALL, ["1 A", ARCH, "x", 3, None, "l-1"]],
                OUTSIDE: [SMALL, ["2 B", PURCHASE, None, None, "12.5", "l-2"]],
                TASKS: [["Entrée", "ID tâche"], ["1 A", "t-1"], ["2 B", "t-2"], ["3 C", None]],
                "Paramètres": [SMALL, ["x", "y", None, 1, None, "z"]],
                "Notes": [["rien"]],
            }
        )
    )

    assert [(line.sheet, line.row, line.lineage) for line in read.lines] == [("SP-1", 2, "l-1")]
    assert [(r.sheet, r.row, r.code) for r in read.rejected] == [(OUTSIDE, 2, "NUMBER_INVALID")]
    assert read.unread_sheets == ("Notes",)
    assert dict(read.tasks) == {"1 A": "t-1", "2 B": "t-2"}


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_line_carries_the_columns_read_whatever_their_rank_and_ignores_the_others() -> None:
    headers = ["Budget", "ID ligne", "Inconnue", DISBURSEMENT_HEADER, "Désignation", DAYS_HEADER]
    headers += ["Rôle ou catégorie", "Tâche"]
    row = [10, "l-9", "?", None, "Une étude", D("2.5"), ARCH, "1 A"]
    read = read_remaining_workbook(workbook({"SP-1": [["en-tête libre"], headers, row]}))

    (line,) = read.lines
    assert (line.sheet, line.row) == ("SP-1", 3)
    assert (line.task, line.role_or_category, line.label) == ("1 A", ARCH, "Une étude")
    assert (line.days, line.disbursement, line.lineage) == (D("2.5"), None, "l-9")
    assert read.missing_headers == {}


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_header_missing_is_reported_and_its_cells_read_as_none() -> None:
    read = read_remaining_workbook(
        workbook({"SP-1": [["Tâche", "Rôle ou catégorie", DAYS_HEADER], ["1 A", ARCH, 1]]})
    )

    assert read.lines[0].lineage is None
    assert read.missing_headers == {"SP-1": ("Désignation", "ID ligne", DISBURSEMENT_HEADER)}


@pytest.mark.requirement("WF-INTF-0120-A")
def test_an_empty_line_and_the_line_of_total_are_ignored() -> None:
    rows = [
        SMALL,
        ["1 A", ARCH, None, 1, None, "l-1"],
        [None, None, None, None, None, None],
        ["  ", None, None, "", None, None],
        ["2 B", PURCHASE, None, None, 5, "l-2"],
        ["Total", None, None, 1, 5, None],
        ["Une note sous le tableau"],
    ]
    read = read_remaining_workbook(workbook({"SP-1": rows}))

    assert [(line.row, line.lineage) for line in read.lines] == [(2, "l-1"), (5, "l-2")]
    assert read.rejected == ()


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_number_written_as_text_is_rejected_by_its_tab_and_its_row() -> None:
    rows = [
        SMALL,
        ["1 A", ARCH, None, "3", None, "l-1"],
        ["1 A", ARCH, None, 2, None, "l-2"],
        ["2 B", PURCHASE, None, None, "12,50", None],
    ]
    read = read_remaining_workbook(workbook({"SP-1": rows}))

    assert [line.lineage for line in read.lines] == ["l-2"]
    assert [(r.sheet, r.row, r.code, r.lineage) for r in read.rejected] == [
        ("SP-1", 2, "NUMBER_INVALID", "l-1"),
        ("SP-1", 4, "NUMBER_INVALID", None),
    ]
    assert dict(read.rejected[0].params) == {"header": DAYS_HEADER, "value": "3"}
    assert dict(read.rejected[1].params) == {"header": DISBURSEMENT_HEADER, "value": "12,50"}


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_tab_without_the_headers_of_lines_is_unread_not_an_error() -> None:
    read = read_remaining_workbook(workbook({"Vide": [], "Autre": [["a", "b"], [1, 2]]}))

    assert read.unread_sheets == ("Vide", "Autre")
    assert read.lines == ()


def _labour(lineage: str, role: str, **fields: Any) -> RemainingLine:
    values: dict[str, Any] = {
        "category": None,
        "label": "",
        "budget": D(1000),
        "previous": None,
        "quantity": D(1),
        "hours": D(8),
        "reestimated_amount": D(0),
    }
    return RemainingLine(lineage, role=role, **{**values, **fields})


def _purchase(lineage: str, **fields: Any) -> RemainingLine:
    values: dict[str, Any] = {
        "label": "",
        "budget": D(3672),
        "previous": D(1600),
        "quantity": D(1),
        "hours": D(0),
        "reestimated_amount": D(1200),
    }
    return RemainingLine(lineage, role=None, category="fo-APPA", **{**values, **fields})


def _task(number: str, label: str, state: Any, *lines: RemainingLine) -> RemainingTask:
    return RemainingTask(f"t-{number}", number, label, state, D(1), f"Description {label}", lines)


def _book() -> RemainingWorkbook:
    services = RemainingTab(
        "SP-PRE",
        "Prestations",
        D("68567.60"),
        D("21500.00"),
        D(0),
        (
            _task(
                "1.1.2",
                "Développement",
                "started",
                _labour("l-1", "ARCH-LOG", quantity=D(3), hours=D(8)),
                _labour("l-2", "DEV", quantity=D(1), hours=D(24), label="=1+1 reste du texte"),
            ),
            _task("1.2.2", "Câblage", "not_started", _purchase("l-3")),
        ),
    )
    outside = RemainingTab(
        "",
        "",
        D("16724.00"),
        D("4200.00"),
        D("1500.00"),
        (_task("3", "Gestion", "started", _labour("l-5", "RA-A1", quantity=D(12))),),
    )
    return RemainingWorkbook(
        company="Exemple Industrie",
        client="Client Exemple",
        project="A.ABC.26001 Contrôle d’accès",
        revision="Revue de février",
        structure="Structure principale",
        review_date=date(2027, 2, 15),
        currency="EUR",
        exported_at=datetime(2027, 2, 15, 9, 30, tzinfo=UTC),
        hours_per_day=D(8),
        natures=(Nature("Main-d’œuvre", "labour"), Nature("Fournitures", "disbursement")),
        categories=(
            Category("I810", "Gestion d’affaires", "Main-d’œuvre", D(100)),
            Category("I329", "Ingénierie logicielle", "Main-d’œuvre", D(80)),
            Category("fo-APPA", "Appareillage", "Fournitures"),
        ),
        roles=(
            Role("RA-A1", "Responsable d’affaire A1", "Affaires > Activité 1", "I810"),
            Role("ARCH-LOG", "Architecte logiciel", "Ingénierie > Logiciel", "I329"),
            Role("DEV", "Développeur", "Ingénierie > Logiciel", "I329"),
        ),
        subprojects=(services,),
        outside=outside,
    )


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_workbook_the_writer_makes_is_read_back_line_for_line() -> None:
    book = _book()
    read = read_remaining_workbook(write_workbook(book))

    assert read.rejected == ()
    assert read.unread_sheets == ()
    assert read.missing_headers == {}
    assert read.review_date == book.review_date
    expected: list[tuple[str, str, str, str | None, Decimal | None, Decimal | None]] = []
    for tab in (*book.subprojects, book.outside):
        assert tab is not None
        for task in tab.tasks:
            for line in task.lines:
                labour = line.role is not None
                days = remaining_days(line.quantity, line.hours, book.hours_per_day)
                expected.append(
                    (
                        tab.code or OUTSIDE,
                        line.lineage,
                        f"{task.number} {task.label}",
                        line.label or None,
                        days if labour else None,
                        None if labour else line.reestimated_amount,
                    )
                )
    assert (read.lines[0].lineage, read.lines[0].days, read.lines[0].disbursement) == (
        "l-1",
        D(3),
        None,
    )
    assert (read.lines[2].lineage, read.lines[2].days, read.lines[2].disbursement) == (
        "l-3",
        None,
        D(1200),
    )
    got = [(r.sheet, r.lineage, r.task, r.label, r.days, r.disbursement) for r in read.lines]
    assert got == expected
    assert dict(read.tasks) == {
        f"{task.number} {task.label}": task.lineage
        for tab in (*book.subprojects, book.outside)
        if tab is not None
        for task in tab.tasks
    }


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_prepared_rows_and_the_row_of_total_of_the_written_tables_are_not_lines() -> None:
    content = write_workbook(_book())
    read = read_remaining_workbook(content)
    sheet = load_workbook(BytesIO(content))["SP-PRE"]
    # Excel rows: the headers at TABLE_ROW + 1, the three lines below them, then the prepared rows.
    first_line = TABLE_ROW + 2
    first_prepared = first_line + 3
    prepared = range(first_prepared, first_prepared + PREPARED)
    total = first_prepared + PREPARED

    assert len(prepared) == 10
    assert sheet.max_row >= total + 2
    assert sheet.cell(total, 1).value == "Total"
    assert all(sheet.cell(row, 2).value is not None for row in prepared)  # their formulas
    assert len(read.lines) == 4
    assert {line.row for line in read.lines if line.sheet == "SP-PRE"} == set(
        range(first_line, first_prepared)
    )


@pytest.mark.requirement("WF-INTF-0120-A")
def test_the_headers_read_are_headers_of_the_layout() -> None:
    assert {DAYS_HEADER, DISBURSEMENT_HEADER} <= set(HEADERS)


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_line_typed_under_the_line_of_total_is_read() -> None:
    rows = [
        SMALL,
        ["1 A", ARCH, None, 1, None, "l-1"],
        ["Total", None, None, 1, None, None],
        ["2 B", ARCH, None, "x", None, "l-2"],
        ["3 C", PURCHASE, None, None, 5, "l-3"],
    ]
    read = read_remaining_workbook(workbook({"SP-1": rows}))

    assert [(line.row, line.lineage) for line in read.lines] == [(2, "l-1"), (5, "l-3")]
    assert [(r.row, r.lineage) for r in read.rejected] == [(4, "l-2")]


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_note_the_writer_sets_under_the_table_is_not_a_line() -> None:
    content = write_workbook(_book())
    sheet = load_workbook(BytesIO(content))["SP-PRE"]
    notes = [
        row
        for row in range(1, sheet.max_row + 1)
        if str(sheet.cell(row, 1).value).startswith("Les tâches")
    ]

    assert len(notes) == 1
    assert notes[0] > TABLE_ROW + 2 + 3 + PREPARED
    assert notes[0] not in {line.row for line in read_remaining_workbook(content).lines}


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_total_that_carries_numbers_a_role_a_label_or_a_lineage_is_not_a_total() -> None:
    rows = [
        SMALL,
        ["1 A", ARCH, None, 1, None, "l-1"],
        ["Total", None, None, 7, None, None],
        ["Total", ARCH, None, None, None, None],
        ["Total", None, "Divers", None, None, None],
        ["Total", None, None, None, None, "l-4"],
    ]
    read = read_remaining_workbook(workbook({"SP-1": rows}))

    assert [line.row for line in read.lines] == [2, 3, 4, 5, 6]
    assert read.rejected == ()


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_workbook_without_any_tab_of_lines_is_read_empty() -> None:
    empty = replace(_book(), subprojects=(), outside=None)
    read = read_remaining_workbook(write_workbook(empty))

    assert read.lines == ()
    assert read.rejected == ()
