# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge of an amendment into the main structure: what each module finds and writes of it.

Two registries of this module (EP-08, "La fusion et la survenance"), that the planning and the
estimate fill at the import of their interface, the planning first: the revisions do not read the
nodes nor the lines of a structure. Each module gives its part of the differences of the amendment
with the main structure, matched by the lineage (WF-DAT-0030), and of their application — the
planning its tasks and links, the estimate its lines —, by one function (``register_merge``):
called while the report is computed (``StructureMerging.applying`` false), it writes nothing;
called by the application, under the lock of the two structures, it writes what the very same
computation finds, so that what the report presented is what is written. Then, once every part has
given its own, the end of the merge (``register_merge_end``, #3946): what is judged on the
structure all the parts leave, once — the engine of the dates replayed, the loops, the links
forbidden, the horizon, the order items out of their work package (WF-PLA-0030, WF-PLA-0150,
WF-PLA-0170). A part may hand what it computed to those after it and to the end
(``StructureMerging.shared``), so that the structure is read once. The parts are in the forms of
the contract, the report of a merge taking up those of an import (``ImportDifference``,
``ImportCompletedTask``, ``ReportRefusal``): the API validates them against its models.

``merge_report`` gives the report before a merge (``getStructureMergeReport``, US-2560/L1): the
structure judged as its merge is (``merging_of``, ``merge_conditions``), the parts asked, writing
nothing, and the counters of the two structures read, which the confirmation sends back. A
differential out of date has none (``structure_up_to_date``, US-2560/L2): the merge applies only
what it designates, its gap to its base, which is its gap to the main structure once it is up to
date (#4034).

Declared by US-2550/L1, the socle of EP-08, with nothing registered; filled by US-2560/L1 (the
report, the end) and US-2560/L2 (the judgement shared with the application, ``merge_applying``).
The mode of a merge (``MergeMode``) declared by US-3070/L1: the occurrence of a risk (US-3100).
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select

from waterfall.core.projects.interface import (
    TERMINAL,
    no_background_task_running,
    project_facts,
)
from waterfall.core.revisions.commands import (
    CREATE_REVISION,
    STRUCTURE_UP_TO_DATE,
    MergeState,
    merge_conditions,
)
from waterfall.core.revisions.interface.revisions import last_marked_revision
from waterfall.core.revisions.interface.shared import bears_main_counter, refuse
from waterfall.core.revisions.interface.structures import AMENDMENT, BASE, MAIN
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.errors import NOT_FOUND, NotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.platform.audit import Act

# The order the report gives the differences in, each change in the order of the parts.
_CHANGES = ("added", "updated", "removed", "kept")
# The modes of a merge (EP-30): the merge of an amendment, and the occurrence of a risk, which
# merges its own estimate on the current figures alone — a line added at a budgeted amount of
# nought and marked of its risk, a task removed kept and completed whatever its state —, marking
# nothing.
type MergeMode = Literal["amendment", "occurrence"]
MERGE_MODES: tuple[MergeMode, ...] = ("amendment", "occurrence")
AMENDMENT_MERGE, OCCURRENCE_MERGE = MERGE_MODES


class MergePartError(ValueError):
    """A part of a merge gives what the contract does not: a defect of the module that gave it.

    Raised by ``merge_parts`` for a difference whose change is none the report knows, so that the
    module at fault is named, instead of an index that fails in the sort (#3948).
    """


@dataclass(frozen=True, slots=True)
class StructureMerging:
    """A merge of an amendment into the main structure of its revision, in its transaction.

    ``applying`` tells the application, which writes, from the report, which writes nothing.
    ``shared`` what a part computes once for the parts after it and the end, under a key of its own.
    ``mode`` what the parts apply (``MergeMode``, EP-30): the merge of an amendment by default; in
    the mode ``occurrence``, ``amendment_id`` is the own estimate of the risk that occurs.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    main_structure_id: UUID
    amendment_id: UUID
    act: Act
    applying: bool
    shared: dict[str, object] = field(default_factory=dict[str, object])
    mode: MergeMode = AMENDMENT_MERGE


@dataclass(frozen=True, slots=True)
class MergePart:
    """What a module finds of a merge, each in the form of the contract, empty when nothing.

    ``differences`` as ``ImportDifference``, ``completed_tasks`` the started tasks the amendment
    removes and the merge completes as ``ImportCompletedTask``, ``refusals`` as ``ReportRefusal``.
    """

    differences: tuple[Mapping[str, object], ...] = ()
    completed_tasks: tuple[Mapping[str, object], ...] = ()
    refusals: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class MergeReport:
    """The report before the merge of a differential (``StructureMergeReport``).

    The counters of the two structures read, whether the merge creates the current revision, and
    what the modules find of it.
    """

    main_structure_lock_version: int
    amendment_lock_version: int
    creates_current_revision: bool
    found: MergePart


# What each module finds and writes of a merge, in the order of registration: the planning before
# the estimate, whose lines name its tasks.
_MERGES: Registry[Callable[[StructureMerging], MergePart]] = Registry("revisions.merge")
# What is judged once every part has given its own, in the order of registration (#3946).
_ENDS: Registry[Callable[[StructureMerging], MergePart]] = Registry("revisions.merge_end")


def register_merge(part: Callable[[StructureMerging], MergePart]) -> Callable[[], None]:
    """Add the part a module takes of a merge after those registered; give its withdrawal.

    A module registers at the import of its interface, which imports this one first. Its part reads
    the mode of the merge (``StructureMerging.mode``): one function serves both, the occurrence of a
    risk being the merge of its own estimate (EP-30, "Ce que la conception décide").
    """
    return _MERGES.register(part)


def register_merge_end(end: Callable[[StructureMerging], MergePart]) -> Callable[[], None]:
    """Add what a module judges once all the parts of a merge are given; give its withdrawal.

    Called once per merge, after every part registered by ``register_merge``, whatever the order
    of the imports (#3946).
    """
    return _ENDS.register(end)


def merge_parts(merging: StructureMerging) -> MergePart:
    """Give what every module registered finds of a merge, the parts then the ends; empty if none.

    The differences in the order of their change — added, updated, removed, kept —, each in the
    order of the parts; the completed tasks and the refusals in the order of the parts. A difference
    of a change unknown is a defect of the module that gave it: ``MergePartError``.
    """
    found = [part(merging) for part in _MERGES.entries()]
    found += [end(merging) for end in _ENDS.entries()]
    return MergePart(
        differences=by_change([each for part in found for each in part.differences], "merge"),
        completed_tasks=tuple(each for part in found for each in part.completed_tasks),
        refusals=tuple(each for part in found for each in part.refusals),
    )


def by_change(
    differences: list[Mapping[str, object]], operation: str
) -> tuple[Mapping[str, object], ...]:
    """Order differences by their change — added, updated, removed, kept —, stably.

    A difference of a change unknown is a defect of the module that gave it, named by the
    operation whose part it is (``MergePartError``, #3948): the update of a differential orders its
    parts likewise (US-3050/L3).
    """
    for each in differences:
        if each.get("change") not in _CHANGES:
            msg = f"a {operation} part gives the change {each.get('change')!r}, none of {_CHANGES}"
            raise MergePartError(msg)
    return tuple(sorted(differences, key=lambda each: _CHANGES.index(str(each.get("change")))))


def _structures(session: Session, project_id: UUID, revision_id: UUID) -> dict[UUID, CostStructure]:
    """Read the structures of a revision of a project, by their identifier; not its bases."""
    rows = session.scalars(
        select(CostStructure).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind != BASE,
        )
    )
    return {row.id: row for row in rows}


@dataclass(frozen=True, slots=True)
class MergeJudged:
    """A merge judged: the frame of its parts, the rows of its two structures, what it does.

    ``creates`` whether the merge creates the current revision (``creates_current_revision``);
    ``up_to_date`` whether the differential is, which the caller judges where its order puts it.
    """

    merging: StructureMerging
    main: CostStructure
    amendment: CostStructure
    creates: bool
    up_to_date: bool


def merging_of(
    session: Session,
    structure: tuple[UUID, UUID, UUID],
    act: Act,
    *,
    creates: bool,
    besides: UUID | None = None,
) -> MergeJudged:
    """Judge the merge of a structure and give it, writing nothing; or refuse (404, 409).

    ``structure`` is the project, the revision and the structure the path names; 404 for a
    revision or a structure that is not of them. Refused by the first condition the command
    ``merge_structure`` lacks (409, ``merge_conditions``) — ``creates`` whether the caller may
    create a revision, ``besides`` the task of the merge itself, which does not count as a task
    that writes —, but ``structure_up_to_date``, which the caller judges where its order puts it:
    the report at once, the confirmation once it has judged the counters it read. Only a
    differential not merged of the current revision is merged, or one of the last marked revision
    of a project without a current revision, whose merge creates it (#790). The rows are read as
    they are: the application locks them before.
    """
    project_id, revision_id, structure_id = structure
    status = session.scalar(
        select(Revision.status).where(Revision.project_id == project_id, Revision.id == revision_id)
    )
    held = _structures(session, project_id, revision_id)
    if status is None or structure_id not in held:
        raise NotFoundError(NOT_FOUND)
    project = project_facts(session, project_id)
    current = project.current_revision_id == revision_id
    source = (
        project.current_revision_id is None
        and last_marked_revision(session, project_id) == revision_id
    )
    amendment = held[structure_id]
    [main] = [row for row in held.values() if row.kind == MAIN]
    state = MergeState(
        terminal=project.state in TERMINAL,
        current=current,
        source=source,
        no_task_running=no_background_task_running(session, project_id, besides),
        mergeable=amendment.kind == AMENDMENT and not amendment.is_merged,
        creates=creates,
        up_to_date=bears_main_counter(amendment, main.lock_version),
    )
    missing = merge_conditions(state)
    if missing and missing[0] != STRUCTURE_UP_TO_DATE:
        raise refuse(missing[0])
    merging = StructureMerging(
        session, project_id, revision_id, main.id, amendment.id, act, applying=False
    )
    return MergeJudged(merging, main, amendment, creates=not current, up_to_date=not missing)


def merge_report(
    session: Session, structure: tuple[UUID, UUID, UUID], viewer: Viewer, act: Act
) -> MergeReport:
    """Give what the merge of a structure would do, writing nothing (``getStructureMergeReport``).

    Judged as its merge is (``merging_of``), the differential out of date refused at once by
    ``structure_up_to_date``, the last condition (409, #4034): only on a differential up to date
    is its gap to the main structure what it designates.
    """
    judged = merging_of(session, structure, act, creates=CREATE_REVISION in viewer.permissions)
    if not judged.up_to_date:
        raise refuse(STRUCTURE_UP_TO_DATE)
    return MergeReport(
        main_structure_lock_version=judged.main.lock_version,
        amendment_lock_version=judged.amendment.lock_version,
        creates_current_revision=judged.creates,
        found=merge_parts(judged.merging),
    )
