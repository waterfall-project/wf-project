# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work breakdown of a project: work packages, order items, deliverables (WF-PRJ-0020).

Read whole or filtered, written whole under its own counter
(``project.work_breakdown_lock_version``); an element left out is deleted. A work package and an
order item left out are first withdrawn from the tasks of the current revision, then marked deleted
(``deleted_at``, left out of every reading of the work breakdown) when a task of a marked revision
bears them — or, for a work package, an order item marked deleted is still under it —, and deleted
for good otherwise (``register_attachments``, WF-PLA-0170, US-1380/L3); a deliverable is always
deleted for good. The project is born with a work package and an order item that bear its label,
without deliverable (``create_project``); the first writing replaces them. The planning reads the
work packages and order items of a project, those marked deleted included, by
``work_breakdown_items``.

The tree is read in one statement, so that the counter and the elements it numbers belong to one
snapshot. It is written under the lock of the project, which every decision is read under; the
positions, unique under their parent, are freed before they are taken again.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy import select, true

from waterfall.core.projects.commands import (
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_NOT_TERMINAL,
    TERMINAL,
)
from waterfall.core.projects.interface.attachments import detach_item, item_cited
from waterfall.core.projects.interface.contributors import require_project_manager
from waterfall.core.projects.interface.lifecycle import no_background_task_running
from waterfall.core.projects.tables import Deliverable, OrderItem, Project, WorkPackage
from waterfall.platform.database import contains
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
    json_pointer,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface.projects import Viewer
    from waterfall.platform.audit import Act

UNKNOWN_WORK_BREAKDOWN_ITEM = "UNKNOWN_WORK_BREAKDOWN_ITEM"
DUPLICATE_WORK_BREAKDOWN_ITEM = "DUPLICATE_WORK_BREAKDOWN_ITEM"
ALREADY_EXISTS = "ALREADY_EXISTS"
# The natures of the elements, as the contract says them (``WorkBreakdownKind``).
WORK_PACKAGE = "work_package"
ORDER_ITEM = "order_item"
DELIVERABLE = "deliverable"
# Where a position is parked while the slots are exchanged: above any position a project may hold.
PARKED = 1_000_000_000
# The counter a project is born with, its work breakdown included: a work breakdown that still
# reads it has not been written (#2762).
BORN_LOCK_VERSION = 1

type Row = WorkPackage | OrderItem | Deliverable


@dataclass(frozen=True, slots=True)
class DeliverableView:
    """A deliverable as the reading gives it; ``is_match`` tells whether the filters retain it."""

    deliverable_id: UUID
    label: str
    is_match: bool


@dataclass(frozen=True, slots=True)
class OrderItemView:
    """An order item as the reading gives it, with the deliverables the filters keep under it."""

    order_item_id: UUID
    label: str
    is_match: bool
    deliverables: tuple[DeliverableView, ...]


@dataclass(frozen=True, slots=True)
class WorkPackageView:
    """A work package as the reading gives it, with the order items the filters keep under it."""

    work_package_id: UUID
    label: str
    is_match: bool
    order_items: tuple[OrderItemView, ...]


@dataclass(frozen=True, slots=True)
class WorkBreakdownRead:
    """The work breakdown read, and its counter: null for a filtered reading."""

    work_packages: tuple[WorkPackageView, ...]
    lock_version: int | None


@dataclass(frozen=True, slots=True)
class WorkBreakdownFilters:
    """What a reading keeps: a search on the label, natures; both must be satisfied."""

    search: str | None = None
    kinds: frozenset[str] | None = None

    @property
    def is_filtered(self) -> bool:
        """Whether the reading omits elements: the counter it gives would not do to write."""
        return self.search is not None or self.kinds is not None


@dataclass(frozen=True, slots=True)
class DeliverableEntry:
    """A deliverable written: new if it has no identifier."""

    label: str
    deliverable_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class OrderItemEntry:
    """An order item written, with its deliverables in their order."""

    label: str
    deliverables: tuple[DeliverableEntry, ...]
    order_item_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class WorkPackageEntry:
    """A work package written, with its order items in their order."""

    label: str
    order_items: tuple[OrderItemEntry, ...]
    work_package_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class WorkBreakdownToWrite:
    """The whole work breakdown written, at the counter of the one read."""

    work_packages: tuple[WorkPackageEntry, ...]
    lock_version: int


@dataclass(frozen=True, slots=True)
class WorkBreakdownLoad:
    """The work breakdown the witness imposes on a project: every element bears its identifier."""

    project_id: UUID
    work_packages: tuple[WorkPackageEntry, ...]
    lock_version: int


