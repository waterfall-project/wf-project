# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbook of an estimate, written.

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file;
US-1550/L1 writes its tests here ("Les tests du back"): the pure writer of the workbook « Devis »
of annex B, on an estimate in memory, and the name of a tab (#2190). No database: the workbook is
read back with openpyxl and with its own XML, as ``docs/spec/exemples/check_xlsx.py`` does.
"""

import re
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pytest
from lxml import etree
from openpyxl import Workbook, load_workbook
from openpyxl.utils.cell import (
    column_index_from_string,
    coordinate_from_string,
    get_column_letter,
    range_boundaries,
)

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
from waterfall.core.estimate.excel.writer import write_workbook
from waterfall.core.estimate.interface import sheet_name

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

D = Decimal
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"m": MAIN}
RELATIONSHIP = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
EXPORTED_AT = datetime(2026, 10, 22, 14, 5, tzinfo=UTC)
LITERAL = "=1+1 reste une désignation"


def _line(lineage: str, **fields: Any) -> Line:
    """Write a line valid unless a test changes a field."""
    values: dict[str, Any] = {
        "role": None,
        "category": None,
        "label": "",
        "quantity": D(1),
        "hours": None,
        "disbursement": None,
        "payment_delay": None,
        "subproject": None,
        "amount": None,
    }
    return Line(lineage, **{**values, **fields})


def _task(number: str, label: str, *lines: Line) -> Task:
    return Task(
        lineage=f"t-{number}",
        number=number,
        label=label,
        start=date(2026, 11, 2),
        end=date(2027, 3, 26),
        description=f"Description de {label}",
        lines=lines,
    )


def _estimate(**changes: Any) -> Estimate:
    """Give the estimate of the prototype of the specification, as the tests read it."""
    package = Tab(
        "1.1",
        "Centrale et logiciel",
        "Centrale et logiciel",
        (
            _task("1.1", "Centrale et logiciel"),
            _task(
                "1.1.1",
                "Management",
                _line(
                    "l-1",
                    role="RA-A1",
                    quantity=D(5),
                    hours=D("7.4"),
                    subproject="SP-PRE",
                    amount=D("3700.00"),
                ),
            ),
            _task(
                "1.1.3",
                "Carte d’interface",
                _line(
                    "l-2",
                    category="fo-AINT",
                    quantity=D(5),
                    disbursement=D(20),
                    payment_delay=30,
                    subproject="SP-MAT",
                    label="Détecteurs",
                    amount=D("100.00"),
                ),
                _line(
                    "l-3",
                    category="PRV",
                    label="Provision — Retard",
                    disbursement=D(1500),
                    amount=D("1500.00"),
                ),
            ),
        ),
    )
    own = Tab(
        "1",
        "Contrôle d’accès",
        "Contrôle d’accès, hors postes",
        (
            _task(
                "1.3",
                "Revue de conception",
                _line("l-4", role="ARCH-LOG", quantity=D(3), hours=D("7.4"), amount=D("1776.00")),
            ),
        ),
    )
    outside = Tab(
        "",
        "Hors lot",
        "Hors lot",
        (
            _task(
                "3",
                "Gestion de projet",
                _line("l-5", role="RA-A1", quantity=D(20), hours=D("7.4"), label=LITERAL),
            ),
        ),
    )
    values: dict[str, Any] = {
        "company": "Exemple Industrie",
        "client": "Client Exemple",
        "project": "AFF-2026-014 Contrôle d’accès du site de Lyon",
        "revision": "Chiffrage v2 (en cours)",
        "structure": "Structure principale",
        "reference_year": 2026,
        "currency": "EUR",
        "exported_at": EXPORTED_AT,
        "natures": (
            Nature("Main-d’œuvre", "labour"),
            Nature("Fournitures", "disbursement"),
            Nature("Provisions pour risques", "provision"),
        ),
        "categories": (
            Category("I810", "Gestion d’affaires", "Main-d’œuvre", D(100)),
            Category("I329", "Ingénierie logicielle", "Main-d’œuvre", D(80)),
            Category("fo-AINT", "Anti-intrusion", "Fournitures"),
            Category("PRV", "Provision pour risques", "Provisions pour risques"),
        ),
        "roles": (
            Role("RA-A1", "Responsable d’affaire A1", "Affaires > Activité 1", "I810"),
            Role("ARCH-LOG", "Architecte logiciel", "Ingénierie > Logiciel", "I329"),
        ),
        "subprojects": (Subproject("SP-MAT", "Matériel"), Subproject("SP-PRE", "Prestations")),
        "lots": (Lot("1", "Contrôle d’accès", (package, own)),),
        "outside_lot": outside,
    }
    values.update(changes)
    return Estimate(**values)


def _open(content: bytes) -> Workbook:
    return load_workbook(BytesIO(content))


def _problems(content: bytes) -> list[str]:
    """Run the checks of ``check_xlsx.py``: declared totals, formulas reading their own cell."""
    archive = zipfile.ZipFile(BytesIO(content))
    book = etree.fromstring(archive.read("xl/workbook.xml"))
    rels = etree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target = {rel.get("Id"): str(rel.get("Target")) for rel in rels}
    problems: list[str] = []
    for sheet in book.findall("m:sheets/m:sheet", NS):
        name, path = sheet.get("name"), "xl/" + target[sheet.get(RELATIONSHIP)]
        xml = archive.read(path)
        rels_path = path.replace("worksheets/", "worksheets/_rels/") + ".rels"
        if rels_path in archive.namelist():
            for rel in etree.fromstring(archive.read(rels_path)):
                if str(rel.get("Target")).startswith("../tables/"):
                    table = archive.read("xl/tables/" + str(rel.get("Target")).split("/")[-1])
                    problems += _totals(str(name), table, xml)
        problems += _circular(str(name), xml)
    return problems


def _totals(name: str, table_xml: bytes, sheet_xml: bytes) -> list[str]:
    table = etree.fromstring(table_xml)
    if table.get("totalsRowCount") != "1":
        return []
    cells = {str(cell.get("r")): cell for cell in etree.fromstring(sheet_xml).iter(f"{{{MAIN}}}c")}
    first, _, _, last = range_boundaries(str(table.get("ref")))
    assert first is not None
    assert last is not None
    problems: list[str] = []
    for position, column in enumerate(table.findall("m:tableColumns/m:tableColumn", NS)):
        cell = cells.get(f"{get_column_letter(first + position)}{last}")
        has_formula = cell is not None and cell.find("m:f", NS) is not None
        declared = column.get("totalsRowFunction")
        if has_formula and not declared:
            problems.append(f"{name}: formula of total not declared in column {position}")
        if declared and not has_formula:
            problems.append(f"{name}: total declared without a formula in column {position}")
    return problems


def _circular(name: str, sheet_xml: bytes) -> list[str]:
    problems: list[str] = []
    for cell in etree.fromstring(sheet_xml).iter(f"{{{MAIN}}}c"):
        formula = cell.find("m:f", NS)
        if formula is None or not formula.text:
            continue
        ref = str(cell.get("r"))
        letters, row = coordinate_from_string(ref)
        column = column_index_from_string(letters)
        text = re.sub(
            r"'[^']*'![$A-Z0-9:]+|[A-Za-z_]+!\$?[A-Z]+\$?\d+(:\$?[A-Z]+\$?\d+)?", "", formula.text
        )
        for found in re.finditer(r"\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?", text):
            left, top = column_index_from_string(found.group(1)), int(found.group(2))
            right, bottom = (
                (column_index_from_string(found.group(3)), int(found.group(4)))
                if found.group(3)
                else (left, top)
            )
            if left <= column <= right and top <= row <= bottom:
                problems.append(f"{name}!{ref}: reads its own cell: {formula.text}")
    return problems


def test_the_checker_finds_a_total_that_is_not_declared() -> None:
    """The check of the tests is itself tried, on a table whose total is not declared."""
    sheet = f'<worksheet xmlns="{MAIN}"><c r="A3"><f>SUM(A1:A2)</f></c></worksheet>'.encode()
    table = (
        f'<table xmlns="{MAIN}" ref="A1:A3" totalsRowCount="1"><tableColumns>'
        "<tableColumn/></tableColumns></table>"
    ).encode()
    assert _totals("t", table, sheet) == ["t: formula of total not declared in column 0"]
    own = f'<worksheet xmlns="{MAIN}"><c r="B2"><f>SUM(B1:B3)</f></c></worksheet>'.encode()
    assert _circular("t", own) == ["t!B2: reads its own cell: SUM(B1:B3)"]


def test_the_workbook_is_free_of_undeclared_totals_and_circular_formulas() -> None:
    assert _problems(write_workbook(_estimate())) == []


def test_the_tabs_are_the_fixed_ones_around_a_tab_per_package_lot_and_outside_lot() -> None:
    book = _open(write_workbook(_estimate()))
    assert book.sheetnames == [
        "Présentation",
        "Devis",
        "1.1 Centrale et logiciel",
        "1 Contrôle d’accès",
        "Hors lot",
        "Tâches",
        "Paramètres",
    ]


def test_the_presentation_opens_with_the_format_and_the_version() -> None:
    sheet = _open(write_workbook(_estimate()))["Présentation"]
    assert [sheet["A1"].value, sheet["B1"].value, sheet["A2"].value, sheet["B2"].value] == [
        "Format",
        "Devis",
        "Version",
        1,
    ]


def test_the_presentation_shows_the_project_and_the_breakdown_by_nature() -> None:
    content = write_workbook(_estimate())
    sheet = _open(content)["Présentation"]
    cells = {str(cell.value) for row in sheet.iter_rows() for cell in row if cell.value is not None}
    assert {
        "Exemple Industrie",
        "Client Exemple",
        "Chiffrage v2 (en cours)",
        "Structure principale",
        "2026",
        "EUR",
        "2026-10-22 14:05",
        "Main-d’œuvre",
        "Fournitures",
        "Provisions pour risques",
    } <= cells
    assert sheet["A4"].value == "AFF-2026-014 Contrôle d’accès du site de Lyon"
    assert "xl/media/image1.png" in zipfile.ZipFile(BytesIO(content)).namelist()


# The headers of annex B, as the prototype writes them: typed here, not read from the writer.
EXPECTED_LINE_HEADERS = [
    "Tâche",
    "Description de la tâche",
    "Rôle ou catégorie",
    "Désignation",
    "Quantité",
    "Heures",
    "Débours unitaire",
    "Délai de paiement (j)",
    "Sous-projet",
    "Nature",
    "Code comptable",
    "Service",
    "Taux horaire",
    "Heures totales",
    "Main-d’œuvre",
    "Débours",
    "Montant",
    "Montant Waterfall",
    "ID ligne",
    "Type",
]
EXPECTED_PARAMETER_HEADERS = [
    "Entrée",
    "Genre",
    "Code",
    "Libellé",
    "Service",
    "Nature",
    "Type de nature",
    "Code comptable",
    "Taux horaire",
]
EXPECTED_TASK_HEADERS = [
    "Entrée",
    "ID tâche",
    "N°",
    "Libellé",
    "Onglet",
    "Début",
    "Fin",
    "Description",
]


@pytest.mark.requirement("WF-INTF-0180-A")
def test_the_headers_of_every_tab_are_the_fixed_french_ones() -> None:
    book = _open(write_workbook(_estimate()))
    assert len(EXPECTED_LINE_HEADERS) == 20
    for name in ("1.1 Centrale et logiciel", "1 Contrôle d’accès", "Hors lot"):
        assert [cell.value for cell in book[name][1]] == EXPECTED_LINE_HEADERS
    # The whole row, read to the last column of the sheet: a column too many would be seen (#2602).
    # Beside the reference, after an empty column, the subprojects (``SUBPROJECT_HEADERS``).
    parameters = [cell.value for cell in book["Paramètres"][3]]
    assert parameters == [*EXPECTED_PARAMETER_HEADERS, None, "Code", "Libellé"]
    tasks = [cell.value for cell in book["Tâches"][3]]
    assert tasks == EXPECTED_TASK_HEADERS


def test_the_same_estimate_gives_the_same_workbook_whoever_exports_it() -> None:
    """The writer takes no language and reads no clock: two exports are the same bytes."""
    assert write_workbook(_estimate()) == write_workbook(_estimate())


def test_a_tab_of_lines_is_a_table_with_a_declared_total_row_and_a_hidden_lineage() -> None:
    sheet = _open(write_workbook(_estimate()))["1.1 Centrale et logiciel"]
    (name,) = sheet.tables
    table = sheet.tables[name]
    assert name == "Lignes_1_1"
    assert table.totalsRowCount == 1
    assert table.ref == "A1:T35"  # the header, 3 lines, 30 prepared, the total row
    assert sheet.column_dimensions["S"].hidden
    assert sheet.column_dimensions["T"].hidden
    assert sheet["S2"].value == "l-1"
    assert sheet.freeze_panes == "B2"


def test_the_calculated_columns_are_formulas_that_name_their_table() -> None:
    sheet = _open(write_workbook(_estimate()))["1.1 Centrale et logiciel"]
    headers = [cell.value for cell in sheet[1]]
    montant = str(sheet.cell(2, headers.index("Montant") + 1).value)
    assert montant.startswith("=IF(")
    assert "Lignes_1_1[[#This Row],[Main-d’œuvre]]" in montant
    taux = str(sheet.cell(2, headers.index("Taux horaire") + 1).value)
    assert "Referentiel[[Taux horaire]]" in taux
    assert "Referentiel[[Entrée]]" in taux
    total = {c.name: c.totalsRowFunction for c in sheet.tables["Lignes_1_1"].tableColumns}
    totalled = {"Heures totales", "Main-d’œuvre", "Débours", "Montant", "Montant Waterfall"}
    for header, function in total.items():
        assert function == ("custom" if header in totalled else None), header


def test_the_lists_of_choice_cover_the_tasks_the_roles_and_the_subprojects() -> None:
    sheet = _open(write_workbook(_estimate()))["1.1 Centrale et logiciel"]
    sources = {
        str(validation.sqref): str(validation.formula1)
        for validation in sheet.data_validations.dataValidation
    }
    assert sources["A2:A1001"].startswith("'Tâches'!$A$")
    assert sources["C2:C1001"] == "'Paramètres'!$A$4:$A$6"  # the provision is not offered
    assert sources["I2:I1001"].startswith("'Paramètres'!$K$4:$K$5")


def test_the_tasks_and_the_parameters_are_protected_and_the_others_are_not() -> None:
    book = _open(write_workbook(_estimate()))
    assert book["Tâches"].protection.sheet
    assert book["Paramètres"].protection.sheet
    for name in book.sheetnames:
        if name not in ("Tâches", "Paramètres"):
            assert not book[name].protection.sheet


def test_the_tasks_tab_gives_the_lineage_the_tab_and_the_description() -> None:
    sheet = _open(write_workbook(_estimate()))["Tâches"]
    rows = [[cell.value for cell in row] for row in sheet.iter_rows(min_row=3)]
    assert rows[0] == [
        "Entrée",
        "ID tâche",
        "N°",
        "Libellé",
        "Onglet",
        "Début",
        "Fin",
        "Description",
    ]
    assert rows[2] == [
        "1.1.1 Management",
        "t-1.1.1",
        "1.1.1",
        "Management",
        "1.1 Centrale et logiciel",
        "2026-11-02",
        "2027-03-26",
        "Description de Management",
    ]


def test_the_parameters_hold_the_reference_the_formulas_read() -> None:
    sheet = _open(write_workbook(_estimate()))["Paramètres"]
    rows = [[cell.value for cell in row][:9] for row in sheet.iter_rows(min_row=4, max_row=7)]
    assert rows[0] == [
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
    assert [row[1] for row in rows] == ["Rôle", "Rôle", "Catégorie", "Catégorie"]
    assert rows[3][6] == "Provision"


def test_a_text_typed_stays_a_text_never_a_formula() -> None:
    sheet = _open(write_workbook(_estimate()))["Hors lot"]
    cell = sheet["D2"]
    assert cell.value == LITERAL
    assert cell.data_type == "s"


def test_the_summary_has_a_row_per_lot_and_per_tab_summed_from_their_tables() -> None:
    sheet = _open(write_workbook(_estimate()))["Devis"]
    assert [sheet.cell(row, 2).value for row in range(6, 12)] == [
        "Contrôle d’accès",
        "Centrale et logiciel",
        "Contrôle d’accès, hors postes",
        "Hors lot",
        "Total",
        None,
    ]
    lot = [sheet.cell(6, column).value for column in range(5, 7)]
    assert lot[0] == "=SUM(E7:E8)"
    package = str(sheet["E7"].value)
    assert package.startswith('=IF($C$7="Oui",SUMIFS(Lignes_1_1[[Montant]],Lignes_1_1[[Nature]],')
    hours = [str(cell.value) for cell in sheet[5] if cell.value is not None]
    assert "Heures I810" in hours
    assert "Heures I329" in hours
    assert sheet["C7"].value == "Oui"
    assert sheet.data_validations.dataValidation[0].formula1 == '"Oui,Non"'
    assert str(sheet["E10"].value).startswith("=SUMIFS(E6:E9,$D$6:$D$9,")


def test_the_footer_carries_the_company_and_the_page_on_every_tab() -> None:
    book = _open(write_workbook(_estimate()))
    for sheet in book.worksheets:
        footer = sheet.oddFooter
        assert footer is not None
        left, right = footer.left, footer.right
        assert left is not None
        assert right is not None
        assert "Exemple Industrie" in str(left.text)
        assert right.text == "Page &P / &N"


def test_a_long_company_does_not_break_the_limit_of_the_footer() -> None:
    long_name = "A & B " * 60
    book = _open(write_workbook(_estimate(company=long_name)))
    footer = book["Devis"].oddFooter
    assert footer is not None
    left = footer.left
    assert left is not None
    assert 0 < len(str(left.text)) < 255
    assert "Généré par Waterfall" in str(left.text)


def test_a_structure_without_a_line_gives_the_blank_model() -> None:
    bare = _estimate(
        lots=(),
        outside_lot=None,
        roles=(),
        categories=(),
        natures=(),
        subprojects=(),
    )
    content = write_workbook(bare)
    book = _open(content)
    assert book.sheetnames == ["Présentation", "Devis", "Hors lot", "Tâches", "Paramètres"]
    assert [cell.value for cell in book["Hors lot"][1]] == EXPECTED_LINE_HEADERS
    assert _problems(content) == []


def test_a_structure_of_tasks_without_a_line_keeps_its_tabs_and_tasks() -> None:
    empty = Tab("1.1", "Centrale", "Centrale", (_task("1.1", "Centrale"),))
    book = _open(write_workbook(_estimate(lots=(Lot("1", "Lot", (empty,)),), outside_lot=None)))
    assert book.sheetnames[2] == "1.1 Centrale"
    assert book["1.1 Centrale"]["A2"].value is None
    sheet: Worksheet = book["Tâches"]
    assert sheet["A4"].value == "1.1 Centrale"


@pytest.mark.requirement("WF-INTF-0110-A")
def test_a_code_shared_by_a_role_and_a_category_writes_each_line_with_its_own_label() -> None:
    # A code of a role is unique among the roles, an accounting code among the categories, not
    # between them (#2690): the role ARCH-LOG and the category of supplies accounted ARCH-LOG keep
    # their labels apart, so that the import reads each line back as of its own kind.
    shared = Category("ARCH-LOG", "Licences logicielles", "Fournitures")
    lines = (
        _line("l-1", role="ARCH-LOG", hours=D(7)),
        _line("l-2", category="ARCH-LOG", disbursement=D(40)),
    )
    outside = Tab("", "Hors lot", "Hors lot", (_task("1", "Études", *lines),))
    estimate = _estimate(
        lots=(),
        outside_lot=outside,
        categories=(*_estimate().categories, shared),
    )
    sheet = _open(write_workbook(estimate))["Hors lot"]
    assert [sheet["C2"].value, sheet["C3"].value] == [
        "Architecte logiciel (ARCH-LOG)",
        "Licences logicielles (ARCH-LOG)",
    ]


def test_a_lot_without_a_tab_sums_to_zero() -> None:
    sheet = _open(write_workbook(_estimate(lots=(Lot("1", "Lot vide", ()),))))["Devis"]
    assert sheet["E6"].value == "=0"


def test_tabs_whose_names_collide_without_regard_to_case_are_suffixed() -> None:
    first = Tab("1.1", "Essais", "Essais", ())
    second = Tab("1.1", "ESSAIS", "Essais bis", ())
    book = _open(
        write_workbook(_estimate(lots=(Lot("1", "Lot", (first, second)),), outside_lot=None))
    )
    assert book.sheetnames[2:4] == ["1.1 Essais", "1.1 ESSAIS (2)"]


def test_a_label_with_refused_characters_and_a_long_one_name_valid_tabs() -> None:
    odd = Tab("2.1", "Études: [A/B]?", "Études", ())
    long = Tab("2.2", "x" * 80, "Long", ())
    book = _open(write_workbook(_estimate(lots=(Lot("2", "Lot", (odd, long)),), outside_lot=None)))
    assert book.sheetnames[2] == "2.1 Études_ _A_B__"
    assert len(book.sheetnames[3]) == 31


def test_a_currency_is_the_installations_in_the_amount_format() -> None:
    sheet = _open(write_workbook(_estimate(currency="USD")))["Devis"]
    assert sheet["E7"].number_format == '#,##0.00 "$"'


def test_sheet_name_replaces_the_characters_excel_refuses() -> None:
    assert sheet_name(r"a:b\c/d?e*f[g]h") == "a_b_c_d_e_f_g_h"
    assert sheet_name("tab\x01one") == "tab_one"


def test_sheet_name_does_not_begin_or_end_with_an_apostrophe() -> None:
    assert sheet_name("'quoted'") == "_quoted_"


def test_sheet_name_of_nothing_is_a_name() -> None:
    assert sheet_name("") == "Onglet"
    assert sheet_name("   ") == "Onglet"


def test_sheet_name_measures_in_utf16_units_not_in_python_characters() -> None:
    name = sheet_name("😀" * 20)  # 20 characters, 40 units
    assert name == "😀" * 15  # 30 units: a sixteenth would make 32
    assert len(name.encode("utf-16-le")) // 2 == 30
    assert sheet_name("é" * 40) == "é" * 31


def test_sheet_name_never_cuts_a_surrogate_pair() -> None:
    name = sheet_name("a" + "😀" * 20)
    assert name == "a" + "😀" * 15
    assert len(name.encode("utf-16-le")) // 2 <= 31


def test_sheet_name_is_unique_without_regard_to_case_by_a_suffix() -> None:
    assert sheet_name("Essais", ["essais"]) == "Essais (2)"
    assert sheet_name("Essais", ["ESSAIS", "essais (2)"]) == "Essais (3)"
    assert sheet_name("Essais", ["autre"]) == "Essais"


def test_sheet_name_leaves_room_for_the_suffix_in_31_units() -> None:
    base = "x" * 31
    second = sheet_name(base, [base])
    assert second == "x" * 27 + " (2)"
    assert len(second) == 31
    emoji = sheet_name("😀" * 20, ["😀" * 15])
    assert emoji == "😀" * 13 + " (2)"
    assert len(emoji.encode("utf-16-le")) // 2 <= 31


def test_sheet_name_suffixed_and_truncated_still_avoids_a_name_taken_in_another_case() -> None:
    assert sheet_name("x" * 40, ["X" * 31, "x" * 27 + " (2)"]) == "x" * 27 + " (3)"
    taken = ["😀" * 15, ("😀" * 13 + " (2)").upper()]
    name = sheet_name("😀" * 20, taken)
    assert name == "😀" * 13 + " (3)"
    assert len(name.encode("utf-16-le")) // 2 <= 31
    # 27 units leave 13 pairs after the « a »; a fourteenth would cut a pair in two.
    pair_cut = sheet_name("a" + "😀" * 20, ["A" + "😀" * 15, "A" + "😀" * 13 + " (2)"])
    assert pair_cut == "a" + "😀" * 13 + " (3)"


CALCULATED = (
    "Description de la tâche",
    "Nature",
    "Code comptable",
    "Service",
    "Taux horaire",
    "Type",
    "Heures totales",
    "Main-d’œuvre",
    "Débours",
    "Montant",
)


def _cached_lines(content: bytes, name: str) -> list[dict[str, Any]]:
    """Read a tab of lines as a viewer that does not recalculate shows it, the totals last."""
    sheet = load_workbook(BytesIO(content), data_only=True)[name]
    headers = [str(cell.value) for cell in sheet[1]]
    return [
        dict(zip(headers, [cell.value for cell in row], strict=True))
        for row in sheet.iter_rows(min_row=2)
    ]


def _cached_summary(content: bytes, name: str, row: int) -> list[Any]:
    """Read the values of a row of « Devis » or « Présentation », from the first column."""
    return [cell.value for cell in load_workbook(BytesIO(content), data_only=True)[name][row]]


@pytest.mark.story("US-3640")
def test_each_calculated_cell_of_a_line_carries_its_value_without_a_recalculation() -> None:
    content = write_workbook(_estimate())
    labour, disbursement, provision = _cached_lines(content, "1.1 Centrale et logiciel")[:3]
    assert {header: labour[header] for header in CALCULATED} == {
        "Description de la tâche": "Description de Management",
        "Nature": "Main-d’œuvre",
        "Code comptable": "I810",
        "Service": "Affaires > Activité 1",
        "Taux horaire": 100,
        "Type": "Main-d’œuvre",
        "Heures totales": pytest.approx(37),
        "Main-d’œuvre": pytest.approx(3700),
        "Débours": 0,
        "Montant": pytest.approx(3700),
    }
    assert {header: disbursement[header] for header in CALCULATED} == {
        "Description de la tâche": "Description de Carte d’interface",
        "Nature": "Fournitures",
        "Code comptable": "fo-AINT",
        "Service": None,
        "Taux horaire": 0,
        "Type": "Hors main-d’œuvre",
        "Heures totales": 0,
        "Main-d’œuvre": 0,
        "Débours": 100,
        "Montant": 100,
    }
    assert (provision["Type"], provision["Débours"], provision["Montant"]) == (
        "Provision",
        1500,
        1500,
    )


@pytest.mark.story("US-3640")
def test_each_amount_of_a_line_equals_the_amount_waterfall_without_a_recalculation() -> None:
    content = write_workbook(_estimate())
    checked = 0
    for name in ("1.1 Centrale et logiciel", "1 Contrôle d’accès", "Hors lot"):
        for line in _cached_lines(content, name)[:-1]:
            if line["Montant Waterfall"] is not None:
                assert line["Montant"] == pytest.approx(line["Montant Waterfall"])
                checked += 1
    assert checked == 4


@pytest.mark.story("US-3640")
def test_a_prepared_row_caches_the_empty_text_and_not_zero() -> None:
    prepared = _cached_lines(write_workbook(_estimate()), "1 Contrôle d’accès")[1:-1]
    assert len(prepared) == 30
    assert all(line[header] is None for line in prepared for header in CALCULATED)


@pytest.mark.story("US-3640")
def test_the_row_of_totals_of_a_tab_carries_its_totals_without_a_recalculation() -> None:
    content = write_workbook(_estimate())
    package = _cached_lines(content, "1.1 Centrale et logiciel")[-1]
    assert [package[header] for header in TOTALS] == [
        pytest.approx(37),
        pytest.approx(3700),
        1600,
        pytest.approx(5300),
        5300,
    ]
    outside = _cached_lines(content, "Hors lot")[-1]
    assert (outside["Heures totales"], outside["Montant Waterfall"]) == (pytest.approx(148), 0)


TOTALS = ("Heures totales", "Main-d’œuvre", "Débours", "Montant", "Montant Waterfall")


@pytest.mark.story("US-3640")
def test_the_summary_and_the_presentation_carry_their_values_without_a_recalculation() -> None:
    content = write_workbook(_estimate())
    # Nature columns (E, F, G), the hours of the codes of the roles (I329, I810), the two totals.
    package = _cached_summary(content, "Devis", 7)[4:]
    assert package == [pytest.approx(3700), 100, 1500, 0, pytest.approx(37), 5300, 5300]
    lot = _cached_summary(content, "Devis", 6)[4:]
    assert lot == [
        pytest.approx(3700 + 1776),
        100,
        1500,
        pytest.approx(22.2),
        pytest.approx(37),
        pytest.approx(5300 + 1776),
        5300 + 1776,
    ]
    total = _cached_summary(content, "Devis", 10)[4:]
    assert total == [
        pytest.approx(3700 + 1776 + 14800),
        100,
        1500,
        pytest.approx(22.2),
        pytest.approx(37 + 148),
        pytest.approx(21876),
        pytest.approx(7076),
    ]
    presentation = {
        row[0]: row[1:3]
        for row in load_workbook(BytesIO(content), data_only=True)["Présentation"].iter_rows(
            values_only=True
        )
        if row[0] in {"Main-d’œuvre", "Fournitures", "Provisions pour risques", "Total"}
        or str(row[0]).startswith("Montant Waterfall")
    }
    assert presentation["Main-d’œuvre"] == (pytest.approx(20276), pytest.approx(20276 / 21876))
    assert presentation["Provisions pour risques"] == (1500, pytest.approx(1500 / 21876))
    assert presentation["Total"][0] == pytest.approx(21876)
    assert presentation["Montant Waterfall, inflation comprise"][0] == pytest.approx(7076)


@pytest.mark.story("US-3640")
def test_the_formulas_stay_beside_the_values_they_cache() -> None:
    book = _open(write_workbook(_estimate()))
    sheet = book["1.1 Centrale et logiciel"]
    headers = [cell.value for cell in sheet[1]]
    first = {header: sheet.cell(2, column + 1).value for column, header in enumerate(headers)}
    assert all(str(first[header]).startswith("=") for header in CALCULATED)
    assert sheet.cell(sheet.max_row, headers.index("Montant") + 1).value == (
        "=SUBTOTAL(109,Lignes_1_1[[Montant]])"
    )
    assert str(book["Devis"]["E7"].value).startswith('=IF($C$7="Oui",SUMIFS(')
    assert str(book["Présentation"]["B16"].value).startswith("=Devis!")


@pytest.mark.story("US-3640")
def test_the_summary_has_a_column_of_hours_per_code_of_the_roles_and_no_other() -> None:
    labour = tuple(
        Category(f"641{number:03d}", f"Catégorie {number}", "Main-d’œuvre", D(50))
        for number in range(1, 151)
    )
    others = (
        Category("fo-AINT", "Anti-intrusion", "Fournitures"),
        Category("PRV", "Provision pour risques", "Provisions pour risques"),
    )
    roles = tuple(
        Role(code, f"Rôle {code}", "Service", accounting)
        for code, accounting in (
            ("RA-A1", "641002"),
            ("ARCH-LOG", "641001"),
            ("DEV", "641001"),
            ("TEST", "641002"),
            ("DOC", "641001"),
        )
    )
    content = write_workbook(_estimate(categories=(*labour, *others), roles=roles))
    headers = [str(cell.value) for cell in _open(content)["Devis"][5] if cell.value is not None]
    assert [header for header in headers if header.startswith("Heures")] == [
        "Heures 641001",
        "Heures 641002",
    ]
    assert len(headers) == 4 + 3 + 2 + 2
    assert _cached_summary(content, "Devis", 10)[7:9] == [pytest.approx(22.2), pytest.approx(185)]


@pytest.mark.story("US-3640")
def test_a_code_no_role_carries_has_no_column_of_hours() -> None:
    purchase = _task("3", "Achats", _line("l-1", category="fo-AINT", disbursement=D(10)))
    outside = Tab("", "Hors lot", "Hors lot", (purchase,))
    content = write_workbook(_estimate(roles=(), lots=(), outside_lot=outside))
    headers = [str(cell.value) for cell in _open(content)["Devis"][5] if cell.value is not None]
    assert not any(header.startswith("Heures") for header in headers)


def test_sheet_name_avoids_the_name_excel_reserves() -> None:
    assert sheet_name("history") == "history (2)"
    assert sheet_name("History") == "History (2)"
