# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The analysis of the workbook of an estimate against a structure, private to the module.

The lines read (``excel/reader``) are matched with those of the structure by their lineage, the
« ID ligne » column the export writes; a line without one, or with one the structure does not
hold — or one an earlier row of the file took already —, is a new line. Its task is the one
« Tâches » gives its entry the lineage of, or else the one task of the structure that carries its
label (``AMBIGUOUS_TASK_LABEL`` for several, ``UNKNOWN_TASK`` for none, ``params.value`` the cell);
its role or its category is read by the entry of the list of « Paramètres », « label (code) », or by
its code (``UNKNOWN_RESOURCE_ROLE``); its subproject by its code (``UNKNOWN_SUBPROJECT``). Each line
is then judged as its entry is (``entries.judged_line``): its refusals on a field reject it, by the
code of the field and the header of its column (``params.header``), a provision category among them
(``PROVISION_CATEGORY_RESERVED``), and the rule of a subproject that received actual costs, which
rejects nothing before EP-09 (``SUBPROJECT_HAS_ACTUAL_COSTS``). On the main structure, a new line
under a completed task, or a line changed or moved under or from one, is rejected as its entry is
refused (``STATE_FORBIDS_OPERATION``, ``task_not_completed``, #1767). A labour line whose role would
leave its task without an hour in its week, the roles of the lines its task keeps intersected day
by day in the order of the file, is rejected (``TASK_WITHOUT_WORKING_HOURS``, WF-PLA-0010). The
lines of the structure the file no longer carries are removed, but kept under a started or
completed task (``kept``, WF-INTF-0100). A cell empty reads as nought for a figure — the default of
a creation —, as no subproject, and as the label left as it is, composed at a creation.

What the workbook does not give is no refusal: a tab without the headers of lines is ignored, as an
unknown column; a header of a column read that a tab lacks reads its cells empty, and what follows
— lines created for want of a lineage, values changed, lines rejected — is in ``differences`` and
``rejected``, which the user reads before confirming (WF-INTF-0080).

The report is the contract's (``ImportReport``): nothing is written by the analysis.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.cost_settings.interface import (
    CostCategoryFilters,
    CostCategorySort,
    Page,
    category_label_of,
    list_cost_categories,
)
from waterfall.core.estimate.costing import TASK_WITHOUT_WORKING_HOURS, calendar_hours
from waterfall.core.estimate.entries import LineEntry, judged_line
from waterfall.core.estimate.excel import reader
from waterfall.core.estimate.excel.writer import FORMAT_VERSION
from waterfall.core.estimate.reading import COMPLETED, NOT_STARTED, TASK_NOT_COMPLETED, rows_of
from waterfall.core.estimate.tables import LABEL_LENGTH
from waterfall.core.planning.interface import (
    BearingTask,
    NodeFilters,
    Place,
    lineages_of,
    lines_of,
    list_nodes,
)
from waterfall.core.projects.interface import (
    SubprojectFilters,
    SubprojectSort,
    Viewer,
    list_subprojects,
)
from waterfall.core.resource_settings.interface import (
    RoleFilters,
    RoleSort,
    RoleWindow,
    list_roles,
    role_calendars,
)
from waterfall.core.revisions.interface import structure_facts
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import CostCategoryView
    from waterfall.core.estimate.entries import Draft
    from waterfall.core.estimate.excel.reader import ReadLine, WorkbookRead
    from waterfall.core.estimate.tables import EstimateLine
    from waterfall.core.exchanges.interface import ImportTarget
    from waterfall.core.planning.interface import TaskView
    from waterfall.core.resource_settings.interface import RoleView

TASK = "task"
LINE = "estimate_line"
NUMBER_INVALID = "NUMBER_INVALID"
VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
UNKNOWN_TASK = "UNKNOWN_TASK"
UNKNOWN_RESOURCE_ROLE = "UNKNOWN_RESOURCE_ROLE"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
AMBIGUOUS_TASK_LABEL = "AMBIGUOUS_TASK_LABEL"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
NOUGHT = Decimal(0)
EVERY = 10**9
NOBODY = UUID(int=0)
# The header of the column that carries each field of a line, as a refusal of its entry names it.
HEADERS = {
    "label": reader.LABEL_HEADER,
    "cost_category_id": reader.ROLE_OR_CATEGORY_HEADER,
    "resource_role_id": reader.ROLE_OR_CATEGORY_HEADER,
    "quantity": reader.QUANTITY_HEADER,
    "hours": reader.HOURS_HEADER,
    "unit_disbursement": reader.DISBURSEMENT_HEADER,
    "payment_delay_days": reader.PAYMENT_DELAY_HEADER,
    "subproject_id": reader.SUBPROJECT_HEADER,
}

