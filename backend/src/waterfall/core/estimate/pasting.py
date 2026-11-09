# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cells a paste gives a line, judged by the functions of the entry of a cell (US-1560).

The planning hands the estimate the cells of a row that fall on a line, or on a line to create, in
the order of ``NodeColumn`` — the label, then the category, the role, the quantity, the hours, the
unit disbursement, the subproject and the payment delay — each with the text of the spreadsheet. A
category, a role and a subproject are named by their label; a figure is a number, the comma
accepted as the decimal separator; a payment delay is a whole number of days.

A computed column is refused by ``COMPUTED_VALUE`` (the amounts and the year of consumption), a
column of the remaining to commit by ``FIELD_NOT_ACCEPTED``; a name that designates no object, or
several, is refused as an object unknown (``UNKNOWN_COST_CATEGORY``, ``UNKNOWN_RESOURCE_ROLE``,
``UNKNOWN_SUBPROJECT``). What is read then goes through the very judgement of ``updateEstimateLine``
and ``createNode`` (``entries``, ``writing.judged_priced``): the category of a labour line computed,
the fields a kind does not accept, the category of provision reserved to the risks, the hours of the
task left by the role (``TASK_WITHOUT_WORKING_HOURS``), the rate found (``HOURLY_RATE_MISSING``),
every fault named at once on its column. The write is that of ``updateEstimateLine``, or the
creation of ``createNode`` for a line created.
"""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from waterfall.core.cost_settings.interface import categories_named
from waterfall.core.estimate.entries import (
    COMPUTED_VALUE,
    FIELD_NOT_ACCEPTED,
    UNKNOWN_COST_CATEGORY,
    UNKNOWN_RESOURCE_ROLE,
    UNKNOWN_SUBPROJECT,
    LineEntry,
)
from waterfall.core.estimate.tables import LABEL_LENGTH
from waterfall.core.estimate.writing import change_line, judged_priced, read_line
from waterfall.core.planning.interface import CellRefusal, CellsJudged
from waterfall.core.projects.interface import subprojects_named
from waterfall.core.resource_settings.interface import roles_named
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from waterfall.core.planning.interface import CellsPasted, FacetWrite

NUMBER_INVALID = "NUMBER_INVALID"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
# The columns a paste fills on a line, in the order of ``NodeColumn``, and the field each writes.
FIELDS = {
    "label": "label",
    "cost_category": "cost_category_id",
    "resource_role": "resource_role_id",
    "quantity": "quantity",
    "hours": "hours",
    "unit_disbursement": "unit_disbursement",
    "subproject": "subproject_id",
    "payment_delay_days": "payment_delay_days",
}
COLUMN_OF = {field: column for column, field in FIELDS.items()}
# What the server computes for a line; the columns after them only the remaining to commit writes.
COMPUTED = frozenset({"consumption_year", "base_amount", "budgeted_amount", "reestimated_amount"})
ORDER = (
    *FIELDS,
    "consumption_year",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)
NAMES = {
    "cost_category": UNKNOWN_COST_CATEGORY,
    "resource_role": UNKNOWN_RESOURCE_ROLE,
    "subproject": UNKNOWN_SUBPROJECT,
}


def _number(text: str) -> Decimal | None:
    """Read a number a spreadsheet writes, the comma a decimal separator; none if it is none."""
    try:
        value = Decimal(text.replace(",", ".").replace(" ", "").replace(" ", ""))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _days(text: str) -> int | None:
    """Read a whole number of days; none for anything else."""
    stripped = text.replace(" ", "").replace(" ", "")
    if stripped.lstrip("-").isdecimal() and stripped.count("-") <= 1:
        return int(stripped)
    return None


def _lookups(pasted: CellsPasted) -> dict[str, Mapping[str, list[UUID]]]:
    """Look up, once, the objects the labels of the cells name: categories, roles, subprojects."""
    session = pasted.session
    labels: dict[str, set[str]] = {}
    for column, text in pasted.cells:
        if column in NAMES:
            labels.setdefault(column, set()).add(text)
    return {
        "cost_category": categories_named(session, labels.get("cost_category", ())),
        "resource_role": roles_named(session, labels.get("resource_role", ())),
        "subproject": subprojects_named(session, pasted.project_id, labels.get("subproject", ())),
    }


def _read(
    column: str, text: str, lookups: Mapping[str, Mapping[str, list[UUID]]]
) -> dict[str, Any] | CellRefusal:
    """Read the cell of a column into the field it writes, or say why it is refused."""
    if column not in FIELDS:
        return CellRefusal(column, COMPUTED_VALUE if column in COMPUTED else FIELD_NOT_ACCEPTED, {})
    field = FIELDS[column]
    found: object = None
    code = NUMBER_INVALID
    if column == "label":
        found = text if len(text) <= LABEL_LENGTH else None
        code = VALUE_TOO_LONG
    elif column in NAMES:
        named = lookups[column].get(text, [])
        found = named[0] if len(named) == 1 else None
        code = NAMES[column]
    else:
        found = _days(text) if column == "payment_delay_days" else _number(text)
    if found is None:
        params = {"max_length": LABEL_LENGTH} if column == "label" else {}
        return CellRefusal(column, code, params)
    return {field: found}


def _order(refusal: CellRefusal) -> int:
    """Order the refusals by the column, a whole row first."""
    return -1 if refusal.column is None else ORDER.index(refusal.column)


def _mapped(refused: UnprocessableError, columns: frozenset[str]) -> list[CellRefusal]:
    """Give the refusals of the entry of a cell as those of the cells that hold them.

    A refusal without a field — the hours of the task, the rate — falls on the role, if the row
    gives one, on the category otherwise, and on the row itself if it gives neither.
    """
    if refused.fields:
        return [
            CellRefusal(COLUMN_OF.get(fault.pointer.rsplit("/", 1)[-1]), fault.code, fault.params)
            for fault in refused.fields
        ]
    column = next((each for each in ("resource_role", "cost_category") if each in columns), None)
    return [CellRefusal(column, refused.code, refused.params)]


def judge_line_cell(pasted: CellsPasted) -> CellsJudged:
    """Judge the cells a paste gives a line, or a line to create, every refusal at once (422).

    Read cell by cell, then judged as the entry of a line is, written or created, down to its
    price; nothing is written. The entry judged is what ``write_line_cell`` writes, and what
    ``create_line`` creates the line from.
    """
    lookups = _lookups(pasted)
    fields: dict[str, Any] = {}
    refusals: list[CellRefusal] = []
    for column, text in pasted.cells:
        read = _read(column, text, lookups)
        if isinstance(read, CellRefusal):
            refusals.append(read)
        else:
            fields.update(read)
    entry = LineEntry(**fields, sent=frozenset(fields))
    if fields:
        current = (
            None
            if pasted.node_id is None
            else read_line(pasted.session, pasted.project_id, pasted.node_id)
        )
        try:
            judged_priced(pasted.session, pasted.project_id, pasted.bearer, entry, current)
        except UnprocessableError as refused:
            refused_columns = {each.column for each in refusals}
            refusals += [
                each
                for each in _mapped(refused, frozenset(column for column, _ in pasted.cells))
                if each.column not in refused_columns
            ]
    if refusals:
        return CellsJudged(tuple(sorted(refusals, key=_order)))
    return CellsJudged((), entry)


def write_line_cell(write: FacetWrite, entry: object) -> None:
    """Write the entry judged on a line, priced again (``updateEstimateLine``)."""
    if not isinstance(entry, LineEntry):
        msg = "a line is written from what the judgement of its cells gave"
        raise TypeError(msg)
    change_line(write, entry)