@dataclass(frozen=True, slots=True)
class WorkBreakdownItem:
    """A work package or an order item a task may bear, marked deleted or not (WF-PLA-0170).

    ``kind`` is ``work_package`` or ``order_item``; ``work_package_id`` the work package of an
    order item, none for a work package.
    """

    item_id: UUID
    kind: str
    label: str
    work_package_id: UUID | None
    deleted: bool


@dataclass(slots=True)
class _Node:
    """An element met by the reading, with whether its own label satisfies the search."""

    id: UUID
    label: str
    hit: bool
    children: dict[UUID, _Node]


@dataclass(frozen=True, slots=True)
class _Planned:
    """An element as the writing leaves it: its identifier, its parent, its label, its position."""

    id: UUID
    parent_id: UUID | None
    label: str
    position: int


def _tree(session: Session, project_id: UUID, search: str | None) -> tuple[int, dict[UUID, _Node]]:
    """Read the counter and the tree in one statement; or refuse (404)."""
    packages, items, deliverables = WorkPackage, OrderItem, Deliverable
    rows = session.execute(
        select(
            Project.work_breakdown_lock_version,
            packages.id,
            packages.label,
            items.id,
            items.label,
            deliverables.id,
            deliverables.label,
            *(
                (true(), true(), true())
                if search is None
                else (
                    contains(packages.label, search),
                    contains(items.label, search),
                    contains(deliverables.label, search),
                )
            ),
        )
        .select_from(Project)
        .outerjoin(packages, (packages.project_id == Project.id) & packages.deleted_at.is_(None))
        .outerjoin(items, (items.work_package_id == packages.id) & items.deleted_at.is_(None))
        .outerjoin(deliverables, deliverables.order_item_id == items.id)
        .where(Project.id == project_id)
        .order_by(packages.position, items.position, deliverables.position)
    ).all()
    if not rows:
        raise NotFoundError(NOT_FOUND)
    tree: dict[UUID, _Node] = {}
    for row in rows:
        # The outer joins give an element without children its columns null.
        (_, package_id, package, item_id, item, deliverable_id, deliverable, *hits) = cast(
            "tuple[int, UUID | None, str, UUID | None, str, UUID | None, str, bool, bool, bool]",
            tuple(row),
        )
        package_hit, item_hit, deliverable_hit = (bool(hit) for hit in hits)
        if package_id is None:
            continue
        node = tree.setdefault(package_id, _Node(package_id, package, package_hit, {}))
        if item_id is None:
            continue
        node = node.children.setdefault(item_id, _Node(item_id, item, item_hit, {}))
        if deliverable_id is not None:
            node.children[deliverable_id] = _Node(deliverable_id, deliverable, deliverable_hit, {})
    return rows[0][0], tree


def _shown(kinds: frozenset[str] | None, nature: str, node: _Node) -> bool:
    """Tell whether the filters retain an element: its nature is asked for and its label found."""
    return (kinds is None or nature in kinds) and node.hit


def _retained(
    session: Session, project_id: UUID, filters: WorkBreakdownFilters
) -> WorkBreakdownRead:
    counter, tree = _tree(session, project_id, filters.search)
    kinds = filters.kinds
    packages: list[WorkPackageView] = []
    for package in tree.values():
        items: list[OrderItemView] = []
        for item in package.children.values():
            deliverables = tuple(
                DeliverableView(deliverable.id, deliverable.label, is_match=True)
                for deliverable in item.children.values()
                if _shown(kinds, DELIVERABLE, deliverable)
            )
            item_match = _shown(kinds, ORDER_ITEM, item)
            if item_match or deliverables:
                items.append(OrderItemView(item.id, item.label, item_match, deliverables))
        package_match = _shown(kinds, WORK_PACKAGE, package)
        if package_match or items:
            packages.append(WorkPackageView(package.id, package.label, package_match, tuple(items)))
    return WorkBreakdownRead(tuple(packages), None if filters.is_filtered else counter)


def read_work_breakdown(
    session: Session, project_id: UUID, filters: WorkBreakdownFilters
) -> WorkBreakdownRead:
    """Read the work breakdown of a project, whole or filtered (``getWorkBreakdown``).

    In the order it was entered. An element is retained when it satisfies every filter — its label
    holds the text searched, its nature is one asked for —; the work packages and order items that
    hold a retained element are given with it, marked not retained, and without the elements they
    hold that are not. The counter is null for a filtered reading, which omits elements: written
    back as it is, it would delete them. Refused if the project does not exist (404).
    """
    return _retained(session, project_id, filters)


