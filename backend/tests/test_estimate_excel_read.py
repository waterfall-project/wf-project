# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbook of an estimate, read and analysed.

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file;
US-1550 writes its tests here ("Les tests du back"). US-1550/L2: the reading, pure.
"""

from decimal import Decimal
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook
from support import CONTRACT

from waterfall.core.estimate.excel.reader import (
    FORMAT_NAME,
    FORMAT_VERSION,
    read_workbook,
)
from waterfall.platform.errors import UnprocessableError

D = Decimal
PROTOTYPE = CONTRACT.parents[1] / "spec" / "exemples" / "devis-prototype.xlsx"
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
    rows = [
        [*HEADERS, "Montant"],
        ["2.1", "DEV", "=1+1", 3, 2, None, None, None, "l-1", "=D2*E2"],
        ["Total", None, None, None, None, None, None, None, None, "=SUBTOTAL(109,A2:A2)"],
    ]

    read = read_workbook(workbook({"2.1 Pose": rows}))

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
        ("1.1", 2, "NUMBER_INVALID", {"column": "Quantité", "value": "12"}),
        ("1.1", 3, "NUMBER_INVALID", {"column": "Heures", "value": "7,4"}),
        ("1.1", 3, "NUMBER_INVALID", {"column": "Débours unitaire", "value": "20"}),
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
