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

A row of the block past the last node of the structure, in the order of the plan, creates a task
(#2559): a sibling of that last node — the anchor, whether its own row is written or refused —,
under the same parent, ranked after it in the order of the block, by the function of the creation
of ``createNode`` (``judge_creation``), which refuses a parent that is a milestone
(``MILESTONE_HAS_NO_SUBTASK``, the milestone named, #1772). Its label is required
(``VALIDATION_FAILED`` on ``label``); a block aimed at a node that is no task (an estimate line,
EP-07) creates none, its rows past the last node refused whole as its other rows
(``FIELD_NOT_ACCEPTED``). Its other cells take first the values of a creation — an automatic task
of a day, without predecessor (WF-DEV-0050) —, then are judged on it as those of a task written.
The plan keeps for each row whether it creates, and the node it creates; the confirmation creates
them in its one write, and its entry of the history has none of them before: undone, they are
deleted, redone, created again, as those of ``createNode``.

Declared by US-1380/L1; filled by US-1450/L2, L5.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from waterfall.core.history.interface import PlanToKeep, drop_plan, keep_plan, read_plan
from waterfall.core.planning.entries import ONE_DAY
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
from waterfall.core.planning.tables import DURATION_UNITS
from waterfall.core.planning.tree import read_tree
from waterfall.core.planning.writing import NodesWritten, facts_of, judge_revision, writing
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.platform.errors import (
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue, KeptPlan, NodeColumn
    from waterfall.core.planning.attachments import Attached
    from waterfall.core.planning.entries import Facet
    from waterfall.core.planning.interface.nodes import CreationJudged
    from waterfall.core.planning.writing import Place, Write, Writer
    from waterfall.core.projects.interface import WorkBreakdownItem
    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
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

    ``creation`` is the task the row creates, as judged, for a row past the last node.
    """

    entry: TaskEntry | None
    judged: tuple[Facet, Attached] | None
    refusals: tuple[PasteRefusal, ...]
    creation: CreationJudged | None = None


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
    if column in COMPUTED:
        return _Fault(COMPUTED_VALUE, {})
    if column in NOT_CARRIED:
        return _Fault(FIELD_NOT_ACCEPTED, {})
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
    column = -1 if refusal.column is None else TASK_COLUMNS.index(refusal.column)
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


def _judged(ground: Ground, items: Mapping[str, list[WorkBreakdownItem]], row: _Row) -> _Outcome:
    """Judge a row of the block on its node: each cell read, then what they send by the entry.

    The refusals of every cell are named at once. A node that is no task is refused whole: its
    facet is the estimate line's (EP-07).
    """
    task = ground.tree.tasks.get(row.node_id)
    if task is None:
        return _Outcome(None, None, (PasteRefusal(row.row, None, FIELD_NOT_ACCEPTED, {}),))
    sent, refusals = _cells(row, task.duration_unit, items)
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
    A row creates a node of the kind of the node the block is aimed at: this service creates tasks
    only (the estimate line's is EP-07's, US-1560), so a block aimed at another kind creates none,
    its row refused as every row of such a block is (``_judged``).
    """
    if board.target not in board.ground.tree.tasks:
        return _Outcome(None, None, (PasteRefusal(row.row, None, FIELD_NOT_ACCEPTED, {}),))
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
    outcome = _judged(board.ground, board.items, row)
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


def preview_paste(
    session: Session, place: Place, block: PasteBlock, writer: Writer
) -> PastePlanned:
    """Judge a block of cells, and keep its plan (``previewPaste``).

    Refused if the structure or the target node is unknown (404), the column is none of the facet's
    (422 ``FIELD_NOT_ACCEPTED`` on ``/target_column``), or the block is wider than the columns from
    the targeted one (422 ``PASTE_TOO_WIDE``, ``max_columns``); nothing is kept then. The counter
    of the structure is read before its tree: a write between the two makes the plan stale, never
    the counter newer than the tree it judged. Each row is judged on the tree the rows accepted
    before it leave — written on a copy, never in the session —, as the confirmation judges it; a
    row past the last node creates a task there, under the identifier the plan keeps for it.
    """
    facts = facts_of(session, place, lock=False)
    tree = read_tree(session, place.project_id, place.structure_id)
    if block.target_node_id not in tree.nodes:
        raise NotFoundError(NOT_FOUND)
    if block.target_column not in TASK_COLUMNS:
        fault = FieldError("/target_column", FIELD_NOT_ACCEPTED)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    columns: tuple[NodeColumn, ...] = TASK_COLUMNS[TASK_COLUMNS.index(block.target_column) :]
    if max(map(len, block.rows)) > len(columns):
        raise UnprocessableError(PASTE_TOO_WIDE, {"max_columns": len(columns)})
    ground = traced(Ground(session, place.project_id, tree, facts.is_main))
    held = (place, writer.act, facts.planning_start_on)
    board = _Board(
        ground, _items(session, place.project_id), held, tree.order[-1], block.target_node_id
    )
    start = tree.order.index(block.target_node_id)
    accepted: list[_Row] = []
    rejected: list[PasteRefusal] = []
    for index, cells in enumerate(block.rows):
        given: tuple[tuple[NodeColumn, str], ...] = tuple(
            (columns[at], text) for at, text in enumerate(cells) if text.strip()
        )
        if not given:
            continue
        row = _row_at(tree.order, start + index, index, given)
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
        dict.fromkeys(
            node_id
            for each, outcome in judged
            for node_id in (
                (each.node_id,) if outcome.creation is None else outcome.creation.touched
            )
        )
    )


def _written(write: Write, ground: Ground, row: _Row, outcome: _Outcome) -> None:
    """Write a row judged again: its cells on its node, or the task it creates, then its cells."""
    entry, judged = outcome.entry, outcome.judged
    if outcome.creation is not None:
        task = write_creation(write, outcome.creation)
        if entry is not None and judged is not None:
            apply_cell(task, entry, judged)
    elif entry is not None and judged is not None:
        write_cell(ground, row.node_id, entry, judged, write.writer.act)


def _blamed(write: Write, first: tuple[_Row, _Outcome]) -> tuple[UUID | None, str]:
    """Name the task a paste beyond the horizon is refused for: its first row, null if created."""
    row, outcome = first
    if outcome.creation is not None:
        task = outcome.creation.creation.task
        return None, "" if task is None else task.label or ""
    return row.node_id, write.tree.tasks[row.node_id].label


def apply_paste(
    session: Session, place: Place, confirmation: PasteConfirmation, writer: Writer
) -> PasteApplied:
    """Apply the plan of a paste, and give the nodes written (``applyPaste``).

    Judged as a write of the tree: the revision (409), the plan (404 if unknown, of another
    structure or account, abandoned or past its hour), the counter of the structure, the one sent
    and the one the plan was judged on (412), its rows judged again under the lock — a row refused
    now is added to the refusals of the preview, and not written —, the others written, the tasks
    of the rows past the last node created, in one operation, redated once, and one entry of the
    history, ``paste``, which names them all and holds none of those created before it. Without
    any row to write, nothing is written: no entry, the counter as it was.
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
            redated = write.redate(_blamed(write, judged[0]))
            write.after(touched)
            result = redated.written(list(node_ids))
    except _NothingToWriteError as nothing:
        refused = nothing.refusals
    if result is None:
        count = len(read_tree(session, place.project_id, place.structure_id).tasks)
        result = NodesWritten((), (), (), count, facts.lock_version)
    drop_plan(session, kept.plan_id)
    return PasteApplied(result, tuple(sorted(refused, key=_order)))
