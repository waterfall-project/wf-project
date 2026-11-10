# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The analysis of the workbook of a remaining to commit against a structure, private (US-1630/L3).

The lines read (``excel/reader``) are matched with those of the structure by their lineage, the
« ID ligne » column the export writes, as the estimate's (``importing``) are. For a line it knows,
the analysis computes again the value the export would have written — the days left of a labour
line, quantity x effort ÷ hours per day (``remaining_days``), the amount left of another, its
re-estimated amount — and judges the line changed only when the cell differs from it, both read
at the fifteen significant digits a spreadsheet keeps: a workbook imported again without a change
gives no difference (WF-INTF-0130). Changed, the line receives its figures, the quantity kept —
brought to one when nought —: the effort, days x hours per day ÷ quantity, to the hundredth of an
hour its column holds; the unit disbursement, amount ÷ (quantity x inflation coefficient of its
consumption year), to the cent; an ``updated`` difference names the columns written, its budgeted
amount and its lineage left (EP-09, "Ce que le cadrage décide"). Unchanged, it counts in
``unchanged_count``, nothing written. Its task, its role and its label are the export's: the
remaining to commit writes only figures, and the subproject of its tab. A line of a task completed
of the main structure is rejected, unchanged too (``task_not_completed``); a figure in the column of
the other kind is refused as its entry refuses it (``FIELD_NOT_ACCEPTED``).

