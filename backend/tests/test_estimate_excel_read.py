# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbook of an estimate, read and analysed.

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file;
US-1550 writes its tests here ("Les tests du back"). US-1550/L2: the reading, pure.
"""

import importlib
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook, load_workbook

from waterfall.core.estimate.excel.model import (
    Category,
    Estimate,
    Line,
    Lot,
    Nature,
    Role,
    Subproject,
    Tab,
    Task,
)
from waterfall.core.estimate.excel.reader import (
    DISBURSEMENT_HEADER,
    FORMAT_LABEL,
    HOURS_HEADER,
    LABEL_HEADER,
    LINEAGE_HEADER,
    PAYMENT_DELAY_HEADER,
    QUANTITY_HEADER,
    ROLE_OR_CATEGORY_HEADER,
    SUBPROJECT_HEADER,
    TASK_HEADER,
    TOTAL_LABEL,
    VERSION_LABEL,
    Rejection,
    read_number,
    read_workbook,
)
from waterfall.core.estimate.excel.writer import (
    FIXED_TABS,
    FORMAT_NAME,
    FORMAT_VERSION,
    LINE_HEADERS,
    PRESENTATION,
    TOTAL_HEADERS,
    write_workbook,
)
from waterfall.core.estimate.interface import sheet_name
from waterfall.platform.errors import UnprocessableError

D = Decimal
# XlsxWriter ships no stubs: the module is loaded as Any.
xlsxwriter: Any = importlib.import_module("xlsxwriter")
ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE = ROOT / "docs" / "spec" / "exemples" / "devis-prototype.xlsx"
HEADERS = [
    "Tâche",
    "Rôle ou catégorie",
    "Désignation",
    "Quantité",
    "Heures",
    "Débours unitaire",
    "Délai de paiement (j)",
    "Sous-projet",
    "ID ligne",
]


def workbook(
    sheets: dict[str, list[list[Any]]],
    header: tuple[Any, Any, Any, Any] = ("Format", FORMAT_NAME, "Version", FORMAT_VERSION),
) -> bytes:
    """Write a workbook: the presentation first, then one tab per entry of ``sheets``."""
    book = Workbook()
    presentation = book.active
    assert presentation is not None
    presentation.title = "Présentation"
    presentation.append(list(header[:2]))
    presentation.append(list(header[2:]))
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def refusal(content: bytes) -> UnprocessableError:
    with pytest.raises(UnprocessableError) as raised:
        read_workbook(content)
    return raised.value


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_workbook_of_the_format_and_a_known_version_is_accepted() -> None:
    read = read_workbook(workbook({"1.1 Lot": [HEADERS]}))

    assert read.lines == ()
    assert read.rejected == ()


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize(
    "header",
    [
        pytest.param(("Format", "Devis", "Version", None), id="no-version"),
        pytest.param(("Format", "Devis", "Version", 2), id="unknown-version"),
        pytest.param(("Format", "Devis", "Version", "v1"), id="text-version"),
        pytest.param(("Format", "Reste à engager", "Version", 1), id="other-format"),
        pytest.param((None, None, None, None), id="no-header"),
        pytest.param(("Format", "Devis", None, 1), id="no-version-label"),
    ],
)
def test_a_workbook_without_a_version_or_of_an_unknown_one_is_refused_naming_the_expected_ones(
    header: tuple[Any, Any, Any, Any],
) -> None:
    error = refusal(workbook({}, header))

    assert error.status == 422
    assert error.code == "FILE_FORMAT_UNREADABLE"
    assert error.params == {"expected_format": "estimate", "expected_version": "1"}


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("content", [b"", b"not a workbook", b"PK\x03\x04broken"])
def test_a_file_that_is_no_workbook_is_refused_as_unreadable(content: bytes) -> None:
    error = refusal(content)

    assert error.code == "FILE_FORMAT_UNREADABLE"
    assert error.params["expected_version"] == "1"


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_version_written_as_a_text_number_is_known() -> None:
    assert read_workbook(workbook({}, ("Format", "Devis", "Version", "1"))).lines == ()


@pytest.mark.requirement("WF-INTF-0100-A")
def test_every_column_read_is_given_with_its_tab_and_its_excel_row() -> None:
    rows = [
        HEADERS,
        ["1.1 Étude", "Développeur (DEV)", "Codage", 60, 7.4, None, None, "SP-PRE", "l-0103"],
        ["1.1 Étude", "Fournitures (fo-AINT)", None, 5, None, 20, 30, None, None],
    ]
    read = read_workbook(workbook({"1.1 Étude": rows}))

    assert read.rejected == ()
    labour, supply = read.lines
    assert (labour.sheet, labour.row) == ("1.1 Étude", 2)
    assert (labour.task, labour.role_or_category, labour.label) == (
        "1.1 Étude",
        "Développeur (DEV)",
        "Codage",
    )
    assert (labour.quantity, labour.hours, labour.disbursement) == (D(60), D("7.4"), None)
    assert (labour.payment_delay, labour.subproject, labour.lineage) == (None, "SP-PRE", "l-0103")
    assert (supply.sheet, supply.row) == ("1.1 Étude", 3)
    assert (supply.label, supply.hours, supply.subproject, supply.lineage) == (
        None,
        None,
        None,
        None,
    )
    assert (supply.quantity, supply.disbursement, supply.payment_delay) == (D(5), D(20), D(30))


@pytest.mark.requirement("WF-INTF-0100-A")
def test_columns_are_read_by_their_headers_whatever_their_rank_and_unknown_ones_are_ignored() -> (
    None
):
    rows = [
        ["Montant", "ID ligne", "Inconnue", "Heures", "Rôle ou catégorie", "Tâche", "Quantité"],
        [999, "l-1", "x", 7.4, "DEV", "1.1 Étude", 3],
    ]
    (line,) = read_workbook(workbook({"1.1 Étude": rows})).lines

    assert (line.lineage, line.hours, line.role_or_category, line.task, line.quantity) == (
        "l-1",
        D("7.4"),
        "DEV",
        "1.1 Étude",
        D(3),
    )
    assert (line.label, line.disbursement, line.subproject) == (None, None, None)


@pytest.mark.requirement("WF-INTF-0100-A")
def test_the_headers_may_sit_below_other_rows_and_the_rows_above_are_not_lines() -> None:
    rows = [["Un titre"], [], HEADERS, ["1.1", "DEV", None, 1, 7.4, None, None, None, None]]
    (line,) = read_workbook(workbook({"1.1": rows})).lines

    assert (line.row, line.task, line.quantity) == (4, "1.1", D(1))


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-INTF-0080-A")
def test_empty_lines_and_the_line_of_total_are_ignored_and_the_rows_keep_their_excel_number() -> (
    None
):
    rows = [
        HEADERS,
        ["1.1", "DEV", None, 1, 7.4, None, None, None, "l-1"],
        [None] * 9,
        ["", "  ", None, None, None, None, None, None, None],
        ["1.1", "DEV", None, 2, 7.4, None, None, None, "l-2"],
        ["Total", None, None, None, None, None, None, None, None],
    ]
    read = read_workbook(workbook({"1.1": rows}))

    assert [(line.row, line.lineage) for line in read.lines] == [(2, "l-1"), (5, "l-2")]
    assert read.rejected == ()


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_line_that_only_has_a_lineage_is_not_empty() -> None:
    rows = [HEADERS, [None, None, None, None, None, None, None, None, "l-9"]]

    assert [line.lineage for line in read_workbook(workbook({"1.1": rows})).lines] == ["l-9"]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_calculated_columns_and_a_total_row_of_formulas_do_not_make_lines() -> None:
    """XlsxWriter caches the value of a formula, so ``data_only`` reads a number, not none."""
    out = BytesIO()
    book: Any = xlsxwriter.Workbook(out, {"in_memory": True})
    presentation: Any = book.add_worksheet("Présentation")
    presentation.write_row(0, 0, ["Format", FORMAT_NAME])
    presentation.write_row(1, 0, ["Version", FORMAT_VERSION])
    sheet: Any = book.add_worksheet("2.1 Pose")
    sheet.write_row(0, 0, [*HEADERS, "Montant"])
    sheet.write_row(1, 0, ["2.1", "DEV", "Pose", 3, 2, None, None, None, "l-1"])
    sheet.write_formula(1, 9, "=D2*E2", None, 6)
    sheet.write(2, 0, "Total")
    sheet.write_formula(2, 9, "=SUBTOTAL(109,J2:J2)", None, 6)
    book.close()

    read = read_workbook(out.getvalue())

    assert [(line.sheet, line.row, line.quantity) for line in read.lines] == [("2.1 Pose", 2, D(3))]
    assert read.rejected == ()


@pytest.mark.requirement("WF-INTF-0100-A")
def test_the_tabs_that_are_not_tabs_of_lines_are_not_read_as_lines() -> None:
    other = [HEADERS, ["x", "DEV", None, 1, None, None, None, None, None]]
    read = read_workbook(
        workbook(
            {"Devis": other, "Tâches": other, "Paramètres": other, "3.1": other, "Notes": [["a"]]}
        )
    )

    assert [line.sheet for line in read.lines] == ["3.1"]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_every_tab_of_lines_is_read_in_the_order_of_the_workbook() -> None:
    row = ["t", "DEV", None, 1, None, None, None, None, None]
    read = read_workbook(workbook({"1.2 B": [HEADERS, row], "1.1 A": [HEADERS, row, row]}))

    assert [(line.sheet, line.row) for line in read.lines] == [
        ("1.2 B", 2),
        ("1.1 A", 2),
        ("1.1 A", 3),
    ]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_number_in_a_numeric_cell_is_read_exactly_with_its_decimals() -> None:
    rows = [HEADERS, ["t", "DEV", None, 0.1, 7.4, 1234.56, 45, None, None]]
    (line,) = read_workbook(workbook({"1.1": rows})).lines

    assert (line.quantity, line.hours, line.disbursement, line.payment_delay) == (
        D("0.1"),
        D("7.4"),
        D("1234.56"),
        D(45),
    )


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_number_in_a_text_cell_is_rejected_at_its_tab_and_row_and_the_other_lines_are_read() -> (
    None
):
    rows = [
        HEADERS,
        ["t", "DEV", None, "12", 7.4, None, None, None, "l-1"],
        ["t", "DEV", None, 1, "7,4", "20", None, None, "l-2"],
        ["t", "DEV", None, 3, 7.4, None, None, None, "l-3"],
    ]
    read = read_workbook(workbook({"1.1": rows}))

    assert [line.lineage for line in read.lines] == ["l-3"]
    assert [(r.sheet, r.row, r.code, dict(r.params)) for r in read.rejected] == [
        ("1.1", 2, "NUMBER_INVALID", {"header": "Quantité", "value": "12"}),
        ("1.1", 3, "NUMBER_INVALID", {"header": "Heures", "value": "7,4"}),
        ("1.1", 3, "NUMBER_INVALID", {"header": "Débours unitaire", "value": "20"}),
    ]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_text_in_an_unknown_column_is_not_a_rejected_number() -> None:
    rows = [[*HEADERS, "Commentaire"], ["t", "DEV", None, 1, None, None, None, None, None, "12"]]

    read = read_workbook(workbook({"1.1": rows}))

    assert len(read.lines) == 1
    assert read.rejected == ()


@pytest.mark.requirement("WF-INTF-0070-A")
def test_the_prototype_of_the_specification_is_a_workbook_of_the_format_whose_lines_are_read() -> (
    None
):
    read = read_workbook(PROTOTYPE.read_bytes())

    assert read.rejected == ()
    assert len(read.lines) > 10
    assert all(line.lineage and line.task and line.role_or_category for line in read.lines)
    assert {line.sheet for line in read.lines}.isdisjoint({"Présentation", "Devis", "Tâches"})


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_rejected_row_carries_the_lineage_of_the_row() -> None:
    rows = [HEADERS, ["t", "DEV", None, "12", 7.4, None, None, None, "l-1"]]

    read = read_workbook(workbook({"1.1": rows}))

    assert read.lines == ()
    assert [(r.row, r.lineage) for r in read.rejected] == [(2, "l-1")]


def test_the_params_of_a_rejection_cannot_be_changed() -> None:
    rejection = Rejection("1.1", 2, "NUMBER_INVALID", {"header": "Quantité"}, "l-1")

    params: Any = rejection.params
    with pytest.raises(TypeError):
        params["header"] = "x"


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_tab_without_the_headers_of_lines_is_named_as_unread() -> None:
    row = ["t", "DEV", None, 1, None, None, None, None, None]
    read = read_workbook(workbook({"1.1": [HEADERS, row], "Notes": [["a"]], "Autre": [["Tâche"]]}))

    assert read.unread_sheets == ("Notes", "Autre")
    assert [line.sheet for line in read.lines] == ["1.1"]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_the_headers_of_a_tab_read_that_are_missing_are_named() -> None:
    complete = [HEADERS, ["t", "DEV", None, 1, None, None, None, None, None]]
    partial = [["Tâche", "Rôle ou catégorie", "Quantité"], ["t", "DEV", 2]]
    read = read_workbook(workbook({"1.1": complete, "1.2": partial}))

    assert dict(read.missing_headers) == {
        "1.2": (
            "Désignation",
            "Sous-projet",
            "ID ligne",
            "Heures",
            "Débours unitaire",
            "Délai de paiement (j)",
        )
    }
    assert read.unread_sheets == ()
    assert [(line.sheet, line.hours) for line in read.lines] == [("1.1", None), ("1.2", None)]


def damaged(part: str) -> bytes:
    """Write the prototype with a part of its zip truncated (its XML is no longer well formed)."""
    out = BytesIO()
    with zipfile.ZipFile(PROTOTYPE) as source, zipfile.ZipFile(out, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            target.writestr(item, data[: len(data) // 2] if item.filename == part else data)
    return out.getvalue()


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize("part", ["xl/worksheets/sheet1.xml", "xl/workbook.xml"])
def test_a_workbook_whose_xml_is_damaged_is_refused_as_unreadable(part: str) -> None:
    error = refusal(damaged(part))

    assert error.code == "FILE_FORMAT_UNREADABLE"
    assert error.params == {"expected_format": "estimate", "expected_version": "1"}


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_workbook_whose_deflate_stream_is_altered_is_refused_as_unreadable() -> None:
    raw = bytearray(PROTOTYPE.read_bytes())
    with zipfile.ZipFile(PROTOTYPE) as source:
        info = source.getinfo("xl/worksheets/sheet1.xml")
    extra_length = int.from_bytes(raw[info.header_offset + 28 : info.header_offset + 30], "little")
    start = info.header_offset + 30 + len(info.filename.encode()) + extra_length
    middle = start + info.compress_size // 2
    raw[middle : middle + 4] = b"\xff\xff\xff\xff"

    error = refusal(bytes(raw))

    assert error.code == "FILE_FORMAT_UNREADABLE"
    assert error.params == {"expected_format": "estimate", "expected_version": "1"}


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(True, id="boolean"),
        pytest.param(date(2026, 1, 2), id="date"),
    ],
)
def test_a_cell_that_is_no_number_in_a_numeric_column_is_rejected(value: object) -> None:
    rows = [HEADERS, ["t", "DEV", None, value, None, None, None, None, "l-1"]]

    read = read_workbook(workbook({"1.1": rows}))

    assert read.lines == ()
    assert [(r.row, r.code, r.params["header"]) for r in read.rejected] == [
        (2, "NUMBER_INVALID", "Quantité")
    ]


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_boolean_is_not_a_version() -> None:
    assert refusal(workbook({}, ("Format", "Devis", "Version", True))).code == (
        "FILE_FORMAT_UNREADABLE"
    )


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_a_non_finite_number_is_not_a_number(value: float) -> None:
    """Openpyxl does not write them, so the branch is tried on the cell value itself."""
    assert read_number(value) == (None, False)


# --- The round trip: the workbook the writer of US-1550/L1 writes, read back ----------------------


def _line(lineage: str, **fields: Any) -> Line:
    values: dict[str, Any] = {"role": None, "category": None, "label": "", "quantity": D(1)}
    return Line(lineage, **{**values, **fields})


def _task(number: str, label: str, *lines: Line) -> Task:
    return Task(f"t-{number}", number, label, date(2026, 11, 2), date(2027, 3, 26), "", lines)


def _model(*, lots: tuple[Lot, ...], outside: Tab | None) -> Estimate:
    return Estimate(
        company="Exemple Industrie",
        client="Client Exemple",
        project="AFF-2026-014",
        revision="Chiffrage v2",
        structure="Structure principale",
        reference_year=2026,
        currency="EUR",
        exported_at=datetime(2026, 10, 22, 14, 5, tzinfo=UTC),
        natures=(Nature("Main-d’œuvre", "labour"), Nature("Fournitures", "disbursement")),
        categories=(
            Category("I810", "Gestion d’affaires", "Main-d’œuvre", D(100)),
            Category("fo-AINT", "Anti-intrusion", "Fournitures"),
        ),
        roles=(Role("RA-A1", "Responsable d’affaire A1", "Affaires > Activité 1", "I810"),),
        subprojects=(Subproject("SP-MAT", "Matériel"), Subproject("SP-PRE", "Prestations")),
        lots=lots,
        outside_lot=outside,
    )


def _round_trip_model() -> Estimate:
    package = Tab(
        "1.1",
        "Centrale",
        "Centrale",
        (
            _task("1.1", "Centrale"),
            _task(
                "1.1.1",
                "Management",
                _line("l-1", role="RA-A1", quantity=D(5), hours=D("7.4"), subproject="SP-PRE"),
                _line("l-2", role="RA-A1", quantity=D("2.5"), hours=D("0.1"), label="Suivi"),
            ),
            _task(
                "1.1.3",
                "Carte d’interface",
                _line(
                    "l-3",
                    category="fo-AINT",
                    quantity=D(5),
                    disbursement=D("20.35"),
                    payment_delay=30,
                    subproject="SP-MAT",
                    label="Détecteurs",
                ),
            ),
        ),
    )
    own = Tab(
        "1",
        "Contrôle d’accès",
        "Hors postes",
        (_task("1.3", "Revue", _line("l-4", role="RA-A1", quantity=D(3), hours=D("7.4"))),),
    )
    outside = Tab(
        "",
        "Hors lot",
        "Hors lot",
        (
            _task(
                "3",
                "Gestion",
                _line("l-5", category="fo-AINT", disbursement=D(1500), label="=1+1 reste du texte"),
            ),
        ),
    )
    return _model(lots=(Lot("1", "Contrôle d’accès", (package, own)),), outside=outside)


def test_the_workbook_the_writer_writes_is_read_back_identical_line_by_line() -> None:
    """WF-INTF-0070-A, WF-INTF-0100-A: the export read by the import loses and adds nothing."""
    estimate = _round_trip_model()
    labels = {role.code: role.label for role in estimate.roles}
    labels.update({category.code: category.label for category in estimate.categories})
    tabs = [tab for lot in estimate.lots for tab in lot.tabs]
    assert estimate.outside_lot is not None
    tabs.append(estimate.outside_lot)
    taken = ["Présentation", "Devis", "Tâches", "Paramètres"]
    expected: list[tuple[Any, ...]] = []
    for tab in tabs:
        name = sheet_name(f"{tab.number} {tab.task_label}".strip(), taken)
        taken.append(name)
        for task in tab.tasks:
            for line in task.lines:
                code = line.role or line.category
                expected.append(
                    (
                        name,
                        f"{task.number} {task.label}",
                        f"{labels[code or '']} ({code})",
                        line.label or None,
                        line.quantity,
                        line.hours,
                        line.disbursement,
                        None if line.payment_delay is None else D(line.payment_delay),
                        line.subproject,
                        line.lineage,
                    )
                )

    read = read_workbook(write_workbook(estimate))

    assert read.rejected == ()
    assert read.unread_sheets == ()
    assert dict(read.missing_headers) == {}
    assert [
        (
            line.sheet,
            line.task,
            line.role_or_category,
            line.label,
            line.quantity,
            line.hours,
            line.disbursement,
            line.payment_delay,
            line.subproject,
            line.lineage,
        )
        for line in read.lines
    ] == expected
    assert len(expected) == 5
    assert len({line.sheet for line in read.lines}) == 3


def test_the_blank_model_of_a_structure_without_a_line_is_read_without_a_line() -> None:
    """WF-INTF-0070-A: the model to fill in is a workbook of the format with its table empty."""
    read = read_workbook(write_workbook(_model(lots=(), outside=None)))

    assert read.lines == ()
    assert read.rejected == ()
    assert read.unread_sheets == ()
    assert dict(read.missing_headers) == {}


def test_the_headers_and_labels_the_reader_expects_are_the_ones_the_writer_writes() -> None:
    """WF-INTF-0070-A: the reader and the writer share one header, one version, one set of tabs.

    The tabs are taken by their names, as the reader identifies them; the totals the writer declares
    are the headers it names (``TOTAL_HEADERS``), on the row of the label the reader skips.
    """
    estimate = _round_trip_model()
    book = load_workbook(BytesIO(write_workbook(estimate)))
    first = book[PRESENTATION]
    assert [first["A1"].value, first["B1"].value, first["A2"].value, first["B2"].value] == [
        FORMAT_LABEL,
        FORMAT_NAME,
        VERSION_LABEL,
        FORMAT_VERSION,
    ]
    for header in (
        TASK_HEADER,
        ROLE_OR_CATEGORY_HEADER,
        LABEL_HEADER,
        QUANTITY_HEADER,
        HOURS_HEADER,
        DISBURSEMENT_HEADER,
        PAYMENT_DELAY_HEADER,
        SUBPROJECT_HEADER,
        LINEAGE_HEADER,
    ):
        assert header in LINE_HEADERS
    tab = estimate.lots[0].tabs[0]
    lines_tab = book[sheet_name(f"{tab.number} {tab.task_label}".strip(), FIXED_TABS)]
    headers = [cell.value for cell in lines_tab[1]]
    assert headers[: len(LINE_HEADERS)] == list(LINE_HEADERS)
    [total] = [row for row in lines_tab.iter_rows() if row[0].value == TOTAL_LABEL]
    totalled = {
        header: total[headers.index(header)].value
        for header in LINE_HEADERS
        if header != TASK_HEADER and total[headers.index(header)].value is not None
    }
    assert set(totalled) == set(TOTAL_HEADERS)
    assert all(str(value).startswith("=SUBTOTAL(109,") for value in totalled.values())