def _locked(session: Session, project_id: UUID) -> Project:
    """Lock the row of a project, then read it under the lock; or refuse (404)."""
    project = session.scalars(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if project is None:
        raise NotFoundError(NOT_FOUND)
    return project


def _held(
    session: Session, project_id: UUID
) -> tuple[dict[UUID, WorkPackage], dict[UUID, OrderItem], dict[UUID, Deliverable]]:
    """Read the elements the project holds, those marked deleted left out, under the lock."""
    packages = {
        row.id: row
        for row in session.scalars(
            select(WorkPackage).where(
                WorkPackage.project_id == project_id, WorkPackage.deleted_at.is_(None)
            )
        )
    }
    items = {
        row.id: row
        for row in session.scalars(
            select(OrderItem).where(
                OrderItem.project_id == project_id, OrderItem.deleted_at.is_(None)
            )
        )
    }
    deliverables = {
        row.id: row
        for row in session.scalars(select(Deliverable).where(Deliverable.project_id == project_id))
    }
    return packages, items, deliverables


def _faults(
    entries: Sequence[WorkPackageEntry],
    packages: Iterable[UUID],
    items: Iterable[UUID],
    deliverables: Iterable[UUID],
) -> list[FieldError]:
    """Point at each identifier the work breakdown read does not hold under its nature, or doubled.

    An identifier sent a second time is a duplicate, whatever it names: only the first occurrence
    is judged.
    """
    known = {
        "work_package_id": frozenset(packages),
        "order_item_id": frozenset(items),
        "deliverable_id": frozenset(deliverables),
    }
    seen: set[UUID] = set()
    faults: list[FieldError] = []

    def judge(pointer: tuple[str | int, ...], name: str, sent: UUID | None) -> None:
        if sent is None:
            return
        place = json_pointer(*pointer, name)
        if sent in seen:
            faults.append(FieldError(place, DUPLICATE_WORK_BREAKDOWN_ITEM))
        elif sent not in known[name]:
            faults.append(FieldError(place, UNKNOWN_WORK_BREAKDOWN_ITEM))
        seen.add(sent)

    for p, package in enumerate(entries):
        judge(("work_packages", p), "work_package_id", package.work_package_id)
        for i, item in enumerate(package.order_items):
            at_item = ("work_packages", p, "order_items", i)
            judge(at_item, "order_item_id", item.order_item_id)
            for d, deliverable in enumerate(item.deliverables):
                judge((*at_item, "deliverables", d), "deliverable_id", deliverable.deliverable_id)
    return faults


def _plan(
    entries: Iterable[WorkPackageEntry],
) -> tuple[list[_Planned], list[_Planned], list[_Planned]]:
    """Give each element its identifier — engendered if it has none — and its place."""
    packages: list[_Planned] = []
    items: list[_Planned] = []
    deliverables: list[_Planned] = []
    for p, package in enumerate(entries):
        package_id = new_id() if package.work_package_id is None else package.work_package_id
        packages.append(_Planned(package_id, None, package.label, p))
        for i, item in enumerate(package.order_items):
            item_id = new_id() if item.order_item_id is None else item.order_item_id
            items.append(_Planned(item_id, package_id, item.label, i))
            for d, deliverable in enumerate(item.deliverables):
                deliverable_id = (
                    new_id() if deliverable.deliverable_id is None else deliverable.deliverable_id
                )
                deliverables.append(_Planned(deliverable_id, item_id, deliverable.label, d))
    return packages, items, deliverables


def _parent(row: Row) -> UUID | None:
    if isinstance(row, OrderItem):
        return row.work_package_id
    if isinstance(row, Deliverable):
        return row.order_item_id
    return None


def _park(session: Session, held: Mapping[UUID, Row], planned: Iterable[_Planned]) -> None:
    """Park the position of every element that leaves its slot, so that no slot is held twice.

    The slots are unique under their parent: an element that exchanges its place with another, or
    takes that of one left out, would break them at its own statement. Every element that changes
    place or leaves is parked first, above any position; the places are then free.
    """
    staying = {plan.id for plan in planned if plan.id in held and _same_place(held[plan.id], plan)}
    for turn, row in enumerate(row for id_, row in held.items() if id_ not in staying):
        row.position = PARKED + turn
    session.flush()


def _same_place(row: Row, plan: _Planned) -> bool:
    return _parent(row) == plan.parent_id and row.position == plan.position


@dataclass(frozen=True, slots=True)
class _Scope:
    """What a writing is done in: the transaction, the project, and who acts when."""

    session: Session
    project_id: UUID
    act: Act


def _write_level[Model: Row](
    scope: _Scope, held: dict[UUID, Model], planned: Iterable[_Planned], make: type[Model]
) -> None:
    """Write the elements of a level: those held are changed where they differ, the others added."""
    session, act = scope.session, scope.act
    for plan in planned:
        row = held.get(plan.id)
        if row is None:
            row = make(
                id=plan.id,
                project_id=scope.project_id,
                label=plan.label,
                position=plan.position,
                created_at=act.at,
                created_by=act.author,
                updated_at=act.at,
                updated_by=act.author,
            )
            _attach(row, plan.parent_id)
            session.add(row)
            continue
        changed = row.label != plan.label or not _same_place(row, plan)
        row.label = plan.label
        row.position = plan.position
        _attach(row, plan.parent_id)
        if changed:
            _stamp(row, act.at, act.author)
    session.flush()


def _stamp(row: Row, at: datetime, author: UUID | None) -> None:
    row.updated_at = at
    row.updated_by = author


def _attach(row: Row, parent_id: UUID | None) -> None:
    if isinstance(row, OrderItem) and parent_id is not None:
        row.work_package_id = parent_id
    elif isinstance(row, Deliverable) and parent_id is not None:
        row.order_item_id = parent_id


def _replace(
    session: Session, project: Project, entries: Sequence[WorkPackageEntry], act: Act
) -> None:
    """Write the work breakdown whole: park, write each level from the top, delete what is left out.

    A parent is written before what it holds, so that an element moved under a new parent finds
    it; an element left out is deleted after everything has left it — deliverables, order items,
    then work packages — and its position was parked, so that nothing waits for its slot.
    """
    packages, items, deliverables = _held(session, project.id)
    plan_packages, plan_items, plan_deliverables = _plan(entries)
    _park(session, packages, plan_packages)
    _park(session, items, plan_items)
    _park(session, deliverables, plan_deliverables)
    scope = _Scope(session, project.id, act)
    _write_level(scope, packages, plan_packages, WorkPackage)
    _write_level(scope, items, plan_items, OrderItem)
    _write_level(scope, deliverables, plan_deliverables, Deliverable)
    for row in _leaving(deliverables, plan_deliverables):
        session.delete(row)
    session.flush()
    _remove(scope, _leaving(items, plan_items), _leaving(packages, plan_packages))


def _leaving[Model: Row](held: Mapping[UUID, Model], planned: Iterable[_Planned]) -> list[Model]:
    """Give the elements held that the writing leaves out."""
    kept = {plan.id for plan in planned}
    return [row for id_, row in held.items() if id_ not in kept]


def _remove(scope: _Scope, items: list[OrderItem], packages: list[WorkPackage]) -> None:
    """Remove the order items and the work packages left out, from the tasks first (WF-PLA-0170).

    Their rows are locked before any task is touched: a write of the planning that attaches one
    reads it under a shared lock, and waits, or is waited for, before it writes its task. Each is
    withdrawn from the tasks of the current revision, then marked deleted when a task of a marked
    revision bears it — a work package also when an order item marked deleted is still under it,
    which its key keeps —, deleted for good otherwise.
    """
    session, act = scope.session, scope.act
    leaving = [row.id for row in (*items, *packages)]
    if not leaving:
        return
    for table in (WorkPackage, OrderItem):  # the order of ``work_breakdown_items``: no deadlock
        session.execute(select(table.id).where(table.id.in_(leaving)).with_for_update())
    for item_id in leaving:
        detach_item(session, scope.project_id, item_id)
    for item in items:
        _drop(session, item, act, kept=item_cited(session, item.id))
    session.flush()
    for package in packages:
        under = session.scalar(
            select(OrderItem.id).where(OrderItem.work_package_id == package.id).limit(1)
        )
        _drop(session, package, act, kept=under is not None or item_cited(session, package.id))
    session.flush()


def _drop(session: Session, row: WorkPackage | OrderItem, act: Act, *, kept: bool) -> None:
    """Mark an element deleted when something still cites it, delete it for good otherwise."""
    if kept:
        row.deleted_at = act.at
        _stamp(row, act.at, act.author)
    else:
        session.delete(row)


def set_work_breakdown(
    session: Session, project_id: UUID, write: WorkBreakdownToWrite, act: Act, viewer: Viewer
) -> WorkBreakdownRead:
    """Write the whole work breakdown of a project at the counter read (``setWorkBreakdown``).

    Under the lock of the project, a writer who is no project manager any more is refused (403,
    404; ``require_project_manager``), then a terminal project (409, ``project_not_terminal``),
    then one that a task of the background is writing in (409, ``no_background_task_running``), a
    counter that is not the project's (412), and each identifier that names no element of its
    nature, or that is sent twice (422, at its field). Nothing is written then. An element sent
    without identifier is new and receives one; an element left out is deleted. The work breakdown
    is answered whole with its next counter, built before the commit.
    """
    project = _locked(session, project_id)
    require_project_manager(session, project_id, viewer)
    if project.state in TERMINAL:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": PROJECT_NOT_TERMINAL})
    if not no_background_task_running(session, project_id):
        raise ConflictError(
            STATE_FORBIDS_OPERATION, {"missing_condition": NO_BACKGROUND_TASK_RUNNING}
        )
    if project.work_breakdown_lock_version != write.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": project.work_breakdown_lock_version}
        )
    packages, items, deliverables = _held(session, project_id)
    faults = _faults(write.work_packages, packages, items, deliverables)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    _replace(session, project, write.work_packages, act)
    project.work_breakdown_lock_version += 1
    session.flush()
    return _retained(session, project_id, WorkBreakdownFilters())