A line without a lineage — or with one the structure does not hold — is created, its budgeted
amount nought on a project that has a reference (WF-DEV-0020), under the task « Tâches » gives its
entry the lineage of or the one task of its label, its role or its category by the code of its
entry, with the rejections of the estimate (``importing.plan``): ``AMBIGUOUS_TASK_LABEL``,
``UNKNOWN_TASK``, ``UNKNOWN_RESOURCE_ROLE``, a provision category, a line under a task completed
of the main structure (``task_not_completed``, ``params.tasks``; I-05, #1794), a role that would
leave its task without an hour (``TASK_WITHOUT_WORKING_HOURS``). Its quantity is one: its effort the
days typed x hours per day, its unit disbursement the amount typed over the inflation coefficient
of the year its task is consumed in.

The subproject of a line is the one of its tab, named by its code as the writer names it
(``sheet_name``), « Hors sous-projet » none: a line placed in another tab changes subproject — an
``updated`` difference on ``subproject`` —, rejected when its task is started or completed and its
subproject received actual costs (``SUBPROJECT_HAS_ACTUAL_COSTS``, by the entry); a tab of no
subproject rejects its lines (``UNKNOWN_SUBPROJECT``, ``params.value`` the tab). The lines of the
structure absent from the file are left as they are, without a difference (WF-INTF-0120).

A task the import leaves with no remaining to commit — every line of it the file writes set to
nought, none of its other lines holding a remaining, a provision never — is completed by the
re-estimate of its last line written, at the date of the review « Synthèse » carries
(``completed_tasks``, WF-RAE-0040): a summary only when its subordinates are all completed, as the
planning completes it. Without a date, its lines set to nought are rejected
(``COMPLETION_DATE_REQUIRED``), as the entry refuses them — ``DATE_INVALID``, ``params.value`` the
cell, when « Synthèse » holds something that is not a date —; before the start of a task started,
too (``VALUE_OUT_OF_RANGE``, ``params.minimum`` the start), the completion never preceding it
(WF-PLA-0130). A task whose lines the file leaves as they are is not re-estimated.

The report is the contract's (``ImportReport``): nothing is written by the analysis.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Context, Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.estimate import importing
from waterfall.core.estimate.costing import basis_of
from waterfall.core.estimate.entries import FIELD_NOT_ACCEPTED, LineEntry
from waterfall.core.estimate.excel import reader as estimate_reader
from waterfall.core.estimate.excel.reader import ReadLine
from waterfall.core.estimate.pricing import inflation_factor, round_to_cent
from waterfall.core.estimate.reading import COMPLETED, TASK_NOT_COMPLETED
from waterfall.core.estimate.remaining.excel.layout import FORMAT_VERSION, tab_subprojects
from waterfall.core.estimate.remaining.excel.model import remaining_days
from waterfall.core.estimate.remaining.excel.reader import DAYS_HEADER, DISBURSEMENT_HEADER
from waterfall.core.estimate.remaining.reviewing import provisions_of
from waterfall.core.estimate.spreading import Placement, spread_by_year
from waterfall.core.planning.interface import weekly_calendar
from waterfall.core.resource_settings.interface import get_duration_units
from waterfall.platform.errors import STATE_FORBIDS_OPERATION

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.costing import Basis
    from waterfall.core.estimate.importing import (
        Aimed,
        Analysis,
        Designations,
        Judging,
        Planned,
        Reference,
    )
    from waterfall.core.estimate.remaining.excel.reader import ReadRemainingLine, RemainingRead
    from waterfall.core.estimate.tables import EstimateLine
    from waterfall.core.planning.interface import BearingTask, TaskView

COMPLETION_DATE_REQUIRED = "COMPLETION_DATE_REQUIRED"
DATE_INVALID = "DATE_INVALID"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
STARTED = "started"
NOUGHT = Decimal(0)
ONE = Decimal(1)
HUNDREDTH = Decimal("0.01")
# The significant digits a spreadsheet keeps of a number: a cell read is compared at them.
SPREADSHEET_DIGITS = Context(prec=15)
# The column of each field of a line, as a refusal of its entry names it; the subproject is the
# tab's, the quantity is never typed: neither has a column.
HEADERS = {
    "label": estimate_reader.LABEL_HEADER,
    "cost_category_id": estimate_reader.ROLE_OR_CATEGORY_HEADER,
    "resource_role_id": estimate_reader.ROLE_OR_CATEGORY_HEADER,
    "hours": DAYS_HEADER,
    "unit_disbursement": DISBURSEMENT_HEADER,
}


@dataclass(frozen=True, slots=True)
class Confirmed(importing.Confirmed):
    """What the report a user confirmed holds back, which its application analyses again with.

    ``rejected`` the rows it rejected, left as they are whatever the analysis now finds (the
    estimate's, whose ``removed`` stays empty: a remaining removes no line); ``updated`` the
    lineages of the lines it announced updated: a line it counted unchanged is not written,
    whatever the structure became since (WF-INTF-0080); ``completed`` the lineages of the tasks
    it announced completed: no other is.
    """

    updated: frozenset[str]
    completed: frozenset[str]


@dataclass(frozen=True, slots=True)
class Scale:
    """What the figures of a file are read at: the hours of a day, the inflation of the revision.

    ``tabs`` gives the subproject of each tab of lines by its name, none for « Hors sous-projet »;
    ``codes`` the code of each subproject.
    """

    hours_per_day: Decimal
    basis: Basis | None
    tabs: Mapping[str, UUID | None]
    codes: Mapping[UUID, str]


@dataclass(slots=True)
class Reviewed:
    """What the analysis of a remaining to commit finds.

    ``found`` the lines accepted and the rejections, as the estimate's; ``closing`` by task it
    completes, the line whose re-estimate completes it; ``review_date`` the date it completes at.
    """

    found: Analysis
    review_date: date | None
    unreadable_date: str | None = None
    closing: dict[UUID, UUID] = field(default_factory=dict[UUID, UUID])


def same_cell(typed: Decimal, written: Decimal) -> bool:
    """Tell a cell that holds what the export wrote, at the digits a spreadsheet keeps."""
    return SPREADSHEET_DIGITS.plus(typed) == SPREADSHEET_DIGITS.plus(written)


def effort(days: Decimal, hours_per_day: Decimal, quantity: Decimal) -> Decimal:
    """Give the effort of a unit of a labour line: days x hours per day ÷ quantity, to 0.01 h."""
    return (days * hours_per_day / quantity).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)


def unit_disbursement(amount: Decimal, quantity: Decimal, coefficient: Decimal) -> Decimal:
    """Give the unit disbursement of a line: amount ÷ (quantity x coefficient), to the cent."""
    return round_to_cent(amount / (quantity * coefficient))


def scale_of(session: Session, held: Aimed, reference: Reference) -> Scale:
    """Read what the figures of a file are read at, for the structure aimed at."""
    hours = get_duration_units(session).units.hours_per_day
    basis = (
        None if held.revision_id is None else basis_of(session, held.project_id, held.revision_id)
    )
    codes = {subproject: code for code, subproject in reference.subprojects.items()}
    return Scale(hours, basis, tab_subprojects(reference.subprojects), codes)


