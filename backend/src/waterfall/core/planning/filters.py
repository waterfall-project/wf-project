# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a reading of the tree retains, private to the module (``listNodes``, WF-PLA-0080).

A filter of the task retains the tasks that satisfy it, with the lines they bear; the filters
combine, and the ancestors of what is retained are returned for the tree to stay readable, but
under ``timeline_id``: a timeline is no tree (WF-PLA-0140). ``kinds`` is no filter: it chooses what
is returned, and the count of the tasks does not change with it. The filters of the line — its
category, its role, its figures, its amounts — retain lines, which EP-07 brings: read by the API
and without effect here. Each bound is inclusive; a task that bears no value — a manual task's
float, a leaf's physical progress — is not retained by a bound on it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.planning.dating import days_of
from waterfall.core.planning.tables import Task
from waterfall.platform.database import contains

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.scheduling import UnitConstants
    from waterfall.core.planning.views import Reading

type Bounds[T] = tuple[T | None, T | None]


@dataclass(frozen=True, slots=True)
class NodeFilters:
    """What a reading of the nodes asks: the kinds it returns, and what it retains of the tasks.

    ``None`` asks nothing; a bound is a pair, either side ``None``.
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
) -> tuple[list[UUID], int]:
    """Give the nodes a reading returns, in the order of the plan, and the tasks it retains."""
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
    returned = set(kept)
    if filters.timeline_id is None:
        returned |= {ancestor for each in kept for ancestor in tree.ancestors(each)}
    returned |= {line for each in kept for line in tree.lines(each)}
    kinds = filters.kinds
    order = [each for each in tree.order if each in returned]
    if kinds is not None:
        order = [each for each in order if tree.nodes[each].kind in kinds]
    return order, len(kept)
