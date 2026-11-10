# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The layout of the workbook « Reste à engager » of annex B: its names, its columns, its formulas.

The headers are the French ones of the annex, fixed (WF-INTF-0180); the import (US-1630/L2) reads
the tabs of lines by these headers.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.estimate.excel.writer import (
    DISBURSEMENT,
    FOOTER_LIMIT,
    FOOTER_MARGIN,
    GREY,
    HOURS_FORMAT,
    INSTANT_FORMAT,
    LABOUR,
    NOTE,
    SYMBOLS,
)

if TYPE_CHECKING:
    from xlsxwriter import Workbook
    from xlsxwriter.format import Format

    from waterfall.core.estimate.remaining.excel.model import RemainingWorkbook

FORMAT_NAME = "Reste à engager"
FORMAT_VERSION = 1
SUMMARY = "Synthèse"
TASKS = "Tâches"
PARAMETERS = "Paramètres"
OUTSIDE = "Hors sous-projet"
FIXED_TABS = (SUMMARY, TASKS, PARAMETERS)
# The row (from 0) of the first fact of the project in the summary: the company, the client, the
# revision, the date of the review, the structure, the currency (annex B, rows 6 to 11).
FACTS_ROW = 5
# The cell of the summary that holds the date of the review, which the import reads (#2702).
REVIEW_DATE_CELL = f"B{FACTS_ROW + 3 + 1}"
# The cell of « Paramètres » that holds the hours per day, which the formulas of the tabs read.
HOURS_PER_DAY_CELL = "'Paramètres'!$B$2"
# The columns of the summary: the progress, then the breakdown of the remaining.
PROGRESS_COLUMN = 6
BREAKDOWN_COLUMN = 7
# The empty rows prepared under the lines exported, for a line the review adds (WF-RAE-0050).
PREPARED = 10
# The lists of choice hold for far more rows than the table, which grows as one types.
VALIDATED_ROWS = 400
# The row (from 0) of the header of the table of lines, under the header of the tab.
TABLE_ROW = 14

COLUMNS = (
    ("Tâche", 34),
    ("Description de la tâche", 40),
    ("État", 13),
    ("Rôle ou catégorie", 32),
    ("Désignation", 34),
    ("Budget", 13),
    ("Reste précédent", 13),
    ("Jours restants", 13),
    ("Débours restant", 13),
    ("Nature", 16),
    ("Code comptable", 13),
    ("Service", 22),
    ("Taux horaire", 13),
    ("Main-d’œuvre", 13),
    ("Débours", 13),
    ("Reste à engager", 13),
    ("Type", 13),
    ("Coefficient", 13),
    ("ID ligne", 13),
)
HEADERS = tuple(header for header, _ in COLUMNS)
INDEX = {header: position for position, header in enumerate(HEADERS)}
MONEY_FORMULAS = ("Main-d’œuvre", "Débours", "Reste à engager")
TOTALS = ("Budget", "Reste précédent", "Jours restants", "Débours restant", *MONEY_FORMULAS)
# What the workbook writes of its own and the user does not type: grey.
GREY_MONEY = ("Budget", "Reste précédent")
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
REFERENCE_WIDTHS = (34, 10, 10, 26, 24, 22, 18, 14, 11)
TASK_HEADERS = ("Entrée", "ID tâche", "Sous-projet", "État", "Coefficient", "Description")
TASK_WIDTHS = (38, 10, 16, 14, 11, 50)
STATES = {"started": "démarrée", "not_started": "non démarrée"}
TABLE_STYLE = "Table Style Light 1"
LINES_STYLE = "Table Style Light 9"


def quote(text: str) -> str:
    """Write a text inside a formula."""
    return '"' + text.replace('"', '""') + '"'


def sheet_ref(name: str) -> str:
    """Write the name of a tab inside a formula."""
    return "'" + name.replace("'", "''") + "'"


def this(table: str, column: str) -> str:
    """Write the cell of a column on the row of the formula."""
    return f"{table}[[#This Row],[{column}]]"


def entry(label: str, code: str) -> str:
    """Write the text of the list of choice for a role or a category."""
    return f"{label} ({code})"