def work_breakdown_present(session: Session, ids: Iterable[UUID]) -> frozenset[UUID]:
    """Name, of the identifiers given, those that an element of a work breakdown bears."""
    wanted = list(ids)
    return frozenset(
        found
        for table in (WorkPackage, OrderItem, Deliverable)
        for found in session.scalars(select(table.id).where(table.id.in_(wanted)))
    )


def work_breakdown_items(
    session: Session, project_id: UUID, *, shared: Collection[UUID] = ()
) -> dict[UUID, WorkBreakdownItem]:
    """Read the work packages and the order items of a project, those marked deleted included.

    ``shared`` names elements to lock ``FOR SHARE`` before the reading: a write that attaches a
    task to one reads it under that lock, so that ``set_work_breakdown`` neither deletes nor marks
    it meanwhile (WF-PLA-0170). By identifier; an element of another project is not given.
    """
    if shared:
        for table in (WorkPackage, OrderItem):
            session.execute(
                select(table.id)
                .where(table.project_id == project_id, table.id.in_(list(shared)))
                .with_for_update(read=True)
            )
    found = {
        row.id: WorkBreakdownItem(row.id, WORK_PACKAGE, row.label, None, row.deleted_at is not None)
        for row in session.scalars(
            select(WorkPackage)
            .where(WorkPackage.project_id == project_id)
            .execution_options(populate_existing=True)
        )
    }
    for row in session.scalars(
        select(OrderItem)
        .where(OrderItem.project_id == project_id)
        .execution_options(populate_existing=True)
    ):
        deleted = row.deleted_at is not None
        found[row.id] = WorkBreakdownItem(
            row.id, ORDER_ITEM, row.label, row.work_package_id, deleted
        )
    return found


