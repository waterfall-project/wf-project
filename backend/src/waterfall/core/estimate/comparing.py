# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of a revision with a marked base, private to the module (US-1530, WF-REV-0080).

The revision read, current or marked, is compared with a marked revision of its project, the base —
a revision unknown or of another project refused first (404), then a base not marked, which still
changes under its reader (409, ``revision_marked``) (EP-27, US-2320) —, their main structures read
whole: a marked one as it was marked, the lines on the amounts they keep and the labels of the
images of their revision (US-1500), nothing priced again on the reference of the day; the current
one in its state of the moment, nothing kept of a comparison. Their union (``uniting``) is read as
``listNodes`` reads a structure (#1193): the filters retain on each side what they retain of its
structure, a removed node judged on its values in the base revision; ``subtree_of`` is a window
onto the union, a removed task included; the ancestors of what is retained come with it, but under
``timeline_id``; ``difference`` keeps the nodes of the marks named, and their ancestors; the sort
orders the lines under each task, a removed one among them on its values; ``kinds`` chooses what
is returned. The totals and the meta are those of the compared revision, ``difference`` not
restricting them. The union compares every value of a node as the API writes it, which its reader
gives (``written``): the core does not know the form of a response.

The differences of amounts are counted on the lines retained, removed ones included, whatever
``kinds`` (``amount_deltas``): each line counts its amounts in the compared revision under the
nature of its category and its subproject there, minus its amounts in the base revision under its
own there (#1751), the nature read on the images of each revision. A key whose two differences are
nought is left out; the sum by subproject is that by nature, each line counted once in each.

A comparison no filter restricts reads the reading kept of the base, and that of the revision read
when it is marked, its columns when it is current (EP-26, "La comparaison", US-2270, US-2220): the
API gives what the union reads of their nodes, and applies to them the place, the mark and the base
of each node returned (``compare_united``); the revisions are read and judged first
(``compared_places``), as ``compare`` reads and judges them.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.indicating import natures_of
from waterfall.core.estimate.reading import LineView, sort_lines
from waterfall.core.estimate.uniting import (
    TASK,
    LineAmounts,
    PlacedNode,
    Union,
    UnitedNode,
    unite,
)
from waterfall.core.planning.interface import Place, read_structure
from waterfall.core.projects.interface import subproject_labels
from waterfall.core.revisions.interface import aimed_structure, read_revision_for
from waterfall.platform.errors import (
    NOT_FOUND,
    STATE_FORBIDS_OPERATION,
    ConflictError,
    NotFoundError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping, Sequence
    from datetime import datetime
    from typing import Any
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import (
        LineSort,
        NodeFilters,
        NodeView,
        StructureTotals,
    )
    from waterfall.core.revisions.interface import RevisionRead

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


# How the reader writes a node whole, as the API does (``Node``): what the union compares of it.
type Written = Callable[[NodeView], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ComparedNode:
    """A node of the comparison: as it is read, numbered in the union, its mark and its base.

    ``base`` what the base carried of the values that differ, by their name in the node, of a
    modified node present on both sides; none for any other (``PlacedNode.base``).
    """

    view: NodeView
    difference: str
    changes: tuple[str, ...]
    base: dict[str, Any] | None


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


@dataclass(frozen=True, slots=True)
class UnitedComparison[K]:
    """A comparison no filter restricts, of what the union reads (``compare_united``).

    ``items`` the nodes returned, in the order of the union, each placed and marked.
    """

    items: tuple[PlacedNode[K], ...]
    amount_deltas: tuple[AmountDelta, ...]


def _revision(session: Session, project_id: UUID, revision_id: UUID) -> tuple[RevisionRead, Place]:
    """Read a revision of the project and its main structure; or refuse (404)."""
    read = read_revision_for(session, project_id, revision_id)
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        raise NotFoundError(NOT_FOUND)
    return read, Place(project_id, revision_id, structure_id)


def compared_places(
    session: Session, project_id: UUID, asked: ComparisonAsked
) -> tuple[tuple[RevisionRead, RevisionRead], tuple[Place, Place]]:
    """Read the two revisions a comparison asks and their main structures, the base one first.

    A revision unknown or of another project refused first (404), then a base not marked (409):
    the revision read may be the current one, which nothing of the comparison keeps.
    """
    base_read, base_place = _revision(session, project_id, asked.from_revision_id)
    compared_read, compared_place = _revision(session, project_id, asked.to_revision_id)
    if not base_read.marked:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": REVISION_MARKED})
    return (base_read, compared_read), (base_place, compared_place)


def _retained[K](
    union: Union[K],
    sides: tuple[Collection[K], Collection[K]],
    subtree_of: K | None,
    differences: tuple[str, ...] | None,
) -> set[K]:
    """Give the nodes the filters and the marks retain themselves, without their ancestors.

    ``sides`` the nodes the filters retain of each structure, the base one first.
    """
    base, compared = sides
    held = set(compared)
    held |= {each for each in union.removed if each in base}
    if subtree_of is not None:
        held &= set(union.subtree(subtree_of))
    if differences is not None:
        held = {each for each in held if union.difference[each] in differences}
    return held


def _ordered[K](union: Union[K], held: set[K], *, ancestors: bool) -> list[K]:
    """Give the nodes returned in the order of the union: those held, and their ancestors."""
    returned = set(held)
    if ancestors:
        returned |= {ancestor for each in held for ancestor in union.ancestors(each)}
    return [each for each in union.order if each in returned]


def _sorted(
    session: Session, project_id: UUID, union: Union[UUID], order: list[UUID], sort: LineSort
) -> list[UUID]:
    """Sort the lines under each task, a removed one on its values; the tasks keep their place.

    The lines of a task come together before its subtasks: each run of them is sorted alone.
    """
    lines = [each for each in order if union.nodes[each].kind != TASK]
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


def _united(view: NodeView, written: Written) -> UnitedNode[UUID]:
    """Give what the union reads of a node as a reading of the rows gives it, and its values."""
    facet = None if view.facet is None else view.facet.view
    line = facet if isinstance(facet, LineView) else None
    return UnitedNode(
        view.node_id,
        view.lineage_id,
        view.kind,
        view.parent_id,
        tuple(each.predecessor_id for each in view.predecessors),
        written(view),
        None
        if line is None
        else LineAmounts(
            line.cost_category_id, line.subproject_id, line.budgeted_amount, line.reestimated_amount
        ),
    )


def _placed_view(view: NodeView, placed: PlacedNode[UUID]) -> NodeView:
    """Give a node of a reading of the rows as the union returns it: placed, renamed, read-only."""
    predecessors = view.predecessors
    if placed.predecessors:
        predecessors = tuple(
            each
            if renamed is None
            else replace(each, predecessor_id=renamed[0], row_number=renamed[1])
            for each, renamed in zip(view.predecessors, placed.predecessors, strict=True)
        )
    return replace(
        view,
        parent_id=placed.parent_id,
        row_number=placed.row_number,
        level=placed.level,
        position=placed.position,
        predecessors=predecessors,
        editable_fields=() if placed.removed else view.editable_fields,
    )


@dataclass(slots=True)
class _Deltas:
    """The differences summed by key, each key with its label."""

    sums: dict[tuple[str, UUID | None], tuple[Decimal, Decimal]]
    labels: dict[tuple[str, UUID | None], str | None]

    def add(self, key: tuple[str, UUID | None], line: LineAmounts, sign: int) -> None:
        """Count the amounts of a line under a key, added or taken away."""
        budgeted, reestimated = self.sums.get(key, (ZERO, ZERO))
        self.sums[key] = (
            budgeted + sign * line.budgeted,
            reestimated + sign * line.reestimated,
        )


def _amount_deltas(
    session: Session,
    project_id: UUID,
    reads: tuple[RevisionRead, RevisionRead],
    sides: tuple[Sequence[LineAmounts], Sequence[LineAmounts]],
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


def _counted[K](
    union: Union[K], held: Collection[K]
) -> tuple[list[LineAmounts], list[LineAmounts]]:
    """Give the lines retained as each revision has them: the base one's, the compared one's."""
    before: list[LineAmounts] = []
    after: list[LineAmounts] = []
    for node_id in held:
        node = union.nodes[node_id]
        if node.kind == TASK:
            continue
        base = union.base.get(node_id)
        if base is not None and base.line is not None:
            before.append(base.line)
        if node_id not in union.removed and node.line is not None:
            after.append(node.line)
    return before, after


def compare(
    session: Session, project_id: UUID, asked: ComparisonAsked, written: Written
) -> Comparison:
    """Compare a revision with a marked base, read as ``listNodes`` reads a structure.

    ``written`` how the reader writes a node whole, whose values the union compares.
    """
    reads, (base_place, compared_place) = compared_places(session, project_id, asked)
    filters = asked.filters
    compared = read_structure(session, compared_place, filters)
    # The window is the union's: a removed node is held in the base structure whole.
    base = read_structure(session, base_place, replace(filters, subtree_of=None))
    union = unite(
        [_united(each, written) for each in base.nodes],
        [_united(each, written) for each in compared.nodes],
    )
    sides = (base.kept | base.lines, compared.kept | compared.lines)
    held = _retained(union, sides, filters.subtree_of, asked.differences)
    order = _ordered(union, held, ancestors=filters.timeline_id is None)
    if filters.sort is not None:
        order = _sorted(session, project_id, union, order, filters.sort)
    if filters.kinds is not None:
        order = [each for each in order if union.nodes[each].kind in filters.kinds]
    views = {each.node_id: each for each in (*base.nodes, *compared.nodes)}
    placed = [union.placed(each) for each in order]
    return Comparison(
        from_revision_id=asked.from_revision_id,
        to_revision_id=asked.to_revision_id,
        items=tuple(
            ComparedNode(
                _placed_view(views[each.node_id], each), each.difference, each.changes, each.base
            )
            for each in placed
        ),
        task_count=compared.task_count,
        totals=compared.totals,
        summary_depth=compared.summary_depth,
        scheduled_at=compared.scheduled_at,
        amount_deltas=_amount_deltas(session, project_id, reads, _counted(union, held)),
    )


def compare_united[K](
    session: Session,
    project_id: UUID,
    reads: tuple[RevisionRead, RevisionRead],
    sides: tuple[Sequence[UnitedNode[K]], Sequence[UnitedNode[K]]],
    differences: tuple[str, ...] | None,
) -> UnitedComparison[K]:
    """Compare two structures read whole, unfiltered, by what the union reads of their nodes.

    What ``compare`` gives of a comparison that no filter restricts, from what the reader gives
    of each structure — the nodes of two readings kept, written as the API writes them (US-2270):
    the nodes returned, placed, marked and with their base, which the reader applies to what it
    read, and the differences of amounts. ``reads`` the two revisions ``compared_places`` read.
    """
    base, compared = sides
    union = unite(base, compared)
    every = ({each.node_id for each in base}, {each.node_id for each in compared})
    held = _retained(union, every, None, differences)
    return UnitedComparison(
        tuple(union.placed(each) for each in _ordered(union, held, ancestors=True)),
        _amount_deltas(session, project_id, reads, _counted(union, held)),
    )