type Report = dict[str, Any]


@dataclass(frozen=True, slots=True)
class Aimed:
    """The structure an import aims at, as read: its tasks, its lines by lineage, their tasks.

    ``revision_id`` is none, and the structure empty, for a project without a revision yet.
    """

    project_id: UUID
    revision_id: UUID | None
    is_main: bool
    tasks: dict[UUID, TaskView]
    task_lineages: dict[UUID, UUID]
    lines: dict[UUID, EstimateLine]
    bearers: dict[UUID, UUID]

    def bearer(self, task_id: UUID) -> BearingTask:
        """Give a task of the structure as the entry of a line judges it."""
        task, revision = self.tasks[task_id], self.revision_id
        if revision is None:
            msg = "a structure without a revision holds no task"
            raise LookupError(msg)
        return BearingTask(
            task_id,
            revision,
            task.label,
            task.start,
            task.finish,
            task.calendar_hours,
            task.progress,
            self.is_main,
        )


@dataclass(frozen=True, slots=True)
class Reference:
    """What a line names of the reference and the project: roles, categories, subprojects."""

    roles: dict[str, RoleView]
    categories: dict[str, CostCategoryView]
    subprojects: dict[str, UUID]
    roles_by_id: dict[UUID, RoleView]


@dataclass(frozen=True, slots=True)
class Planned:
    """A line of the file accepted: its row, its task, what it writes, the line it changes."""

    line: ReadLine
    task_id: UUID
    entry: LineEntry
    current: EstimateLine | None
    role_id: UUID | None
    label: str
    fields: tuple[str, ...]


@dataclass(slots=True)
class Analysis:
    """What the analysis finds: the lines accepted, the rejections, the lines left behind."""

    planned: list[Planned] = field(default_factory=list[Planned])
    rejected: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    left: list[UUID] = field(default_factory=list[UUID])


def aimed(session: Session, target: ImportTarget) -> Aimed:
    """Read the structure an import aims at; an empty one when the project has no revision yet."""
    project_id, revision_id, structure_id = (
        target.project_id,
        target.revision_id,
        target.structure_id,
    )
    if revision_id is None or structure_id is None:
        return Aimed(
            project_id, None, is_main=True, tasks={}, task_lineages={}, lines={}, bearers={}
        )
    is_main = structure_facts(session, project_id, structure_id, lock=False).is_main
    read = list_nodes(
        session, Place(project_id, revision_id, structure_id), NodeFilters(kinds=(TASK,))
    )
    tasks = {item.node_id: item.task for item in read.items if item.task is not None}
    bearing = lines_of(session, project_id, list(tasks))
    nodes = [node for held in bearing.values() for node in held]
    rows = {row.node_id: row for row in rows_of(session, project_id, nodes)}
    lineages = lineages_of(session, project_id, nodes)
    task_lineages = {item.node_id: item.lineage_id for item in read.items}
    held = Aimed(project_id, revision_id, is_main, tasks, task_lineages, {}, {})
    for task_id, lines in bearing.items():
        for node in lines:
            if node in rows:
                held.lines[lineages[node]] = rows[node]
                held.bearers[node] = task_id
    return held


def reference_of(session: Session, project_id: UUID) -> Reference:
    """Read the roles and the categories by their entry and their code, the subprojects by code."""
    every = frozenset({True, False})
    roles = list_roles(
        session,
        RoleFilters(states=every),
        RoleSort(category_label_of),
        RoleWindow(EVERY, 0),
        may_change=False,
    ).roles
    categories = list_cost_categories(
        session,
        CostCategoryFilters(states=every),
        CostCategorySort(),
        Page(EVERY, 0),
        may_change=False,
    ).categories
    named_roles: dict[str, RoleView] = {}
    for role in roles:
        named_roles.setdefault(f"{role.label} ({role.code})", role)
    named_categories: dict[str, CostCategoryView] = {}
    for category in categories:
        named_categories.setdefault(f"{category.label} ({category.code})", category)
    for role in roles:
        named_roles.setdefault(role.code, role)
    for category in categories:
        named_categories.setdefault(category.code, category)
    # The commands of the subprojects are not read: an account that holds no permission lists them.
    viewer = Viewer(NOBODY, frozenset())
    subprojects = list_subprojects(
        session, project_id, viewer, SubprojectFilters(), SubprojectSort()
    )
    return Reference(
        named_roles,
        named_categories,
        {each.code: each.subproject_id for each in subprojects},
        {role.resource_role_id: role for role in roles},
    )


