# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The paste of a block of cells into the planning: its plan previewed, then applied.

``previewPaste`` judges each cell of the block on the facet task in the order of ``NodeColumn``, by
the very functions of the entry of a cell (``judge_cell``), and keeps the plan with the counter of
the structure (``history.keep_plan``); ``applyPaste`` reads the plan again, refuses a structure that
moved (412), judges again and writes the rows accepted in one operation and one entry of the history
(EP-06, "L'historique annulable et le collage").

The block fills, from the targeted column, the columns of the facet task — ``label`` to
``work_breakdown`` —, each row writing the node at the same distance below the targeted one, in the
order of the plan; a row falling past the last node creates one (below). An empty cell writes
nothing. A cell is refused by its reason, named by its row and its column: a computed value
(``COMPUTED_VALUE``), a column that no write carries — the dates of start and completion, which
only the Kanban writes, and the predecessors, which ``setPredecessors`` writes
(``FIELD_NOT_ACCEPTED``) —, a value that is no number, no date, no mode, no element of the work
breakdown, and what the entry of a cell refuses (a non-working day, a summary's dates, an
attachment already borne). A row one of whose cells is refused is refused whole.

A row of the block past the last node of the structure, in the order of the plan, creates a node
(#2559) of the kind of the node the block is aimed at: a sibling of that last node — the anchor,
whether its own row is written or refused —, under the same parent, ranked after it in the order
of the block. A task is created by the function of the creation of ``createNode``
(``judge_creation``), which refuses a parent that is a milestone (``MILESTONE_HAS_NO_SUBTASK``, the
milestone named, #1772). Its label is required (``VALIDATION_FAILED`` on ``label``). Its other cells
take first the values of a creation — an automatic task of a day, without predecessor
(WF-DEV-0050) —, then are judged on it as those of a task written. The plan keeps for each row
whether it creates, and the node it creates; the confirmation creates them in its one write, and
its entry of the history has none of them before: undone, they are deleted, redone, created again,
as those of ``createNode``.

The columns of a line of another kind than the task — the estimate line's, EP-07 — follow the
label in the order of ``NodeColumn``: the hooks of its kind judge its cells (``judge_cell``) by the
very functions of the entry of a cell, and write them (``write_cell``), or create the line
(``write_line_node``, the hook ``create``). A cell on a column the node does not bear is refused
(``FIELD_NOT_ACCEPTED``); on the main structure, every non-empty cell of a line of a completed
task is refused (``STATE_FORBIDS_OPERATION``, ``task_not_completed``, #1767), a line created under
one too. A row for a line is judged on the base and on the rows accepted before it under the same
task: the entries of those rows are handed to the hook (``CellsPasted.earlier``), so that the
preview and the confirmation reach the same verdict.

A paste is asked for by whoever may write one at least of the three grids (#2601), but the columns
of a task's own are the planning's (#2775): a block one of whose rows writes a cell of a task — any
column of ``TASK_COLUMNS``, the label included —, or creates a task with another cell than its
label, as ``createNode`` does from the three grids, is refused whole to whoever does not hold
``planning.write``, by 403 ``PERMISSION_MISSING`` naming it, at its preview before any row is
judged, and again at its confirmation; nothing is kept nor written then. The columns of the
execution of a task — its physical progress and the days it started and completed on, the
Kanban's ``setTaskProgress`` writes them — are the remaining to commit's (#2805, EP-09): they ask
for ``remaining.write`` instead, and a block that writes both kinds asks for both, the planning's
named first when neither is held.

Declared by US-1380/L1; filled by US-1450/L2, L5; the lines by US-1560/L1; the permission of the
columns of a task by US-1570/L7.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sqlalchemy import inspect

from waterfall.core.history.interface import PlanToKeep, drop_plan, keep_plan, read_plan
from waterfall.core.planning.carrying import (
    STATE_FORBIDS_OPERATION,
    TASK_NOT_COMPLETED,
    bearing,
)
from waterfall.core.planning.entries import (
    ONE_DAY,
    PERMISSION_MISSING,
    PLANNING_WRITE,
    REMAINING_WRITE,
)
from waterfall.core.planning.interface.facets import CellsPasted, FacetWrite, facets
from waterfall.core.planning.interface.lines import (
    judge_line_creation,
    new_line_node,
    write_line_node,
)
from waterfall.core.planning.interface.nodes import (
    Ground,
    InstantSent,
    NodeCreation,
    TaskEntry,
    apply_cell,
    judge_cell,
    judge_creation,
    traced,
    traced_creation,
    write_cell,
    write_creation,
)
from waterfall.core.planning.scheduling import Duration
from waterfall.core.planning.shaping import stamp
from waterfall.core.planning.tables import DURATION_UNITS, Node
from waterfall.core.planning.tree import LINE, TASK, Tree, read_tree
from waterfall.core.planning.views import COMPLETED, state_of
from waterfall.core.planning.writing import NodesWritten, facts_of, judge_revision, writing
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    FieldError,
    ForbiddenError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue, KeptPlan, NodeColumn
    from waterfall.core.planning.attachments import Attached
    from waterfall.core.planning.entries import Facet
    from waterfall.core.planning.interface.facets import CellsJudged
    from waterfall.core.planning.interface.lines import LineJudged
    from waterfall.core.planning.interface.nodes import CreationJudged
    from waterfall.core.planning.writing import Place, Write, Writer
    from waterfall.core.projects.interface import WorkBreakdownItem
    from waterfall.platform.audit import Act

COMPUTED_VALUE = "COMPUTED_VALUE"
FIELD_NOT_ACCEPTED = "FIELD_NOT_ACCEPTED"
PASTE_TOO_WIDE = "PASTE_TOO_WIDE"
NUMBER_INVALID = "NUMBER_INVALID"
DATE_INVALID = "DATE_INVALID"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
UNKNOWN_WORK_BREAKDOWN_ITEM = "UNKNOWN_WORK_BREAKDOWN_ITEM"
LABEL_LENGTH = 300
# The columns of the facet task, in the order of ``NodeColumn``: the others are the estimate line's.
TASK_COLUMNS: tuple[NodeColumn, ...] = (
    "label",
    "description",
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "physical_progress",
    "total_float",
    "is_critical",
    "started_on",
    "completed_on",
    "predecessors",
    "work_breakdown",
)
# The columns of a task that its execution writes, which ``setTaskProgress`` writes under
# ``remaining.write`` (EP-09): the others of ``TASK_COLUMNS`` are the planning's.
EXECUTION_COLUMNS: frozenset[str] = frozenset(("physical_progress", "started_on", "completed_on"))
# The columns of the estimate line, after its label, in the order of ``NodeColumn`` (EP-07).
LINE_COLUMNS: tuple[NodeColumn, ...] = (
    "cost_category",
    "resource_role",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject",
    "payment_delay_days",
    "consumption_year",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)
# The columns a block aimed at a node of a kind fills, by kind; the order of the refusals.
COLUMNS_OF: dict[str, tuple[NodeColumn, ...]] = {
    TASK: TASK_COLUMNS,
    LINE: ("label", *LINE_COLUMNS),
}
ALL_COLUMNS: tuple[NodeColumn, ...] = (*TASK_COLUMNS, *LINE_COLUMNS)
# The columns the server computes for a task; those that no write of the facet carries.
COMPUTED = frozenset({"physical_progress", "total_float", "is_critical"})
NOT_CARRIED = frozenset({"started_on", "completed_on", "predecessors"})
MODES = ("automatic", "manual")
# The column that holds the property of the entry a pointer of a refusal designates.
COLUMN_OF: dict[str, NodeColumn] = {
    "label": "label",
    "description": "description",
    "scheduling_mode": "scheduling_mode",
    "duration": "duration",
    "start": "start",
    "finish": "finish",
    "work_package_id": "work_breakdown",
    "order_item_id": "work_breakdown",
}
DURATION = re.compile(r"(\d+(?:[.,]\d+)?)\s*([a-z]+)?")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True, slots=True)
class PasteBlock:
    """A block pasted: the node and the column it starts from, the cells of its rows."""

    target_node_id: UUID
    target_column: NodeColumn
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class PasteRefusal:
    """The refusal of a cell of the block, or of its whole row (``column`` none), and its reason."""

    row: int
    column: NodeColumn | None
    code: str
    params: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PastePlanned:
    """What a paste will write and refuse (``PastePlan``): the plan kept under ``paste_id``.

    ``created`` counts the rows accepted that create a task, counted in ``accepted`` too.
    """

    paste_id: UUID
    accepted: int
    created: int
    rejected: tuple[PasteRefusal, ...]


@dataclass(frozen=True, slots=True)
class PasteConfirmation:
    """The confirmation of a plan, at the counter of the structure its sender read."""

    paste_id: UUID
    lock_version: int


@dataclass(frozen=True, slots=True)
class PasteApplied:
    """What a confirmation wrote (``NodesWritten``) and the refusals it repeats or adds."""

    written: NodesWritten
    rejected: tuple[PasteRefusal, ...]


@dataclass(frozen=True, slots=True)
class _Row:
    """A row of the block that writes something: its place in the block, its node, its cells.

    ``creates`` tells that the row falls past the last node, and creates its node, ``node_id``.
    """

    row: int
    node_id: UUID
    cells: tuple[tuple[NodeColumn, str], ...]
    creates: bool = False


@dataclass(frozen=True, slots=True)
class _Fault:
    """Why a cell is refused, before the entry of a cell judges what it sends."""

    code: str
    params: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class _Outcome:
    """A row judged: what it sends and how the entry of a cell judged it, or why it is refused.

    ``creation`` is the task the row creates, as judged, for a row past the last node; ``cells``
    what the hooks of a line judged of the row, ``placed`` the line it creates and where.
    """

    entry: TaskEntry | None
    judged: tuple[Facet, Attached] | None
    refusals: tuple[PasteRefusal, ...]
    creation: CreationJudged | None = None
    cells: CellsJudged | None = None
    placed: LineJudged | None = None


@dataclass(slots=True)
class _Board:
    """What the rows of a block are judged on, one after the other.

    The ground the rows accepted before leave (``traced``), the elements of the work breakdown by
    label, the structure, act and planning start a task is created at, and the node a row past the
    last node is created after: the anchor, then the task the row before created; and the node the
    block is aimed at, whose kind is the kind of what the block creates.
    """

    ground: Ground
    items: Mapping[str, list[WorkBreakdownItem]]
    held: tuple[Place, Act, date]
    after: UUID
    target: UUID
    lines: dict[UUID, dict[UUID, object]] = field(default_factory=dict[UUID, dict[UUID, object]])


class _NothingToWriteError(Exception):
    """The rows judged again leave none to write; carries the refusals to give."""

    def __init__(self, refusals: list[PasteRefusal]) -> None:
        super().__init__()
        self.refusals = refusals


def _author(writer: Writer) -> UUID:
    """Give the account that pastes: a paste is kept for its account, never for the platform."""
    if writer.act.author is None:
        msg = "a paste is the act of an account"
        raise RuntimeError(msg)
    return writer.act.author


def _duration(text: str, unit: str) -> Duration | _Fault:
    """Read a duration: a number, then its unit if it names one, the task's own by default."""
    found = DURATION.fullmatch(text)
    if found is None:
        return _Fault(NUMBER_INVALID, {})
    named = found.group(2) or unit
    if named not in DURATION_UNITS:
        return _Fault(VALIDATION_FAILED, {})
    return Duration(Decimal(found.group(1).replace(",", ".")), named)


def _day(text: str) -> InstantSent | _Fault:
    """Read a day written ``YYYY-MM-DD``; the hours are the calendar's to complete."""
    if DAY.fullmatch(text) is not None:
        try:
            return InstantSent(date.fromisoformat(text))
        except ValueError:
            pass
    return _Fault(DATE_INVALID, {})


def _plain(column: NodeColumn, text: str) -> dict[str, Any] | _Fault | None:
    """Read the cell of a column of text: the label, the description, the mode; none for another."""
    if column == "label":
        if len(text) > LABEL_LENGTH:
            return _Fault(VALUE_TOO_LONG, {"max_length": LABEL_LENGTH})
        return {"label": text}
    if column == "description":
        return {"description": text}
    if column == "scheduling_mode":
        if text.lower() not in MODES:
            return _Fault(VALIDATION_FAILED, {})
        return {"scheduling_mode": text.lower()}
    return None


def _read(
    column: NodeColumn, text: str, unit: str, items: Mapping[str, list[WorkBreakdownItem]]
) -> dict[str, Any] | _Fault:
    """Read the cell of a column into what the entry of a cell sends, or say why it is refused."""
    if column not in TASK_COLUMNS or column in NOT_CARRIED:
        return _Fault(FIELD_NOT_ACCEPTED, {})
    if column in COMPUTED:
        return _Fault(COMPUTED_VALUE, {})
    plain = _plain(column, text)
    if plain is not None:
        return plain
    if column == "work_breakdown":
        found = items.get(text, [])
        if len(found) != 1:
            return _Fault(UNKNOWN_WORK_BREAKDOWN_ITEM, {})
        return {f"{found[0].kind}_id": found[0].item_id}
    read = _duration(text, unit) if column == "duration" else _day(text)
    return read if isinstance(read, _Fault) else {column: read}


def _items(session: Session, project_id: UUID) -> dict[str, list[WorkBreakdownItem]]:
    """Give the elements of the work breakdown not marked deleted, by label."""
    named: dict[str, list[WorkBreakdownItem]] = {}
    for item in work_breakdown_items(session, project_id).values():
        if not item.deleted:
            named.setdefault(item.label, []).append(item)
    return named


def _entry(sent: dict[str, Any]) -> TaskEntry:
    """Give the entry of a cell that a row sends: what it names, ``sent`` naming it."""
    return TaskEntry(**sent, sent=frozenset(sent))


def _order(refusal: PasteRefusal) -> tuple[int, int]:
    """Order the refusals by the row of the block, then by the column; a whole row first."""
    column = -1 if refusal.column is None else ALL_COLUMNS.index(refusal.column)
    return refusal.row, column


def _mapped(row: int, refused: UnprocessableError) -> list[PasteRefusal]:
    """Give the refusals of the entry of a cell as those of the cells that hold them."""
    if not refused.fields:
        return [PasteRefusal(row, None, refused.code, refused.params)]
    return [
        PasteRefusal(row, COLUMN_OF.get(fault.pointer.split("/")[1]), fault.code, fault.params)
        for fault in refused.fields
    ]


def _cells(
    row: _Row, unit: str, items: Mapping[str, list[WorkBreakdownItem]]
) -> tuple[dict[str, Any], list[PasteRefusal]]:
    """Read each cell of a row: what the row sends, and the refusals of the cells unread."""
    sent: dict[str, Any] = {}
    refusals: list[PasteRefusal] = []
    for column, text in row.cells:
        read = _read(column, text, unit, items)
        if isinstance(read, _Fault):
            refusals.append(PasteRefusal(row.row, column, read.code, read.params))
        else:
            sent.update(read)
    return sent, refusals


def _forbidden(row: _Row) -> list[PasteRefusal]:
    """Refuse every cell of a row on a line of a completed task of the main structure (#1767)."""
    named = {"missing_condition": TASK_NOT_COMPLETED}
    return [
        PasteRefusal(row.row, column, STATE_FORBIDS_OPERATION, named) for column, _ in row.cells
    ]


def _line_cells(
    board: _Board, held: tuple[str, UUID | None, UUID], row: _Row
) -> tuple[CellsJudged | None, list[PasteRefusal]]:
    """Judge the cells of a row on a node of another kind than the task, by the hooks of its kind.

    ``held`` is the kind, the node, none if the row creates it, and the task that bears it. A line
    of a completed task refuses every cell; a cell on a column the kind does not bear is refused;
    the others are judged by ``judge_cell``, every refusal at once, on the entries of the lines of
    the same task that the rows before it were accepted with.
    """
    ground = board.ground
    kind, node_id, parent = held
    hooks = facets().get(kind)
    if hooks is None:
        return None, [PasteRefusal(row.row, None, FIELD_NOT_ACCEPTED, {})]
    if ground.is_main and state_of(ground.tree, parent).progress == COMPLETED:
        return None, _forbidden(row)
    borne = COLUMNS_OF[kind]
    refusals = [
        PasteRefusal(row.row, column, FIELD_NOT_ACCEPTED, {})
        for column, _ in row.cells
        if column not in borne
    ]
    given = tuple((column, text) for column, text in row.cells if column in borne)
    bearer = bearing(ground.session, ground.project_id, ground.tree, parent, is_main=ground.is_main)
    earlier = tuple(board.lines.get(parent, {}).items())
    pasted = CellsPasted(ground.session, ground.project_id, node_id, bearer, given, earlier)
    judged = hooks.judge_cell(pasted)
    refusals += [
        PasteRefusal(row.row, cast("NodeColumn | None", each.column), each.code, each.params)
        for each in judged.refusals
    ]
    return judged, refusals


def _judged_line(board: _Board, row: _Row) -> _Outcome:
    """Judge a row on a node that is no task: a line of the estimate, by the hooks of its kind."""
    node = board.ground.tree.nodes[row.node_id]
    if node.parent_id is None:
        return _Outcome(None, None, (PasteRefusal(row.row, None, FIELD_NOT_ACCEPTED, {}),))
    judged, refusals = _line_cells(board, (node.kind, row.node_id, node.parent_id), row)
    refusals.sort(key=_order)
    if not refusals and judged is not None:
        board.lines.setdefault(node.parent_id, {})[row.node_id] = judged.entry
    return _Outcome(None, None, tuple(refusals), cells=None if refusals else judged)


def _copied(node: Node, **changes: object) -> Node:
    """Give a copy of a node, never added to the session, with columns changed."""
    held = {attr.key: getattr(node, attr.key) for attr in inspect(Node).column_attrs}
    return Node(**held | changes)


def _traced_line(ground: Ground, held: tuple[Place, Act, date], judged: LineJudged) -> Ground:
    """Give a traced ground that holds a line ``judge_line_creation`` judged, nothing written.

    The lines its rank moves down are copies, so that the ground it comes from is left as it was.
    """
    nodes = dict(ground.tree.nodes)
    for each in judged.shifted:
        nodes[each] = _copied(nodes[each], rank=nodes[each].rank + 1)
    nodes[judged.node_id] = new_line_node(held[0], held[1], judged)
    tree = ground.tree.with_nodes(nodes, ground.tree.tasks)
    return Ground(ground.session, ground.project_id, tree, ground.is_main)


def _creating_line(board: _Board, row: _Row, kind: str) -> _Outcome:
    """Judge a row past the last node that creates a line, or a node of another kind than the task.

    A sibling of the anchor, ranked after it (``judge_line_creation``): under the task that bears
    the anchor, which is no task if the anchor stands at the root (``UNKNOWN_TASK``). Its label is
    required (``VALIDATION_FAILED`` on ``label``); its cells are judged by the hooks of its kind,
    every refusal at once. A row refused creates nothing; accepted, its line is traced on the
    board, the next created after.
    """
    tree = board.ground.tree
    creation = NodeCreation(
        parent_id=tree.nodes[board.after].parent_id,
        after_node_id=board.after,
        after_given=True,
        kind=kind,
    )
    refusals: list[PasteRefusal] = []
    judged: CellsJudged | None = None
    placed: LineJudged | None = None
    try:
        placed = judge_line_creation(tree, creation, row.node_id)
    except UnprocessableError as refused:
        refusals += _mapped(row.row, refused)
    if placed is not None:
        judged, refusals = _line_cells(board, (kind, None, placed.parent_id), row)
    if all(column != "label" for column, _ in row.cells):
        refusals.append(PasteRefusal(row.row, "label", VALIDATION_FAILED, {}))
    if refusals or placed is None:
        return _Outcome(None, None, tuple(sorted(refusals, key=_order)))
    board.ground, board.after = _traced_line(board.ground, board.held, placed), row.node_id
    if judged is not None:
        board.lines.setdefault(placed.parent_id, {})[row.node_id] = judged.entry
    return _Outcome(None, None, (), cells=judged, placed=placed)


def _judged(board: _Board, row: _Row) -> _Outcome:
    """Judge a row of the block on its node: each cell read, then what they send by the entry.

    The refusals of every cell are named at once. A node that is no task is judged by the hooks of
    its kind (``_judged_line``).
    """
    ground = board.ground
    task = ground.tree.tasks.get(row.node_id)
    if task is None:
        return _judged_line(board, row)
    sent, refusals = _cells(row, task.duration_unit, board.items)
    entry = _entry(sent) if sent else None
    judged = None
    if entry is not None:
        try:
            judged = judge_cell(ground, row.node_id, entry)
        except UnprocessableError as refused:
            refusals += _mapped(row.row, refused)
    refusals.sort(key=_order)
    return _Outcome(entry, None if refusals else judged, tuple(refusals))


def _creating(board: _Board, row: _Row) -> _Outcome:
    """Judge a row past the last node: the task it creates, then its cells on that task.

    The task is judged by the function of ``createNode`` with the label of the row, required, and
    the values of a creation (WF-DEV-0050); the other cells, then, as those of a task written. A
    row refused creates nothing; accepted, its task is traced on the board, the next created after.
    A row creates a node of the kind of the node the block is aimed at: another kind than the task
    is judged by the hooks of its kind (``_creating_line``).
    """
    kind = board.ground.tree.nodes[board.target].kind
    if kind != TASK:
        return _creating_line(board, row, kind)
    sent, refusals = _cells(row, ONE_DAY.unit, board.items)
    label = sent.pop("label", None)
    if label is None:
        if all(each.column != "label" for each in refusals):
            refusals.append(PasteRefusal(row.row, "label", VALIDATION_FAILED, {}))
        return _Outcome(None, None, tuple(sorted(refusals, key=_order)))
    parent = board.ground.tree.nodes[board.after].parent_id
    creation = NodeCreation(
        parent_id=parent, after_node_id=board.after, after_given=True, task=TaskEntry(label=label)
    )
    try:
        created = judge_creation(board.ground, creation, row.node_id)
    except UnprocessableError as refused:
        refusals += _mapped(row.row, refused)
        return _Outcome(None, None, tuple(sorted(refusals, key=_order)))
    ground = traced_creation(board.ground, board.held, created)
    entry = _entry(sent) if sent else None
    judged = None
    if entry is not None:
        try:
            judged = judge_cell(ground, row.node_id, entry)
        except UnprocessableError as refused:
            refusals += _mapped(row.row, refused)
    if refusals:
        return _Outcome(entry, None, tuple(sorted(refusals, key=_order)))
    if entry is not None and judged is not None:
        apply_cell(ground.tree.tasks[row.node_id], entry, judged)
    board.ground, board.after = ground, row.node_id
    return _Outcome(entry, judged, (), created)


def _settled(board: _Board, row: _Row) -> _Outcome:
    """Judge a row on the board, and trace it there if accepted, for the rows after it.

    The ground is a copy of the tree (``traced``): the preview and the confirmation judge each row
    on what the rows accepted before it leave, so that the one never promises what the other
    refuses (WF-IHM-0050).
    """
    if row.creates:
        return _creating(board, row)
    outcome = _judged(board, row)
    if outcome.entry is not None and outcome.judged is not None:
        apply_cell(board.ground.tree.tasks[row.node_id], outcome.entry, outcome.judged)
    return outcome


def _encoded(rows: list[_Row], rejected: list[PasteRefusal]) -> JsonValue:
    """Give the accepted rows and the refusals of a preview as the plan keeps them in JSON."""
    return {
        "rows": [
            {
                "row": each.row,
                "node_id": str(each.node_id),
                "cells": [[column, text] for column, text in each.cells],
                "creates": each.creates,
            }
            for each in rows
        ],
        "rejected": [
            {"row": each.row, "column": each.column, "code": each.code, "params": dict(each.params)}
            for each in rejected
        ],
    }


def _decoded(kept: JsonValue) -> tuple[list[_Row], list[PasteRefusal]]:
    """Give back the accepted rows and the refusals of a plan kept."""
    held = cast("dict[str, list[dict[str, Any]]]", kept)
    rows = [
        _Row(
            each["row"],
            UUID(each["node_id"]),
            tuple((cast("NodeColumn", column), text) for column, text in each["cells"]),
            creates=bool(each.get("creates", False)),
        )
        for each in held["rows"]
    ]
    rejected = [
        PasteRefusal(each["row"], each["column"], each["code"], each["params"])
        for each in held["rejected"]
    ]
    return rows, rejected


def _row_at(
    tree_order: list[UUID], at: int, index: int, given: tuple[tuple[NodeColumn, str], ...]
) -> _Row:
    """Give the row of the block at a place in the order of the plan; past its end, one creating."""
    if at < len(tree_order):
        return _Row(index, tree_order[at], given)
    return _Row(index, new_id(), given, creates=True)


def _task_columns(tree: Tree, target: UUID, row: _Row) -> set[str]:
    """Give the columns of a task's own that a row writes (#2775).

    A row on a task writes its columns, whichever they are; a row that creates a task, its label
    alone being a creation the three grids make alike (#2601), writes them with any other cell.
    """
    columns = {column for column, _ in row.cells}
    kept: set[str] = set()
    if row.creates and tree.nodes[target].kind == TASK:
        kept = columns - {"label"}
    elif not row.creates and row.node_id in tree.tasks:
        kept = columns & set(TASK_COLUMNS)
    return kept


def _refuse_task_columns(
    tree: Tree, target: UUID, rows: Iterable[_Row], permissions: Collection[str]
) -> None:
    """Refuse a block that writes the columns of a task to whoever may not write them.

    The planning's for the columns of a task's own, the remaining to commit's for those of its
    execution (#2805); whoever holds both writes both, a block that mixes them asks for both.

    The ``REMAINING_WRITE`` branch is defensive: the paste refuses the three columns of the
    execution cell by cell, so no plan kept holds one and the replay at the confirmation never
    asks for it. It stays so that the day the paste writes them, the permission is already asked
    on both paths; no test carries it, a plan holding such a cell being buildable only by hand
    in the database.
    """
    written: set[str] = set()
    for each in rows:
        written |= _task_columns(tree, target, each)
    asked = (
        (PLANNING_WRITE, bool(written - EXECUTION_COLUMNS)),
        (REMAINING_WRITE, bool(written & EXECUTION_COLUMNS)),
    )
    for permission, needed in asked:
        if needed and permission not in permissions:
            raise ForbiddenError(PERMISSION_MISSING, {"missing_permission": permission})


def preview_paste(
    session: Session,
    place: Place,
    block: PasteBlock,
    writer: Writer,
    permissions: Collection[str],
) -> PastePlanned:
    """Judge a block of cells, and keep its plan (``previewPaste``).

    Refused if the structure or the target node is unknown (404), the column is none of the facet's
    (422 ``FIELD_NOT_ACCEPTED`` on ``/target_column``), or the block is wider than the columns from
    the targeted one (422 ``PASTE_TOO_WIDE``, ``max_columns``); nothing is kept then. The counter
    of the structure is read before its tree: a write between the two makes the plan stale, never
    the counter newer than the tree it judged. Each row is judged on the tree the rows accepted
    before it leave — written on a copy, never in the session —, as the confirmation judges it; a
    row past the last node creates a task there, under the identifier the plan keeps for it. A
    block that writes the columns of a task is refused first to whoever does not hold
    ``permissions`` ``planning.write`` — ``remaining.write`` for the columns of its execution
    (403, #2775, #2805).
    """
    facts = facts_of(session, place, lock=False)
    tree = read_tree(session, place.project_id, place.structure_id)
    if block.target_node_id not in tree.nodes:
        raise NotFoundError(NOT_FOUND)
    borne = COLUMNS_OF.get(tree.nodes[block.target_node_id].kind, ())
    if block.target_column not in borne:
        fault = FieldError("/target_column", FIELD_NOT_ACCEPTED)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    columns: tuple[NodeColumn, ...] = borne[borne.index(block.target_column) :]
    if max(map(len, block.rows)) > len(columns):
        raise UnprocessableError(PASTE_TOO_WIDE, {"max_columns": len(columns)})
    ground = traced(Ground(session, place.project_id, tree, facts.is_main))
    held = (place, writer.act, facts.planning_start_on)
    board = _Board(
        ground, _items(session, place.project_id), held, tree.order[-1], block.target_node_id
    )
    start = tree.order.index(block.target_node_id)
    given_rows: list[_Row] = []
    for index, cells in enumerate(block.rows):
        given: tuple[tuple[NodeColumn, str], ...] = tuple(
            (columns[at], text) for at, text in enumerate(cells) if text.strip()
        )
        if given:
            given_rows.append(_row_at(tree.order, start + index, index, given))
    _refuse_task_columns(tree, block.target_node_id, given_rows, permissions)
    accepted: list[_Row] = []
    rejected: list[PasteRefusal] = []
    for row in given_rows:
        outcome = _settled(board, row)
        if outcome.refusals:
            rejected += outcome.refusals
        else:
            accepted.append(row)
    plan = PlanToKeep(
        project_id=place.project_id,
        revision_id=facts.revision_id,
        structure_id=place.structure_id,
        user_account_id=_author(writer),
        target_node_id=block.target_node_id,
        target_column=block.target_column,
        rows=_encoded(accepted, rejected),
        structure_lock_version=facts.lock_version,
    )
    kept = keep_plan(session, plan, writer.act.at)
    created = sum(each.creates for each in accepted)
    return PastePlanned(kept.plan_id, len(accepted), created, tuple(rejected))


def _stale(current: int, kept: KeptPlan, confirmation: PasteConfirmation) -> None:
    """Refuse a plan judged on another version of the structure, or confirmed at another (412)."""
    if current != kept.plan.structure_lock_version or current != confirmation.lock_version:
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": current})


def _rejudged(
    board: _Board, rows: list[_Row], refused: list[PasteRefusal]
) -> list[tuple[_Row, _Outcome]]:
    """Judge the rows of a plan again, each on the rows accepted before it; add what is refused.

    Nothing is written: the rows are traced on the board, a copy of the tree.
    """
    accepted: list[tuple[_Row, _Outcome]] = []
    for each in rows:
        outcome = _settled(board, each)
        if outcome.refusals:
            refused += outcome.refusals
        else:
            accepted.append((each, outcome))
    return accepted


def _some(written: list[tuple[_Row, _Outcome]], refused: list[PasteRefusal]) -> None:
    """Stop the write of a paste whose rows, judged again, leave none to write."""
    if not written:
        raise _NothingToWriteError(refused)


def _touched(judged: list[tuple[_Row, _Outcome]]) -> tuple[UUID, ...]:
    """Give the nodes a paste touches: those of its rows, and what each creation moves."""
    return tuple(
        dict.fromkeys(node_id for each, outcome in judged for node_id in _moved(each, outcome))
    )


def _moved(row: _Row, outcome: _Outcome) -> tuple[UUID, ...]:
    """Give the nodes a row touches: its own, and what the creation it makes moves."""
    if outcome.creation is not None:
        return outcome.creation.touched
    if outcome.placed is not None:
        return outcome.placed.touched
    return (row.node_id,)


def _written_line(write: Write, row: _Row, outcome: _Outcome) -> None:
    """Write a row judged again on a line: the line it creates, or its cells on the line."""
    cells = outcome.cells
    if cells is None:
        msg = "a row accepted for a line is judged by the hooks of its kind"
        raise RuntimeError(msg)
    if outcome.placed is not None:
        write_line_node(write, outcome.placed, cells.entry)
        return
    session, place, act = write.session, write.place, write.writer.act
    node = write.tree.nodes[row.node_id]
    if node.parent_id is None:
        msg = "a line has a task that bears it"
        raise RuntimeError(msg)
    is_main = write.facts.is_main
    bearer = bearing(session, place.project_id, write.tree, node.parent_id, is_main=is_main)
    change = FacetWrite(session, place.project_id, place.revision_id, row.node_id, bearer, act)
    facets()[node.kind].write_cell(change, cells.entry)
    stamp(node, act)


def _written(write: Write, ground: Ground, row: _Row, outcome: _Outcome) -> None:
    """Write a row judged again: its cells on its node, or the task it creates, then its cells."""
    entry, judged = outcome.entry, outcome.judged
    if outcome.cells is not None:
        _written_line(write, row, outcome)
    elif outcome.creation is not None:
        task = write_creation(write, outcome.creation)
        if entry is not None and judged is not None:
            apply_cell(task, entry, judged)
    elif entry is not None and judged is not None:
        write_cell(ground, row.node_id, entry, judged, write.writer.act)


def _bearer_of(write: Write, row: _Row, outcome: _Outcome) -> UUID | None:
    """Give the task that bears the line a row writes or creates; none for a row of a task."""
    if outcome.placed is not None:
        return outcome.placed.parent_id
    if outcome.cells is not None:
        return write.tree.nodes[row.node_id].parent_id
    return None


def _blamed(write: Write, first: tuple[_Row, _Outcome]) -> tuple[UUID | None, str]:
    """Name the task a paste beyond the horizon is refused for: its first row, null if created.

    A row of a line names the task that bears it.
    """
    row, outcome = first
    bearer = _bearer_of(write, row, outcome)
    if bearer is not None:
        return bearer, write.tree.tasks[bearer].label
    if outcome.creation is not None:
        task = outcome.creation.creation.task
        return None, "" if task is None else task.label or ""
    return row.node_id, write.tree.tasks[row.node_id].label


def apply_paste(
    session: Session,
    place: Place,
    confirmation: PasteConfirmation,
    writer: Writer,
    permissions: Collection[str],
) -> PasteApplied:
    """Apply the plan of a paste, and give the nodes written (``applyPaste``).

    Judged as a write of the tree: the revision (409), the plan (404 if unknown, of another
    structure or account, abandoned or past its hour), the counter of the structure, the one sent
    and the one the plan was judged on (412), its rows judged again under the lock — a row refused
    now is added to the refusals of the preview, and not written —, the others written, the tasks
    of the rows past the last node created, in one operation, redated once, and one entry of the
    history, ``paste``, which names them all and holds none of those created before it. Without
    any row to write, nothing is written: no entry, the counter as it was. A plan that writes the
    columns of a task is refused, under the lock, to whoever no longer holds ``planning.write``
    among ``permissions`` — ``remaining.write`` for the columns of its execution — (403, #2775,
    #2805); nothing is written then.
    """
    facts = facts_of(session, place, lock=False)
    judge_revision(session, place.project_id, place.revision_id)
    kept = read_plan(
        session, confirmation.paste_id, place.structure_id, _author(writer), writer.act.at
    )
    if kept is None:
        raise NotFoundError(NOT_FOUND)
    rows, refused = _decoded(kept.plan.rows)
    _stale(facts.lock_version, kept, confirmation)
    result: NodesWritten | None = None
    try:
        with writing(session, place, writer, ("paste", ())) as write:
            _stale(write.facts.lock_version, kept, confirmation)
            _refuse_task_columns(write.tree, kept.plan.target_node_id, rows, permissions)
            ground = Ground(session, place.project_id, write.tree, write.facts.is_main)
            held = (place, writer.act, write.facts.planning_start_on)
            items = _items(session, place.project_id)
            board = _Board(
                traced(ground), items, held, write.tree.order[-1], kept.plan.target_node_id
            )
            judged = _rejudged(board, rows, refused)
            _some(judged, refused)
            node_ids = tuple(each.node_id for each, _ in judged)
            touched = _touched(judged)
            write.name(node_ids)
            write.before(touched)
            for each, outcome in judged:
                _written(write, ground, each, outcome)
            bearers = tuple(
                dict.fromkeys(
                    bearer
                    for each, outcome in judged
                    if (bearer := _bearer_of(write, each, outcome)) is not None
                )
            )
            redated = write.redate(_blamed(write, judged[0]), None, bearers)
            write.after(touched)
            result = redated.written(list(node_ids))
    except _NothingToWriteError as nothing:
        refused = nothing.refusals
    if result is None:
        count = len(read_tree(session, place.project_id, place.structure_id).tasks)
        result = NodesWritten((), (), (), count, facts.lock_version)
    drop_plan(session, kept.plan_id)
    return PasteApplied(result, tuple(sorted(refused, key=_order)))