def _coefficient(scale: Scale, year: int) -> Decimal:
    """Give the inflation coefficient of a year of consumption, one without a revision."""
    basis = scale.basis
    if basis is None:
        return ONE
    return inflation_factor(basis.inflation_rate, basis.reference_year, year)


def consumption_year_of(bearer: BearingTask, fallback: int) -> int:
    """Give the year a task consumes most of a line in, on its own calendar."""
    placement = Placement(weekly_calendar(bearer.week), bearer.start, bearer.finish)
    shares = spread_by_year(placement, ONE)
    return max(shares.items(), key=lambda share: share[1])[0] if shares else fallback


@dataclass(frozen=True, slots=True)
class Sent:
    """What a line without a lineage sends of its figures, as an estimate's cells would."""

    quantity: Decimal
    hours: Decimal | None
    disbursement: Decimal | None
    subproject: str | None


def _placed(line: ReadRemainingLine, sent: Sent | None = None) -> ReadLine:
    """Give a line of the file as the estimate reads one, with the figures it sends."""
    return ReadLine(
        sheet=line.sheet,
        row=line.row,
        task=line.task,
        role_or_category=line.role_or_category,
        label=line.label,
        quantity=None if sent is None else sent.quantity,
        hours=None if sent is None else sent.hours,
        disbursement=None if sent is None else sent.disbursement,
        payment_delay=None,
        subproject=None if sent is None else sent.subproject,
        lineage=line.lineage,
    )


def analyse(
    session: Session, held: Aimed, read: RemainingRead, confirmed: Confirmed | None = None
) -> Reviewed:
    """Match and judge every line read against the structure; nothing is written.

    ``confirmed`` the report the application writes, none for the analysis: a row it rejected, or a
    line it counted unchanged, is left out before the hours and the completions are judged.
    """
    reference = importing.reference_of(session, held.project_id)
    named = importing.designations(held, read.tasks)
    scale = scale_of(session, held, reference)
    found = importing.Analysis(
        rejected=[importing.reader_rejection(each) for each in read.rejected]
    )
    taken: set[UUID] = {
        lineage
        for each in read.rejected
        if (lineage := importing.lineage_of(each.lineage)) is not None and lineage in held.lines
    }
    judging = importing.Judging(confirmed is not None, HEADERS)
    for line in read.lines:
        lineage = importing.lineage_of(line.lineage)
        current = held.lines.get(lineage) if lineage is not None and lineage not in taken else None
        if lineage is not None and current is not None:
            taken.add(lineage)
        if line.sheet not in scale.tabs:
            unknown = {"value": line.sheet}
            found.rejected.append(importing.rejection(_placed(line), UNKNOWN_SUBPROJECT, unknown))
        elif current is None:
            _create(session, line, held, (reference, named, scale), (found, judging))
        else:
            _known(session, (line, current), held, scale, (found, judging))
    if confirmed is not None:
        lineages = lineages_by_node(held)
        found.planned = [each for each in found.planned if _confirmed(lineages, each, confirmed)]
    importing.judge_hours(session, held, reference, found)
    reviewed = Reviewed(found, read.review_date, read.unreadable_review)
    _close(session, held, reviewed)
    return reviewed


def lineages_by_node(held: Aimed) -> dict[UUID, UUID]:
    """Give the lineage of each line of the structure, by its node."""
    return {row.node_id: lineage for lineage, row in held.lines.items()}


def _confirmed(lineages: Mapping[UUID, UUID], planned: Planned, confirmed: Confirmed) -> bool:
    """Tell a line accepted that the report confirmed: not rejected, and announced if it exists."""
    line, current = planned.line, planned.current
    if (line.sheet, line.row) in confirmed.rejected:
        return False
    return current is None or str(lineages[current.node_id]) in confirmed.updated


def _create(
    session: Session,
    line: ReadRemainingLine,
    held: Aimed,
    named: tuple[Reference, Designations, Scale],
    outcome: tuple[Analysis, Judging],
) -> None:
    """Plan a line without a lineage, a unit of its kind, under its task; or reject it."""
    reference, designations, scale = named
    text = line.role_or_category
    role, _ = (None, None) if text is None else reference.named(text)
    hours = None if line.days is None else effort(line.days, scale.hours_per_day, ONE)
    disbursement = line.disbursement
    task = importing.designated_task(_placed(line), held, designations)
    basis = scale.basis
    if role is None and disbursement is not None and basis is not None and isinstance(task, UUID):
        year = consumption_year_of(held.bearer(task), basis.reference_year)
        disbursement = unit_disbursement(disbursement, ONE, _coefficient(scale, year))
    subproject = scale.tabs[line.sheet]
    placed = _placed(
        line,
        Sent(ONE, hours, disbursement, None if subproject is None else scale.codes[subproject]),
    )
    importing.plan(session, (placed, None), held, (reference, designations), outcome)


