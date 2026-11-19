# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The part of the estimate in the update of a differential (US-3050; EP-08, "Modules").

Its part of ``register_rebase``, after the planning's, whose plan says where each line stands
(``rebased_lines``). What a line designates is, as for a merge, its columns — its label, its
category, its role, its quantity, its hours, its unit disbursement, its subproject, its delay of
payment, in the order of ``NodeColumn`` — and its task (``parent``); the differential and the main
structure are each compared with the base of the differential, by the lineage:

- a line the main structure adds enters the differential (``added``), under its task, or the task
  its own goes to when the differential removed it; a column it changes is taken (``updated``); a
  line it removes leaves the differential (``removed``);
- a column the differential changes too keeps the differential's (``kept``, its columns named):
  for the figures of a line, the rule of WF-REV-0050 — the merge gives them to the line as its
  reference, and the main structure keeps its current ones, re-estimated (rule 1);
- a line the differential modifies and the main structure removes stays, as an addition (rule 2),
  and a line it adds under a task that leaves stays too (rule 3), each under the task the planning
  says its own goes to, signalled (``kept``).

The provision lines stay out (#4008): a base holds none, nor a differential. Then what refuses the
update: a task whose lines, once updated, would name roles whose calendars share no working hour in
the week (``TASK_WITHOUT_WORKING_HOURS``, WF-PLA-0010) — judged on every task the update leaves,
which the engine replayed could not place, each named by its node in the differential and its
label, or, for a task the main structure adds, by its lineage. And the calendars of every task it
leaves, which the end of the planning reads to replay the engine (``hand_calendars``).

Written by US-3050/L3.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.estimate.costing import TASK_WITHOUT_WORKING_HOURS, calendar_hours
from waterfall.core.estimate.interface.merging import COLUMNS, LINE
from waterfall.core.estimate.reading import line_rows
from waterfall.core.planning.interface import hand_calendars, rebased_lines
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
    """

    where: RebasedLines
    differences: list[Json] = field(default_factory=list[Json])
    roles: dict[UUID, set[UUID]] = field(default_factory=dict[UUID, set[UUID]])

    def placed(self, task: UUID) -> UUID | None:
        """Give the task a line goes under once updated: its own, or where its own goes."""
        return task if task in self.where.tasks else self.where.staying.get(task)

    def leave(self, line: tuple[UUID, str], task: UUID, role: UUID | None) -> bool:
        """Leave a line under the task it goes to, its role counted; false if none remains.

        A line no task remains for leaves the differential, which says so (``removed``).
        """
        placed = self.placed(task)
        if placed is None:
            self.differences.append(_difference("removed", line, []))
            return False
        if role is not None:
            self.roles.setdefault(placed, set()).add(role)
        return True

    def kept(self, line: tuple[UUID, str], task: UUID, role: UUID | None) -> None:
        """Keep a line the rules 2 or 3 keep, signalled, under the task it goes to."""
        if self.leave(line, task, role):
            self.differences.append(_difference("kept", line, []))

    def both(self, own: _Line, old: _Line, new: _Line) -> None:
        """Carry what the main structure changes of a line, keep what the differential changes."""
        designates, received = _fields(old, own), _fields(old, new)
        carried = received - designates
        kept = frozenset(
            name for name in received & designates if new.value(name) != own.value(name)
        )
        taken = new if "label" in carried else own
        named = (own.lineage, taken.row.label)
        role = (new if "resource_role" in carried else own).row.resource_role_id
        if not self.leave(named, (new if PARENT in carried else own).task, role):
            return
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
        elif _fields(old, line):
            # Rule 2: a line the differential modifies stays, as an addition.
            found.kept(named, line.task, role)
        else:
            found.differences.append(_difference("removed", named, []))
    for lineage, line in main.items():
        if lineage not in own and lineage not in base:
            named = (lineage, line.row.label)
            if found.leave(named, line.task, line.row.resource_role_id):
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


def rebase_lines(rebasing: StructureRebasing) -> RebasePart:
    """Give the part of the estimate in an update: lines carried or kept, and what refuses it.

    Hands the end of the planning the calendars of the tasks the update leaves.
    """
    where = rebased_lines(rebasing)
    lines = _read(rebasing, where)
    found = _found(where, lines)
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
    refusals = tuple(_refusals(rebasing, found, calendars))
    return RebasePart(differences=tuple(found.differences), refusals=refusals)
