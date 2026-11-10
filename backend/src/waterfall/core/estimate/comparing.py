# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two marked revisions, private to the module (US-1530, WF-REV-0080).

Two marked revisions of a project are compared — a revision unknown or of another project refused
first (404), then the current one, which still changes under its reader (409, ``revision_marked``)
—, their main structures read whole, as they were marked: the lines on the amounts they keep and
the labels of the images of their revision (US-1500), nothing priced again on the reference of the
day. Their union (``uniting``) is read as ``listNodes`` reads a structure (#1193): the filters
retain on each side what they retain of its structure, a removed node judged on its values in the
base revision; ``subtree_of`` is a window onto the union, a removed task included; the ancestors
of what is retained come with it, but under ``timeline_id``; ``difference`` keeps the nodes of
the marks named, and their ancestors; the sort orders the lines under each task, a removed one
among them on its values; ``kinds`` chooses what is returned. The totals and the meta are those of
the compared revision, ``difference`` not restricting them.

The differences of amounts are counted on the lines retained, removed ones included, whatever
``kinds`` (``amount_deltas``): each line counts its amounts in the compared revision under the
nature of its category and its subproject there, minus its amounts in the base revision under its
own there (#1751), the nature read on the images of each revision. A key whose two differences are
nought is left out; the sum by subproject is that by nature, each line counted once in each.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.indicating import natures_of
from waterfall.core.estimate.reading import LineView, sort_lines
from waterfall.core.estimate.uniting import TASK, Union, unite
from waterfall.core.planning.interface import Place, read_structure
from waterfall.core.projects.interface import subproject_labels
from waterfall.core.revisions.interface import aimed_structure, read_revision_for
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError, NotFoundError

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import (
        LineSort,
        NodeFilters,
        NodeView,
        StructureRead,
        StructureTotals,
    )
    from waterfall.core.revisions.interface import RevisionRead

NOT_FOUND = "NOT_FOUND"
REVISION_MARKED = "revision_marked"
COST_TYPE = "cost_type"
SUBPROJECT = "subproject"
UNASSIGNED = "unassigned"
ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class ComparisonAsked:
    """What a comparison asks: the base revision, the compared one, and how its tree is read.

    ``differences`` the marks ``difference`` keeps, none to keep them all.
    """

    from_revision_id: UUID
    to_revision_id: UUID
    filters: NodeFilters
    differences: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class ComparedNode:
    """A node of the comparison: as it is read, numbered in the union, and its mark."""

    view: NodeView
    difference: str
    changes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AmountDelta:
    """The differences of the budgeted and re-estimated amounts of a nature or a subproject."""

    dimension: str
    key: str
    label: str | None
    budgeted: Decimal
    reestimated: Decimal


@dataclass(frozen=True, slots=True)
class Comparison:
    """A comparison of two revisions (``RevisionComparison``), the totals of the compared one."""

    from_revision_id: UUID
    to_revision_id: UUID
    items: tuple[ComparedNode, ...]
    task_count: int
    totals: StructureTotals
    summary_depth: int
    scheduled_at: datetime
    amount_deltas: tuple[AmountDelta, ...]


def _revision(session: Session, project_id: UUID, revision_id: UUID) -> tuple[RevisionRead, Place]:
    """Read a revision of the project and its main structure; or refuse (404)."""
    read = read_revision_for(session, project_id, revision_id)
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        raise NotFoundError(NOT_FOUND)
    return read, Place(project_id, revision_id, structure_id)


def _retained(
    union: Union,
    sides: tuple[StructureRead, StructureRead],
    filters: NodeFilters,
    differences: tuple[str, ...] | None,
) -> set[UUID]:
    """Give the nodes the filters and the marks retain themselves, without their ancestors."""
    base, compared = sides
    held = set(compared.kept | compared.lines)
    held |= {each for each in union.removed if each in base.kept or each in base.lines}
    if filters.subtree_of is not None:
        held &= set(union.subtree(filters.subtree_of))
    if differences is not None:
        held = {each for each in held if union.difference[each] in differences}
    return held


def _sorted(
    session: Session, project_id: UUID, union: Union, order: list[UUID], sort: LineSort
) -> list[UUID]:
    """Sort the lines under each task, a removed one on its values; the tasks keep their place.

    The lines of a task come together before its subtasks: each run of them is sorted alone.
    """
    lines = [each for each in order if union.views[each].kind != TASK]
    ordered = sort_lines(session, project_id, lines, sort) if lines else None
    if ordered is None:
        return order
    rank = {each: place for place, each in enumerate(ordered)}
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


def _line_of(view: NodeView | None) -> LineView | None:
    """Give the facet of a line as it is read, none for a task or a node absent."""
    facet = None if view is None or view.facet is None else view.facet.view
    return facet if isinstance(facet, LineView) else None


@dataclass(slots=True)
class _Deltas:
    """The differences summed by key, each key with its label."""

    sums: dict[tuple[str, UUID | None], tuple[Decimal, Decimal]]
    labels: dict[tuple[str, UUID | None], str | None]

    def add(self, key: tuple[str, UUID | None], line: LineView, sign: int) -> None:
        """Count the amounts of a line under a key, added or taken away."""
        budgeted, reestimated = self.sums.get(key, (ZERO, ZERO))
        self.sums[key] = (
            budgeted + sign * line.budgeted_amount,
            reestimated + sign * line.reestimated_amount,
        )


def _amount_deltas(
    session: Session,
    project_id: UUID,
    reads: tuple[RevisionRead, RevisionRead],
    sides: tuple[Sequence[LineView], Sequence[LineView]],
) -> tuple[AmountDelta, ...]:
    """Sum the differences of the lines, each under its key in each revision; drop the nought."""
    base_read, compared_read = reads
    before, after = sides
    deltas = _Deltas({}, {})
    for read, lines, sign in ((base_read, before, -1), (compared_read, after, 1)):
        natures = natures_of(session, project_id, read, {each.cost_category_id for each in lines})
        for line in lines:
            # Never a ``KeyError``: ``natures_of`` finds the category of every line, on the images
            # or on the reference; proved by ``test_comparison.py``,
            # ``test_a_category_a_line_bears_lacks_never_both_its_image_and_the_reference``.
            nature = natures[line.cost_category_id]
            # The label of the compared revision prevails: it is added after the base one.
            deltas.labels[(COST_TYPE, nature.cost_type_id)] = nature.label
            deltas.add((COST_TYPE, nature.cost_type_id), line, sign)
            deltas.add((SUBPROJECT, line.subproject_id), line, sign)
    named = [key for dimension, key in deltas.sums if dimension == SUBPROJECT and key is not None]
    for subproject_id, label in subproject_labels(session, project_id, named).items():
        deltas.labels[(SUBPROJECT, subproject_id)] = label
    found: list[AmountDelta] = []
    for dimension in (COST_TYPE, SUBPROJECT):
        keys = [key for held, key in deltas.sums if held == dimension]
        ordered: list[UUID | None] = [*sorted(each for each in keys if each is not None)]
        if None in keys:
            ordered.append(None)
        for key in ordered:
            budgeted, reestimated = deltas.sums[(dimension, key)]
            if budgeted == 0 and reestimated == 0:
                continue
            found.append(
                AmountDelta(
                    dimension,
                    UNASSIGNED if key is None else str(key),
                    deltas.labels.get((dimension, key)),
                    budgeted,
                    reestimated,
                )
            )
    return tuple(found)


def _counted(union: Union, held: Collection[UUID]) -> tuple[list[LineView], list[LineView]]:
    """Give the lines retained as each revision has them: the base one's, the compared one's."""
    before: list[LineView] = []
    after: list[LineView] = []
    for node_id in held:
        if union.views[node_id].kind == TASK:
            continue
        base = _line_of(union.base.get(node_id))
        if base is not None:
            before.append(base)
        if node_id not in union.removed:
            compared = _line_of(union.views[node_id])
            if compared is not None:
                after.append(compared)
    return before, after


def compare(session: Session, project_id: UUID, asked: ComparisonAsked) -> Comparison:
    """Compare two marked revisions of a project, read as ``listNodes`` reads a structure."""
    base_read, base_place = _revision(session, project_id, asked.from_revision_id)
    compared_read, compared_place = _revision(session, project_id, asked.to_revision_id)
    if not (base_read.marked and compared_read.marked):
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": REVISION_MARKED})
    filters = asked.filters
    compared = read_structure(session, compared_place, filters)
    # The window is the union's: a removed node is held in the base structure whole.
    base = read_structure(session, base_place, replace(filters, subtree_of=None))
    union = unite(base.nodes, compared.nodes)
    held = _retained(union, (base, compared), filters, asked.differences)
    returned = set(held)
    if filters.timeline_id is None:
        returned |= {ancestor for each in held for ancestor in union.ancestors(each)}
    order = [each for each in union.order if each in returned]
    if filters.sort is not None:
        order = _sorted(session, project_id, union, order, filters.sort)
    if filters.kinds is not None:
        order = [each for each in order if union.views[each].kind in filters.kinds]
    return Comparison(
        from_revision_id=asked.from_revision_id,
        to_revision_id=asked.to_revision_id,
        items=tuple(
            ComparedNode(union.views[each], union.difference[each], union.changes[each])
            for each in order
        ),
        task_count=compared.task_count,
        totals=compared.totals,
        summary_depth=compared.summary_depth,
        scheduled_at=compared.scheduled_at,
        amount_deltas=_amount_deltas(
            session, project_id, (base_read, compared_read), _counted(union, held)
        ),
    )
