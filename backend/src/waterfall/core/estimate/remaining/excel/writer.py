# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workbook « Reste à engager » of annex B, written from a revision in memory (US-1630/L1).

Pure: a ``RemainingWorkbook`` in, the bytes of an ``.xlsx`` out, with XlsxWriter, without a
database, a clock or a language. The design follows the prototype of the specification
(``docs/spec/exemples/prototype_rae.py``): « Synthèse », a tab of lines per subproject and one
for the lines outside any, « Tâches » and « Paramètres ». A text typed is written as a text —
never as a formula, never as a link — and only the formulas written here are formulas.
"""

import re
from dataclasses import dataclass, replace
from decimal import Decimal
from importlib.resources import files
from io import BytesIO
from typing import TYPE_CHECKING, Any

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

from waterfall.core.estimate.excel.writer import (
    KIND_NAMES,
    KIND_ORDER,
    LABOUR,
    LOGO,
    PACKAGE,
    PROVISION,
)
from waterfall.core.estimate.remaining.excel import layout
from waterfall.core.estimate.remaining.excel.layout import (
    COLUMNS,
    HEADERS,
    INDEX,
    PARAMETERS,
    SUMMARY,
    TASKS,
    entry,
    quote,
    sheet_ref,
)
from waterfall.core.estimate.remaining.excel.model import RemainingTab, remaining_days

if TYPE_CHECKING:
    from xlsxwriter.format import Format
    from xlsxwriter.worksheet import Worksheet

    from waterfall.core.estimate.remaining.excel.model import (
        RemainingLine,
        RemainingTask,
        RemainingWorkbook,
    )

ZERO = Decimal(0)


@dataclass(frozen=True)
class _Context:
    """What the sheets share: the revision, its tabs with their names, the formats."""

    book: RemainingWorkbook
    tabs: tuple[RemainingTab, ...]
    sheets: tuple[str, ...]
    tables: tuple[str, ...]
    fmt: dict[str, Format]
    labels: dict[str, str]  # the label of a role or of a category, by code
    labour_codes: tuple[str, ...]  # the accounting codes of labour, which the summary sums in days


@dataclass(frozen=True)
class _Cells:
    """The cells of a tab that the summary reads, as formulas without the sign ``=``."""

    budget: str
    actual: str
    remaining: str
    projection: str
    gap: str
    progress: str
    by_nature: tuple[str, ...]
    days: tuple[str, ...]


def _title(tab: RemainingTab) -> str:
    return f"{tab.code} {tab.label}".strip() or layout.OUTSIDE


def _task_entry(task: RemainingTask) -> str:
    return f"{task.number} {task.label}"


def _table_names(tabs: tuple[RemainingTab, ...]) -> tuple[str, ...]:
    """Name the table of each tab of lines from its code, unique without regard to case."""
    names: list[str] = []
    for tab in tabs:
        base = "RAE_" + (re.sub(r"\W", "_", tab.code) if tab.code else "hors_sous_projet")
        name, count = base, 1
        while name.lower() in {other.lower() for other in names}:
            count += 1
            name = f"{base}_{count}"
        names.append(name)
    return tuple(names)


def _reference_rows(book: RemainingWorkbook) -> list[list[Any]]:
    """Give the rows of the table of the reference: roles, then categories, by type."""
    kinds = {nature.name: KIND_NAMES[nature.kind] for nature in book.natures}
    categories = {category.code: category for category in book.categories}
    rows: list[list[Any]] = []
    for role in book.roles:
        category = categories[role.category]
        kind = kinds[category.nature]
        rows.append(
            [
                entry(role.label, role.code),
                "Rôle",
                role.code,
                role.label,
                role.department,
                category.nature,
                kind,
                category.code,
                category.hourly_rate,
            ]
        )
    rows.extend(
        [
            entry(category.label, category.code),
            "Catégorie",
            category.code,
            category.label,
            "",
            category.nature,
            kinds[category.nature],
            category.code,
            None,
        ]
        for category in book.categories
        if kinds[category.nature] != LABOUR
    )
    rows.sort(key=lambda row: KIND_ORDER[row[6]])
    return rows


def _padded(rows: list[list[Any]], width: int) -> list[list[Any]]:
    """Give a table a row at least: an empty list of rows gets a blank one."""
    return rows or [[None] * width]


def _write_parameters(sheet: Worksheet, ctx: _Context) -> str:
    """Write « Paramètres »: the reference and the hours per day; give the list of choice."""
    book, fmt = ctx.book, ctx.fmt
    book_note = "Référentiel de la révision : écrit par l’export, ignoré à l’import."
    sheet.write("A1", book_note, fmt["bold"])
    sheet.write("A2", "Heures par jour")
    sheet.write_number("B2", float(book.hours_per_day))
    sheet.write_comment("B2", "Constante de l’installation : les jours restants s’y mesurent.")
    sheet.protect("", {"autofilter": True, "sort": True})
    rows = _reference_rows(book)
    first = 3
    sheet.add_table(
        first,
        0,
        first + len(_padded(rows, 1)),
        len(layout.REFERENCE_HEADERS) - 1,
        {
            "name": "Referentiel",
            "data": _padded(rows, len(layout.REFERENCE_HEADERS)),
            "style": layout.TABLE_STYLE,
            "columns": [{"header": header} for header in layout.REFERENCE_HEADERS],
        },
    )
    for index, width in enumerate(layout.REFERENCE_WIDTHS):
        sheet.set_column(index, index, width)
    # A provision is never typed: it is written by the marking of a risk.
    chosen = max(1, sum(1 for row in rows if row[6] != PROVISION))
    return f"='{PARAMETERS}'!$A${first + 2}:$A${first + 1 + chosen}"


def _write_tasks(sheet: Worksheet, ctx: _Context) -> tuple[str, ...]:
    """Write « Tâches »; give, for each tab of lines, the list of choice of its tasks."""
    sheet.write(
        "A1", "Tâches non terminées par sous-projet : la liste de chaque onglet.", ctx.fmt["bold"]
    )
    rows: list[list[Any]] = []
    ranges: list[str] = []
    top = 3
    for tab in ctx.tabs:
        begin = top + len(rows)
        rows.extend(
            [
                _task_entry(task),
                task.lineage,
                tab.code,
                layout.STATES[task.state],
                float(task.inflation),
                task.description,
            ]
            for task in tab.tasks
        )
        count = max(1, len(tab.tasks))
        ranges.append(f"='{TASKS}'!$A${begin + 2}:$A${begin + 1 + count}")
    sheet.add_table(
        top,
        0,
        top + len(_padded(rows, 1)),
        len(layout.TASK_HEADERS) - 1,
        {
            "name": "Taches",
            "data": _padded(rows, len(layout.TASK_HEADERS)),
            "style": layout.TABLE_STYLE,
            "columns": [{"header": header} for header in layout.TASK_HEADERS],
        },
    )
    for index, width in enumerate(layout.TASK_WIDTHS):
        sheet.set_column(index, index, width)
    sheet.protect("", {"autofilter": True, "sort": True})
    return tuple(ranges)


def _line_row(ctx: _Context, task: RemainingTask, line: RemainingLine) -> list[Any]:
    """Give the cells a line writes; the calculated columns stay empty."""
    labour = line.role is not None
    code = line.role if line.role is not None else line.category or ""
    values: dict[str, Any] = {
        "Tâche": _task_entry(task),
        "Rôle ou catégorie": entry(ctx.labels[code], code),
        "Désignation": line.label or None,
        "Budget": line.budget,
        "Reste précédent": line.previous,
        "ID ligne": line.lineage,
    }
    if labour:
        values["Jours restants"] = remaining_days(line.quantity, line.hours, ctx.book.hours_per_day)
    else:
        values["Débours restant"] = line.reestimated_amount
    return [values.get(header) for header in HEADERS]


def _column_specs(ctx: _Context, table: str) -> list[dict[str, Any]]:
    """Give the columns of the table of lines: formats, formulas, declared totals."""
    fmt = ctx.fmt
    formulas = layout.line_formulas(table)
    columns: list[dict[str, Any]] = []
    for header in HEADERS:
        spec: dict[str, Any] = {"header": header, "header_format": fmt["head"]}
        if header in formulas:
            spec["formula"] = formulas[header]
            spec["format"] = fmt["grey_money"] if header in layout.MONEY_FORMULAS else fmt["grey"]
        elif header in layout.GREY_MONEY:
            spec["format"] = fmt["grey_money"]
        elif header == "ID ligne":
            spec["format"] = fmt["grey"]
        elif header == "Jours restants":
            spec["format"] = fmt["days"]
        elif header == "Débours restant":
            spec["format"] = fmt["money"]
        else:
            spec["format"] = fmt["text"]
        if header in layout.TOTALS:
            # Declared in the table (Excel repairs a total it does not find), and naming the table:
            # LibreOffice does not read the short form « [Column] » that "sum" would write.
            spec["total_function"] = f"=SUBTOTAL(109,{table}[[{header}]])"
        columns.append(spec)
    columns[0]["total_string"] = "Total"
    return columns


def _write_band(
    sheet: Worksheet, row: int, columns: tuple[int, int], text: str, style: Format
) -> None:
    """Write a title over columns: merged when it spans several, as the prototype does."""
    first, last = columns
    if last > first:
        sheet.merge_range(row, first, row, last, text, style)
    else:
        sheet.write(row, first, text, style)


def _write_header(sheet: Worksheet, ctx: _Context, tab: RemainingTab, table: str) -> dict[str, str]:
    """Write the header of a tab: its amounts and its indicators; give their cells."""
    fmt = ctx.fmt
    sheet.write("A1", _title(tab), fmt["title"])
    sheet.write(
        "A2",
        f"Revue du {ctx.book.review_date.isoformat()} — une ligne par rôle ou par débours, comme "
        f"au devis. La main-d’œuvre se saisit en jours de {ctx.book.hours_per_day.normalize():f} "
        "heures, un débours en montant.",
        fmt["note"],
    )
    cells: dict[str, str] = {}
    amounts = (
        ("Budget du sous-projet", tab.budget, "budget"),
        ("Coûts réels imputés", tab.actual_costs, "actual"),
        ("Reste à engager du tableau", f"=SUBTOTAL(109,{table}[[Reste à engager]])", "table"),
        ("Provisions des risques identifiés", tab.provisions, "provisions"),
    )
    for offset, (label, value, key) in enumerate(amounts):
        sheet.write(3 + offset, 0, label)
        if isinstance(value, str):
            sheet.write_formula(3 + offset, 1, value, fmt["money"])
        else:
            sheet.write_number(3 + offset, 1, float(value), fmt["money"])
        cells[key] = xl_rowcol_to_cell(3 + offset, 1, row_abs=True, col_abs=True)
    indicators = (
        ("Reste à engager", "={table}+{provisions}", "money_bold", "remaining"),
        ("Projection (coûts réels + reste)", "={actual}+{remaining}", "money_bold", "projection"),
        ("Écart au budget", "={projection}-{budget}", "money_bold", "gap"),
        (
            "Avancement financier",
            '=IF({projection}=0,"non calculable",{actual}/{projection})',
            "percent",
            "progress",
        ),
    )
    for offset, (label, formula, style, key) in enumerate(indicators):
        row = 4 + len(amounts) + offset
        sheet.write(row, 0, label, fmt["bold"])
        sheet.write_formula(row, 1, formula.format(**cells), fmt[style])
        cells[key] = xl_rowcol_to_cell(row, 1, row_abs=True, col_abs=True)
    return cells


def _write_tab(
    sheet: Worksheet, ctx: _Context, position: int, roles_list: str, tasks_list: str
) -> _Cells:
    """Write a tab of lines: its header, its table with the total row, its lists."""
    tab, table, name = ctx.tabs[position], ctx.tables[position], ctx.sheets[position]
    fmt, top = ctx.fmt, layout.TABLE_ROW
    cells = _write_header(sheet, ctx, tab, table)
    _write_band(
        sheet,
        top - 1,
        (INDEX["Jours restants"], INDEX["Débours restant"]),
        f"Reste au {ctx.book.review_date.isoformat()}",
        fmt["band"],
    )
    data = [_line_row(ctx, task, line) for task in tab.tasks for line in task.lines]
    data += [[None] * len(HEADERS) for _ in range(layout.PREPARED)]
    sheet.add_table(
        top,
        0,
        top + len(data) + 1,
        len(HEADERS) - 1,
        {
            "name": table,
            "data": data,
            "columns": _column_specs(ctx, table),
            "total_row": True,
            "style": layout.LINES_STYLE,
        },
    )
    for header, source, message in (
        ("Tâche", tasks_list, "Choisis une tâche non terminée du sous-projet (onglet Tâches)."),
        ("Rôle ou catégorie", roles_list, "Choisis un rôle ou une catégorie du référentiel."),
    ):
        sheet.data_validation(
            top + 1,
            INDEX[header],
            top + layout.VALIDATED_ROWS,
            INDEX[header],
            {"validate": "list", "source": source, "error_title": header, "error_message": message},
        )
    for header in ("Jours restants", "Débours restant"):
        sheet.data_validation(
            top + 1,
            INDEX[header],
            top + layout.VALIDATED_ROWS,
            INDEX[header],
            {
                "validate": "decimal",
                "criteria": ">=",
                "value": 0,
                "error_message": "Un reste à engager est un nombre positif ou nul.",
            },
        )
    first_hidden = INDEX["Type"]
    for index, (_, width) in enumerate(COLUMNS):
        if index >= first_hidden:
            sheet.set_column(index, index, width, None, {"level": 1, "hidden": True})
        else:
            sheet.set_column(index, index, width)
    sheet.freeze_panes(top + 1, 1)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.write(
        top + len(data) + 3,
        0,
        "Les tâches terminées ne sont pas dans le fichier. Une tâche dont tout le reste vaut zéro "
        "est terminée à la date de la revue.",
        fmt["note"],
    )
    return _cells_of(ctx, name, table, cells)


def _cells_of(ctx: _Context, sheet: str, table: str, cells: dict[str, str]) -> _Cells:
    """Give what the summary reads of a tab: its indicators and its breakdown."""

    def read(key: str) -> str:
        return f"{sheet_ref(sheet)}!{cells[key]}"

    by_nature = tuple(
        read("provisions")
        if nature.kind == "provision"
        else f"SUMIFS({table}[[Reste à engager]],{table}[[Nature]],{quote(nature.name)})"
        for nature in ctx.book.natures
    )
    days = tuple(
        f"SUMIFS({table}[[Jours restants]],{table}[[Code comptable]],{quote(code)})"
        for code in ctx.labour_codes
    )
    return _Cells(
        read("budget"),
        read("actual"),
        read("remaining"),
        read("projection"),
        read("gap"),
        read("progress"),
        by_nature,
        days,
    )


def _write_summary(sheet: Worksheet, ctx: _Context, cells: list[_Cells], mention: str) -> None:
    """Write « Synthèse »: format and version, the project, then the subprojects and the project."""
    book, fmt = ctx.book, ctx.fmt
    sheet.write("A1", "Format")
    sheet.write("B1", layout.FORMAT_NAME)
    sheet.write("A2", "Version")
    sheet.write_number("B2", layout.FORMAT_VERSION, fmt["left"])
    sheet.write_comment("A1", "Format et version, lus à l’import (annexe B) : ne pas modifier.")
    logo = BytesIO(files(PACKAGE).joinpath(*LOGO).read_bytes())
    sheet.insert_image(
        "E1",
        "waterfall_logo.png",
        {
            "image_data": logo,
            "x_scale": 0.2,
            "y_scale": 0.2,
            "y_offset": 4,
            "object_position": 3,
            "description": "Waterfall",
        },
    )
    sheet.write("A4", book.project, fmt["title"])
    # The facts of the project, in the order of annex B: the date of the review falls in the
    # cell the import reads (B9, #2702).
    facts = (
        ("Entreprise", book.company),
        ("Client", book.client),
        ("Révision", book.revision),
        ("Revue du", book.review_date.isoformat()),
        ("Structure", book.structure),
        ("Devise", book.currency),
    )
    for offset, (key, value) in enumerate(facts):
        sheet.write(layout.FACTS_ROW + offset, 0, key, fmt["bold"])
        sheet.write(layout.FACTS_ROW + offset, 1, value, fmt["left"])
    top = layout.FACTS_ROW + len(facts) + 1 + 2
    natures = [nature.name for nature in book.natures]
    headers = [
        "Sous-projet",
        "Budget",
        "Coûts réels",
        "Reste à engager",
        "Projection",
        "Écart au budget",
        "Avancement financier",
        *(f"Reste — {name}" for name in natures),
        *(f"Jours {code}" for code in ctx.labour_codes),
    ]
    last = len(headers) - 1
    _write_band(
        sheet,
        top - 1,
        (layout.BREAKDOWN_COLUMN, last),
        "Ventilation du reste à engager",
        fmt["band"],
    )
    sheet.write_row(top, 0, headers, fmt["head"])
    sheet.set_row(top, 30, fmt["head"])
    for offset, (tab, read) in enumerate(zip(ctx.tabs, cells, strict=True)):
        row = top + 1 + offset
        sheet.write(row, 0, _title(tab))
        for column, source in enumerate(
            (read.budget, read.actual, read.remaining, read.projection, read.gap), 1
        ):
            sheet.write_formula(row, column, f"={source}", fmt["money"])
        sheet.write_formula(row, layout.PROGRESS_COLUMN, f"={read.progress}", fmt["percent"])
        for column, source in enumerate(read.by_nature, layout.BREAKDOWN_COLUMN):
            sheet.write_formula(row, column, f"={source}", fmt["money"])
        for column, source in enumerate(read.days, layout.BREAKDOWN_COLUMN + len(natures)):
            sheet.write_formula(row, column, f"={source}", fmt["days"])
    total = top + 1 + len(ctx.tabs)
    sheet.write(total, 0, "Projet", fmt["bold"])
    for column in range(1, last + 1):
        if column == layout.PROGRESS_COLUMN:
            progress = f'=IF(E{total + 1}=0,"non calculable",C{total + 1}/E{total + 1})'
            sheet.write_formula(total, column, progress, fmt["percent_bold"])
            continue
        letter = xl_col_to_name(column)
        style = (
            fmt["days_bold"]
            if column >= layout.BREAKDOWN_COLUMN + len(natures)
            else fmt["money_bold"]
        )
        sheet.write_formula(total, column, f"=SUM({letter}{top + 2}:{letter}{total})", style)
    sheet.write(
        total + 2,
        0,
        "Écart signé dans le sens de la dérive : positif quand le sous-projet coûte plus que son "
        "budget (WF-RAE-0020). Avancement financier : coûts réels sur projection (WF-IND-0040).",
        fmt["note"],
    )
    sheet.write(total + 4, 0, mention, fmt["small"])
    sheet.set_column(0, 0, 30)
    sheet.set_column(1, last, 15)
    sheet.print_area(0, 0, total + 4, last)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 1)


def _context(book: RemainingWorkbook, workbook: xlsxwriter.Workbook) -> _Context:
    tabs = (*book.subprojects, *((book.outside,) if book.outside is not None else ()))
    names = layout.tab_names(tab.code for tab in book.subprojects)
    sheets = tuple(names[tab.code] for tab in tabs)
    kinds = {nature.name: nature.kind for nature in book.natures}
    labour_codes = tuple(
        dict.fromkeys(c.code for c in book.categories if kinds[c.nature] == "labour")
    )
    labels = {category.code: category.label for category in book.categories}
    labels.update({role.code: role.label for role in book.roles})
    return _Context(
        book,
        tabs,
        sheets,
        _table_names(tabs),
        layout.text_formats(workbook, book.currency),
        labels,
        labour_codes,
    )


def write_workbook(book: RemainingWorkbook) -> bytes:
    """Write the workbook « Reste à engager » of a revision; no tab at all gives the blank model.

    A text typed is a text: ``strings_to_formulas`` and ``strings_to_urls`` are off. The instant
    of the export is the one the revision carries, in the properties as in the footer, so that the
    same revision gives the same workbook.
    """
    if book.hours_per_day <= 0:
        msg = "the hours per day must be positive"
        raise ValueError(msg)
    if not book.subprojects and book.outside is None:
        book = replace(book, outside=RemainingTab("", "", ZERO, ZERO, ZERO, ()))
    buffer = BytesIO()
    workbook = xlsxwriter.Workbook(
        buffer,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "remove_timezone": True,
        },
    )
    workbook.set_properties(
        {
            "title": f"Reste à engager — {book.project}",
            "author": "Waterfall",
            "created": book.exported_at,
        }
    )
    workbook.set_calc_mode("auto")
    workbook.define_name(layout.HOURS_PER_DAY, f"={layout.HOURS_PER_DAY_CELL}")
    ctx = _context(book, workbook)
    summary = workbook.add_worksheet(SUMMARY)
    sheets = [workbook.add_worksheet(name) for name in ctx.sheets]
    tasks = workbook.add_worksheet(TASKS)
    parameters = workbook.add_worksheet(PARAMETERS)
    roles_list = _write_parameters(parameters, ctx)
    lists = _write_tasks(tasks, ctx)
    cells = [
        _write_tab(sheet, ctx, position, roles_list, lists[position])
        for position, sheet in enumerate(sheets)
    ]
    mention, footer = layout.footers(book)
    _write_summary(summary, ctx, cells, mention)
    for sheet in workbook.worksheets():
        sheet.set_footer(f"&L&8{footer}&R&8Page &P / &N")
    summary.activate()
    workbook.close()
    return buffer.getvalue()