def money_format(currency: str) -> str:
    """Give the number format of an amount in a currency."""
    symbol = SYMBOLS.get(currency, currency).replace('"', "")
    return f'#,##0.00 "{symbol}"'


def footers(book: RemainingWorkbook) -> tuple[str, str]:
    """Give the mention of the summary and the same for the footer, within Excel's limit."""
    year = book.exported_at.year
    instant = book.exported_at.strftime(INSTANT_FORMAT)

    def mention(company: str) -> str:
        return (
            f"© {year} {company} — Généré par Waterfall le {instant} — "
            "logiciel libre sous licence AGPL-3.0 — www.waterfall-project.pro"
        )

    company = book.company
    while len(mention(company).replace("&", "&&")) > FOOTER_LIMIT - FOOTER_MARGIN and company:
        company = company[:-2] + "…" if len(company) > 1 else ""
    return mention(book.company), mention(company).replace("&", "&&")


def text_formats(workbook: Workbook, currency: str) -> dict[str, Format]:
    """Add the formats of the cells of the workbook."""
    money = money_format(currency)
    spec: dict[str, dict[str, Any]] = {
        "bold": {"bold": True},
        "title": {"bold": True, "font_size": 14},
        "left": {"align": "left"},
        "money": {"num_format": money},
        "money_bold": {"num_format": money, "bold": True},
        "days": {"num_format": HOURS_FORMAT},
        "days_bold": {"num_format": HOURS_FORMAT, "bold": True},
        "percent": {"num_format": "0.0 %", "align": "right"},
        "percent_bold": {"num_format": "0.0 %", "align": "right", "bold": True},
        "note": NOTE,
        "small": {"font_size": 8, "font_color": "#666666"},
        "band": {"bold": True, "center_across": True, "bg_color": "#DDEBF7", "border": 1},
        "grey": GREY,
        "grey_money": {**GREY, "num_format": money},
        "text": {"num_format": "@"},
        "head": {"bold": True, "text_wrap": True, "valign": "top", "bottom": 1},
    }
    return {name: workbook.add_format(properties) for name, properties in spec.items()}


def line_formulas(table: str) -> dict[str, str]:
    """Give the calculated columns of a tab of lines: each formula names its table."""

    def cell(column: str) -> str:
        return this(table, column)

    def lookup(column: str, suffix: str = "") -> str:
        key = cell("Rôle ou catégorie")
        return (
            f'=IF({key}="","",IFERROR(INDEX(Referentiel[[{column}]],'
            f'MATCH({key},Referentiel[[Entrée]],0)){suffix},"?"))'
        )

    def of_task(column: str, default: str) -> str:
        found = f"MATCH({cell('Tâche')},Taches[[Entrée]],0)"
        return f"IFERROR(INDEX(Taches[[{column}]],{found}),{default})"

    empty = f'{cell("Rôle ou catégorie")}=""'
    labour = f"{cell('Type')}={quote(LABOUR)}"
    return {
        "Description de la tâche": (
            f'=IF({cell("Tâche")}="","",{of_task("Description", quote(""))})'
        ),
        "État": f'=IF({cell("Tâche")}="","",{of_task("État", quote(""))})',
        "Nature": lookup("Nature"),
        "Code comptable": lookup("Code comptable"),
        # An empty text stays empty, not 0.
        "Service": lookup("Service", suffix='&""'),
        "Taux horaire": lookup("Taux horaire"),
        "Type": lookup("Type de nature"),
        "Coefficient": f"={of_task('Coefficient', '1')}",
        "Main-d’œuvre": (
            f'=IF({empty},"",IF({labour},N({cell("Jours restants")})*{HOURS_PER_DAY_CELL}'
            f"*{cell('Taux horaire')}*{cell('Coefficient')},0))"
        ),
        # A disbursement typed is an amount, inflation included: it enters as it is.
        "Débours": (
            f'=IF({empty},"",IF({cell("Type")}={quote(DISBURSEMENT)},'
            f"N({cell('Débours restant')}),0))"
        ),
        "Reste à engager": f'=IF({empty},"",{cell("Main-d’œuvre")}+{cell("Débours")})',
    }
