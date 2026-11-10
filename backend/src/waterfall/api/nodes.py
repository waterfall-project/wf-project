# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the tasks of a structure (WF-PLA-0040, 0050, 0070, 0150, 0170).

``listNodes``, ``createNode``, ``updateTaskFacet``, ``getComputedValueDependencies`` and
``resolveRowNumber`` (US-1380/L2); ``deleteNode`` and ``moveNodes`` (US-1380/L3); the lines of
estimate in them, their facet, their filters, their sort, their totals and the amounts of the tasks
(US-1490/L3), which the planning reads by the hooks of the facet the estimate registers.

A structure is read by whoever may consult the planning of its project; its tasks are written by
the contributors of the project who may write the planning (``StructureCommand.edit_planning``).
A node is created, deleted and moved alike from the three grids, by a contributor who may write
one at least of the planning, the estimate and the remaining to commit, as ``StructureCommand``
says (#2601).
The parameters of a reading are judged here, every bound at once (``NUMBER_INVALID``,
``DATE_INVALID``, ``VALUE_OUT_OF_RANGE``, WF-IHM-0130), those of the line too, which retain lines
(``LineFilters``); ``fields`` names what is returned of each node, an unknown property refused
(``FIELD_NOT_ACCEPTED``). A line is created from ``EstimateLineWrite``, refused without it.
"""

import re
from dataclasses import replace
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import BaseModel, Field

from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import Text
from waterfall.api.contract.models import (
    ComputedValueDependencies,
    ComputedValueField,
    EstimateLineFacet,
    EstimateLineUpdate,
    EstimateLineWrite,
    Node,
    NodeColumn,
    NodeCreate,
    NodeKind,
    NodeListMeta,
    NodeMove,
    RowNumberResolution,
    SchedulingMode,
    SortOrder,
    TaskFacet,
    TaskFacetUpdate,
    TaskFacetWrite,
    TaskProgress,
    WorkInstantWrite,
)
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.queries import read_list, refuse_query
from waterfall.core.estimate.interface import LineEntry, LineFilters, LineView
from waterfall.core.planning.interface import (
    Amounts,
    ConflictView,
    Duration,
    InstantSent,
    LineSort,
    NodeCreation,
    NodeFilters,
    NodeMoving,
    NodesWritten,
    NodeView,
    Place,
    StructureTotals,
    TaskEntry,
    TaskView,
    Writer,
    computed_value_dependencies,
    create_node,
    delete_node,
    list_nodes,
    move_nodes,
    resolve_row_number,
    update_task_facet,
)
from waterfall.core.planning.interface import WorkInstant as Instant
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError, UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable

router = APIRouter(tags=["revisions"])

CONSULT = "planning.read"
CHANGE = "planning.write"
# The permissions of the three grids, one of which a write they make alike asks for (#2601), in the
# order of ``StructureCommand``: the first named when the caller holds none.
ENTRIES = ("planning.write", "estimate.write", "remaining.write")
STRUCTURE = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}"
VALIDATION_FAILED = "VALIDATION_FAILED"
NUMBER_INVALID = "NUMBER_INVALID"
DATE_INVALID = "DATE_INVALID"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
VALUE_REQUIRED = "VALUE_REQUIRED"
FIELD_NOT_ACCEPTED = "FIELD_NOT_ACCEPTED"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
CENT = Decimal("0.01")
UNASSIGNED = "unassigned"
# The forms of a bound of the query: a decimal, an amount, a whole number, a date (README).
DECIMAL = re.compile(r"-?\d+(\.\d+)?")
MONEY = re.compile(r"-?\d+(\.\d{1,2})?")
WHOLE = re.compile(r"\d+")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
# The columns of numbers filtered by two bounds, by the form of their bound; the first three
# retain tasks, the others lines (EP-07).
DECIMAL_BOUNDS = (
    "duration",
    "physical_progress",
    "total_float",
    "quantity",
    "hours",
    "previous_quantity",
    "previous_hours",
)
MONEY_BOUNDS = (
    "unit_disbursement",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)
WHOLE_BOUNDS = ("payment_delay_days", "consumption_year")
PERIODS = ("start", "finish", "started_on", "completed_on")
# The properties ``fields`` may name: of a node, then of each facet, ``<facet>.<property>``.
FACETS = {"task": TaskFacet, "estimate_line": EstimateLineFacet}
# What every node returns, whatever ``fields`` names.
ALWAYS = ("node_id", "row_number", "level", "lock_version")


class Unassigned(StrEnum):
    """What the filter of the subproject names besides a subproject: none (WF-IND-0020)."""

    unassigned = UNASSIGNED


class NodeQuery(BaseModel):
    """The parameters of ``listNodes`` the service reads typed; the lists and bounds are text."""

    kinds: str | None = None
    search: Annotated[Text | None, Field(min_length=1, max_length=200)] = None
    subtree_of: UUID | None = None
    work_package_id: UUID | None = None
    order_item_id: UUID | None = None
    progress: str | None = None
    is_critical: bool | None = None
    summaries_only: bool | None = None
    max_level: Annotated[int | None, Field(ge=1)] = None
    timeline_id: UUID | None = None
    description: Annotated[Text | None, Field(min_length=1)] = None
    scheduling_mode: str | None = None
    is_milestone: bool | None = None
    finish_overdue: bool | None = None
    is_from_risk: bool | None = None
    origin_risk_ids: str | None = None
    uses_inactive_object: bool | None = None
    subproject_id: Unassigned | UUID | None = None
    cost_type_id: UUID | None = None
    cost_category_id: UUID | None = None
    resource_role_id: UUID | None = None
    sort_by: NodeColumn | None = None
    sort_order: SortOrder | None = None
    fields: str | None = None


def _bound(name: str, text: str | None, form: re.Pattern[str]) -> tuple[Any, list[FieldError]]:
    """Read a bound of the query in its form, a number or a date; its fault, the parameter."""
    if text is None:
        return None, []
    if form is DAY:
        malformed = [FieldError(f"/query/{name}", DATE_INVALID)]
        if form.fullmatch(text) is None:
            return None, malformed
        try:
            return date.fromisoformat(text), []
        except ValueError:
            return None, malformed
    if form.fullmatch(text) is None:
        return None, [FieldError(f"/query/{name}", NUMBER_INVALID)]
    return Decimal(text), []


def _pair(
    query: dict[str, str], column: str, form: re.Pattern[str]
) -> tuple[tuple[Any, Any], list[FieldError]]:
    """Read the two bounds of a column; the upper before the lower refused, the lower named."""
    low_end, high_end = ("from", "to") if form is DAY else ("min", "max")
    low_name, high_name = f"{column}_{low_end}", f"{column}_{high_end}"
    low, low_faults = _bound(low_name, query.get(low_name), form)
    high, high_faults = _bound(high_name, query.get(high_name), form)
    faults = low_faults + high_faults
    if low is not None and high is not None and high < low:
        named = {"minimum": query[low_name]}
        faults.append(FieldError(f"/query/{high_name}", VALUE_OUT_OF_RANGE, named))
    return (low, high), faults


def _known(name: str) -> bool:
    """Tell whether ``fields`` may name a property: of a node, or ``<facet>.<property>``."""
    facet, _, held = name.partition(".")
    if held:
        return facet in FACETS and held in FACETS[facet].model_fields
    return name in Node.model_fields


def node_reading(
    request: Request, query: Annotated[NodeQuery, Query()]
) -> tuple[NodeFilters, frozenset[str] | None]:
    """Read what ``listNodes`` asks: its filters, and the properties it names (``fields``).

    Every fault of a list or a bound is named at once (422); an unknown property of ``fields``
    after them.
    """
    raw = dict(request.query_params)
    faults: list[FieldError] = []
    kinds, wrong = read_list("kinds", query.kinds, NodeKind)
    faults += wrong
    progress, wrong = read_list("progress", query.progress, TaskProgress)
    faults += wrong
    modes, wrong = read_list("scheduling_mode", query.scheduling_mode, SchedulingMode)
    faults += wrong
    risks, wrong = read_list("origin_risk_ids", query.origin_risk_ids, UUID)
    faults += wrong
    bounds: dict[str, tuple[Any, Any]] = {}
    for form, columns in (
        (DECIMAL, DECIMAL_BOUNDS),
        (MONEY, MONEY_BOUNDS),
        (WHOLE, WHOLE_BOUNDS),
        (DAY, PERIODS),
    ):
        for column in columns:
            bounds[column], wrong = _pair(raw, column, form)
            faults += wrong
    refuse_query(faults)
    fields = None if query.fields is None else frozenset(query.fields.split(","))
    if fields is not None and not all(_known(name) for name in fields):
        refuse_query([FieldError("/query/fields", FIELD_NOT_ACCEPTED)])
    filters = NodeFilters(
        kinds=None if kinds is None else tuple(kind.value for kind in kinds),
        search=query.search,
        subtree_of=query.subtree_of,
        work_package_id=query.work_package_id,
        order_item_id=query.order_item_id,
        progress=None if progress is None else tuple(each.value for each in progress),
        is_critical=query.is_critical,
        summaries_only=bool(query.summaries_only),
        max_level=query.max_level,
        timeline_id=query.timeline_id,
        description=query.description,
        scheduling_modes=None if modes is None else tuple(mode.value for mode in modes),
        duration_days=bounds["duration"],
        physical_progress=bounds["physical_progress"],
        total_float=bounds["total_float"],
        start=bounds["start"],
        finish=bounds["finish"],
        started_on=bounds["started_on"],
        completed_on=bounds["completed_on"],
        is_milestone=query.is_milestone,
        finish_overdue=query.finish_overdue,
        is_from_risk=query.is_from_risk,
        origin_risk_ids=risks,
        lines=_line_filters(query, bounds),
        sort=None if query.sort_by is None else LineSort(query.sort_by.value, _descending(query)),
    )
    return filters, fields


def _descending(query: NodeQuery) -> bool:
    """Tell whether the sort asked goes from the greatest to the least."""
    return query.sort_order is not None and query.sort_order.value == "desc"


def _line_filters(query: NodeQuery, bounds: dict[str, tuple[Any, Any]]) -> LineFilters | None:
    """Give what a reading asks of the lines, none when it asks nothing of them."""
    subproject = query.subproject_id
    asked = LineFilters(
        subproject_id=subproject if isinstance(subproject, UUID) else None,
        unassigned=query.subproject_id is Unassigned.unassigned,
        cost_type_id=query.cost_type_id,
        cost_category_id=query.cost_category_id,
        resource_role_id=query.resource_role_id,
        uses_inactive_object=query.uses_inactive_object,
        quantity=bounds["quantity"],
        hours=bounds["hours"],
        unit_disbursement=bounds["unit_disbursement"],
        payment_delay_days=bounds["payment_delay_days"],
        consumption_year=bounds["consumption_year"],
        base_amount=bounds["base_amount"],
        budgeted_amount=bounds["budgeted_amount"],
        reestimated_amount=bounds["reestimated_amount"],
        previous=tuple(
            bounds[name]
            for name in (
                "previous_quantity",
                "previous_hours",
                "previous_unit_disbursement",
                "previous_reestimated_amount",
            )
        ),
    )
    return None if asked == LineFilters(previous=((None, None),) * 4) else asked


def _text(value: Decimal) -> str:
    """Give a decimal as the contract writes it: without exponent nor trailing zeros."""
    return format(value.normalize(), "f")


def _money(value: Decimal) -> str:
    """Give an amount as the contract writes it: to the cent."""
    return format(value.quantize(CENT), "f")


def _instant(instant: Instant) -> dict[str, Any]:
    return {"date": instant.day.isoformat(), "hours": _text(instant.hours)}


def _conflicts(conflicts: tuple[ConflictView, ...]) -> list[dict[str, Any]]:
    return [
        {
            "predecessor_node_id": str(each.predecessor_id),
            "successor_node_id": str(each.successor_id),
            "link_type": each.link_type,
        }
        for each in conflicts
    ]


def _float(value: Decimal | None) -> dict[str, Any] | None:
    return None if value is None else {"value": _text(value), "unit": "d"}


def _id(value: UUID | None) -> str | None:
    return None if value is None else str(value)


def _day(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _task(view: TaskView) -> dict[str, Any]:
    """Write a facet task as the contract does; its amounts, those of its lines and subordinates."""
    # A summary's physical progress follows the budgets of its subtree, none without a line.
    progress = (
        {"is_computable": False, "value": None, "reason": "no_budgeted_amount"}
        if view.is_summary
        else None
    )
    return {
        "label": view.label,
        "description": view.description,
        "scheduling_mode": view.scheduling_mode,
        "duration": {"value": _text(view.duration_value), "unit": view.duration_unit},
        "start": _instant(view.start),
        "finish": _instant(view.finish),
        "progress": view.progress,
        "finish_overdue": view.finish_overdue,
        "awaiting_own_lines": view.awaiting_own_lines,
        "started_on": _day(view.started_on),
        "completed_on": _day(view.completed_on),
        "is_summary": view.is_summary,
        "is_milestone": view.is_milestone,
        "calendar_id": _id(view.calendar_id),
        "calendar_hours": {
            day: _text(hours) for day, hours in zip(DAYS, view.calendar_hours, strict=True)
        },
        "total_float": _float(view.total_float),
        "is_critical": view.is_critical,
        "link_conflicts": _conflicts(view.link_conflicts),
        "physical_progress": progress,
        "base_amount": _money(view.amounts.base),
        "budgeted_amount": _money(view.amounts.budgeted),
        "reestimated_amount": _money(view.amounts.reestimated),
        "tracking": [
            {"kind": entry.kind, "timeline_id": _id(entry.timeline_id)} for entry in view.tracking
        ],
        "order_item_id": _id(view.order_item_id),
        "work_package_id": _id(view.work_package_id),
        "work_breakdown_label": view.work_breakdown_label,
        "external_id": view.external_id,
    }


def _optional(value: Decimal | None, write: Callable[[Decimal], str]) -> str | None:
    return None if value is None else write(value)


def _line(view: LineView) -> dict[str, Any]:
    """Write a facet estimate line as the contract does, its review before and its reason."""
    return {
        "label": view.label,
        "cost_category_id": str(view.cost_category_id),
        "cost_category_label": view.cost_category_label,
        "resource_role_id": _id(view.resource_role_id),
        "resource_role_label": view.resource_role_label,
        "quantity": _text(view.quantity),
        "hours": _optional(view.hours, _text),
        "unit_disbursement": _optional(view.unit_disbursement, _money),
        "payment_delay_days": view.payment_delay_days,
        "subproject_id": _id(view.subproject_id),
        "subproject_label": view.subproject_label,
        "base_amount": _money(view.base_amount),
        "budgeted_amount": _money(view.budgeted_amount),
        "reestimated_amount": _money(view.reestimated_amount),
        "previous_quantity": _optional(view.previous_quantity, _text),
        "previous_hours": _optional(view.previous_hours, _text),
        "previous_unit_disbursement": _optional(view.previous_unit_disbursement, _money),
        "previous_reestimated_amount": _optional(view.previous_reestimated_amount, _money),
        "remaining_reason": view.remaining_reason,
        "consumption_year": view.consumption_year,
        "is_computed": False,
        "uses_inactive_object": view.uses_inactive_object,
        "remaining_entry": {
            "is_available": not view.remaining_missing,
            "missing_conditions": list(view.remaining_missing),
        },
    }


def _facet(view: NodeView) -> dict[str, Any] | None:
    """Write the facet of a node of another kind than the task: an estimate line's."""
    facet = None if view.facet is None else view.facet.view
    return _line(facet) if isinstance(facet, LineView) else None


def node_body(view: NodeView, fields: frozenset[str] | None = None) -> dict[str, Any]:
    """Write a node as the contract does: whole, or what ``fields`` names and the four."""
    whole: dict[str, Any] = {
        "node_id": str(view.node_id),
        "lineage_id": str(view.lineage_id),
        "kind": view.kind,
        "parent_id": _id(view.parent_id),
        "position": view.position,
        "row_number": view.row_number,
        "level": view.level,
        "origin_risk_id": _id(view.origin_risk_id),
        "lock_version": view.lock_version,
        "task": None if view.task is None else _task(view.task),
        "estimate_line": _facet(view),
        "predecessors": [
            {
                "predecessor_node_id": str(each.predecessor_id),
                "predecessor_row_number": each.row_number,
                "link_type": each.link_type,
                "lag": {"value": _text(each.lag_value), "unit": each.lag_unit},
            }
            for each in view.predecessors
        ],
        "computed_fields": list(view.computed_fields),
        "editable_fields": list(view.editable_fields),
    }
    if fields is None:
        return whole
    chosen = {name: whole[name] for name in ALWAYS}
    for name in sorted(fields):
        facet, _, held = name.partition(".")
        if not held:
            if name in whole:
                chosen[name] = whole[name]
        elif isinstance(whole.get(facet), dict) and held in whole[facet]:
            chosen.setdefault(facet, {})[held] = whole[facet][held]
    return chosen


def totals_body(task_count: int, totals: StructureTotals | None) -> dict[str, Any]:
    """Write the totals of the tasks counted and of the lines retained, their hours and amounts."""
    amounts = Amounts() if totals is None else totals.amounts
    return {
        "task_count": task_count,
        "estimate_line_count": 0 if totals is None else totals.line_count,
        "hours": _text(amounts.hours),
        "base_amount": _money(amounts.base),
        "budgeted_amount": _money(amounts.budgeted),
        "reestimated_amount": _money(amounts.reestimated),
    }


def written_of(result: NodesWritten) -> dict[str, Any]:
    """Write what a write of the tree gives back (``NodesWritten``); ``scheduling`` too."""
    return {
        "nodes": [node_body(each) for each in result.nodes],
        "ancestors": [node_body(each) for each in result.ancestors],
        "rescheduled": [
            {
                "node_id": str(each.node_id),
                "start": _instant(each.start),
                "finish": _instant(each.finish),
                "total_float": _float(each.total_float),
                "is_critical": each.is_critical,
                "link_conflicts": _conflicts(each.link_conflicts),
                "finish_overdue": each.finish_overdue,
            }
            for each in result.rescheduled
        ],
        "reinflated": [
            {
                "node_id": str(each.node_id),
                "budgeted_amount": _money(each.budgeted),
                "reestimated_amount": _money(each.reestimated),
                "consumption_year": each.consumption_year,
            }
            for each in result.reinflated
        ],
        "totals": totals_body(result.task_count, result.totals),
        "structure_lock_version": result.structure_lock_version,
    }


def _sent_instant(sent: WorkInstantWrite | None) -> InstantSent | None:
    if sent is None:
        return None
    hours = None if sent.hours is None else Decimal(sent.hours.root.root)
    return InstantSent(sent.date.root, hours)


def _entry(body: TaskFacetWrite | TaskFacetUpdate, sent: frozenset[str] = frozenset()) -> TaskEntry:
    """Read the facet a body sends, its attachment to the work breakdown with it."""
    duration = body.duration
    return TaskEntry(
        label=body.label,
        description=body.description,
        scheduling_mode=None if body.scheduling_mode is None else body.scheduling_mode.value,
        duration=None
        if duration is None
        else Duration(Decimal(duration.value.root), duration.unit.value),
        start=_sent_instant(body.start),
        finish=_sent_instant(body.finish),
        sent=sent,
        work_package_id=None if body.work_package_id is None else body.work_package_id.root,
        order_item_id=None if body.order_item_id is None else body.order_item_id.root,
    )


def _money_of(value: Any) -> Decimal | None:
    """Read an amount, a figure or hours a body sends, none if null."""
    if value is None:
        return None
    root = value
    while hasattr(root, "root"):
        root = root.root
    return Decimal(str(root))


def line_entry(
    body: EstimateLineWrite | EstimateLineUpdate, sent: frozenset[str], lock_version: int | None
) -> LineEntry:
    """Read what a body sends of a line, the fields it holds named, null ones included."""
    delay = body.payment_delay_days
    return LineEntry(
        label=body.label,
        cost_category_id=None if body.cost_category_id is None else body.cost_category_id.root,
        quantity=_money_of(body.quantity),
        resource_role_id=None if body.resource_role_id is None else body.resource_role_id.root,
        hours=_money_of(body.hours),
        unit_disbursement=_money_of(body.unit_disbursement),
        payment_delay_days=None if delay is None else delay.root,
        subproject_id=None if body.subproject_id is None else body.subproject_id.root,
        sent=sent,
        lock_version=lock_version,
    )


async def sent_body(request: Request) -> dict[str, Any]:
    """Give the body a write sends as it is, to name the fields its schema does not know."""
    try:
        body: object = await request.json()
    except ValueError:
        return {}
    return cast("dict[str, Any]", body) if isinstance(body, dict) else {}


def unknown_fields(sent: object, known: type[BaseModel], prefix: str) -> list[FieldError]:
    """Name the fields a body of a line sends that its schema does not know.

    The amounts among them, which no write carries (WF-DEV-0020, WF-IHM-0030).
    """
    held = cast("dict[str, Any]", sent) if isinstance(sent, dict) else {}
    return [
        FieldError(f"{prefix}/{name}", FIELD_NOT_ACCEPTED)
        for name in held
        if name not in known.model_fields
    ]


Sent = Annotated[dict[str, Any], Depends(sent_body)]


def writer_of(actor: Acting, account: Caller) -> Writer:
    """Give who writes, now, and the session of sign-in the history keeps the write by."""
    return Writer(Act(actor.user_id, utc_now()), account.session_id)


def place_of(project_id: UUID, revision_id: UUID, structure_id: UUID) -> Place:
    """Give the structure the path names, of its revision and its project."""
    return Place(project_id, revision_id, structure_id)


Placed = Annotated[Place, Depends(place_of)]
Writing = Annotated[Writer, Depends(writer_of)]


@router.get(
    f"{STRUCTURE}/nodes",
    operation_id="listNodes",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_nodes(
    place: Placed,
    asked: Annotated[tuple[NodeFilters, frozenset[str] | None], Depends(node_reading)],
    session: Transaction,
) -> dict[str, Any]:
    """Give the nodes of a structure retained, depth first, their totals and its meta."""
    filters, fields = asked
    read = list_nodes(session, place, filters)
    meta = NodeListMeta.model_validate(
        {"summary_depth": read.summary_depth, "scheduled_at": read.scheduled_at}
    )
    return {
        "items": [node_body(each, fields) for each in read.items],
        "totals": totals_body(read.task_count, read.totals),
        "meta": meta.model_dump(mode="json"),
    }


@router.post(
    f"{STRUCTURE}/nodes",
    operation_id="createNode",
    dependencies=[Depends(RequiresProject(CONSULT, one_of=ENTRIES))],
    status_code=201,
    response_model=None,
)
def post_node(
    place: Placed,
    body: NodeCreate,
    sent: Sent,
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Create a task or an estimate line of a structure, from the facet of its kind."""
    own, other = (
        ("task", "estimate_line") if body.kind is NodeKind.task else ("estimate_line", "task")
    )
    faults: list[FieldError] = []
    if getattr(body, own) is None:
        faults.append(FieldError(f"/{own}", VALUE_REQUIRED))
    if getattr(body, other) is not None:
        faults.append(FieldError(f"/{other}", FIELD_NOT_ACCEPTED))
    if body.kind is NodeKind.estimate_line:
        faults += unknown_fields(sent.get("estimate_line"), EstimateLineWrite, "/estimate_line")
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    line = body.estimate_line
    creation = NodeCreation(
        parent_id=None if body.parent_id is None else body.parent_id.root,
        after_node_id=None if body.after_node_id is None else body.after_node_id.root,
        after_given="after_node_id" in body.model_fields_set,
        task=None if body.task is None else _entry(body.task),
        kind=body.kind.value,
        facet=None if line is None else line_entry(line, frozenset(line.model_fields_set), None),
    )
    return written_of(create_node(session, place, creation, writer))


@router.patch(
    f"{STRUCTURE}/nodes/{{node_id}}/task",
    operation_id="updateTaskFacet",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def patch_task(
    place: Placed,
    node_id: UUID,
    body: TaskFacetUpdate,
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Write what is sent of the facet of a task, at the counter read; nothing else changes."""
    sent = frozenset(body.model_fields_set - {"lock_version"})
    faults = [
        FieldError(f"/{name}", VALIDATION_FAILED)
        for name in ("label", "scheduling_mode", "duration")
        if name in sent and getattr(body, name) is None
    ]
    # A modification sends one field at least beside its counter (``minProperties``).
    if faults or not sent:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    change = replace(_entry(body, sent), lock_version=body.lock_version.root)
    return written_of(update_task_facet(session, place, node_id, change, writer))


@router.delete(
    f"{STRUCTURE}/nodes/{{node_id}}",
    operation_id="deleteNode",
    dependencies=[Depends(RequiresProject(CONSULT, one_of=ENTRIES))],
    response_model=None,
)
def delete_task(
    place: Placed,
    node_id: UUID,
    lock_version: Annotated[int, Query(ge=0)],
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Delete a node of a structure and its subtree, at the counter of the node read."""
    return written_of(delete_node(session, place, node_id, lock_version, writer))


@router.post(
    f"{STRUCTURE}/nodes/move",
    operation_id="moveNodes",
    dependencies=[Depends(RequiresProject(CONSULT, one_of=ENTRIES))],
    response_model=None,
)
def post_move(
    place: Placed,
    body: NodeMove,
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Move a selection of nodes under a parent, at the counter of the structure read."""
    moving = NodeMoving(
        node_ids=tuple(each.root for each in body.node_ids),
        parent_id=None if body.parent_id is None else body.parent_id.root,
        after_node_id=None if body.after_node_id is None else body.after_node_id.root,
        after_given="after_node_id" in body.model_fields_set,
        lock_version=body.lock_version.root,
    )
    return written_of(move_nodes(session, place, moving, writer))


@router.get(
    f"{STRUCTURE}/nodes/{{node_id}}/dependencies",
    operation_id="getComputedValueDependencies",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=ComputedValueDependencies,
)
def get_dependencies(
    place: Placed,
    node_id: UUID,
    field: Annotated[ComputedValueField, Query()],
    session: Transaction,
) -> ComputedValueDependencies:
    """Name what a computed value of a node depends on, the rows by number and label."""
    found = computed_value_dependencies(session, place, node_id, field.value)
    return ComputedValueDependencies.model_validate(
        {
            "node_id": found.node_id,
            "field": found.field,
            "depends_on": list(found.depends_on),
            "rows": [
                {"node_id": row.node_id, "row_number": row.row_number, "label": row.label}
                for row in found.rows
            ],
        }
    )


@router.get(
    f"{STRUCTURE}/rows/{{row_number}}",
    operation_id="resolveRowNumber",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=RowNumberResolution,
)
def get_row(
    place: Placed,
    row_number: Annotated[int, Path(ge=1)],
    session: Transaction,
) -> RowNumberResolution:
    """Give the node a row number designates in the numbering of the whole structure."""
    found = resolve_row_number(session, place, row_number)
    return RowNumberResolution.model_validate(
        {
            "node_id": found.node_id,
            "row_number": found.row_number,
            "label": found.label,
            "kind": found.kind,
        }
    )