def follow_project_label(session: Session, project: Project, label: str, act: Act) -> None:
    """Make the work package and the order item of the birth bear a new label of the project.

    They follow the label of the project (D-11) while no writing has set the work breakdown, that
    is while its counter is the one of its birth; written once, they are the writing's and stay as
    it set them. To be called under the lock of the project, which ``update_project`` holds.
    """
    if project.work_breakdown_lock_version != BORN_LOCK_VERSION:
        return
    packages, items, _ = _held(session, project.id)
    for row in (*packages.values(), *items.values()):
        if row.label != label:
            row.label = label
            _stamp(row, act.at, act.author)
    session.flush()


def load_work_breakdown(session: Session, load: WorkBreakdownLoad, act: Act) -> None:
    """Write the work breakdown of a project of the witness, as it imposes it, with its counter.

    It replaces the one the project was born with, which nothing has written yet: a project whose
    work breakdown was written is refused (409, ``ALREADY_EXISTS``), as the witness never
    overwrites what a platform holds. The identifiers the witness imposes are kept.
    """
    project = _locked(session, load.project_id)
    if project.work_breakdown_lock_version != BORN_LOCK_VERSION:
        raise ConflictError(ALREADY_EXISTS, {"conflicting_object_id": str(project.id)})
    _replace(session, project, load.work_packages, act)
    project.work_breakdown_lock_version = load.lock_version
    session.flush()
