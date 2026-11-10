# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbook « Reste à engager », written (US-1630/L1).

The pure writer of the workbook of annex B, on a revision in memory: no database, no exchanges. The
workbook is read back with openpyxl and with its own XML, and ``docs/spec/exemples/check_xlsx.py``
is run on it as the specification gives it. The export that fills the model is US-1630/L4; the
round trip is proved there.
"""

import subprocess
import sys
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from openpyxl import Workbook, load_workbook

from waterfall.core.estimate.remaining.excel.layout import line_formulas
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
from waterfall.core.estimate.remaining.excel.writer import write_workbook

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

    from waterfall.core.estimate.remaining.excel.model import TaskState

D = Decimal
CHECKER = Path(__file__).resolve().parents[2] / "docs" / "spec" / "exemples" / "check_xlsx.py"
EXPORTED_AT = datetime(2027, 2, 15, 9, 30, tzinfo=UTC)
HEADER_ROW = 15  # the row (from 1) of the header of the table of lines
LITERAL = "=1+1 reste une désignation"
ARCH = "Architecte logiciel (ARCH-LOG)"
PURCHASE = "Appareillage (fo-APPA)"


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


def _task(
    number: str, label: str, state: TaskState, *lines: RemainingLine, inflation: str = "1"
) -> Any:
    return RemainingTask(
        lineage=f"t-{number}",
        number=number,
        label=label,
        state=state,
        inflation=D(inflation),
        description=f"Description de {label}",
        lines=lines,
    )


def _book(**changes: Any) -> RemainingWorkbook:
    """Give the revision of the prototype of the specification, as the tests read it."""
    services = RemainingTab(
        "SP-PRE",
        "Prestations",
        D("68567.60"),
        D("21500.00"),
        D(0),
        (
            _task(
                "1.1.2",
                "Développement du logiciel",
                "started",
                _labour("l-1", "ARCH-LOG", quantity=D(3), hours=D(8), previous=D(6000)),
                _labour("l-2", "DEV", quantity=D(1), hours=D(24), label=LITERAL),
            ),
            _task("1.2.2", "Câblage", "not_started", _purchase("l-3"), inflation="1.02"),
        ),
    )
    hardware = RemainingTab(
        "sp-pre",  # the same name as the first, without regard to case
        "Matériel",
        D("7444.00"),
        D("3800.00"),
        D(0),
        (_task("1.2.1", "Approvisionnement", "started", _purchase("l-4", label="Lot 1")),),
    )
    outside = RemainingTab(
        "",
        "",
        D("16724.00"),
        D("4200.00"),
        D("1500.00"),
        (_task("3", "Gestion de projet", "started", _labour("l-5", "RA-A1", quantity=D(12))),),
    )
    values: dict[str, Any] = {
        "company": "Exemple Industrie",
        "client": "Client Exemple",
        "project": "A.ABC.26001 Contrôle d’accès du site de Lyon",
        "revision": "Revue de février (en cours)",
        "structure": "Structure principale",
        "review_date": date(2027, 2, 15),
        "currency": "EUR",
        "exported_at": EXPORTED_AT,
        "hours_per_day": D(8),
        "natures": (
            Nature("Main-d’œuvre", "labour"),
            Nature("Fournitures", "disbursement"),
            Nature("Provisions pour risques", "provision"),
        ),
        "categories": (
            Category("I810", "Gestion d’affaires", "Main-d’œuvre", D(100)),
            Category("I329", "Ingénierie logicielle", "Main-d’œuvre", D(80)),
            Category("fo-APPA", "Appareillage", "Fournitures"),
            Category("PRV", "Provision pour risques", "Provisions pour risques"),
        ),
        "roles": (
            Role("RA-A1", "Responsable d’affaire A1", "Affaires > Activité 1", "I810"),
            Role("ARCH-LOG", "Architecte logiciel", "Ingénierie > Logiciel", "I329"),
            Role("DEV", "Développeur", "Ingénierie > Logiciel", "I329"),
        ),
        "subprojects": (services, hardware),
        "outside": outside,
    }
    values.update(changes)
    return RemainingWorkbook(**values)


def _open(content: bytes) -> Workbook:
    return load_workbook(BytesIO(content))


def _row(sheet: Worksheet, row: int) -> dict[str, Any]:
    """Give a row of a table of lines by header."""
    headers = [cell.value for cell in sheet[HEADER_ROW]]
    values = [cell.value for cell in sheet[row]]
    return {str(header): value for header, value in zip(headers, values, strict=True)}


def _footer(sheet: Worksheet) -> tuple[str, str]:
    """Give the left and the right part of the footer of a tab."""
    footer = sheet.oddFooter
    assert footer is not None
    assert footer.left is not None
    assert footer.right is not None
    return str(footer.left.text), str(footer.right.text)


@pytest.fixture(scope="module")
def content() -> bytes:
    return write_workbook(_book())


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_checker_of_the_specification_finds_no_problem_in_the_workbook(
    content: bytes, tmp_path: Path
) -> None:
    path = tmp_path / "reste-a-engager.xlsx"
    path.write_bytes(content)
    done = subprocess.run(
        [sys.executable, "-I", str(CHECKER), str(path)], capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == "problèmes : 0"


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_tabs_are_the_summary_the_subprojects_the_outside_tab_the_tasks_and_the_parameters(
    content: bytes,
) -> None:
    assert _open(content).sheetnames == [
        "Synthèse",
        "SP-PRE",
        "sp-pre (2)",
        "Hors sous-projet",
        "Tâches",
        "Paramètres",
    ]


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_summary_opens_with_the_format_then_the_facts_the_review_in_b9() -> None:
    sheet = _open(write_workbook(_book()))["Synthèse"]
    assert [sheet[cell].value for cell in ("A1", "B1", "A2", "B2")] == [
        "Format",
        "Reste à engager",
        "Version",
        1,
    ]
    # The facts of annex B, rows 6 to 11; the date of the review in B9, where the import reads it.
    assert [(sheet[f"A{row}"].value, sheet[f"B{row}"].value) for row in range(6, 12)] == [
        ("Entreprise", "Exemple Industrie"),
        ("Client", "Client Exemple"),
        ("Révision", "Revue de février (en cours)"),
        ("Revue du", "2027-02-15"),
        ("Structure", "Structure principale"),
        ("Devise", "EUR"),
    ]
    assert sheet["A4"].value == "A.ABC.26001 Contrôle d’accès du site de Lyon"


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_summary_breaks_down_each_subproject_and_the_project_by_formulas(
    content: bytes,
) -> None:
    sheet = _open(content)["Synthèse"]
    headers = [cell.value for cell in sheet[15]]
    assert headers[:7] == [
        "Sous-projet",
        "Budget",
        "Coûts réels",
        "Reste à engager",
        "Projection",
        "Écart au budget",
        "Avancement financier",
    ]
    assert headers[7:] == [
        "Reste — Main-d’œuvre",
        "Reste — Fournitures",
        "Reste — Provisions pour risques",
        "Jours I810",
        "Jours I329",
    ]
    assert [sheet.cell(16 + i, 1).value for i in range(4)] == [
        "SP-PRE Prestations",
        "sp-pre Matériel",
        "Hors sous-projet",
        "Projet",
    ]
    assert sheet["B16"].value == "='SP-PRE'!$B$4"
    assert sheet["C17"].value == "='sp-pre (2)'!$B$5"
    assert sheet["D18"].value == "='Hors sous-projet'!$B$9"
    assert sheet["J18"].value == "='Hors sous-projet'!$B$7"  # the provisions, from the header
    assert sheet["H16"].value == (
        '=SUMIFS(RAE_SP_PRE[[Reste à engager]],RAE_SP_PRE[[Nature]],"Main-d’œuvre")'
    )
    assert sheet["K16"].value == (
        '=SUMIFS(RAE_SP_PRE[[Jours restants]],RAE_SP_PRE[[Code comptable]],"I810")'
    )
    assert sheet["B19"].value == "=SUM(B16:B18)"
    assert sheet["G19"].value == '=IF(E19=0,"non calculable",C19/E19)'


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_tab_opens_with_its_amounts_and_the_indicators_the_table_does_not_hold(
    content: bytes,
) -> None:
    sheet = _open(content)["Hors sous-projet"]
    assert sheet["A1"].value == "Hors sous-projet"
    assert [(sheet[f"A{r}"].value, sheet[f"B{r}"].value) for r in range(4, 8)] == [
        ("Budget du sous-projet", 16724),
        ("Coûts réels imputés", 4200),
        ("Reste à engager du tableau", "=SUBTOTAL(109,RAE_hors_sous_projet[[Reste à engager]])"),
        ("Provisions des risques identifiés", 1500),
    ]
    assert sheet["B9"].value == "=$B$6+$B$7"
    assert sheet["B10"].value == "=$B$5+$B$9"
    assert sheet["B11"].value == "=$B$10-$B$4"
    assert sheet["B12"].value == '=IF($B$10=0,"non calculable",$B$5/$B$10)'
    assert sheet["H14"].value == "Reste au 2027-02-15"


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_tab_of_lines_lists_the_columns_of_the_annex_in_order(content: bytes) -> None:
    sheet = _open(content)["SP-PRE"]
    assert [cell.value for cell in sheet[HEADER_ROW]] == [
        "Tâche",
        "Description de la tâche",
        "État",
        "Rôle ou catégorie",
        "Désignation",
        "Budget",
        "Reste précédent",
        "Jours restants",
        "Débours restant",
        "Nature",
        "Code comptable",
        "Service",
        "Taux horaire",
        "Main-d’œuvre",
        "Débours",
        "Reste à engager",
        "Type",
        "Coefficient",
        "ID ligne",
    ]


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_line_of_labour_carries_the_days_left_quantity_times_effort_over_hours_per_day(
    content: bytes,
) -> None:
    sheet = _open(content)["SP-PRE"]
    first, second = _row(sheet, 16), _row(sheet, 17)
    # Three units of eight hours with eight hours a day: three days.
    assert (first["Jours restants"], first["Débours restant"]) == (3, None)
    # One unit of twenty-four hours: three days as well, whatever the quantity.
    assert second["Jours restants"] == 3
    assert (first["Budget"], first["Reste précédent"]) == (1000, 6000)
    assert second["Reste précédent"] is None


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_days_follow_the_hours_per_day_of_the_installation() -> None:
    assert remaining_days(D(3), D(8), D(8)) == D(3)
    assert remaining_days(D(1), D(24), D(8)) == D(3)
    assert remaining_days(D(3), D(8), D("7.5")) == D("3.2")
    sheet = _open(write_workbook(_book(hours_per_day=D("7.5"))))
    assert sheet["Paramètres"]["B2"].value == 7.5
    assert _row(sheet["SP-PRE"], 16)["Jours restants"] == pytest.approx(3.2)


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_line_of_disbursement_carries_the_amount_reestimated_not_days(content: bytes) -> None:
    row = _row(_open(content)["sp-pre (2)"], 16)
    assert (row["Jours restants"], row["Débours restant"]) == (None, 1200)
    assert row["Rôle ou catégorie"] == PURCHASE
    assert row["Désignation"] == "Lot 1"
    assert (row["Budget"], row["Reste précédent"]) == (3672, 1600)
    assert row["ID ligne"] == "l-4"
    assert _row(_open(content)["SP-PRE"], 16)["Rôle ou catégorie"] == ARCH


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_text_typed_stays_a_text_never_a_formula(content: bytes) -> None:
    sheet = _open(content)["SP-PRE"]
    cell = sheet.cell(17, 5)
    assert cell.value == LITERAL
    assert cell.data_type == "s"


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_table_has_a_declared_total_row_ten_empty_rows_and_a_hidden_lineage(
    content: bytes,
) -> None:
    sheet = _open(content)["SP-PRE"]
    table = sheet.tables["RAE_SP_PRE"]
    # The header, three lines, ten empty rows, the total row.
    assert table.ref == "A15:S29"
    assert table.totalsRowCount == 1
    declared = {
        column.name: column.totalsRowFunction
        for column in table.tableColumns
        if column.totalsRowFunction
    }
    assert declared["Jours restants"] == "custom"
    assert set(declared) == {
        "Budget",
        "Reste précédent",
        "Jours restants",
        "Débours restant",
        "Main-d’œuvre",
        "Débours",
        "Reste à engager",
    }
    assert sheet.cell(29, 1).value == "Total"
    assert all(_row(sheet, row)["Tâche"] is None for row in range(19, 29))
    # The type, the coefficient and the lineage: columns Q to S, grouped and hidden.
    hidden = sheet.column_dimensions["Q"]
    assert (hidden.min, hidden.max, hidden.hidden) == (17, 19, True)
    assert not sheet.column_dimensions["P"].hidden


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_calculated_columns_are_formulas_that_name_their_table(content: bytes) -> None:
    sheet = _open(content)["SP-PRE"]
    row = _row(sheet, 20)  # the first of the prepared rows
    for header in ("Description de la tâche", "État", "Nature", "Code comptable", "Taux horaire"):
        assert row[header].startswith("=IF(")
    assert "RAE_SP_PRE[[#This Row],[Jours restants]]" in row["Main-d’œuvre"]
    assert "*HeuresParJour*" in row["Main-d’œuvre"]
    assert "RAE_SP_PRE[[#This Row],[Coefficient]]" in row["Main-d’œuvre"]
    assert "RAE_SP_PRE[[#This Row],[Débours restant]]" in row["Débours"]
    assert row["Reste à engager"].endswith("[Main-d’œuvre]]+RAE_SP_PRE[[#This Row],[Débours]])")


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_lists_of_choice_cover_the_tasks_the_roles_and_the_amounts_left(
    content: bytes,
) -> None:
    sheet = _open(content)["SP-PRE"]
    validations = {
        str(item.sqref): (item.type, item.formula1)
        for item in sheet.data_validations.dataValidation
    }
    assert validations["A16:A415"] == ("list", "'Tâches'!$A$5:$A$6")
    assert validations["D16:D415"] == ("list", "'Paramètres'!$A$5:$A$8")
    assert validations["H16:H415"][0] == "decimal"
    assert validations["I16:I415"][0] == "decimal"
    assert _open(content)["sp-pre (2)"].data_validations.dataValidation[0].formula1 == (
        "'Tâches'!$A$7:$A$7"
    )


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_tasks_tab_gives_the_lineage_the_subproject_the_state_and_the_inflation(
    content: bytes,
) -> None:
    sheet = _open(content)["Tâches"]
    assert [cell.value for cell in sheet[4]] == [
        "Entrée",
        "ID tâche",
        "Sous-projet",
        "État",
        "Coefficient",
        "Description",
    ]
    assert [cell.value for cell in sheet[5]] == [
        "1.1.2 Développement du logiciel",
        "t-1.1.2",
        "SP-PRE",
        "démarrée",
        1,
        "Description de Développement du logiciel",
    ]
    assert [cell.value for cell in sheet[6]][3:5] == ["non démarrée", 1.02]
    assert sheet["C9"].value in ("", None)  # a task outside any subproject has no code


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_parameters_hold_the_reference_and_the_hours_per_day(content: bytes) -> None:
    sheet = _open(content)["Paramètres"]
    assert (sheet["A2"].value, sheet["B2"].value) == ("Heures par jour", 8)
    assert [cell.value for cell in sheet[4]][:3] == ["Entrée", "Genre", "Code"]
    assert [cell.value for cell in sheet[5]] == [
        "Responsable d’affaire A1 (RA-A1)",
        "Rôle",
        "RA-A1",
        "Responsable d’affaire A1",
        "Affaires > Activité 1",
        "Main-d’œuvre",
        "Main-d’œuvre",
        "I810",
        100,
    ]
    # The provision comes last, outside the list of choice.
    assert sheet["A9"].value == "Provision pour risques (PRV)"


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_tasks_and_the_parameters_are_protected_and_the_others_are_not(
    content: bytes,
) -> None:
    book = _open(content)
    assert {name: book[name].protection.sheet for name in book.sheetnames} == {
        "Synthèse": False,
        "SP-PRE": False,
        "sp-pre (2)": False,
        "Hors sous-projet": False,
        "Tâches": True,
        "Paramètres": True,
    }


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_logo_and_the_footer_are_those_of_the_estimate(content: bytes) -> None:
    archive = zipfile.ZipFile(BytesIO(content))
    assert [name for name in archive.namelist() if name.startswith("xl/media/")] == [
        "xl/media/image1.png"
    ]
    book = _open(content)
    for sheet in book.worksheets:
        left, right = _footer(sheet)
        assert left.startswith("© 2027 Exemple Industrie — Généré par Waterfall le ")
        assert "2027-02-15 09:30" in left
        assert right == "Page &P / &N"
    assert "www.waterfall-project.pro" in str(book["Synthèse"]["A23"].value)


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_long_company_does_not_break_the_limit_of_the_footer() -> None:
    book = _open(write_workbook(_book(company="Société & " + "Z" * 400)))
    assert len(_footer(book["Synthèse"])[0]) < 255


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_same_revision_gives_the_same_workbook_whoever_exports_it() -> None:
    assert write_workbook(_book()) == write_workbook(_book())


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_revision_without_a_tab_gives_the_blank_model() -> None:
    blank = _open(write_workbook(_book(subprojects=(), outside=None)))
    assert blank.sheetnames == ["Synthèse", "Hors sous-projet", "Tâches", "Paramètres"]
    sheet = blank["Hors sous-projet"]
    assert sheet.tables["RAE_hors_sous_projet"].ref == "A15:S26"
    assert blank["Tâches"]["A5"].value is None


@pytest.mark.requirement("WF-INTF-0130-A")
def test_a_currency_is_the_installations_in_the_amount_format() -> None:
    sheet = _open(write_workbook(_book(currency="USD")))["SP-PRE"]
    assert sheet["B4"].number_format == '#,##0.00 "$"'


@pytest.mark.requirement("WF-INTF-0130-A")
def test_hours_per_day_that_is_not_positive_is_refused() -> None:
    with pytest.raises(ValueError, match="hours per day"):
        write_workbook(_book(hours_per_day=D(0)))


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_service_column_turns_an_empty_text_into_an_empty_text() -> None:
    key = "T[[#This Row],[Rôle ou catégorie]]"
    assert line_formulas("T")["Service"] == (
        f'=IF({key}="","",IFERROR(INDEX(Referentiel[[Service]],'
        f'MATCH({key},Referentiel[[Entrée]],0))&"","?"))'
    )


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_summary_and_the_tabs_of_lines_are_printed_in_landscape(content: bytes) -> None:
    book = _open(content)
    for name in ("Synthèse", "SP-PRE", "sp-pre (2)", "Hors sous-projet"):
        assert book[name].page_setup.orientation == "landscape", name


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_hours_per_day_is_a_defined_name_the_formulas_use(content: bytes) -> None:
    book = _open(content)
    assert book.defined_names["HeuresParJour"].attr_text == "'Paramètres'!$B$2"
    formula = line_formulas("T")["Main-d’œuvre"]
    assert "HeuresParJour" in formula
    assert "$B$2" not in formula
    archive = zipfile.ZipFile(BytesIO(content))
    assert '<definedName name="HeuresParJour">' in archive.read("xl/workbook.xml").decode()


@pytest.mark.requirement("WF-INTF-0130-A")
def test_the_bands_are_merged_across_their_columns(content: bytes) -> None:
    book = _open(content)
    assert {str(r) for r in book["SP-PRE"].merged_cells.ranges} == {"H14:I14"}
    assert any(str(r).startswith("H") for r in book["Synthèse"].merged_cells.ranges)
