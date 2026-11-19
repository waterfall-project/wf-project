# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge of a differential applied (``mergeCostStructure``; WF-REV-0050, US-2560/L2).

One operation, one transaction, as a background task of the kind ``structure_merge``
(WF-ARC-0090): the very computation of the report (``merge_parts``), applied under the locks, so
that what the report presented is what is written; then the marking of the revision, as any
marking does it (``mark_revision``: the images, the indicators kept, the history of the revision
finished, the journal), and the reference designated by the way of the designation
(``refer_after_merge``). Nothing enters the history that can be undone: the marking finishes it
(WF-IHM-0110).

- **The request** (``submit_merge``) judges the confirmation in the order of the contract, under
  the lock of the project — the current revision shared before it, as every write of the revision
  that locks the project —, then of the two structures in the order of their identifiers: the
  project manager (403, 404), the conditions of the command ``merge_structure`` (409), the
  counters the report read (412 ``STALE_LOCK_VERSION``, ``params.expected_lock_version`` the
  counter of the differential, the object the path names), the differential up to date (409
  ``structure_up_to_date``), then the name of version (409 ``ALREADY_EXISTS``). A write of the main
  structure since the report is thus a 412, the counter it advanced: the up to date is judged on a
  differential whose report was not read. Nothing is written but the task.
