# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The part of the estimate in the update of a differential (US-3050; EP-08, "Modules").

Its part of ``register_rebase``, after the planning's, whose plan says where each line stands
(``rebased_lines``). What a line designates is, as for a merge, its columns — its label, its
category, its role, its quantity, its hours, its unit disbursement, its subproject, its delay of
payment, in the order of ``NodeColumn`` — and its task (``parent``); the differential and the main
structure are each compared with the base of the differential, by the lineage:

- a line the main structure adds enters the differential (``added``), under its task, or, when the
  differential removed it, under its nearest ancestor that remains — none from the first level, and
  the line does not enter, as a link the main structure adds to the task does not —; a column it
  changes is taken (``updated``); a line it removes leaves the differential (``removed``);
- a column the differential changes too keeps the differential's (``kept``, its columns named):
  for the figures of a line, the rule of WF-REV-0050 — the merge gives them to the line as its
  reference, and the main structure keeps its current ones, re-estimated (rule 1);
- a line the differential modifies and the main structure removes stays, as an addition (rule 2),
  and a line it adds under a task that leaves stays too (rule 3), each under the task the planning
  says its own goes to, signalled (``kept``); a line of the base it moves under a task that leaves
  goes there likewise, its parent named — the line it modifies and the main structure removes as
  well, under a task that leaves.

