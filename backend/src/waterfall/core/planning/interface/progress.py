# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The state of a task: not started, started, completed (``setTaskProgress``; EP-06, US-1410).

A leaf is started, completed or reopened by a gesture of the Kanban, at the counter read, on the
day of the gesture by default (WF-PLA-0130, WF-RAE-0030). The first condition the gesture lacks is
named by a 409 ``STATE_FORBIDS_OPERATION``, in the order of the card (``KanbanCommand``):
``task_is_milestone`` (a task not started that is no milestone, completed), ``task_without_lines``
(a task that bears a line besides the provisions, completed: the entry of its remaining to commit
completes it), ``task_not_milestone`` (a milestone, started), ``completed_milestone``
(``not_started``, for a task that is not a completed milestone); then the conditions of
``edit_remaining`` the gesture is an entry of: the phase of the project, ``project_in_progress`` on
the main structure alone, by the rule the commands of a structure state
(``structure_phase_conditions``, #2494), then those of the revision (``revision_draft``,
``no_background_task_running``). A summary is refused by 422 ``SUMMARY_TASK_DERIVED``, naming its
direct subordinates: its state and its dates are derived from theirs at the reading (``Reading``,
WF-PLA-0040), never written. A completion is not dated before the start of its task (422
``VALUE_OUT_OF_RANGE`` on ``/occurred_on``, the start named; WF-PLA-0130, #2495); the day of the
gesture is the current day by default (``current_day``). A milestone completed carries
``started_on`` equal to ``completed_on``; reopened, it loses both, the only task that returns to
not started. ``load_progress`` writes the state of a task of the witness at the instant it
imposes.

A task bearing a line besides the provisions is completed by its remaining to commit instead
(US-1580/L2): ``write_remaining`` frames the re-estimate of a line (``setLineRemaining``), whose
facet the estimate writes, and completes its task when the last of its open lines is set to nought
— none of its lines keeps a remaining, the estimate tells (``RemainingChange.keeps_open``) —, in
the same write, at the date the entry sends (``completed_on``, WF-RAE-0040, WF-PLA-0130). A task
not started is started and completed that day, a milestone too, which never goes through the
started state: both carry ``started_on`` equal to ``completed_on`` (WF-RAE-0030); a task started
keeps its start, which the completion may not precede (422 ``VALUE_OUT_OF_RANGE`` on
``/completed_on``). Without a date, 422 ``COMPLETION_DATE_REQUIRED`` on ``/completed_on``, the task
named, and nothing is written. The state of a summary is derived (WF-PLA-0040): its own lines set
to nought complete nothing here (US-1590). The line is judged before the revision, in the order of
its ``remaining_entry``: ``task_not_completed`` — ``line_not_provision`` is never missing before
EP-08 —, then the phase of the project (``project_in_progress``), then ``revision_draft``,
``project_not_terminal`` and ``no_background_task_running``.
"""

from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from waterfall.core.planning.carrying import bearing
from waterfall.core.planning.interface.facets import FacetWrite
from waterfall.core.planning.shaping import stamp
from waterfall.core.planning.snapshotting import taken
from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.tree import TASK, read_tree
from waterfall.core.planning.views import COMPLETED, NOT_STARTED, STARTED, state_of
from waterfall.core.planning.writing import (
    NodesWritten,
    Place,
    Writer,
    facts_of,
    writing,
)
from waterfall.core.projects.interface import TERMINAL, current_day, project_facts
from waterfall.core.revisions.interface import structure_phase_conditions
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.tree import Tree
    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
SUMMARY_TASK_DERIVED = "SUMMARY_TASK_DERIVED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
TASK_IS_MILESTONE = "task_is_milestone"
TASK_WITHOUT_LINES = "task_without_lines"
TASK_NOT_MILESTONE = "task_not_milestone"
COMPLETED_MILESTONE = "completed_milestone"
TASK_NOT_COMPLETED = "task_not_completed"
COMPLETION_DATE_REQUIRED = "COMPLETION_DATE_REQUIRED"
COMPLETED_ON = "/completed_on"
# The command of a structure a gesture on the state of a task is an entry of (WF-RAE-0040).
EDIT_REMAINING = "edit_remaining"
STATES = (NOT_STARTED, STARTED, COMPLETED)


@dataclass(frozen=True, slots=True)
class ProgressEntry:
    """The state a gesture sends, at the counter read, and the day it happened (today if none)."""

    progress: str
    lock_version: int
    occurred_on: date | None = None


@dataclass(frozen=True, slots=True)
class RemainingChange:
    """A re-estimate of a line: the line, the counter read, what writes it, the date it completes.

    ``apply`` writes the facet of the line, the estimate's (``FacetWrite``); ``keeps_open`` tells,
    of the lines a task bears, in their order, whether one still holds a remaining to commit — a
    line besides the provisions whose re-estimated amount is not nought —, read once the facet is
    written; ``completed_on`` the date of the completion of the task, if the entry completes it.
    """

    node_id: UUID
    lock_version: int
    apply: Callable[[FacetWrite], None]
    keeps_open: Callable[[Session, UUID, Sequence[UUID]], bool]
    completed_on: date | None = None


@dataclass(frozen=True, slots=True)
class ProgressLoad:
    """The state of a task of the witness, and its two dates, as the fixture describes them."""

    node_id: UUID
    progress: str
    started_on: date | None
    completed_on: date | None


def _refuse(missing: str) -> ConflictError:
    """Give the 409 of a gesture, or of an entry of the remaining to commit, naming a condition."""
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": missing})


def _missing_gesture(tree: Tree, node_id: UUID, target: str) -> str | None:
    """Name the first condition a gesture on a leaf lacks, as the card of the Kanban states it."""
    task = tree.tasks[node_id]
    milestone = tree.is_milestone(node_id)
    if target == STARTED:
        return TASK_NOT_MILESTONE if milestone else None
    if target == COMPLETED:
        if task.progress == NOT_STARTED and not milestone:
            return TASK_IS_MILESTONE
        # A provision is written for information (WF-PLA-0050): it holds a task back from nothing.
        if any(tree.nodes[each].origin_risk_id is None for each in tree.lines(node_id)):
            return TASK_WITHOUT_LINES
        return None
    return None if task.progress == COMPLETED and milestone else COMPLETED_MILESTONE


def _judge(
    session: Session, where: tuple[Place, bool], tree: Tree, node_id: UUID, entry: ProgressEntry
) -> None:
    """Refuse a gesture the task, its state or its project forbids; the first reason named.

    The task is no task of the structure (404), the counter read is not its own (412), the task is
    a summary (422), the gesture lacks a condition (409), the project is not in progress while the
    structure is the main one (409, the rule of ``edit_remaining``). ``where`` is the structure
    and whether it is the main one. A terminal project is left to the judgement of its revision
    (``project_not_terminal``).
    """
    place, main = where
    if node_id not in tree.tasks:
        raise NotFoundError(NOT_FOUND)
    node = tree.nodes[node_id]
    if node.lock_version != entry.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version}
        )
    if tree.is_summary(node_id):
        named = [str(each) for each in tree.subtasks(node_id)]
        raise UnprocessableError(SUMMARY_TASK_DERIVED, {"subordinate_node_ids": named})
    missing = _missing_gesture(tree, node_id, entry.progress)
    if missing is not None:
        raise _refuse(missing)
    state = project_facts(session, place.project_id).state
    if state in TERMINAL:
        return
    phase = structure_phase_conditions(EDIT_REMAINING, state, main=main)
    if phase:
        raise _refuse(phase[0])


def _dated(tree: Tree, node_id: UUID, target: str, day: date) -> None:
    """Refuse a completion dated before the start of its task, the start named (WF-PLA-0130).

    A task completed without having been started takes its completion for its start, and one
    completed already is left as it is: only a task started has a start to precede (#2495).
    """
    task = tree.tasks[node_id]
    started = task.started_on
    if target == COMPLETED and task.progress == STARTED and started is not None and day < started:
        fault = FieldError("/occurred_on", VALUE_OUT_OF_RANGE, {"minimum": started.isoformat()})
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))


def _apply(task: Task, *, milestone: bool, target: str, day: date) -> None:
    """Put a leaf in the state a gesture sends, on the day it names.

    Started from not started: the day is its start. Completed: the day is its completion, and its
    start too when it had none — a milestone's always, it never goes through the started state.
    Reopened: a completed milestone loses both dates, any other task loses its completion. A
    gesture that sends the state the task is in changes nothing.
    """
    if task.progress == target:
        return
    if target == STARTED:
        task.started_on = task.started_on if task.progress == COMPLETED else day
        task.completed_on = None
    elif target == COMPLETED:
        task.started_on = day if milestone or task.started_on is None else task.started_on
        task.completed_on = day
    else:
        task.started_on = None
        task.completed_on = None
    task.progress = target


def set_task_progress(
    session: Session, place: Place, node_id: UUID, entry: ProgressEntry, writer: Writer
) -> NodesWritten:
    """Start, complete or reopen a leaf, at the counter read, and give the nodes written.

    Judged under the lock of the structure, the project read under that of the revision. When the
    revision itself refuses the write — marked, or a background task writing in the project —, the
    gesture is judged on the tree as it is first, for it comes before the conditions of the
    revision in the order of the contract: nothing is written either way, the read only chooses
    the condition named. A completion dated before the start is refused then (422). The dates are
    not redone: the engine replays on the structure, which counts the write and moves the date of
    calculation (``finish_overdue``).
    """
    stack = ExitStack()
    try:
        write = stack.enter_context(writing(session, place, writer, ("progress", (node_id,))))
    except ConflictError:
        main = facts_of(session, place, lock=False).is_main
        tree = read_tree(session, place.project_id, place.structure_id)
        if node_id not in tree.tasks:
            raise NotFoundError(NOT_FOUND) from None
        _judge(session, (place, main), tree, node_id, entry)
        raise
    with stack:
        tree = write.tree
        _judge(session, (place, write.facts.is_main), tree, node_id, entry)
        act = writer.act
        day = entry.occurred_on or current_day(act.at)
        _dated(tree, node_id, entry.progress, day)
        write.before((node_id,))
        _apply(
            tree.tasks[node_id],
            milestone=tree.is_milestone(node_id),
            target=entry.progress,
            day=day,
        )
        node = tree.nodes[node_id]
        node.lock_version += 1
        node.updated_at = act.at
        node.updated_by = act.author
        redated = write.redate((node_id, tree.tasks[node_id].label))
        write.after((node_id,))
        return redated.written((node_id,))


def _bearer_of(tree: Tree, node_id: UUID) -> UUID:
    """Give the task that bears a line of the structure; refuse a node that is none (404)."""
    node = tree.nodes.get(node_id)
    if node is None or node_id in tree.tasks or node.parent_id is None:
        raise NotFoundError(NOT_FOUND)
    return node.parent_id


def _judge_entry(session: Session, where: tuple[Place, bool], tree: Tree, task_id: UUID) -> None:
    """Refuse a re-estimate the line, then the phase of its project, forbid; the first named.

    The lines of a completed task of the main structure are not re-estimated
    (``task_not_completed``, WF-RAE-0040); a provision line never is (``line_not_provision``), none
    before EP-08. Then the rule of ``edit_remaining``: the project in progress, on the main
    structure. A terminal project is left to the judgement of its revision
    (``project_not_terminal``).
    """
    place, main = where
    if main and state_of(tree, task_id).progress == COMPLETED:
        raise _refuse(TASK_NOT_COMPLETED)
    state = project_facts(session, place.project_id).state
    if state in TERMINAL:
        return
    phase = structure_phase_conditions(EDIT_REMAINING, state, main=main)
    if phase:
        raise _refuse(phase[0])


def _complete(tree: Tree, task_id: UUID, day: date | None, act: Act) -> None:
    """Complete a leaf whose last open line is set to nought, on the day sent; or refuse (422).

    Not started, it is started and completed that day, a milestone without going through the
    started state (WF-RAE-0030); started, it keeps its start, which the day may not precede.
    """
    if day is None:
        named = {"task_node_id": str(task_id)}
        fault = FieldError(COMPLETED_ON, COMPLETION_DATE_REQUIRED, named)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    task = tree.tasks[task_id]
    started = task.started_on
    if task.progress == STARTED and started is not None and day < started:
        fault = FieldError(COMPLETED_ON, VALUE_OUT_OF_RANGE, {"minimum": started.isoformat()})
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    _apply(task, milestone=tree.is_milestone(task_id), target=COMPLETED, day=day)
    stamp(tree.nodes[task_id], act)


def write_remaining(
    session: Session, place: Place, change: RemainingChange, writer: Writer
) -> NodesWritten:
    """Re-estimate a line at the counter read, and complete its task by it; the nodes written.

    The completion of a task by its remaining to commit (``setLineRemaining``, US-1580/L2), which
    the estimate calls with what writes the facet of the line. Under the lock of the structure: the
    line is no line of the structure (404), the counter read is not its own (412), then its entry
    lacks a condition (409, ``_judge_entry``). The facet is written, refusing what it does not
    accept (422); then, when none of the lines of a leaf keeps a remaining to commit, the leaf is
    completed in the same write (``_complete``): the line and the task written, and both kept by
    the entry of the history, the task only when it is completed. When the revision itself refuses
    the write, the entry is judged on the tree as it is first, as a gesture is. The structure is
    replayed, its lines priced again.
    """
    node_id = change.node_id
    stack = ExitStack()
    try:
        write = stack.enter_context(writing(session, place, writer, ("remaining", (node_id,))))
    except ConflictError:
        main = facts_of(session, place, lock=False).is_main
        tree = read_tree(session, place.project_id, place.structure_id)
        _judge_entry(session, (place, main), tree, _bearer_of(tree, node_id))
        raise
    with stack:
        tree, act = write.tree, writer.act
        task_id = _bearer_of(tree, node_id)
        node = tree.nodes[node_id]
        if node.lock_version != change.lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version}
            )
        main = write.facts.is_main
        _judge_entry(session, (place, main), tree, task_id)
        before = taken(session, place.project_id, (node_id, task_id))
        bearer = bearing(session, place.project_id, tree, task_id, is_main=main)
        change.apply(FacetWrite(session, place.project_id, place.revision_id, node_id, bearer, act))
        stamp(node, act)
        written: tuple[UUID, ...] = (node_id,)
        lines = tree.lines(task_id)
        if not tree.is_summary(task_id) and not change.keeps_open(session, place.project_id, lines):
            _complete(tree, task_id, change.completed_on, act)
            written = (node_id, task_id)
        # The task enters the entry of the history only when it is written: kept unchanged, it
        # would refuse the undoing of the line after another write of the task (UNDO_CONFLICT).
        write.touched.update(written)
        write.frame.keep_before(tuple(state for state in before if state.object_id in written))
        write.name(written)
        redated = write.redate((task_id, tree.tasks[task_id].label), None, (task_id,))
        write.after(written)
        return redated.written(written)


def load_progress(session: Session, project_id: UUID, load: ProgressLoad, act: Act) -> None:
    """Write the state of a task of the witness, at the instant it imposes.

    By the rules of the state: a leaf, its dates those of its state — none when not started,
    a start when started, both when completed, a milestone's equal and never
    started. No gesture is judged: the witness tells where its tasks stand. The task counts one
    write.
    """
    row = session.execute(
        select(Node, Task)
        .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
        .where(Node.project_id == project_id, Node.id == load.node_id)
        .with_for_update(of=Node)
    ).one_or_none()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    node, task = row
    summary = session.scalar(
        select(
            exists().where(
                Node.project_id == project_id, Node.parent_id == node.id, Node.kind == TASK
            )
        )
    )
    faults = _load_faults(load, summary=bool(summary), milestone=task.duration_value == 0)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    task.progress = load.progress
    task.started_on = load.started_on
    task.completed_on = load.completed_on
    node.lock_version += 1
    node.updated_at = act.at
    node.updated_by = act.author
    session.flush()


def _load_faults(load: ProgressLoad, *, summary: bool, milestone: bool) -> list[FieldError]:
    """Name what a state of the witness gets wrong: its kind of task, its dates."""
    faults: list[FieldError] = []
    if load.progress not in STATES:
        faults.append(FieldError("/progress", VALIDATION_FAILED))
    if summary:
        faults.append(FieldError("/node_id", SUMMARY_TASK_DERIVED))
    if load.progress == STARTED and milestone:
        faults.append(FieldError("/progress", VALIDATION_FAILED))
    if (load.progress == NOT_STARTED) != (load.started_on is None):
        faults.append(FieldError("/started_on", VALIDATION_FAILED))
    if (load.progress == COMPLETED) != (load.completed_on is not None):
        faults.append(FieldError("/completed_on", VALIDATION_FAILED))
    if load.progress == COMPLETED and milestone and load.started_on != load.completed_on:
        faults.append(FieldError("/started_on", VALIDATION_FAILED))
    return faults
