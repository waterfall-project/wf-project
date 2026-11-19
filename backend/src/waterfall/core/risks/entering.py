# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The entry of a risk in the current revision, private to the module (US-2580/L1; US-2590/L1).

What the three writes of a risk in the revision share — the change of its provision, its review,
its deletion — judged in the order of the contract (409 ``STATE_FORBIDS_OPERATION``, H-09): a
terminal project (``project_not_terminal``), a background task that writes in the project
(``no_background_task_running``), then, the risk read in its revision and the counter it was read
at (404, 412), what the command judges of the risk (``Judge``: its state, its citation, the
structure that would bear its line) and, the project without a current revision, the permission to
create it (``may_create_revision``). The designations, refused on their fields (422), come after,
in the write itself: nothing is written then.

The order of the locks, which every write that touches a risk and its line follows (a deletion, an
import, a write of the own estimate; see ``follow_own_estimate``): the lock of the natures of cost
first, as every write of the tree does (#2615); the revision; the stack of the history of the
writer, which the entry opens (``Held.opened``, US-2590/L2); the own estimate of the risk, for a
write that deletes it; the main structure that bears the line; then the risk, whose counter
advances under it. The opening of a revision by the entry is the one exception: the reference,
shared, then the project, as every opening does, then the risk, then the stack and the main
structure of the revision opened, which no other transaction sees before the commit. The current
revision is created, if the project has none, a copy of the last marked one that copies the
evaluation of the risk and its line; the counter and the state of the risk are judged under its
lock, in both cases.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import share_natures
from waterfall.core.planning.interface import Place
from waterfall.core.projects.interface import (
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_NOT_TERMINAL,
    lock_project,
    no_background_task_running,
    project_facts,
)
from waterfall.core.resource_settings.interface import share_reference
from waterfall.core.revisions.interface import (
    aimed_structure,
    create_revision,
    revision_draft,
    structure_facts,
)
from waterfall.core.risks.commands import MAY_CREATE_REVISION, REVISIONS_WRITE, is_terminal
from waterfall.core.risks.declaring import refuse
from waterfall.core.risks.reading import evaluation_of, found_risk, read_found
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    NotFoundError,
    PreconditionFailedError,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.tables import Risk, RiskEvaluation

# What a command judges of the risk, under its lock: the evaluation read, and the revision the
# structure that would bear its line is judged in (the one written in, or the last marked one a
# creation would copy). It raises the refusal (409) of the first condition that lacks.
type Judge = Callable[[RiskEvaluation, UUID], None]


@dataclass(frozen=True, slots=True)
class Entered:
    """A risk entered, under its lock: the revision written in, its main structure, the rows.

    ``created`` whether this entry created the revision: a node named is then one of the revision
    it copied, found in the copy by its lineage (WF-DAT-0030).
    """

    revision_id: UUID
    place: Place
    risk: Risk
    evaluation: RiskEvaluation
    created: bool


@dataclass(frozen=True, slots=True)
class Held:
    """A risk to enter at the counter its caller read, and what the command judges of it.

    ``lock_own_estimate`` takes the own estimate of the risk before the main structure, for the
    write that deletes it. ``opened`` is told the revision written in once it is known — created
    if need be — and before any structure is locked: the entry of the history opens there, which
    locks the stack of the writer between the revision and the structures (US-2590/L2).
    """

    risk_id: UUID
    lock_version: int
    judge: Judge
    lock_own_estimate: bool = False
    opened: Callable[[UUID], None] | None = None


def _judge_held(risk: Risk, lock_version: int) -> None:
    """Judge the counter of the risk read under its lock (412)."""
    if risk.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": risk.lock_version}
        )


def _read_before(session: Session, project_id: UUID, held: Held, viewer: Viewer) -> None:
    """Judge an entry that would create the revision, on the risk of the last marked one.

    The risk unknown or held by no revision (404), the counter read (412), what the command judges
    of the risk, the creation of the revision a permission of its own (``may_create_revision``).
    The risk is locked first, and held until the commit, so that the counter judged is the one the
    opening of the revision starts from.
    """
    found_risk(session, project_id, held.risk_id, lock=True)
    found = read_found(session, project_id, held.risk_id, None)
    _judge_held(found.risk, held.lock_version)
    held.judge(found.evaluation, found.evaluation.revision_id)
    if REVISIONS_WRITE not in viewer.permissions:
        raise refuse(MAY_CREATE_REVISION)


def enter(
    session: Session, project_id: UUID, held: Held, writer: Writer, viewer: Viewer
) -> Entered:
    """Enter a risk at the counter read in the current revision, created if the project has none.

    Every refusal is raised before anything is written but the revision created, which the
    transaction takes back.
    """
    risk_id = held.risk_id
    share_natures(session)
    facts = project_facts(session, project_id)
    if is_terminal(facts.state):
        raise refuse(PROJECT_NOT_TERMINAL)
    revision_id = facts.current_revision_id
    if revision_id is not None:
        revision_draft(session, revision_id)
    if not no_background_task_running(session, project_id, writer.running):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)
    if revision_id is None:
        # The reference shared, then the project, as the opening of a revision does (``_open``
        # shares it again, to no effect): another opening waits for the project before it advances
        # this risk, and the revision it opened is the one we write in. The project first would
        # close an interlock with a writer of the reference that waits behind an opening.
        share_reference(session)
        facts = lock_project(session, project_id)
        if is_terminal(facts.state):
            raise refuse(PROJECT_NOT_TERMINAL)
        revision_id = facts.current_revision_id
        if revision_id is not None:
            revision_draft(session, revision_id)
    created = revision_id is None
    if revision_id is None:
        _read_before(session, project_id, held, viewer)
        revision_id = create_revision(session, project_id, writer.act, viewer).revision_id
    if held.opened is not None:
        held.opened(revision_id)
    if not created and held.lock_own_estimate:
        # The structure of an evaluation never changes: read before the lock, it is the one the
        # evaluation read under the lock of the risk names.
        pending = evaluation_of(session, project_id, risk_id, revision_id)
        if pending is None:
            raise NotFoundError(NOT_FOUND)
        structure_facts(session, project_id, pending.structure_id, lock=True)
    main = aimed_structure(session, project_id, revision_id, None)
    if main is None:
        raise NotFoundError(NOT_FOUND)
    structure_facts(session, project_id, main, lock=True)
    risk = found_risk(session, project_id, risk_id, lock=True)
    evaluation = evaluation_of(session, project_id, risk_id, revision_id)
    if evaluation is None:
        raise NotFoundError(NOT_FOUND)
    if not created:
        # A revision we created advanced the counter at its opening, which was judged before it,
        # under the lock of the risk held since.
        _judge_held(risk, held.lock_version)
        held.judge(evaluation, revision_id)
    return Entered(revision_id, Place(project_id, revision_id, main), risk, evaluation, created)
