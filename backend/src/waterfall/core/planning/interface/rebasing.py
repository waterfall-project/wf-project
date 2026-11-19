# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The part of the planning in the update of a differential (US-3050; EP-08, "Modules").

``rebase_tasks`` is its part of ``register_rebase``: what the update carries from the main structure
into the differential, tasks and links, and what the differential keeps against it, by the four
rules (``rebasing``); ``rebase_end`` its part of ``register_rebase_end``: what refuses the update,
judged once on the differential it leaves, the engine replayed (WF-PLA-0030, WF-PLA-0150). The
estimate, whose part comes after, reads of the same plan where each line stands (``rebased_lines``):
the lines of the three structures by the lineage of their task, the tasks the update leaves, and
where the lines of a task that leaves go — to the nearest ancestor that remains; from the first
level, a line the differential holds goes to the first task of the first level, as a provision line
does at a merge (WF-RIS-0010; #789), and one the main structure adds does not enter, as a link it
adds to the task does not. It hands the end the calendars its lines will name
(``RebasedCalendars``).

``designated`` gives what a structure designates against its base, by lineage; neither it nor the
update names the nature of the differential (EP-30).

The report reads; the application (US-3050/L4) writes what the same plan finds.

Written by US-3050/L3.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.planning.interface.merging import lines_in_order
from waterfall.core.planning.rebasing import (
    CALENDARS,
    Gap,
    RebasedCalendars,
    read_side,
    rebase_plan,
    rebase_refusals,
    task_differences,
)
from waterfall.core.planning.rebasing import designated as _designated
from waterfall.core.revisions.interface import RebasePart

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface.merging import MergedLine
    from waterfall.core.revisions.interface import StructureRebasing


@dataclass(frozen=True, slots=True)
class RebasedTask:
    """A task an update leaves: its node in the differential, none for one the main adds; label."""

    node_id: UUID | None
    label: str


@dataclass(frozen=True, slots=True)
class RebasedLines:
    """Where the lines of an update stand, each structure in the order of its plan.

    ``tasks`` the tasks the update leaves, by lineage, in the order of the plan; ``staying`` the
    nearest ancestor the update leaves of each other task of the three, none from the first level;
    ``first`` the first task of the plan, where a line of the differential goes from there.
    """

    base: tuple[MergedLine, ...]
    structure: tuple[MergedLine, ...]
    main: tuple[MergedLine, ...]
    tasks: Mapping[UUID, RebasedTask]
    staying: Mapping[UUID, UUID | None]
    first: UUID | None


def designated(session: Session, project_id: UUID, structures: tuple[UUID, UUID]) -> Gap:
    """Give what a structure designates against its base, both named: tasks and links, by lineage.

    ``structures`` the base, then the structure; computed on demand, never kept (US-3050).
    """
    base, structure = structures
    return _designated(
        read_side(session, project_id, base), read_side(session, project_id, structure)
    )


def rebase_tasks(rebasing: StructureRebasing) -> RebasePart:
    """Give the part of the planning in an update: the tasks and the links carried or kept."""
    return RebasePart(differences=task_differences(rebasing))


def rebase_end(rebasing: StructureRebasing) -> RebasePart:
    """Judge the differential an update leaves, once every part is given; give its refusals."""
    return RebasePart(refusals=rebase_refusals(rebasing))


def rebased_lines(rebasing: StructureRebasing) -> RebasedLines:
    """Tell the estimate where the lines of an update stand, of the plan the planning built."""
    plan = rebase_plan(rebasing)
    tasks = {
        each: RebasedTask(plan.structure.tasks.get(each), plan.label_of(each))
        for each in plan.order
    }
    staying: dict[UUID, UUID | None] = {}
    for side in (plan.structure, plan.main, plan.base):
        for lineage in side.tasks:
            if lineage not in tasks and lineage not in staying:
                staying[lineage] = plan.staying(lineage)
    return RebasedLines(
        lines_in_order(plan.base.tree),
        lines_in_order(plan.structure.tree),
        lines_in_order(plan.main.tree),
        tasks,
        staying,
        plan.order[0] if plan.order else None,
    )


def hand_calendars(rebasing: StructureRebasing, by_task: Mapping[UUID, frozenset[UUID]]) -> None:
    """Hand the end of an update the calendars the lines name under each task it leaves."""
    rebasing.shared[CALENDARS] = RebasedCalendars(by_task)