def _known(
    session: Session,
    read: tuple[ReadRemainingLine, EstimateLine],
    held: Aimed,
    scale: Scale,
    outcome: tuple[Analysis, Judging],
) -> None:
    """Plan a line the structure holds when its cell or its tab changes it; or reject it."""
    line, current = read
    found, judging = outcome
    placed = _placed(line)
    task_id = held.bearers[current.node_id]
    if held.is_main and held.tasks[task_id].progress == COMPLETED:
        tasks = [importing.named_task(held, task_id)]
        params = {"missing_condition": TASK_NOT_COMPLETED, "tasks": tasks}
        found.rejected.append(importing.rejection(placed, STATE_FORBIDS_OPERATION, params))
        return
    labour = current.resource_role_id is not None
    if (line.disbursement if labour else line.days) is not None:
        header = DISBURSEMENT_HEADER if labour else DAYS_HEADER
        found.rejected.append(importing.rejection(placed, FIELD_NOT_ACCEPTED, {"header": header}))
        return
    entry = _figures(current, line, scale)
    if entry is None:
        return
    sent = (task_id, entry, current)
    draft = importing.judged(session, placed, held, sent, judging)
    if isinstance(draft, list):
        found.rejected.extend(draft)
        return
    fields = importing.changed_columns(draft, current, moved=False)
    if fields:
        role = current.resource_role_id
        found.planned.append(
            importing.Planned(placed, task_id, entry, current, role, draft.label, fields)
        )


def _figures(current: EstimateLine, line: ReadRemainingLine, scale: Scale) -> LineEntry | None:
    """Give what a line known sends: its changed figures, its tab's subproject; none if neither.

    The cell is compared to what the export would have written of the line; an empty cell of a
    line the structure holds reads nought — « Jours restants » or « Débours restant » left blank
    sets the remaining to nought, as typing 0 does (to be settled by the author, #2410). The
    quantity is kept, brought to one when nought.
    """
    labour = current.resource_role_id is not None
    typed = (line.days if labour else line.disbursement) or NOUGHT
    written = (
        remaining_days(current.quantity, current.hours or NOUGHT, scale.hours_per_day)
        if labour
        else current.reestimated_amount
    )
    subproject = scale.tabs[line.sheet]
    sent: set[str] = set() if subproject == current.subproject_id else {"subproject_id"}
    quantity = current.quantity or ONE
    hours = disbursement = None
    if not same_cell(typed, written):
        if labour:
            hours = effort(typed, scale.hours_per_day, quantity)
            sent |= {"quantity", "hours"}
        else:
            coefficient = _coefficient(scale, current.consumption_year)
            disbursement = unit_disbursement(typed, quantity, coefficient)
            sent |= {"quantity", "unit_disbursement"}
    if not sent:
        return None
    return LineEntry(
        quantity=quantity,
        hours=hours,
        unit_disbursement=disbursement,
        subproject_id=subproject,
        sent=frozenset(sent),
    )


def writes_figures(planned: Planned) -> bool:
    """Tell a line accepted whose figures the file writes: created, or its cell changed."""
    return planned.current is None or bool({"hours", "unit_disbursement"} & planned.entry.sent)


def _nought(planned: Planned) -> bool:
    """Tell a line whose figures the file writes and sets its remaining to nought."""
    entry = planned.entry
    value = entry.hours if planned.role_id is not None else entry.unit_disbursement
    return writes_figures(planned) and value is not None and value == 0


