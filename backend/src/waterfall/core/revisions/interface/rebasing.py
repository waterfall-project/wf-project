# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of a differential from the main structure: what each module finds and writes of it.

Three structures play in it (EP-08, "La base d'un différentiel et sa mise à jour"): the main
structure, a differential, and its base — the main structure as it was when the differential copied
it, or at its last update. What a structure designates is its gap to its base, by the lineage; the
update carries into the differential what the main structure has received since the base — its own
gap to the same base —, without changing what the differential designates, and signals what it
keeps against it (``kept``, four rules).

Two registries of this module, on the model of the merge (``merging``), that the planning and the
estimate fill at the import of their interface, the planning first: the revisions do not read the
nodes nor the lines of a structure. Each module gives its part of what the update carries and keeps
— the planning its tasks and links, the estimate its lines —, by one function
(``register_rebase``): called while the report is computed (``StructureRebasing.applying`` false),
it writes nothing; called by the application (``rebaseCostStructure``, US-3050/L4), under the lock
of the project and of the three structures, it writes what the very same computation finds, so that
what the report presented is what is written. Then, once every part has given its own
(``register_rebase_end``), what is judged once on the differential the update leaves: the engine of
the dates replayed, the loops, the links forbidden, the horizon (WF-PLA-0030, WF-PLA-0150). A part
may hand what it computed to those after it and to the end (``StructureRebasing.shared``). The
parts are in the forms of the contract (``ImportDifference``, ``ReportRefusal``): the API validates
them against its models.

Neither the update nor what a structure designates names the nature of the differential: the own
estimate of a risk will take them up (EP-30).

``rebase_report`` gives the report before an update (``getStructureRebaseReport``): the structure
judged as its update is (``rebase_conditions``), the parts asked, writing nothing, and the counters
of the two structures read, which the confirmation sends back.

Written by US-3050/L3.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.projects.interface import (
    TERMINAL,
    no_background_task_running,
    project_facts,
)
from waterfall.core.revisions.commands import RebaseState, rebase_conditions
from waterfall.core.revisions.interface.bases import differential_base
from waterfall.core.revisions.interface.merging import by_change
from waterfall.core.revisions.interface.shared import refuse
from waterfall.core.revisions.interface.structures import AMENDMENT, BASE, MAIN
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.errors import NOT_FOUND, NotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class StructureRebasing:
    """An update of a differential from the main structure of its revision, in its transaction.

    ``structure_id`` the differential updated, ``base_id`` its base; ``applying`` tells the
    application, which writes, from the report, which writes nothing. ``shared`` what a part
    computes once for the parts after it and the end, under a key of its own.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    main_structure_id: UUID
    structure_id: UUID
    base_id: UUID
    act: Act
    applying: bool
    shared: dict[str, object] = field(default_factory=dict[str, object])


@dataclass(frozen=True, slots=True)
class RebasePart:
    """What a module finds of an update, each in the form of the contract, empty when nothing.

    ``differences`` as ``ImportDifference`` — what the update carries, ``added``, ``updated``,
    ``removed``, and what the differential keeps, ``kept`` —, ``refusals`` as ``ReportRefusal``.
    """

    differences: tuple[Mapping[str, object], ...] = ()
    refusals: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class RebaseReport:
    """The report before the update of a differential (``StructureRebaseReport``).

    The counters of the main structure and of the differential read, and what the modules find.
    """

    main_structure_lock_version: int
    structure_lock_version: int
    found: RebasePart


# What each module finds and writes of an update, in the order of registration: the planning
# before the estimate, whose lines name its tasks.
_REBASES: Registry[Callable[[StructureRebasing], RebasePart]] = Registry("revisions.rebase")
# What is judged once every part has given its own, in the order of registration.
_ENDS: Registry[Callable[[StructureRebasing], RebasePart]] = Registry("revisions.rebase_end")


def register_rebase(part: Callable[[StructureRebasing], RebasePart]) -> Callable[[], None]:
    """Add the part a module takes of an update after those registered; give its withdrawal.

    A module registers at the import of its interface, which imports this one first.
    """
    return _REBASES.register(part)


def register_rebase_end(end: Callable[[StructureRebasing], RebasePart]) -> Callable[[], None]:
    """Add what a module judges once all the parts of an update are given; give its withdrawal.

    Called once per update, after every part registered by ``register_rebase``, whatever the
    order of the imports.
    """
    return _ENDS.register(end)


def rebase_parts(rebasing: StructureRebasing) -> RebasePart:
    """Give what every module registered finds of an update, the parts then the ends; empty if none.

    The differences in the order of their change — added, updated, removed, kept —, each in the
    order of the parts; the refusals in the order of the parts. A difference of a change unknown
    is a defect of the module that gave it (``MergePartError``).
    """
    found = [part(rebasing) for part in _REBASES.entries()]
    found += [end(rebasing) for end in _ENDS.entries()]
    return RebasePart(
        differences=by_change([each for part in found for each in part.differences], "rebase"),
        refusals=tuple(each for part in found for each in part.refusals),
    )


def rebasing_of(
    session: Session, structure: tuple[UUID, UUID, UUID], act: Act, *, applying: bool
) -> tuple[StructureRebasing, CostStructure, CostStructure]:
    """Judge the update of a structure and give it, with the rows of the main and the differential.

    ``structure`` is the project, the revision and the structure the path names; 404 for a
    revision or a structure that is not of them, a base included, which no operation serves. Then
    refused by the first condition the command ``rebase`` lacks (409, ``rebase_conditions``): only
    a differential not merged of the current revision, out of date, is updated. The rows are read
    as they are: the application locks them before (US-3050/L4).
    """
    project_id, revision_id, structure_id = structure
    status = session.scalar(
        select(Revision.status).where(Revision.project_id == project_id, Revision.id == revision_id)
    )
    rows = session.scalars(
        select(CostStructure).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind != BASE,
        )
    )
    held = {row.id: row for row in rows}
    if status is None or structure_id not in held:
        raise NotFoundError(NOT_FOUND)
    project = project_facts(session, project_id)
    [main] = [row for row in held.values() if row.kind == MAIN]
    differential = held[structure_id]
    state = RebaseState(
        terminal=project.state in TERMINAL,
        current=project.current_revision_id == revision_id,
        no_task_running=no_background_task_running(session, project_id),
        differential=differential.kind == AMENDMENT and not differential.is_merged,
        out_of_date=differential.main_lock_version != main.lock_version,
    )
    missing = rebase_conditions(state)
    if missing:
        raise refuse(missing[0])
    base_id = differential_base(session, project_id, structure_id)
    if base_id is None:
        raise NotFoundError(NOT_FOUND)
    rebasing = StructureRebasing(
        session, project_id, revision_id, main.id, structure_id, base_id, act, applying=applying
    )
    return rebasing, main, differential


def rebase_report(session: Session, structure: tuple[UUID, UUID, UUID], act: Act) -> RebaseReport:
    """Give what the update of a differential would do (``getStructureRebaseReport``).

    Writes nothing; judged as the update is (``rebasing_of``), the parts asked, the counters read.
    """
    rebasing, main, differential = rebasing_of(session, structure, act, applying=False)
    return RebaseReport(
        main_structure_lock_version=main.lock_version,
        structure_lock_version=differential.lock_version,
        found=rebase_parts(rebasing),
    )
