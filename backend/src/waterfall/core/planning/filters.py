# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a reading of the tree retains, private to the module (``listNodes``, WF-PLA-0080).

A filter of the task retains the tasks that satisfy it, with the lines they bear; the filters
combine, and the ancestors of what is retained are returned for the tree to stay readable, but
under ``timeline_id``: a timeline is no tree (WF-PLA-0140). ``kinds`` is no filter: it chooses what
is returned, and the count of the tasks does not change with it. The filters of the line — its
category, its role, its figures, its amounts — retain lines, judged by the hooks of their facet
(``FacetHooks.filters``, EP-07), opaque here: asked, a task is retained only if it bears a line
they retain, which alone it returns, and the task is then rendered for the tree alone: the count
of the tasks is nought, as ``NodeTotals`` says of the ancestors (#2699). The lines are sorted under each task by those hooks too
(``FacetHooks.sort``), the tasks keeping the order of the tree (WF-IHM-0060). Each bound is
inclusive; a task that bears no value — a manual task's float, a leaf's physical progress — is not
retained by a bound on it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.planning.dating import days_of
from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.tables import Task
from waterfall.platform.database import contains

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface.facets import LineSort
    from waterfall.core.planning.scheduling import UnitConstants
    from waterfall.core.planning.views import Reading

type Bounds[T] = tuple[T | None, T | None]


@dataclass(frozen=True, slots=True)
class NodeFilters:
    """What a reading of the nodes asks: the kinds it returns, and what it retains of the tasks.

    ``None`` asks nothing; a bound is a pair, either side ``None``. ``lines`` is what the reading
    asks of the facets of the other kinds, opaque here; ``sort`` the order of their nodes.
    """

    kinds: tuple[str, ...] | None = None
    search: str | None = None
    subtree_of: UUID | None = None
    work_package_id: UUID | None = None
    order_item_id: UUID | None = None
    progress: tuple[str, ...] | None = None
    is_critical: bool | None = None
    summaries_only: bool = False
    max_level: int | None = None
    timeline_id: UUID | None = None
    description: str | None = None
    scheduling_modes: tuple[str, ...] | None = None
    duration_days: Bounds[Decimal] = (None, None)
    physical_progress: Bounds[Decimal] = (None, None)
    total_float: Bounds[Decimal] = (None, None)
    start: Bounds[date] = (None, None)
    finish: Bounds[date] = (None, None)
    started_on: Bounds[date] = (None, None)
    completed_on: Bounds[date] = (None, None)
    is_milestone: bool | None = None
    finish_overdue: bool | None = None
    is_from_risk: bool | None = None
    origin_risk_ids: tuple[UUID, ...] | None = None
    lines: object | None = None
    sort: LineSort | None = None


@dataclass(frozen=True, slots=True)
class Retained:
    """What a reading returns: its nodes in order, the tasks it retains, the lines it retains.

    ``kept`` the tasks the filters retain themselves, without the ancestors ``order`` adds;
    ``task_count`` those of them counted, none under a filter of the line (#2699).
    """

    order: list[UUID]
    task_count: int
    lines: frozenset[UUID]
    kept: frozenset[UUID] = frozenset()


def _within[T: (Decimal, date)](value: T | None, bounds: Bounds[T]) -> bool:
    """Tell whether a value lies between two bounds, inclusive; none lies within a bound."""
    low, high = bounds
    if low is None and high is None:
        return True
    if value is None:
        return False
    return (low is None or low <= value) and (high is None or value <= high)


def _searched(
    session: Session, project_id: UUID, structure_id: UUID, text: str, column: str
) -> frozenset[UUID]:
    """Give the tasks of a structure whose label or description holds a text, any case or accent."""
    searched = Task.label if column == "label" else Task.description
    found = select(Task.node_id).where(
        Task.project_id == project_id,
        Task.structure_id == structure_id,
        contains(searched, text),
    )
    return frozenset(session.scalars(found))


def _subtree(reading: Reading, root: UUID) -> frozenset[UUID]:
    """Give the subtree of a task of the structure, the task included; nothing for another."""
    tree = reading.tree
    return frozenset(tree.subtree(root)) if root in tree.tasks else frozenset()


def _carrying(reading: Reading, column: str, item: UUID) -> frozenset[UUID]:
    """Give the subtree of the task that bears a work package or an order item (WF-PLA-0170)."""
    tree = reading.tree
    for node_id, task in tree.tasks.items():
        if getattr(task, column) == item:
            return frozenset(tree.subtree(node_id))
    return frozenset()


def _predicates(
    reading: Reading, filters: NodeFilters, constants: UnitConstants
) -> list[Callable[[UUID], bool]]:
    """Give the tests of a task the filters ask for, each on the task alone."""
    tree = reading.tree
    tasks = tree.tasks
    tests: list[Callable[[UUID], bool]] = [
        lambda each: _within(tasks[each].start_date, filters.start),
        lambda each: _within(tasks[each].finish_date, filters.finish),
        lambda each: _within(tasks[each].total_float_days, filters.total_float),
        lambda each: _within(reading.states[each].started_on, filters.started_on),
        lambda each: _within(reading.states[each].completed_on, filters.completed_on),
        # A physical progress is EP-07's, from the budgets of the lines: none is computed here.
        lambda _each: _within(None, filters.physical_progress),
        lambda each: _within(days_of(tasks[each], constants), filters.duration_days),
    ]
    if filters.progress is not None:
        tests.append(lambda each: reading.states[each].progress in (filters.progress or ()))
    if filters.is_critical is not None:
        tests.append(lambda each: tasks[each].is_critical is filters.is_critical)
    if filters.summaries_only:
        tests.append(tree.is_summary)
    if filters.max_level is not None:
        limit = filters.max_level
        tests.append(lambda each: tree.level[each] <= limit)
    if filters.scheduling_modes is not None:
        modes = filters.scheduling_modes
        tests.append(lambda each: tasks[each].scheduling_mode in modes)
    if filters.is_milestone is not None:
        tests.append(lambda each: tree.is_milestone(each) is filters.is_milestone)
    if filters.finish_overdue is not None:
        tests.append(lambda each: reading.schedule(each).finish_overdue is filters.finish_overdue)
    if filters.is_from_risk is not None:
        from_risk = filters.is_from_risk
        tests.append(lambda each: (tree.nodes[each].origin_risk_id is not None) is from_risk)
    if filters.origin_risk_ids is not None:
        risks = set(filters.origin_risk_ids)
        tests.append(lambda each: tree.nodes[each].origin_risk_id in risks)
    return tests


def retained(
    session: Session,
    structure: tuple[UUID, UUID],
    reading: Reading,
    filters: NodeFilters,
    constants: UnitConstants,
) -> Retained:
    """Give the nodes a reading returns, in the order of the plan, the tasks and lines retained."""
    project_id, structure_id = structure
    tree = reading.tree
    kept = set(tree.tasks)
    if filters.search is not None:
        kept &= _searched(session, project_id, structure_id, filters.search, "label")
    if filters.description is not None:
        kept &= _searched(session, project_id, structure_id, filters.description, "description")
    if filters.subtree_of is not None:
        kept &= _subtree(reading, filters.subtree_of)
    if filters.work_package_id is not None:
        kept &= _carrying(reading, "work_package_id", filters.work_package_id)
    if filters.order_item_id is not None:
        kept &= _carrying(reading, "order_item_id", filters.order_item_id)
    if filters.timeline_id is not None:
        inscribed = {
            lineage
            for lineage, entries in reading.tracking.items()
            if any(entry.timeline_id == filters.timeline_id for entry in entries)
        }
        kept = {each for each in kept if tree.nodes[each].lineage_id in inscribed}
    for test in _predicates(reading, filters, constants):
        kept = {each for each in kept if test(each)}
    lines = _lines(session, project_id, reading, kept, filters.lines)
    if filters.lines is not None:
        kept = {each for each in kept if not lines.isdisjoint(tree.lines(each))}
    returned = set(kept) | lines
    if filters.timeline_id is None:
        returned |= {ancestor for each in kept for ancestor in tree.ancestors(each)}
    kinds = filters.kinds
    order = [each for each in tree.order if each in returned]
    if filters.sort is not None:
        order = _sorted(session, project_id, reading, order, filters.sort)
    if kinds is not None:
        order = [each for each in order if tree.nodes[each].kind in kinds]
    # Under a filter of the line, the tasks bear the lines retained and are not counted (#2699).
    counted = 0 if filters.lines is not None else len(kept)
    return Retained(order, counted, lines, frozenset(kept))


def _lines(
    session: Session, project_id: UUID, reading: Reading, kept: set[UUID], asked: object | None
) -> frozenset[UUID]:
    """Give the lines the tasks retained bear that the filters of their facets retain."""
    tree = reading.tree
    borne = [line for each in kept for line in tree.lines(each)]
    if asked is None:
        return frozenset(borne)
    found: set[UUID] = set()
    for kind, hooks in facets().items():
        held = [each for each in borne if tree.nodes[each].kind == kind]
        if held:
            found |= hooks.filters(session, project_id, held, asked)
    return frozenset(found)


def _sorted(
    session: Session, project_id: UUID, reading: Reading, order: list[UUID], sort: LineSort
) -> list[UUID]:
    """Sort the lines under each task by the hooks of their facets; the tasks keep their place.

    The lines of a task come together before its subtasks: each run of them is sorted alone.
    """
    tree = reading.tree
    rank: dict[UUID, int] = {}
    for kind, hooks in facets().items():
        held = [each for each in order if tree.nodes[each].kind == kind]
        ordered = hooks.sort(session, project_id, held, sort) if held else None
        if ordered is not None:
            rank.update({each: place for place, each in enumerate(ordered)})
    if not rank:
        return order
    result: list[UUID] = []
    run: list[UUID] = []
    for each in [*order, None]:
        if each is not None and each in rank:
            run.append(each)
            continue
        result += sorted(run, key=rank.__getitem__)
        run = []
        if each is not None:
            result.append(each)
    return result