The provision lines stay out (#4008): a base holds none, nor a differential. Then what refuses the
update: a task whose lines, once updated, would name roles whose calendars share no working hour in
the week (``TASK_WITHOUT_WORKING_HOURS``, WF-PLA-0010) — judged on every task the update leaves,
which the engine replayed could not place, each named by its node in the differential and its
label, or, for a task the main structure adds, by its lineage. And the calendars of every task it
leaves, which the end of the planning reads to replay the engine (``hand_calendars``).

The application (``StructureRebasing.applying``, US-3050/L4) writes what the same computation finds:
the planning writes the nodes of the lines where they go (``place_rebased_lines``), after its tasks;
the estimate then writes their facets — a line the main structure adds is a copy of the main
structure's, its figures as they are, a column carried is taken —, and the lines are priced again
by the replay of the dates that ends the update.

Written by US-3050/L3; the application by US-3050/L4.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.estimate.costing import TASK_WITHOUT_WORKING_HOURS, calendar_hours
from waterfall.core.estimate.interface.merging import COLUMNS, LINE
from waterfall.core.estimate.reading import line_rows, rows_of
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import (
    LinesPlaced,
    hand_calendars,
    place_rebased_lines,
    rebased_lines,
)
from waterfall.core.resource_settings.interface import read_roles, role_calendars
from waterfall.core.revisions.interface import RebasePart

if TYPE_CHECKING:
    from collections.abc import Iterator

    from waterfall.core.estimate.reading import LineRow
    from waterfall.core.planning.interface import RebasedLines
    from waterfall.core.revisions.interface import StructureRebasing

type Json = dict[str, Any]
PARENT = "parent"
# The fields of a line, as the differences name them: its columns, then its task.
FIELDS = (*(name for name, _ in COLUMNS), PARENT)
_COLUMN = dict(COLUMNS)


@dataclass(frozen=True, slots=True)
class _Line:
    """A line of a structure: its lineage, its node, the lineage of its task, its columns."""

    lineage: UUID
    node_id: UUID
    task: UUID
    row: LineRow

    def value(self, name: str) -> object:
        """Give the value of a field of the line, its task for the parent."""
        return self.task if name == PARENT else getattr(self.row, _COLUMN[name])


def _fields(old: _Line, new: _Line) -> frozenset[str]:
    """Name the fields that differ between two states of a line, by lineage."""
    return frozenset(name for name in FIELDS if old.value(name) != new.value(name))


def _ordered(names: frozenset[str]) -> list[str]:
    """Give fields in the order of ``NodeColumn``, then the parent."""
    return [name for name in FIELDS if name in names]


def _difference(change: str, named: tuple[UUID, str], fields: list[str]) -> Json:
    """Give a difference of a line the update carries or keeps (``ImportDifference``)."""
    lineage, label = named
    return {
        "change": change,
        "target": LINE,
        "lineage_id": str(lineage),
        "label": label,
        "predecessor_label": None,
        "fields": fields,
    }


def _read(rebasing: StructureRebasing, where: RebasedLines) -> tuple[dict[UUID, _Line], ...]:
    """Read the lines of the base, the differential and the main structure, by lineage.

    The provision lines left out: a base and a differential hold none.
    """
    sides = (where.base, where.structure, where.main)
    nodes = [each.node_id for side in sides for each in side]
    rows = {row.node_id: row for row in line_rows(rebasing.session, rebasing.project_id, nodes)}
    return tuple(
        {
            each.lineage_id: _Line(
                each.lineage_id, each.node_id, each.task_lineage_id, rows[each.node_id]
            )
            for each in side
            if not each.is_provision
        }
        for side in sides
    )


@dataclass(slots=True)
class _Update:
    """What the estimate finds of an update, as it goes: its differences, the roles it leaves.

    ``roles`` the roles of the lines each task the update leaves bears once updated, by lineage.
    What the application writes of them: ``placed`` the task each line of the differential ends
    under, none for one that leaves; ``by_main`` those whose place the main structure gives;
    ``updates`` the columns each takes of the main structure's line, with that line; ``created``
    each line the main structure adds, with the task it enters under.
    """

    where: RebasedLines
    differences: list[Json] = field(default_factory=list[Json])
    roles: dict[UUID, set[UUID]] = field(default_factory=dict[UUID, set[UUID]])
    placed: dict[UUID, UUID | None] = field(default_factory=dict[UUID, UUID | None])
    by_main: set[UUID] = field(default_factory=set[UUID])
    updates: dict[UUID, tuple[frozenset[str], _Line]] = field(
        default_factory=dict[UUID, tuple[frozenset[str], _Line]]
    )
    created: dict[UUID, tuple[_Line, UUID]] = field(default_factory=dict[UUID, tuple[_Line, UUID]])

    def placed_under(self, task: UUID, *, held: bool = True) -> UUID | None:
        """Give the task a line goes under once updated: its own, or where its own goes.

        From the first level, the first task of the plan for a line the differential ``held``,
        none for one the main structure adds.
        """
        if task in self.where.tasks:
            return task
        staying = self.where.staying.get(task)
        return self.where.first if staying is None and held else staying

    def leave(
        self, line: tuple[UUID, str], task: UUID, role: UUID | None, *, held: bool = True
    ) -> UUID | None:
        """Leave a line under the task it goes to, its role counted; give it, none if none remains.

        A line of the differential no task remains for leaves it, which says so (``removed``); one
        the main structure adds does not enter it, unnamed.
        """
        placed = self.placed_under(task, held=held)
        if held:
            self.placed[line[0]] = placed
        if placed is None:
            if held:
                self.differences.append(_difference("removed", line, []))
            return None
        if role is not None:
            self.roles.setdefault(placed, set()).add(role)
        return placed

    def kept(
        self,
        line: tuple[UUID, str],
        task: UUID,
        role: UUID | None,
        fields: frozenset[str] = frozenset(),
    ) -> None:
        """Keep a line the rules 2 or 3 keep, signalled, under the task it goes to.

        ``fields`` its parent, for a line the differential moved under a task that leaves.
        """
        if self.leave(line, task, role) is not None:
            self.differences.append(_difference("kept", line, _ordered(fields)))

    def both(self, own: _Line, old: _Line, new: _Line) -> None:
        """Carry what the main structure changes of a line, keep what the differential changes.

        A task the differential moves the line to and that leaves keeps its parent, named (rule 3).
        """
        designates, received = _fields(old, own), _fields(old, new)
        carried = received - designates
        kept = frozenset(
            name for name in received & designates if new.value(name) != own.value(name)
        )
        task = (new if PARENT in carried else own).task
        if PARENT in designates and task not in self.where.tasks:
            kept |= {PARENT}
        taken = new if "label" in carried else own
        named = (own.lineage, taken.row.label)
        role = (new if "resource_role" in carried else own).row.resource_role_id
        placed = self.leave(named, task, role)
        if placed is None:
            return
        if PARENT in carried and placed == task:
            self.by_main.add(own.lineage)
        if carried - {PARENT}:
            self.updates[own.lineage] = (carried - {PARENT}, new)
        if carried:
            self.differences.append(_difference("updated", named, _ordered(carried)))
        if kept:
            self.differences.append(_difference("kept", named, _ordered(kept)))


def _found(where: RebasedLines, lines: tuple[dict[UUID, _Line], ...]) -> _Update:
    """Find what the update carries and keeps of the lines, in the order of the differential.

    Then the lines the main structure adds, in its order.
    """
    base, own, main = lines
    found = _Update(where)
    for lineage, line in own.items():
        named = (lineage, line.row.label)
        role = line.row.resource_role_id
        old, new = base.get(lineage), main.get(lineage)
        if old is None:
            # Rule 3: a line the differential adds under a task that leaves.
            if line.task in where.tasks:
                found.leave(named, line.task, role)
            else:
                found.kept(named, line.task, role)
        elif new is not None:
            found.both(line, old, new)
        elif designates := _fields(old, line):
            # Rule 2: a line the differential modifies stays, as an addition; moved under a task
            # that leaves, it goes under the task its own goes to, its parent named (rule 3).
            moved = PARENT in designates and line.task not in where.tasks
            found.kept(named, line.task, role, frozenset({PARENT}) if moved else frozenset())
        else:
            found.placed[lineage] = None
            found.differences.append(_difference("removed", named, []))
    for lineage, line in main.items():
        if lineage not in own and lineage not in base:
            named = (lineage, line.row.label)
            placed = found.leave(named, line.task, line.row.resource_role_id, held=False)
            if placed is not None:
                found.created[lineage] = (line, placed)
                found.differences.append(_difference("added", named, []))
    return found


def _refusals(
    rebasing: StructureRebasing,
    found: _Update,
    calendars: dict[UUID, UUID],
) -> Iterator[Json]:
    """Refuse each task the update leaves whose roles' calendars share no hour in the week.

    The roles of its lines, once updated, intersected day by day, as an entry judges them
    (WF-PLA-0010); the task by its node in the differential, or by its lineage when the main
    structure adds it, as the report names its objects. ``calendars`` the calendar of each role.
    """
    session = rebasing.session
    weeks = calendar_hours(session, set(calendars.values()))
    for task, named in found.where.tasks.items():
        held = found.roles.get(task, set())
        if not held:
            continue
        days = [weeks[calendars[role]] for role in held if role in calendars]
        if any(min(day) > 0 for day in zip(*days, strict=True)):
            continue
        roles = [
            {"resource_role_id": str(role.resource_role_id), "code": role.code, "label": role.label}
            for role in read_roles(session, held, may_change=False)
        ]
        if named.node_id is None:
            bearer: Json = {"lineage_id": str(task), "label": named.label}
        else:
            node = str(named.node_id)
            bearer = {"project_id": str(rebasing.project_id), "node_id": node, "label": named.label}
        yield {
            "code": TASK_WITHOUT_WORKING_HOURS,
            "params": {"resource_roles": roles, "tasks": [bearer]},
        }


def _copied(taken: EstimateLine, node_id: UUID, rebasing: StructureRebasing) -> EstimateLine:
    """Give the facet of a line the main structure adds, as the main structure's, under its node.

    Every column as it is — its budgeted amount, its remaining to commit before, the mark of its
    last re-estimate —, at its first version, as the copy of a structure into another does.
    """
    act = rebasing.act
    columns = {each.key: getattr(taken, each.key) for each in EstimateLine.__table__.columns}
    columns.update(
        node_id=node_id,
        lock_version=1,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
    )
    return EstimateLine(**columns)


def _write(
    rebasing: StructureRebasing, found: _Update, lines: tuple[dict[UUID, _Line], ...]
) -> None:
    """Write what the update finds of the lines: their nodes by the planning, then their facets.

    A column carried is taken of the main structure's line, the counter of the line advancing; a
    line the main structure adds is a copy of the main structure's (``_copied``). The amounts are
    priced again by the replay of the dates, which ends the update.
    """
    session, project_id, act = rebasing.session, rebasing.project_id, rebasing.act
    _, own, _ = lines
    created = {lineage: task for lineage, (_, task) in found.created.items()}
    placed = LinesPlaced(found.placed, created, frozenset(found.by_main), frozenset(found.updates))
    nodes = place_rebased_lines(rebasing, placed)
    sources = [new.node_id for _, new in found.updates.values()]
    sources += [line.node_id for line, _ in found.created.values()]
    taken = {each.node_id: each for each in rows_of(session, project_id, sources)}
    changed = [own[each].node_id for each in found.updates]
    held = {each.node_id: each for each in rows_of(session, project_id, changed)}
    for lineage, (names, new) in found.updates.items():
        row, source = held[own[lineage].node_id], taken[new.node_id]
        for name in names:
            setattr(row, _COLUMN[name], getattr(source, _COLUMN[name]))
        row.lock_version += 1
        row.updated_at, row.updated_by = act.at, act.author
    for lineage, (line, _) in found.created.items():
        session.add(_copied(taken[line.node_id], nodes[lineage], rebasing))
    session.flush()


def rebase_lines(rebasing: StructureRebasing) -> RebasePart:
    """Give the part of the estimate in an update: lines carried or kept, and what refuses it.

    Hands the end of the planning the calendars of the tasks the update leaves. The application
    writes the lines first, and judges no refusal: it judged them before it wrote.
    """
    where = rebased_lines(rebasing)
    lines = _read(rebasing, where)
    found = _found(where, lines)
    if rebasing.applying:
        _write(rebasing, found, lines)
    calendars = role_calendars(
        rebasing.session, {role for held in found.roles.values() for role in held}
    )
    hand_calendars(
        rebasing,
        {
            task: frozenset(
                calendars[role] for role in found.roles.get(task, ()) if role in calendars
            )
            for task in where.tasks
        },
    )
    refusals = () if rebasing.applying else tuple(_refusals(rebasing, found, calendars))
    return RebasePart(differences=tuple(found.differences), refusals=refusals)