- **The worker** (``run_merge``) judges the same again as it stands when the task runs — the
  current revision locked first, as the marking does, then the project, then the two structures —,
  the task itself not counting as one that writes in the project. Without a current revision, the
  reasons of the report are judged on the revision marked, whose structures the marking froze;
  then the task opens the current revision, a copy of the marked one at the rates it kept,
  projected (``open_revision_by_task``), and merges into it the copy of the differential, found by
  its lineage (#790). The differences are written by the parts of the planning and of the
  estimate, the differential marked merged (``is_merged``, its counter advanced), the merge
  inscribed in the journal (``structure_merge``), the revision marked under the name confirmed,
  then made the reference. A reason of the report fails the task with its code and its
  parameters, nothing written; so does any failure, no revision left opened (WF-DAT-0040).

``load_merge_at`` merges a differential of the witness at the instant it imposes, by the same
transaction as the worker, without a report to confirm.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sqlalchemy import update

from waterfall.core.projects.interface import (
    lock_project,
    project_facts,
    require_project_manager,
)
from waterfall.core.revisions.commands import CREATE_REVISION, STRUCTURE_UP_TO_DATE
from waterfall.core.revisions.interface.marking import judge_version_name, mark_revision
from waterfall.core.revisions.interface.merging import MergeJudged, merge_parts, merging_of
from waterfall.core.revisions.interface.reference import refer_after_merge
from waterfall.core.revisions.interface.revisions import open_revision_by_task
from waterfall.core.revisions.interface.shared import (
    found_revision,
    hold_current_revision,
    inscribe_structure,
    refuse,
)
from waterfall.core.revisions.interface.structures import structure_facts, structure_in_revision
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import (
    Act,
)
from waterfall.platform.database import utc_now
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.tasks import PROJECT, submit

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.revisions.interface.merging import StructureMerging
    from waterfall.platform.queue import TaskQueue

# What the task of a merge carries besides its project: the path, the confirmation.
REVISION = "revision_id"
STRUCTURE = "structure_id"
NAME = "version_name"
DESCRIPTION = "description"
MAIN_LOCK_VERSION = "main_structure_lock_version"
AMENDMENT_LOCK_VERSION = "amendment_lock_version"


@dataclass(frozen=True, slots=True)
class MergeRequest:
    """A merge confirmed (``StructureMerge``): the differential the path names, what was read.

    ``counters`` the counters of the main structure and of the differential the report read, none
    for the witness's, which confirms no report.
    """

    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    version_name: str
    description: str | None
    counters: tuple[int, int] | None

    def payload(self) -> dict[str, Any]:
        """Give what the task carries of it."""
        if self.counters is None:
            msg = "a merge handed to the worker carries the counters its report read"
            raise ValueError(msg)
        return {
            PROJECT: str(self.project_id),
            REVISION: str(self.revision_id),
            STRUCTURE: str(self.structure_id),
            NAME: self.version_name,
            DESCRIPTION: self.description,
            MAIN_LOCK_VERSION: self.counters[0],
            AMENDMENT_LOCK_VERSION: self.counters[1],
        }

    @classmethod
    def of(cls, payload: Mapping[str, Any]) -> MergeRequest:
        """Read the request a task carries."""
        return cls(
            UUID(payload[PROJECT]),
            UUID(payload[REVISION]),
            UUID(payload[STRUCTURE]),
            payload[NAME],
            payload[DESCRIPTION],
            (payload[MAIN_LOCK_VERSION], payload[AMENDMENT_LOCK_VERSION]),
        )

    @property
    def path(self) -> tuple[UUID, UUID, UUID]:
        """Give the project, the revision and the structure the path names."""
        return self.project_id, self.revision_id, self.structure_id


def _judged(
    session: Session, request: MergeRequest, act: Act, *, creates: bool, besides: UUID | None
) -> MergeJudged:
    """Judge a merge confirmed under the locks of its two structures, in the order of the contract.

    The conditions of its command (409), the two structures locked in the order of their
    identifiers and read again, the counters read (412), the differential up to date (409
    ``structure_up_to_date``), the name of version (409 ``ALREADY_EXISTS``): a name a marked
    revision bears, but the one the merge marks, when it marks the current one.
    """
    judged = merging_of(session, request.path, act, creates=creates, besides=besides)
    project_id = request.project_id
    for each in sorted((judged.main.id, judged.amendment.id)):
        structure_facts(session, project_id, each, lock=True)
    judged = merging_of(session, request.path, act, creates=creates, besides=besides)
    read = (judged.main.lock_version, judged.amendment.lock_version)
    if request.counters is not None and request.counters != read:
        expected = {"expected_lock_version": judged.amendment.lock_version}
        raise PreconditionFailedError(STALE_LOCK_VERSION, expected)
    if not judged.up_to_date:
        raise refuse(STRUCTURE_UP_TO_DATE)
    marked = None if judged.creates else request.revision_id
    judge_version_name(session, project_id, request.version_name, marked)
    return judged


def submit_merge(
    session: Session, queue: TaskQueue, request: MergeRequest, act: Act, viewer: Viewer
) -> UUID:
    """Judge a merge confirmed, then submit its task, in the transaction of the request.

    The current revision shared, then the project locked, under which the requester is judged
    again as a project manager (#2207); then as ``_judged`` says. Nothing is written but the task.
    """
    project_id = request.project_id
    hold_current_revision(session, project_id)
    lock_project(session, project_id)
    require_project_manager(session, project_id, viewer)
    _judged(session, request, act, creates=CREATE_REVISION in viewer.permissions, besides=None)
    return submit(session, queue, "structure_merge", act.author, request.payload())


def run_merge(session: Session, payload: Mapping[str, Any], act: Act, task_id: UUID) -> None:
    """Apply the merge a task names, in the transaction of the task (the worker's).

    Judged again under the locks as the request judged it, the requester having been judged a
    project manager who may create a revision there; refused, it fails with its code and nothing is
    written. The instant of the merge is taken once the revision and the project are locked.
    """
    _merged(session, MergeRequest.of(payload), act, task_id)


def load_merge_at(session: Session, request: MergeRequest, act: Act) -> None:
    """Merge a differential of the witness at the instant it imposes, as the worker merges it.

    No report confirmed (``request.counters`` none); refused as the worker refuses it.
    """
    _merged(session, request, act, None)


def _merged(session: Session, request: MergeRequest, act: Act, task_id: UUID | None) -> None:
    """Merge a differential, mark its revision and make it the reference, in one transaction.

    ``task_id`` the task of the merge, none for the witness, whose instant ``act`` imposes.
    """
    project_id = request.project_id
    # The current revision locked first, then the project, as the marking does: which revision to
    # lock is read before the lock of the project, which the order of the locks forbids to take
    # first. Nothing is decided on that reading: ``_judged`` reads the project again under its lock
    # (``merging_of``), and a revision that stopped being current meanwhile — marked by another
    # task — is refused by ``revision_draft``, its row locked all the same; a revision never
    # becomes current after its creation, so none the merge writes is left unlocked.
    if project_facts(session, project_id).current_revision_id == request.revision_id:
        found_revision(session, request.revision_id, project_id, lock=True)
    lock_project(session, project_id)
    if task_id is not None:
        act = Act(act.author, utc_now())
    judged = _judged(session, request, act, creates=True, besides=task_id)
    _refused_by_report(judged.merging)
    merging = judged.merging
    if judged.creates:
        merging = _opened(session, judged, act, task_id)
    merge_parts(replace(merging, applying=True))
    _consumed(session, merging, act)
    _inscribe(session, merging, request.version_name, act)
    mark_revision(session, merging.revision_id, request.version_name, request.description, act)
    refer_after_merge(session, project_id, merging.revision_id, act)


def _refused_by_report(merging: StructureMerging) -> None:
    """Refuse a merge a reason of its report refuses: its first, its code and its parameters (422).

    Judged before anything is written, on the structures the report reads: the task fails with
    it, as an import refused does (``BackgroundTask.problem``, WF-PLA-0170, WF-PLA-0030).
    """
    refusals = merge_parts(merging).refusals
    if refusals:
        first = refusals[0]
        params = cast("Mapping[str, Any]", first["params"])
        raise UnprocessableError(str(first["code"]), params)


def _opened(
    session: Session, judged: MergeJudged, act: Act, task_id: UUID | None
) -> StructureMerging:
    """Open the current revision the merge creates; give the merge of the copy of the differential.

    A copy of the revision marked (WF-REV-0010), which the copy finds by its lineage; the main
    structure and the copy of the differential locked in the order of their identifiers. The
    witness opens it as the task would, none naming the task.
    """
    merging = judged.merging
    project_id = merging.project_id
    revision_id = open_revision_by_task(session, project_id, act, task_id)
    main = structure_in_revision(session, project_id, merging.main_structure_id, revision_id)
    amendment = structure_in_revision(session, project_id, merging.amendment_id, revision_id)
    if main is None or amendment is None:
        raise NotFoundError(NOT_FOUND)
    for each in sorted((main, amendment)):
        structure_facts(session, project_id, each, lock=True)
    return replace(
        merging,
        revision_id=revision_id,
        main_structure_id=main,
        amendment_id=amendment,
        shared={},
    )


def _consumed(session: Session, merging: StructureMerging, act: Act) -> None:
    """Mark the differential merged, its counter advanced: the next revision does not take it up.

    It keeps its base in the revision the merge marks, against which it is read there
    (WF-REV-0100, US-3050).
    """
    session.execute(
        update(CostStructure)
        .where(
            CostStructure.project_id == merging.project_id,
            CostStructure.id == merging.amendment_id,
        )
        .values(
            is_merged=True,
            lock_version=CostStructure.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
        .execution_options(synchronize_session=False)
    )
    session.flush()


def _inscribe(session: Session, merging: StructureMerging, version_name: str, act: Act) -> None:
    """Inscribe the merge in the journal: the differential, the revision it marks, its project.

    Before the marking and the designation, at the same instant (WF-SEC-0030).
    """
    facts = structure_facts(session, merging.project_id, merging.amendment_id, lock=False)
    merged = (merging.revision_id, version_name)
    inscribe_structure(session, merging.project_id, facts, act, merged)