def _close(session: Session, held: Aimed, reviewed: Reviewed) -> None:
    """Find the tasks the import completes, and reject the lines that cannot complete them.

    A task is completed when a line it bears that the file sets to nought exists already — its
    re-estimate completes it, as ``setLineRemaining`` does — and none of its lines holds a
    remaining once the file is written: neither one the file writes, nor one it leaves, a provision
    never. A summary only once its subordinates are all completed (``awaiting_own_lines``).
    """
    found = reviewed.found
    written = {each.current.node_id: each for each in found.planned if each.current is not None}
    created: dict[UUID, list[Planned]] = {}
    closers: dict[UUID, list[Planned]] = {}
    for each in found.planned:
        if each.current is None:
            created.setdefault(each.task_id, []).append(each)
        elif _nought(each):
            closers.setdefault(each.task_id, []).append(each)
    if not closers:
        return
    holding = [row for row in held.lines.values() if row.reestimated_amount != 0]
    provisions = provisions_of(session, holding)
    held_open: set[UUID] = set()
    for row in held.lines.values():
        planned = written.get(row.node_id)
        if planned is not None and writes_figures(planned):
            still = not _nought(planned)
        else:
            still = row.reestimated_amount != 0 and row.node_id not in provisions
        if still:
            held_open.add(held.bearers[row.node_id])
    held_open |= {task for task, lines in created.items() if not all(map(_nought, lines))}
    for task_id in held.tasks:
        lines = closers.get(task_id)
        task = held.tasks[task_id]
        if (
            lines is None
            or task_id in held_open
            or task.progress == COMPLETED
            or (task.is_summary and not task.awaiting_own_lines)
        ):
            continue
        refusal = _refusal(task, reviewed)
        if refusal is None:
            node = lines[-1].current
            if node is not None:
                reviewed.closing[task_id] = node.node_id
            continue
        code, params = refusal
        params["tasks"] = [importing.named_task(held, task_id)]
        found.rejected.extend(importing.rejection(each.line, code, params) for each in lines)
        refused = {id(each) for each in lines}
        found.planned = [each for each in found.planned if id(each) not in refused]


def _refusal(task: TaskView, reviewed: Reviewed) -> tuple[str, dict[str, Any]] | None:
    """Give why a task cannot be completed at the date of the review: none, or the reason.

    No date, or one that is none: ``COMPLETION_DATE_REQUIRED``, or ``DATE_INVALID`` when the cell
    holds something that is not a date; a date before the start of a task started,
    ``VALUE_OUT_OF_RANGE``.
    """
    review_date, started_on = reviewed.review_date, task.started_on
    if review_date is None:
        if reviewed.unreadable_date is None:
            return COMPLETION_DATE_REQUIRED, {}
        return DATE_INVALID, {"value": reviewed.unreadable_date}
    if task.progress == STARTED and started_on is not None and review_date < started_on:
        return VALUE_OUT_OF_RANGE, {"minimum": started_on.isoformat()}
    return None


def report_of(held: Aimed, read: RemainingRead, reviewed: Reviewed) -> dict[str, Any]:
    """Give the report of an analysis, as the contract reads it (``ImportReport``).

    The rejections in the order of the workbook, tab by tab and row by row; the lines added and
    updated in the order of the file; the tasks completed in the order of the plan, at the date of
    the review. No line absent from the file is named (WF-INTF-0120).
    """
    found = reviewed.found
    rows = [(line.sheet, line.row) for line in read.lines]
    rows += [(each.sheet, each.row) for each in read.rejected]
    tabs = {sheet: rank for rank, sheet in enumerate(dict.fromkeys(sheet for sheet, _ in rows))}
    rejected = sorted(found.rejected, key=lambda each: (tabs.get(each["sheet"], 0), each["row"]))
    lineages = lineages_by_node(held)
    differences = [
        importing.difference("added", None, each.label)
        if each.current is None
        else importing.difference(
            "updated", lineages[each.current.node_id], each.label, each.fields
        )
        for each in found.planned
    ]
    day = reviewed.review_date
    completed = [
        {
            "lineage_id": str(held.task_lineages[task_id]),
            "label": held.tasks[task_id].label,
            "completed_on": None if day is None else day.isoformat(),
        }
        for task_id in held.tasks
        if task_id in reviewed.closing
    ]
    rejected_rows = {(each["sheet"], each["row"]) for each in rejected}
    read_count = len(set(rows))
    return {
        "format_version": str(FORMAT_VERSION),
        "read_count": read_count,
        "unchanged_count": read_count - len(rejected_rows) - len(found.planned),
        "rejected": rejected,
        "refusals": [],
        "differences": differences,
        "ignored": [],
        "completed_tasks": completed,
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": [],
    }
