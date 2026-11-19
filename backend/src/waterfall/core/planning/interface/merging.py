# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The part of the planning in the merge of a differential (WF-REV-0050; EP-08, "Modules").

``merge_tasks`` is its part of ``register_merge``: the tasks and the links of the differential
matched with the main structure by their lineage — added, updated, removed, or kept and completed
when started (``merging``) —; ``merge_end`` its part of ``register_merge_end``: what refuses the
merge, judged once on the structure the merge leaves (WF-PLA-0030, WF-PLA-0150, WF-PLA-0170). The
estimate, whose part comes after, reads of the same plan where each line stands
(``merged_lines``): in the main structure and in the differential, by the lineage of its task, the
provisions told; which tasks the merge keeps, and where the provision lines of a task it removes
go — to the nearest ancestor it leaves, or, from the first level, to the first task of the first
level (WF-RIS-0010; #789); the tasks the merge leaves, named, which the estimate judges for their
working hours; and, to the application, the started tasks it completes as the facet of a line is
told of its task (``BearingTask``), whose lines the estimate re-estimates to nought.

The report reads; the application (``StructureMerging.applying``, US-2560/L2) writes what the same
plan finds, under the lock of the two structures (``merging_writing``): the planning writes its
tasks and links in its part, the nodes of the lines when the estimate asks it
(``place_merged_lines``), whose facets the estimate writes, and, at the end, removes the tasks the
merge does not keep, completes the started ones it keeps, and replays the engine.

Written by US-2560/L1; the application by US-2560/L2.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.planning.carrying import bearing
from waterfall.core.planning.interface.facets import BearingTask
from waterfall.core.planning.interface.rebased import load_rebase
from waterfall.core.planning.merging import merge_plan, merge_refusals, task_differences
from waterfall.core.planning.merging_writing import finish, place_lines, write_tasks
from waterfall.core.planning.tree import LINE
from waterfall.core.planning.views import NOT_STARTED, STARTED, state_of
from waterfall.core.revisions.interface import (
    MergePart,
    MergeRequest,
    differential_up_to_date,
    load_merge_at,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.planning.tree import NodeRow, TaskRow, Tree
    from waterfall.core.planning.writing import Place
    from waterfall.core.revisions.interface import StructureMerging
    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class MergedLine:
    """A line of a structure merged: its node, its lineage, its task's, if it is a provision."""

    node_id: UUID
    lineage_id: UUID
    task_lineage_id: UUID
    is_provision: bool


@dataclass(frozen=True, slots=True)
class MergedLines:
    """Where the lines of a merge stand, each structure in the order of its plan.

    ``kept`` the lineages of the tasks the differential removes and the merge keeps, started;
    ``moved`` the lineage of each task it removes whose provision lines go to another task, with
    the node of that task — in the main structure, or in the differential for a task it adds;
    ``completing`` the lineages of the tasks kept that are started, which the merge completes;
    ``started`` those of the tasks of the main structure that are started or completed; ``tasks``
    each task the merge leaves, by its lineage, in the order of the plan, with its node in the main
    structure — none for a task the differential adds — and its label; ``bearers`` each task it
    completes, by its lineage, as the facet of a line it bears is told of it, for the application
    alone, which brings their remaining to nought.
    """

    main: tuple[MergedLine, ...]
    amendment: tuple[MergedLine, ...]
    kept: frozenset[UUID]
    moved: Mapping[UUID, UUID]
    completing: frozenset[UUID] = frozenset()
    started: frozenset[UUID] = frozenset()
    tasks: Mapping[UUID, tuple[UUID | None, str]] = field(
        default_factory=dict[UUID, tuple[UUID | None, str]]
    )
    bearers: Mapping[UUID, BearingTask] = field(default_factory=dict[UUID, BearingTask])


def merge_tasks(merging: StructureMerging) -> MergePart:
    """Give the part of the planning in a merge: its tasks and its links, the tasks it completes.

    The application writes them, the tasks removed staying until the end.
    """
    differences, completed = task_differences(merging)
    if merging.applying:
        write_tasks(merging)
    return MergePart(differences=differences, completed_tasks=completed)


def merge_end(merging: StructureMerging) -> MergePart:
    """Judge the structure a merge leaves, once every part is given (#3946); give its refusals.

    The application judged them before it wrote: it ends the merge instead (``finish``).
    """
    if merging.applying:
        finish(merging)
        return MergePart()
    return MergePart(refusals=merge_refusals(merging))


def place_merged_lines(merging: StructureMerging) -> Mapping[UUID, UUID]:
    """Write the nodes of the lines a merge leaves in the main structure, after its tasks.

    Give, by the node in the differential of each line it creates, its node in the main structure,
    whose facet the estimate writes.
    """
    return place_lines(merging)


def lines_in_order(tree: Tree[NodeRow, TaskRow]) -> tuple[MergedLine, ...]:
    """Give the lines of a structure in the order of its plan, by the lineage of their task."""
    found: list[MergedLine] = []
    for node_id in tree.order:
        node = tree.nodes[node_id]
        if node.kind != LINE or node.parent_id is None:
            continue
        task = tree.nodes[node.parent_id].lineage_id
        found.append(MergedLine(node_id, node.lineage_id, task, node_id in tree.provisions))
    return tuple(found)


def merged_lines(merging: StructureMerging) -> MergedLines:
    """Tell the estimate where the lines of a merge stand, of the plan the planning built."""
    plan = merge_plan(merging)
    first = plan.order[0] if plan.order else None
    moved: dict[UUID, UUID] = {}
    for task_id in plan.removed:
        target = plan.staying(task_id) or first
        if target is not None:
            moved[plan.main.nodes[task_id].lineage_id] = target
    main = plan.main
    kept = frozenset(main.nodes[each].lineage_id for each in plan.kept)
    completing = frozenset(
        main.nodes[each].lineage_id
        for each in plan.kept
        if state_of(main, each).progress == STARTED
    )
    started = frozenset(
        main.nodes[each].lineage_id
        for each in main.tasks
        if state_of(main, each).progress != NOT_STARTED
    )
    tasks: dict[UUID, tuple[UUID | None, str]] = {}
    for task_id in plan.order:
        node = main.nodes.get(task_id) or plan.amendment.nodes[plan.sources[task_id]]
        tasks[node.lineage_id] = (
            task_id if task_id in main.nodes else None,
            plan.label_of(task_id),
        )
    bearers = {
        main.nodes[each].lineage_id: bearing(
            merging.session, merging.project_id, main, each, is_main=True
        )
        for each in plan.kept
        if merging.applying and main.nodes[each].lineage_id in completing
    }
    return MergedLines(
        lines_in_order(main),
        lines_in_order(plan.amendment),
        kept,
        moved,
        completing,
        started,
        tasks,
        bearers,
    )


def load_merge(session: Session, place: Place, named: tuple[str, str | None], act: Act) -> None:
    """Merge a differential of the witness at the instant it imposes, as the worker merges it.

    ``named`` the name of version and the description of the revision it marks. A differential
    out of date — the walk of the events wrote the main structure since its opening — is updated
    first, by the function of the update, without a report (``load_rebase``; EP-08, "Le chargeur
    du témoin"): the merge applies only what it designates, and requires it up to date.
    """
    if not differential_up_to_date(session, place.project_id, place.structure_id):
        load_rebase(session, place, act)
    version_name, description = named
    request = MergeRequest(
        place.project_id, place.revision_id, place.structure_id, version_name, description, None
    )
    load_merge_at(session, request, act)