def _rejection(
    line: ReadLine, code: str, params: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    return {"sheet": line.sheet, "row": line.row, "code": code, "params": dict(params or {})}


@dataclass(frozen=True, slots=True)
class Designations:
    """What designates a task: « Tâches » by entry, the tasks by lineage and by label."""

    entries: Mapping[str, str]
    by_lineage: dict[str, UUID]
    by_label: dict[str, list[UUID]]


def designations(held: Aimed, entries: Mapping[str, str]) -> Designations:
    """Index the tasks of a structure by their lineage and their label, in the order of the plan."""
    by_label: dict[str, list[UUID]] = {}
    for node, task in held.tasks.items():
        by_label.setdefault(task.label, []).append(node)
    by_lineage = {str(held.task_lineages[node]): node for node in held.tasks}
    return Designations(entries, by_lineage, by_label)


def _task(line: ReadLine, held: Aimed, named: Designations) -> UUID | dict[str, Any]:
    """Designate the task of a line: by « Tâches », else by its label; or give its rejection."""
    text = line.task
    if text is None:
        return _rejection(line, VALUE_REQUIRED, {"header": reader.TASK_HEADER})
    lineage = named.entries.get(text)
    if lineage is not None:
        found = named.by_lineage.get(lineage)
        return _rejection(line, UNKNOWN_TASK, {"value": text}) if found is None else found
    same = named.by_label.get(text, [])
    if len(same) == 1:
        return same[0]
    if not same:
        return _rejection(line, UNKNOWN_TASK, {"value": text})
    tasks = [_named_task(held, node) for node in same]
    return _rejection(line, AMBIGUOUS_TASK_LABEL, {"label": text, "tasks": tasks})


def _named_task(held: Aimed, task_id: UUID) -> dict[str, str]:
    return {"lineage_id": str(held.task_lineages[task_id]), "label": held.tasks[task_id].label}


def _figure(value: Decimal | None) -> Decimal:
    return NOUGHT if value is None else value


def _entry(
    line: ReadLine, reference: Reference, rejected: list[dict[str, Any]]
) -> tuple[LineEntry, UUID | None] | None:
    """Give what a line sends, as its entry would; or none, its rejections added."""
    before = len(rejected)
    role = category = None
    text = line.role_or_category
    if text is None:
        rejected.append(
            _rejection(line, VALUE_REQUIRED, {"header": reader.ROLE_OR_CATEGORY_HEADER})
        )
    else:
        role = reference.roles.get(text)
        category = None if role is not None else reference.categories.get(text)
        if role is None and category is None:
            rejected.append(_rejection(line, UNKNOWN_RESOURCE_ROLE, {"value": text}))
    subproject = None
    if line.subproject is not None:
        subproject = reference.subprojects.get(line.subproject)
        if subproject is None:
            rejected.append(_rejection(line, UNKNOWN_SUBPROJECT, {"value": line.subproject}))
    delay = _figure(line.payment_delay)
    if delay != delay.to_integral_value():
        header = reader.PAYMENT_DELAY_HEADER
        rejected.append(_rejection(line, NUMBER_INVALID, {"value": str(delay), "header": header}))
    if line.label is not None and len(line.label) > LABEL_LENGTH:
        params = {"max_length": LABEL_LENGTH, "header": reader.LABEL_HEADER}
        rejected.append(_rejection(line, VALUE_TOO_LONG, params))
    if len(rejected) > before:
        return None
    # A labour line sends its role and its hours, another its category and its disbursement; the
    # figure of the other kind is sent only when the cell carries one, which the entry refuses.
    labour = role is not None
    sent = {"quantity", "payment_delay_days", "subproject_id"}
    sent |= {"resource_role_id", "hours"} if labour else {"cost_category_id", "unit_disbursement"}
    if (line.disbursement if labour else line.hours) is not None:
        sent.add("unit_disbursement" if labour else "hours")
    if line.label is not None:
        sent.add("label")
    entry = LineEntry(
        label=line.label,
        cost_category_id=None if category is None else category.cost_category_id,
        quantity=_figure(line.quantity),
        resource_role_id=None if role is None else role.resource_role_id,
        hours=_figure(line.hours) if labour else line.hours,
        unit_disbursement=line.disbursement if labour else _figure(line.disbursement),
        payment_delay_days=int(delay),
        subproject_id=subproject,
        sent=frozenset(sent),
    )
    return entry, None if role is None else role.resource_role_id


def _changed(draft: Draft, current: EstimateLine, *, moved: bool) -> tuple[str, ...]:
    """Name the columns a line changes, in the order of ``NodeColumn``, then ``parent``."""
    pairs = (
        ("label", draft.label, current.label),
        ("cost_category", draft.cost_category_id, current.cost_category_id),
        ("resource_role", draft.resource_role_id, current.resource_role_id),
        ("quantity", draft.quantity, current.quantity),
        ("hours", draft.hours, current.hours),
        ("unit_disbursement", draft.unit_disbursement, current.unit_disbursement),
        ("subproject", draft.subproject_id, current.subproject_id),
        ("payment_delay_days", draft.payment_delay_days, current.payment_delay_days),
    )
    changed = [name for name, after, held in pairs if after != held]
    return (*changed, "parent") if moved else tuple(changed)


def _judged(
    session: Session, line: ReadLine, held: Aimed, sent: tuple[UUID, LineEntry, EstimateLine | None]
) -> Draft | list[dict[str, Any]]:
    """Judge a line as its entry is; give its draft, or the rejections of its fields."""
    task_id, entry, current = sent
    try:
        return judged_line(session, (held.project_id, held.bearer(task_id)), entry, current)
    except UnprocessableError as refusal:
        return [
            _rejection(
                line,
                fault.code,
                {**fault.params, "header": HEADERS[fault.pointer.rsplit("/", 1)[-1]]},
            )
            for fault in refusal.fields
        ]


def _completed(held: Aimed, tasks: Iterable[UUID]) -> UUID | None:
    """Give the first completed task among those named, on the main structure alone (#1767)."""
    if not held.is_main:
        return None
    return next((each for each in tasks if held.tasks[each].progress == COMPLETED), None)


def analyse(session: Session, held: Aimed, read: WorkbookRead) -> Analysis:
    """Match and judge every line read against the structure; nothing is written."""
    reference = reference_of(session, held.project_id)
    named = designations(held, read.tasks)
    found = Analysis(rejected=[_reader_rejection(each) for each in read.rejected])
    taken: set[UUID] = {
        lineage
        for each in read.rejected
        if (lineage := _lineage(each.lineage)) is not None and lineage in held.lines
    }
    for line in read.lines:
        lineage = _lineage(line.lineage)
        current = held.lines.get(lineage) if lineage is not None and lineage not in taken else None
        if current is not None and lineage is not None:
            taken.add(lineage)
        _plan(session, (line, current), held, (reference, named), found)
    found.left = [line.node_id for lineage, line in held.lines.items() if lineage not in taken]
    _judge_hours(session, held, reference, found)
    return found


def _plan(
    session: Session,
    read: tuple[ReadLine, EstimateLine | None],
    held: Aimed,
    named: tuple[Reference, Designations],
    found: Analysis,
) -> None:
    """Plan a line read, or reject it; a line rejected that exists is left as it is."""
    line, current = read
    reference, designated = named
    task = _task(line, held, designated)
    if isinstance(task, dict):
        found.rejected.append(task)
        _entry(line, reference, found.rejected)
        return
    sent = _entry(line, reference, found.rejected)
    if sent is None:
        return
    entry, role_id = sent
    draft = _judged(session, line, held, (task, entry, current))
    if isinstance(draft, list):
        found.rejected.extend(draft)
        return
    fields: tuple[str, ...] = ()
    if current is not None:
        before = held.bearers[current.node_id]
        fields = _changed(draft, current, moved=before != task)
        concerned = (before, task) if fields else ()
    else:
        concerned = (task,)
    completed = _completed(held, concerned)
    if completed is not None:
        params = {"missing_condition": TASK_NOT_COMPLETED, "tasks": [_named_task(held, completed)]}
        found.rejected.append(_rejection(line, STATE_FORBIDS_OPERATION, params))
        return
    found.planned.append(Planned(line, task, entry, current, role_id, draft.label, fields))


def _judge_hours(session: Session, held: Aimed, reference: Reference, found: Analysis) -> None:
    """Reject, in the order of the file, a labour line that would leave its task without an hour.

    The roles a task keeps are those of its lines the import leaves as they are, then those of the
    lines accepted before; a line rejected keeps its task and its role.
    """
    moving = {each.current.node_id for each in found.planned if each.current is not None}
    moving |= {node for node in found.left if not _started(held, node)}
    kept: dict[UUID, set[UUID]] = {}
    for line in held.lines.values():
        role = line.resource_role_id
        if line.node_id not in moving and role is not None:
            kept.setdefault(held.bearers[line.node_id], set()).add(role)
    employed = {role for roles in kept.values() for role in roles}
    employed |= {each.role_id for each in found.planned if each.role_id is not None}
    calendars = role_calendars(session, employed)
    weeks = calendar_hours(session, calendars.values())
    accepted: list[Planned] = []
    for each in found.planned:
        roles = kept.setdefault(each.task_id, set())
        if each.role_id is None or _works({*roles, each.role_id}, calendars, weeks):
            if each.role_id is not None:
                roles.add(each.role_id)
            accepted.append(each)
            continue
        named = [_named_role(reference, role) for role in sorted({*roles, each.role_id})]
        task = _named_task(held, each.task_id)
        params = {"resource_roles": named, "tasks": [task]}
        found.rejected.append(_rejection(each.line, TASK_WITHOUT_WORKING_HOURS, params))
        if each.current is not None and each.current.resource_role_id is not None:
            kept.setdefault(held.bearers[each.current.node_id], set()).add(
                each.current.resource_role_id
            )
    found.planned = accepted


def _started(held: Aimed, node: UUID) -> bool:
    """Tell whether the task that bears a line of the structure is started or completed."""
    return held.tasks[held.bearers[node]].progress != NOT_STARTED


def _works(
    roles: set[UUID], calendars: Mapping[UUID, UUID], weeks: Mapping[UUID, tuple[Decimal, ...]]
) -> bool:
    """Tell whether the calendars of the roles share an hour on a day of the week."""
    days = [weeks[calendars[role]] for role in roles]
    return any(min(day) > 0 for day in zip(*days, strict=True))


def _named_role(reference: Reference, role_id: UUID) -> dict[str, str]:
    role = reference.roles_by_id[role_id]
    return {"resource_role_id": str(role_id), "code": role.code, "label": role.label}


def _lineage(text: str | None) -> UUID | None:
    if text is None:
        return None
    try:
        return UUID(text)
    except ValueError:
        return None


def _reader_rejection(rejection: reader.Rejection) -> dict[str, Any]:
    return {
        "sheet": rejection.sheet,
        "row": rejection.row,
        "code": rejection.code,
        "params": dict(rejection.params),
    }


def report_of(held: Aimed, read: WorkbookRead, found: Analysis) -> Report:
    """Give the report of an analysis, as the contract reads it (``ImportReport``).

    The rejections in the order of the workbook, tab by tab and row by row; the lines added and
    updated in the order of the file, then those it removes or keeps in the order of the structure.
    """
    rows = [(line.sheet, line.row) for line in read.lines]
    rows += [(each.sheet, each.row) for each in read.rejected]
    tabs = {sheet: rank for rank, sheet in enumerate(dict.fromkeys(sheet for sheet, _ in rows))}
    rejected = sorted(found.rejected, key=lambda each: (tabs.get(each["sheet"], 0), each["row"]))
    lineages = {row.node_id: lineage for lineage, row in held.lines.items()}
    differences: list[dict[str, Any]] = []
    for each in found.planned:
        if each.current is None:
            differences.append(_difference("added", None, each.label))
        elif each.fields:
            lineage = lineages[each.current.node_id]
            differences.append(_difference("updated", lineage, each.label, each.fields))
    for node in found.left:
        change = "kept" if _started(held, node) else "removed"
        differences.append(_difference(change, lineages[node], held.lines[lineages[node]].label))
    rejected_rows = {(each["sheet"], each["row"]) for each in rejected}
    written = sum(1 for each in found.planned if each.current is None or each.fields)
    read_count = len(set(rows))
    return {
        "format_version": str(FORMAT_VERSION),
        "read_count": read_count,
        "unchanged_count": read_count - len(rejected_rows) - written,
        "rejected": rejected,
        "refusals": [],
        "differences": differences,
        "ignored": [],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": [],
    }


def _difference(
    change: str, lineage: UUID | None, label: str, fields: tuple[str, ...] = ()
) -> dict[str, Any]:
    return {
        "change": change,
        "target": LINE,
        "lineage_id": None if lineage is None else str(lineage),
        "label": label,
        "fields": list(fields),
    }
