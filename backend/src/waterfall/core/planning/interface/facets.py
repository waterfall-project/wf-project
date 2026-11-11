# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The facets of a node other than the task: what a later module registers for its own kind.

A node is a task here, an estimate line by EP-07, whose facet is a table of its module: EP-07
registers, for its kind, the hooks the planning asks (``FacetHooks``) — the reading of its facet
(``listNodes`` returns it), its creation with its node, its copy and its deletion with the node (a
revision opened, a node deleted), its snapshot and its restoration for the history, its amounts
priced again on the dates of the tasks redated, its figures summed in the totals, its filters and
its sort, and the calendars of the roles of its lines, which the calendar applicable to a task
intersects (``calendar_of``, WF-PLA-0010). The planning knows no other facet than its own: it asks
the hooks of the kind, and hands them what it knows of the task that bears each node
(``BearingTask``); what a write sends of the facet stays opaque to it (EP-06 and EP-07, "Les points
d'extension").

Declared by US-1380/L1; filled by US-1380/L2: ``calendar_of`` gives the default calendar to a task
whose facets name no calendar, the intersection of those they name otherwise; ``calendars_of``
gives it to the tasks of a structure, the default read once, the calendars of the facets asked
once. Completed by US-1490/L3 (EP-07, "Les points d'extension"), by US-1490/L4 with the
judgement of the nodes a move gives another task (``moved``), by US-1560/L1 with the judgement
and the write of the cells a paste gives a node of the kind (``judge_cell``, ``write_cell``), and by
US-1570/L5 with what a write takes before the lock of its structure (``before_lock``, #2615).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from waterfall.core.planning.calendars import applicable_of, default_calendar
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue
    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import WorkInstant
    from waterfall.core.revisions.interface import RevisionCopy
    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class Amounts:
    """What a node of a kind counts in the totals: its hours and its three amounts, and its year.

    ``budgeted`` is the amount as it is read (WF-DEV-0020); ``consumption_year`` none for a task.
    """

    hours: Decimal = Decimal(0)
    base: Decimal = Decimal("0.00")
    budgeted: Decimal = Decimal("0.00")
    reestimated: Decimal = Decimal("0.00")
    consumption_year: int | None = None

    def __add__(self, other: Amounts) -> Amounts:
        """Give the sum of two, without a year: amounts already at the cent add exactly."""
        return Amounts(
            self.hours + other.hours,
            self.base + other.base,
            self.budgeted + other.budgeted,
            self.reestimated + other.reestimated,
        )


@dataclass(frozen=True, slots=True)
class BearingTask:
    """The task that bears a node of a kind, as the planning knows it.

    Its revision, its label, its dates, the hours of its applicable calendar, Monday first, its
    state — a summary's derived
    from its subordinates —, and whether its structure is the main one.
    """

    task_id: UUID
    revision_id: UUID
    label: str
    start: WorkInstant
    finish: WorkInstant
    week: tuple[Decimal, ...]
    progress: str
    is_main: bool


@dataclass(frozen=True, slots=True)
class FacetRead:
    """The facet of a node as it is read: its view, opaque, its label, its computed fields."""

    view: object
    label: str
    computed_fields: tuple[str, ...]
    editable_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FacetState:
    """The facet of a node as the history keeps it: its label, its rows as JSON holds them."""

    label: str
    rows: JsonValue


@dataclass(frozen=True, slots=True)
class FacetCreation:
    """A node of the kind created: where, under which task, by whom, and what its write sends.

    ``entry`` is what the API read of the facet, opaque to the planning; the node is written, its
    facet is not.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    node_id: UUID
    bearer: BearingTask
    entry: object
    act: Act


@dataclass(frozen=True, slots=True)
class FacetWrite:
    """A write of the facet of a node, under the lock of its structure, its node to be counted."""

    session: Session
    project_id: UUID
    revision_id: UUID
    node_id: UUID
    bearer: BearingTask
    act: Act


@dataclass(frozen=True, slots=True)
class CellsPasted:
    """The cells a paste gives a node of the kind, in the order of ``NodeColumn``, to be judged.

    ``node_id`` the node they fall on, none for a node the paste creates; ``bearer`` the task that
    bears it; ``cells`` the column of each cell, as ``NodeColumn`` names it, and its text. An empty
    cell is never given: it writes nothing. ``earlier`` is, node by node, what the entry judged of
    the rows of the same block accepted before this one under the same task: the node, written or
    created, and the entry its hook gave (``CellsJudged.entry``), opaque to the planning.
    """

    session: Session
    project_id: UUID
    node_id: UUID | None
    bearer: BearingTask
    cells: tuple[tuple[str, str], ...]
    earlier: tuple[tuple[UUID, object], ...] = ()


@dataclass(frozen=True, slots=True)
class CellRefusal:
    """The refusal of a cell a paste gives a node, or of its whole row (``column`` none)."""

    column: str | None
    code: str
    params: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CellsJudged:
    """What the hook of a kind judged of the cells of a row: its refusals, and what it would write.

    ``entry`` is opaque to the planning, which hands it back to ``write_cell`` for a node written,
    to ``create`` (``FacetCreation.entry``) for a node created; none when a cell is refused.
    """

    refusals: tuple[CellRefusal, ...]
    entry: object = None


@dataclass(frozen=True, slots=True)
class LineSort:
    """The sort of the nodes of a kind under each task: a column and its direction."""

    column: str
    descending: bool


@dataclass(frozen=True, slots=True)
class FacetHooks:
    """What the planning asks of the facet of a kind of node, each hook given its session.

    ``read`` the facet of each node named, by node, the task bearing it given; ``copy`` copies the
    facets of the source into the revision opened, the nodes copied found in ``copy.identifiers``;
    ``delete`` deletes the facets of nodes deleted; ``calendars`` gives the calendars of the roles
    of the nodes of the kind under each task named; ``create`` writes the facet of a node created;
    ``snapshot`` gives the facets as the history keeps them, ``restore`` writes them back;
    ``reinflate`` prices again the nodes on the dates of their tasks and gives those whose amounts
    or year moved; ``totals`` gives the figures of each node named; ``filters`` keeps, of the
    nodes named, those a filter asked of the kind retains; ``sort`` orders them, or gives none for a
    column it does not sort; ``dependencies`` names what a computed value of a node depends on,
    none for a field it does not compute; ``moved`` judges the nodes a move gives another task,
    placed under it already, in the order of the plan, and refuses what it does not accept (422);
    ``judge_cell`` judges the cells a paste gives a node, by the very functions of the entry of a
    cell, naming every refusal at once; ``write_cell`` writes the entry it judged; ``before_lock``
    takes what a write of the tree must hold before the lock of its structure — the estimate shares
    the lock of the natures (#2615) —, called first by every write of the tree.
    """

    read: Callable[[Session, UUID, Mapping[UUID, BearingTask]], Mapping[UUID, FacetRead]]
    copy: Callable[[RevisionCopy], None]
    delete: Callable[[Session, UUID, Collection[UUID]], None]
    calendars: Callable[[Session, UUID, Collection[UUID]], Mapping[UUID, Collection[UUID]]]
    create: Callable[[FacetCreation], None]
    snapshot: Callable[[Session, UUID, Collection[UUID]], Mapping[UUID, FacetState]]
    restore: Callable[[Session, UUID, Mapping[UUID, JsonValue], Act], None]
    reinflate: Callable[[Session, UUID, Mapping[UUID, BearingTask]], frozenset[UUID]]
    totals: Callable[[Session, UUID, Collection[UUID]], Mapping[UUID, Amounts]]
    filters: Callable[[Session, UUID, Collection[UUID], object], frozenset[UUID]]
    sort: Callable[[Session, UUID, Collection[UUID], LineSort], list[UUID] | None]
    dependencies: Callable[[Session, UUID, UUID, str], tuple[str, ...] | None]
    moved: Callable[[Session, UUID, Mapping[UUID, BearingTask]], None]
    judge_cell: Callable[[CellsPasted], CellsJudged]
    write_cell: Callable[[FacetWrite, object], None]
    before_lock: Callable[[Session], None]


# The hooks of each kind of node other than the task, in the order of their registration.
_FACETS: Registry[tuple[str, FacetHooks]] = Registry("planning.facets")


def register_facet(kind: str, hooks: FacetHooks) -> Callable[[], None]:
    """Add the hooks of the facet of a kind of node; give their withdrawal; refused if held."""
    if kind in facets():
        msg = f"the facet {kind} is registered already"
        raise ValueError(msg)
    return _FACETS.register((kind, hooks))


def facets() -> Mapping[str, FacetHooks]:
    """Give the hooks of each kind of node registered, by kind."""
    return dict(_FACETS.entries())


def named_calendars(
    session: Session, project_id: UUID, task_ids: Collection[UUID]
) -> dict[UUID, set[UUID]]:
    """Give the calendars the facets of the kinds registered name under each task, asked once."""
    named: dict[UUID, set[UUID]] = {task_id: set() for task_id in task_ids}
    if not task_ids:
        return named
    for hooks in facets().values():
        for task_id, calendars in hooks.calendars(session, project_id, task_ids).items():
            named.setdefault(task_id, set()).update(calendars)
    return named


def calendar_of(
    session: Session, project_id: UUID, task_id: UUID, *, default: Applicable | None = None
) -> Applicable:
    """Give the calendar applicable to a task (WF-PLA-0010).

    The calendars the facets of the kinds registered name under the task, intersected day by day;
    the default calendar when they name none — read here unless ``default`` gives it.
    """
    named = named_calendars(session, project_id, (task_id,))[task_id]
    return applicable_of(session, named, default or default_calendar(session))


def calendars_of(
    session: Session, project_id: UUID, task_ids: Collection[UUID]
) -> dict[UUID, Applicable]:
    """Give the calendar applicable to each task named, the default and the facets read once."""
    default = default_calendar(session)
    named = named_calendars(session, project_id, task_ids)
    return {task_id: applicable_of(session, named[task_id], default) for task_id in task_ids}
