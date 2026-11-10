# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbook « Devis » of annex B, written from an estimate in memory (US-1550/L1).

Pure: an ``Estimate`` in, the bytes of an ``.xlsx`` out, with XlsxWriter, without a database, a
clock or a language — the headers are the French ones of the annex, fixed (WF-INTF-0180). The
design follows the prototype of the specification (``docs/spec/exemples/prototype_devis.py``):
« Présentation », « Devis », a tab of lines per package, per lot outside its packages and for the
tasks outside any lot, « Tâches » and « Paramètres ». A text typed is written as a text — never
as a formula, never as a link — and only the formulas written here are formulas.
"""

import re
from dataclasses import dataclass, replace
from importlib.resources import files
from io import BytesIO
from typing import TYPE_CHECKING, Any, Literal

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

from waterfall.core.estimate.excel.model import Tab
from waterfall.core.estimate.excel.names import sheet_name

if TYPE_CHECKING:
    from xlsxwriter.format import Format
    from xlsxwriter.worksheet import Worksheet

    from waterfall.core.estimate.excel.model import Estimate, Line, Task

FORMAT_NAME = "Devis"
FORMAT_VERSION = 1
PRESENTATION = "Présentation"
SUMMARY = "Devis"
TASKS = "Tâches"
PARAMETERS = "Paramètres"
NO_LOT = "Hors lot"
FIXED_TABS = (PRESENTATION, SUMMARY, TASKS, PARAMETERS)
# The empty rows prepared under the lines exported, with their lists and their formulas.
PREPARED = 30
# The lists of choice hold for far more rows than the table, which grows as one types.
VALIDATED_ROWS = 1000
# Excel refuses a footer of more than 255 characters.
FOOTER_LIMIT = 255
FOOTER_MARGIN = 30
LABOUR = "Main-d’œuvre"
DISBURSEMENT = "Hors main-d’œuvre"
PROVISION = "Provision"
KIND_NAMES = {"labour": LABOUR, "disbursement": DISBURSEMENT, "provision": PROVISION}
KIND_ORDER = {LABOUR: 0, DISBURSEMENT: 1, PROVISION: 2}
SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}
PACKAGE = "waterfall.core.estimate.excel"
LOGO = ("assets", "waterfall_logo.png")
INSTANT_FORMAT = "%Y-%m-%d %H:%M"

# (header, width) of a tab of lines, in the order of the annex. The import reads by header.
LINE_COLUMNS = (
    ("Tâche", 34),
    ("Description de la tâche", 34),
    ("Rôle ou catégorie", 34),
    ("Désignation", 30),
    ("Quantité", 10),
    ("Heures", 9),
    ("Débours unitaire", 12),
    ("Délai de paiement (j)", 11),
    ("Sous-projet", 12),
    ("Nature", 18),
    ("Code comptable", 11),
    ("Service", 22),
    ("Taux horaire", 9),
    ("Heures totales", 10),
    ("Main-d’œuvre", 13),
    ("Débours", 13),
    ("Montant", 13),
    ("Montant Waterfall", 14),
    ("ID ligne", 10),
    ("Type", 14),
)
LINE_HEADERS = tuple(header for header, _ in LINE_COLUMNS)
AMOUNT_HEADERS = ("Main-d’œuvre", "Débours", "Montant", "Montant Waterfall")
TOTAL_HEADERS = ("Heures totales", *AMOUNT_HEADERS)
TEXT_HEADERS = ("Tâche", "Rôle ou catégorie", "Désignation", "Sous-projet")
HIDDEN_HEADERS = ("ID ligne", "Type")
REFERENCE_HEADERS = (
    "Entrée",
    "Genre",
    "Code",
    "Libellé",
    "Service",
    "Nature",
    "Type de nature",
    "Code comptable",
    "Taux horaire",
)
TASK_HEADERS = ("Entrée", "ID tâche", "N°", "Libellé", "Onglet", "Début", "Fin", "Description")
SUBPROJECT_HEADERS = ("Code", "Libellé")
REFERENCE_WIDTHS = (34, 10, 10, 26, 24, 22, 18, 14, 11, 2, 10, 16)
TASK_WIDTHS = (40, 10, 8, 34, 26, 11, 11, 50)
TABLE_STYLE = "Table Style Light 1"
LINES_STYLE = "Table Style Light 9"
# The hours are written to one decimal, an amount to the cent.
HOURS_FORMAT = "#,##0.0"
GREY = {"bg_color": "#EEEEEE", "font_color": "#555555"}
NOTE = {"italic": True, "font_color": "#666666"}


def _quote(text: str) -> str:
    """Write a text inside a formula."""
    return '"' + text.replace('"', '""') + '"'


def _this(table: str, column: str) -> str:
    return f"{table}[[#This Row],[{column}]]"


def _entry(label: str, code: str) -> str:
    """Write the text of the list of choice for a role or a category."""
    return f"{label} ({code})"


def _amount_format(currency: str) -> str:
    symbol = SYMBOLS.get(currency, currency).replace('"', "")
    return f'#,##0.00 "{symbol}"'


def _footer_text(estimate: Estimate) -> tuple[str, str]:
    """Give the mention of the presentation and the same for the footer, within its limit."""
    year = estimate.exported_at.year
    instant = estimate.exported_at.strftime(INSTANT_FORMAT)

    def mention(company: str) -> str:
        return (
            f"© {year} {company} — Généré par Waterfall le {instant} — "
            "logiciel libre sous licence AGPL-3.0 — www.waterfall-project.pro"
        )

    company = estimate.company
    while len(mention(company).replace("&", "&&")) > FOOTER_LIMIT - FOOTER_MARGIN and company:
        company = company[:-2] + "…" if len(company) > 1 else ""
    return mention(estimate.company), mention(company).replace("&", "&&")


def _text_formats(book: xlsxwriter.Workbook, currency: str) -> dict[str, Format]:
    money = _amount_format(currency)
    spec: dict[str, dict[str, Any]] = {
        "bold": {"bold": True},
        "title": {"bold": True, "font_size": 14},
        "money": {"num_format": money},
        "money_bold": {"num_format": money, "bold": True, "top": 1},
        "hours": {"num_format": HOURS_FORMAT},
        "hours_bold": {"num_format": HOURS_FORMAT, "bold": True, "top": 1},
        "percent": {"num_format": "0.0 %"},
        "grey": GREY,
        "grey_money": {**GREY, "num_format": money},
        "grey_hours": {**GREY, "num_format": HOURS_FORMAT},
        "note": {**NOTE, "text_wrap": True, "valign": "top"},
        "italic": NOTE,
        "lot": {"bold": True, "bg_color": "#DDEBF7"},
        "lot_money": {"bold": True, "bg_color": "#DDEBF7", "num_format": money},
        "lot_hours": {"bold": True, "bg_color": "#DDEBF7", "num_format": HOURS_FORMAT},
        "text": {"num_format": "@"},
        "left": {"align": "left"},
        "head": {"bold": True, "text_wrap": True, "bottom": 1, "valign": "top"},
        "small": {"font_size": 8, "font_color": "#666666"},
    }
    return {name: book.add_format(properties) for name, properties in spec.items()}


@dataclass(frozen=True)
class _Lists:
    """The lists of choice of the tabs of lines that « Paramètres » holds."""

    roles: str
    subprojects: str
    tasks: tuple[str, ...]


@dataclass(frozen=True)
class _Row:
    """A row of the breakdown: a lot (with its count of tabs) or a tab (with its table)."""

    level: Literal["lot", "tab"]
    number: str
    label: str
    tabs: int = 0
    table: str = ""


@dataclass(frozen=True)
class _Labels:
    """The label of every role and of every category, by code, each kind apart (#2690).

    A code of a role is unique among the roles, an accounting code among the categories, not
    between them: one index would give a role the label of a category of the same code.
    """

    roles: dict[str, str]
    categories: dict[str, str]


@dataclass(frozen=True)
class _Context:
    """What the sheets share: the estimate, its tabs of lines with their names, the formats."""

    estimate: Estimate
    tabs: tuple[Tab, ...]
    sheets: tuple[str, ...]
    tables: tuple[str, ...]
    fmt: dict[str, Format]
    labels: _Labels


def _labels(estimate: Estimate) -> _Labels:
    """Give the labels of the roles and of the categories, once for the whole workbook."""
    return _Labels(
        {role.code: role.label for role in estimate.roles},
        {category.code: category.label for category in estimate.categories},
    )


def _name_tabs(estimate: Estimate) -> tuple[tuple[Tab, ...], tuple[str, ...]]:
    """Give the tabs of lines in the order of the workbook, and their names (#2190)."""
    tabs = [tab for lot in estimate.lots for tab in lot.tabs]
    if estimate.outside_lot is not None:
        tabs.append(estimate.outside_lot)
    taken = list[str](FIXED_TABS)
    for tab in tabs:
        taken.append(sheet_name(f"{tab.number} {tab.task_label}".strip(), taken))
    return tuple(tabs), tuple(taken[len(FIXED_TABS) :])


def _reference_rows(estimate: Estimate) -> list[list[Any]]:
    """Give the lines of the table of the reference: roles, then categories, by type."""
    natures = {nature.name: nature for nature in estimate.natures}
    categories = {category.code: category for category in estimate.categories}
    rows: list[list[Any]] = []
    for role in estimate.roles:
        category = categories[role.category]
        kind = KIND_NAMES[natures[category.nature].kind]
        rate = category.hourly_rate
        rows.append(
            [
                _entry(role.label, role.code),
                "Rôle",
                role.code,
                role.label,
                role.department,
                category.nature,
                kind,
                category.code,
                rate,
            ]
        )
    for category in estimate.categories:
        kind = KIND_NAMES[natures[category.nature].kind]
        if kind != LABOUR:
            rows.append(
                [
                    _entry(category.label, category.code),
                    "Catégorie",
                    category.code,
                    category.label,
                    "",
                    category.nature,
                    kind,
                    category.code,
                    None,
                ]
            )
    rows.sort(key=lambda row: KIND_ORDER[row[6]])
    return rows


def _padded(rows: list[list[Any]], width: int) -> list[list[Any]]:
    """Give a table a row at least: an empty list of rows gets a blank one."""
    return rows or [[None] * width]


def _write_parameters(sheet: Worksheet, ctx: _Context) -> tuple[str, str]:
    """Write « Paramètres »; give the two lists of choice (roles and categories, subprojects)."""
    estimate, fmt = ctx.estimate, ctx.fmt
    sheet.write(
        "A1", "Référentiel de la révision : écrit par l’export, ignoré à l’import.", fmt["bold"]
    )
    sheet.write(
        "A2",
        f"Taux horaires de l’année de référence {estimate.reference_year} retenus par la révision. "
        "Les modifier ici ne change aucun taux dans Waterfall.",
        fmt["note"],
    )
    rows = _reference_rows(estimate)
    first = 3
    sheet.add_table(
        first - 1,
        0,
        first - 1 + len(_padded(rows, 1)),
        len(REFERENCE_HEADERS) - 1,
        {
            "name": "Referentiel",
            "data": _padded(rows, len(REFERENCE_HEADERS)),
            "style": TABLE_STYLE,
            "columns": [{"header": header} for header in REFERENCE_HEADERS],
        },
    )
    # A provision is never typed: it is written by the marking of a risk.
    chosen = max(1, sum(1 for row in rows if row[6] != PROVISION))
    roles_list = f"='{PARAMETERS}'!$A${first + 1}:$A${first + chosen}"
    column = len(REFERENCE_HEADERS) + 1
    subprojects = [[s.code, s.label] for s in estimate.subprojects]
    sheet.add_table(
        first - 1,
        column,
        first - 1 + len(_padded(subprojects, 1)),
        column + 1,
        {
            "name": "SousProjets",
            "data": _padded(subprojects, 2),
            "style": TABLE_STYLE,
            "columns": [{"header": header} for header in SUBPROJECT_HEADERS],
        },
    )
    letter = xl_col_to_name(column)
    count = max(1, len(subprojects))
    subprojects_list = f"='{PARAMETERS}'!${letter}${first + 1}:${letter}${first + count}"
    for index, width in enumerate(REFERENCE_WIDTHS):
        sheet.set_column(index, index, width)
    sheet.protect("", {"autofilter": True, "sort": True})
    return roles_list, subprojects_list


def _write_tasks(sheet: Worksheet, ctx: _Context) -> tuple[str, ...]:
    """Write « Tâches »; give, for each tab of lines, the list of choice of its tasks."""
    fmt = ctx.fmt
    sheet.write(
        "A1",
        "Tâches de la structure : la liste de chaque onglet, et l’identifiant retrouvé à l’import.",
        fmt["bold"],
    )
    rows: list[list[Any]] = []
    ranges: list[str] = []
    first = 3
    for tab, name in zip(ctx.tabs, ctx.sheets, strict=True):
        begin = first + len(rows)
        rows.extend(
            [
                _task_entry(task),
                task.lineage,
                task.number,
                task.label,
                name,
                task.start.isoformat(),
                task.end.isoformat(),
                task.description,
            ]
            for task in tab.tasks
        )
        count = max(1, len(tab.tasks))
        ranges.append(f"='{TASKS}'!$A${begin + 1}:$A${begin + count}")
    sheet.add_table(
        first - 1,
        0,
        first - 1 + len(_padded(rows, 1)),
        len(TASK_HEADERS) - 1,
        {
            "name": "Taches",
            "data": _padded(rows, len(TASK_HEADERS)),
            "style": TABLE_STYLE,
            "columns": [{"header": header} for header in TASK_HEADERS],
        },
    )
    for index, width in enumerate(TASK_WIDTHS):
        sheet.set_column(index, index, width)
    sheet.protect("", {"autofilter": True, "sort": True})
    return tuple(ranges)


def _task_entry(task: Task) -> str:
    return f"{task.number} {task.label}"


def _line_formulas(table: str) -> dict[str, str]:
    """Give the calculated columns of a tab of lines: each formula names its table."""

    def cell(column: str) -> str:
        return _this(table, column)

    def lookup(column: str) -> str:
        key = cell("Rôle ou catégorie")
        return (
            f'=IF({key}="","",IFERROR(INDEX(Referentiel[[{column}]],'
            f'MATCH({key},Referentiel[[Entrée]],0)),"?"))'
        )

    empty = f'{cell("Rôle ou catégorie")}=""'
    labour = f"{cell('Type')}={_quote(LABOUR)}"
    non_labour = f"OR({cell('Type')}={_quote(DISBURSEMENT)},{cell('Type')}={_quote(PROVISION)})"
    return {
        "Description de la tâche": (
            f'=IF({cell("Tâche")}="","",IFERROR(INDEX(Taches[[Description]],'
            f'MATCH({cell("Tâche")},Taches[[Entrée]],0)),""))'
        ),
        "Nature": lookup("Nature"),
        "Code comptable": lookup("Code comptable"),
        # An empty text stays empty, not 0.
        "Service": lookup("Service")[:-1] + '&"")',
        "Taux horaire": lookup("Taux horaire"),
        "Heures totales": f'=IF({empty},"",IF({labour},{cell("Quantité")}*{cell("Heures")},0))',
        "Main-d’œuvre": (
            f'=IF({empty},"",IF({labour},'
            f"{cell('Quantité')}*{cell('Heures')}*{cell('Taux horaire')},0))"
        ),
        "Débours": (
            f'=IF({empty},"",IF({non_labour},{cell("Quantité")}*{cell("Débours unitaire")},0))'
        ),
        "Montant": f'=IF({empty},"",{cell("Main-d’œuvre")}+{cell("Débours")})',
        "Type": lookup("Type de nature"),
    }


def _table_names(tabs: tuple[Tab, ...]) -> tuple[str, ...]:
    """Name the table of each tab of lines from its number, unique without regard to case."""
    names: list[str] = []
    for tab in tabs:
        base = "Lignes_" + (re.sub(r"\W", "_", tab.number) if tab.number else "hors_lot")
        name, count = base, 1
        while name.lower() in {other.lower() for other in names}:
            count += 1
            name = f"{base}_{count}"
        names.append(name)
    return tuple(names)


def _line_row(labels: _Labels, task: Task, line: Line) -> list[Any]:
    """Give the cells a line writes; the calculated columns stay empty."""
    if line.role is not None:
        entry = _entry(labels.roles[line.role], line.role)
    else:
        code = line.category or ""
        entry = _entry(labels.categories[code], code)
    values: dict[str, Any] = {
        "Tâche": _task_entry(task),
        "Rôle ou catégorie": entry,
        "Désignation": line.label,
        "Quantité": line.quantity,
        "Heures": line.hours,
        "Débours unitaire": line.disbursement,
        "Délai de paiement (j)": line.payment_delay,
        "Sous-projet": line.subproject or "",
        "Montant Waterfall": line.amount,
        "ID ligne": line.lineage,
    }
    return [values.get(header) for header in LINE_HEADERS]


def _write_lines_tab(sheet: Worksheet, ctx: _Context, position: int, lists: _Lists) -> None:
    """Write a tab of lines: a table with its total row, its lists, its calculated columns."""
    fmt = ctx.fmt
    tab, table, tasks_list = ctx.tabs[position], ctx.tables[position], lists.tasks[position]
    formulas = _line_formulas(table)
    data = [_line_row(ctx.labels, task, line) for task in tab.tasks for line in task.lines]
    last = len(data) + PREPARED
    data += [[None] * len(LINE_HEADERS) for _ in range(PREPARED)]
    columns: list[dict[str, Any]] = []
    for header in LINE_HEADERS:
        spec: dict[str, Any] = {"header": header}
        if header in formulas:
            spec["formula"] = formulas[header]
            spec["format"] = (
                fmt["grey_money"]
                if header in AMOUNT_HEADERS
                else fmt["grey_hours"]
                if header == "Heures totales"
                else fmt["grey"]
            )
        elif header == "Montant Waterfall":
            spec["format"] = fmt["grey_money"]
        elif header in TEXT_HEADERS:
            spec["format"] = fmt["text"]
        if header in TOTAL_HEADERS:
            # Declared in the table (Excel repairs a total it does not find), and naming the table:
            # LibreOffice does not read the short form « [Column] » that "sum" would write.
            spec["total_function"] = f"=SUBTOTAL(109,{table}[[{header}]])"
        columns.append(spec)
    columns[0]["total_string"] = "Total"
    sheet.add_table(
        0,
        0,
        last + 1,
        len(LINE_HEADERS) - 1,
        {
            "name": table,
            "data": data,
            "columns": columns,
            "total_row": True,
            "style": LINES_STYLE,
        },
    )
    index = {header: position for position, header in enumerate(LINE_HEADERS)}
    for header, source, title, message in (
        ("Tâche", tasks_list, "Tâche", "Choisis une tâche de cet onglet (onglet Tâches)."),
        (
            "Rôle ou catégorie",
            lists.roles,
            "Rôle ou catégorie",
            "Choisis un rôle ou une catégorie du référentiel.",
        ),
    ):
        sheet.data_validation(
            1,
            index[header],
            VALIDATED_ROWS,
            index[header],
            {"validate": "list", "source": source, "error_title": title, "error_message": message},
        )
    sheet.data_validation(
        1,
        index["Sous-projet"],
        VALIDATED_ROWS,
        index["Sous-projet"],
        {"validate": "list", "source": lists.subprojects, "ignore_blank": True},
    )
    for column, (header, width) in enumerate(LINE_COLUMNS):
        if header in HIDDEN_HEADERS:
            sheet.set_column(column, column, width, None, {"level": 1, "hidden": True})
        else:
            sheet.set_column(column, column, width)
    sheet.freeze_panes(1, 1)
    sheet.write_comment(
        0,
        index["Montant Waterfall"],
        "Écrit par l’export : le montant de la ligne inflation comprise, que Waterfall calcule "
        "à l’année de consommation de la tâche. Vide pour une ligne ajoutée dans Excel.",
    )
    sheet.write_comment(
        0,
        index["ID ligne"],
        "Identifiant de lignée, écrit par l’export. Vide : la ligne est nouvelle.",
    )


def _summary_columns(estimate: Estimate) -> list[tuple[str, str, str]]:
    """Give the columns after « Niveau »: (header, kind, key)."""
    natures = {nature.name: nature for nature in estimate.natures}
    columns = [("nature", nature.name, nature.name) for nature in estimate.natures]
    seen: set[str] = set()
    for category in estimate.categories:
        if natures[category.nature].kind == "labour" and category.code not in seen:
            seen.add(category.code)
            columns.append(("hours", category.code, f"Heures {category.code}"))
    columns += [("total", "", "Total"), ("waterfall", "", "Montant Waterfall")]
    return [(header, kind, key) for kind, key, header in columns]


def _tab_formula(kind: str, key: str, table: str) -> str:
    """Give the formula of a tab for one column of the summary, without « Inclus »."""
    if kind == "hours":
        return f"SUMIFS({table}[[Heures totales]],{table}[[Code comptable]],{_quote(key)})"
    if kind == "total":
        return f"SUM({table}[[Montant]])"
    if kind == "waterfall":
        return f"SUM({table}[[Montant Waterfall]])"
    return f"SUMIFS({table}[[Montant]],{table}[[Nature]],{_quote(key)})"


def _write_summary(sheet: Worksheet, ctx: _Context) -> tuple[int, list[tuple[str, str, str]]]:
    """Write « Devis »: a row per lot, per tab; give the row of the total and the columns."""
    estimate, fmt = ctx.estimate, ctx.fmt
    sheet.write("A1", f"Devis — {estimate.project}", fmt["title"])
    sheet.write(
        "A2",
        "Aux taux de l’année de référence, avant inflation. « Inclus » n’est pas lu à l’import.",
        fmt["italic"],
    )
    columns = _summary_columns(estimate)
    header = ["N°", "Lot ou poste", "Inclus", "Niveau", *(column[0] for column in columns)]
    top = 4
    sheet.write_row(top, 0, header, fmt["head"])
    sheet.set_row(top, 32)
    plan: list[_Row] = []
    tables = iter(ctx.tables)  # in the order of the tabs: the lots', then the one outside
    for lot in estimate.lots:
        plan.append(_Row("lot", lot.number, lot.label, tabs=len(lot.tabs)))
        plan += [_Row("tab", tab.number, tab.label, table=next(tables)) for tab in lot.tabs]
    if estimate.outside_lot is not None:
        outside = estimate.outside_lot
        plan.append(_Row("tab", outside.number, outside.label, table=next(tables)))
    first = top + 1
    last = top + len(plan)
    for offset, entry in enumerate(plan):
        row = first + offset
        number, label = entry.number, entry.label
        if entry.level == "lot":
            count = entry.tabs
            sheet.write_string(row, 0, number, fmt["lot"])
            sheet.write(row, 1, label, fmt["lot"])
            sheet.write(row, 2, "", fmt["lot"])
            sheet.write(row, 3, "lot", fmt["lot"])
            for position, (_, kind, _) in enumerate(columns, start=4):
                style = fmt["lot_hours"] if kind == "hours" else fmt["lot_money"]
                # The tabs of the lot follow its row: the sum never holds the row of the lot.
                formula = (
                    f"=SUM({xl_rowcol_to_cell(row + 1, position)}:"
                    f"{xl_rowcol_to_cell(row + count, position)})"
                    if count
                    else "=0"
                )
                sheet.write_formula(row, position, formula, style)
            continue
        sheet.write_string(row, 0, number)
        sheet.write(row, 1, label)
        sheet.write(row, 2, "Oui")
        sheet.data_validation(row, 2, row, 2, {"validate": "list", "source": ["Oui", "Non"]})
        sheet.write(row, 3, "onglet")
        for position, (_, kind, key) in enumerate(columns, start=4):
            style = fmt["hours"] if kind == "hours" else fmt["money"]
            formula = f'=IF($C${row + 1}="Oui",{_tab_formula(kind, key, entry.table)},0)'
            sheet.write_formula(row, position, formula, style)
    total = last + 1
    sheet.write(total, 1, "Total", fmt["bold"])
    levels = f"$D${first + 1}:$D${last + 1}"
    for position, (_, kind, _) in enumerate(columns, start=4):
        cells = f"{xl_rowcol_to_cell(first, position)}:{xl_rowcol_to_cell(last, position)}"
        style = fmt["hours_bold"] if kind == "hours" else fmt["money_bold"]
        sheet.write_formula(total, position, f'=SUMIFS({cells},{levels},"onglet")', style)
    sheet.set_column(0, 0, 6)
    sheet.set_column(1, 1, 30)
    sheet.set_column(2, 2, 7)
    sheet.set_column(3, 3, 7, None, {"hidden": True})
    sheet.set_column(4, len(header) - 1, 14)
    sheet.freeze_panes(top + 1, 2)
    return total, columns


def _write_presentation(
    sheet: Worksheet,
    ctx: _Context,
    total_row: int,
    columns: list[tuple[str, str, str]],
    mention: str,
) -> None:
    """Write « Présentation »: format and version first (A1-B2), then the project, the breakdown."""
    estimate, fmt = ctx.estimate, ctx.fmt
    sheet.write("A1", "Format")
    sheet.write("B1", FORMAT_NAME)
    sheet.write("A2", "Version")
    sheet.write_number("B2", FORMAT_VERSION, fmt["left"])
    sheet.write_comment("A1", "Format et version, lus à l’import (annexe B) : ne pas modifier.")
    logo = BytesIO(files(PACKAGE).joinpath(*LOGO).read_bytes())
    sheet.insert_image(
        "D1",
        "waterfall_logo.png",
        {
            "image_data": logo,
            "x_scale": 0.2,
            "y_scale": 0.2,
            "x_offset": 0,
            "y_offset": 4,
            "object_position": 3,
            "description": "Waterfall",
        },
    )
    sheet.write("A4", estimate.project, fmt["title"])
    infos = [
        ("Entreprise", estimate.company),
        ("Client", estimate.client),
        ("Révision", estimate.revision),
        ("Structure", estimate.structure),
        ("Année de référence", estimate.reference_year),
        ("Devise", estimate.currency),
        ("Exporté le", estimate.exported_at.strftime(INSTANT_FORMAT)),
    ]
    for offset, (key, value) in enumerate(infos):
        sheet.write(5 + offset, 0, key, fmt["bold"])
        sheet.write(5 + offset, 1, value, fmt["left"])
    base = 6 + len(infos)
    sheet.write(
        base,
        0,
        "Ventilation par nature de coût, aux taux de l’année de référence, avant inflation",
        fmt["bold"],
    )
    sheet.write_row(base + 1, 0, ["Nature", "Montant", "Part"], fmt["bold"])
    natures = [
        (position, column)
        for position, column in enumerate(columns, start=4)
        if column[1] == "nature"
    ]
    total_line = base + 2 + len(natures)
    for offset, (position, column) in enumerate(natures):
        row = base + 2 + offset
        sheet.write(row, 0, column[0])
        sheet.write_formula(
            row, 1, f"={SUMMARY}!{xl_rowcol_to_cell(total_row, position)}", fmt["money"]
        )
        share = (
            f"=IF({xl_rowcol_to_cell(total_line, 1)}=0,0,"
            f"{xl_rowcol_to_cell(row, 1)}/{xl_rowcol_to_cell(total_line, 1)})"
        )
        sheet.write_formula(row, 2, share, fmt["percent"])
    sheet.write(total_line, 0, "Total", fmt["bold"])
    total_formula = (
        f"=SUM({xl_rowcol_to_cell(base + 2, 1)}:{xl_rowcol_to_cell(total_line - 1, 1)})"
        if natures
        else "=0"
    )
    sheet.write_formula(total_line, 1, total_formula, fmt["money_bold"])
    waterfall = next(
        position for position, column in enumerate(columns, start=4) if column[1] == "waterfall"
    )
    end = total_line + 2
    sheet.write(end, 0, "Montant Waterfall, inflation comprise", fmt["bold"])
    sheet.write_formula(
        end, 1, f"={SUMMARY}!{xl_rowcol_to_cell(total_row, waterfall)}", fmt["money_bold"]
    )
    sheet.write(
        end + 1,
        0,
        "Celui des lignes exportées : le montant inflation comprise d’une ligne ajoutée ou "
        "modifiée dans Excel n’est connu qu’après l’import.",
        fmt["italic"],
    )
    sheet.write(end + 3, 0, mention, fmt["small"])
    sheet.set_column(0, 0, 44)
    sheet.set_column(1, 1, 24)
    sheet.set_column(2, 2, 10)
    sheet.set_column(3, 3, 34)  # the logo
    sheet.print_area(0, 0, end + 3, 3)
    sheet.fit_to_pages(1, 1)


def write_workbook(estimate: Estimate) -> bytes:
    """Write the workbook « Devis » of an estimate; no line at all gives the blank model.

    A text typed is a text: ``strings_to_formulas`` and ``strings_to_urls`` are off. The instant of
    the export is the one the estimate carries, in the properties as on the presentation, so that
    the same estimate gives the same workbook.
    """
    # A workbook always has a tab of lines: the blank model of a structure that has none is
    # "Hors lot", with its prepared rows.
    if not any(lot.tabs for lot in estimate.lots) and estimate.outside_lot is None:
        estimate = replace(estimate, outside_lot=Tab("", NO_LOT, NO_LOT, ()))
    buffer = BytesIO()
    book = xlsxwriter.Workbook(
        buffer,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "remove_timezone": True,
        },
    )
    book.set_properties(
        {
            "title": f"Devis — {estimate.project}",
            "author": "Waterfall",
            "created": estimate.exported_at,
        }
    )
    book.set_calc_mode("auto")
    tabs, sheet_names = _name_tabs(estimate)
    ctx = _Context(
        estimate,
        tabs,
        sheet_names,
        _table_names(tabs),
        _text_formats(book, estimate.currency),
        _labels(estimate),
    )
    presentation = book.add_worksheet(PRESENTATION)
    summary = book.add_worksheet(SUMMARY)
    sheets = [book.add_worksheet(name) for name in sheet_names]
    tasks = book.add_worksheet(TASKS)
    parameters = book.add_worksheet(PARAMETERS)

    roles_list, subprojects_list = _write_parameters(parameters, ctx)
    lists = _Lists(roles_list, subprojects_list, _write_tasks(tasks, ctx))
    for position, sheet in enumerate(sheets):
        _write_lines_tab(sheet, ctx, position, lists)
    total_row, columns = _write_summary(summary, ctx)
    mention, footer = _footer_text(estimate)
    _write_presentation(presentation, ctx, total_row, columns, mention)
    for sheet in book.worksheets():
        sheet.set_footer(f"&L&8{footer}&R&8Page &P / &N")
    presentation.activate()
    book.close()
    return buffer.getvalue()
