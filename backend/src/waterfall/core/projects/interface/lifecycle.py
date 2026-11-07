# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cycle of life of a project (§3.3.2): its next state, its transitions, its exits.

``next_state`` is a pure function of the facts — the state, whether the project has a revision, a
reference, a code — that gives the next state, its trigger and the conditions that remain
(WF-CYC-0050). The transactions that realise a fact — ``createRevision``,
``designateReferenceRevision``, ``updateProject`` for the code — call ``advance`` under the lock
of the project, which writes the state and the transition, at the instant of the transaction, its
author the account that realised the fact (Created → Pricing, Pricing → In progress, WF-CYC-0030).
An exit writes likewise, with its reason, and refuses a project that bears a current revision
(WF-CYC-0090). The transitions are listed in their order (WF-CYC-0130).

Declared by US-0910/L1; US-0980/L1 fills it but for the designation of the reference, which
US-0980/L2 brings (``advance`` writes the passage to In progress all the same, once the reference
and the code are there). ``load_transitions`` stays as declared, for US-0990/L2, which imposes the
instants of the chronology: ``load_project`` writes the first transition of each project already.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select

from waterfall.core.projects.commands import EXITS, state_conditions
from waterfall.core.projects.tables import STATES, Project, ProjectStateTransition
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditObject, AuditProject, Inscription, record
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id
from waterfall.platform.tasks import project_task_pending

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The two facts that move a project forward, as the contract says them (``LifecycleTrigger``).
type LifecycleTrigger = Literal["first_revision_created", "reference_designated_and_code_set"]
# The states a manual exit reaches (``ProjectExit.to_state``), and the fate of a current revision.
type ExitState = Literal["completed", "lost", "abandoned"]
type RevisionFate = Literal["mark", "abandon"]

# Created, Pricing and In progress: the states before a terminal one.
BEFORE_TERMINAL = STATES[:3]

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_REQUIRED = "VALUE_REQUIRED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
NO_CURRENT_REVISION = "no_current_revision"
PROJECT_CODE_SET = "project_code_set"
REFERENCE_DESIGNATED = "reference_revision_designated"


@dataclass(frozen=True, slots=True)
class NextState:
    """Where a project goes next, by which fact, and what it still lacks to get there.

    The last three are empty for a project that no fact leads any further (``getProjectNextState``).
    """

    state: str
    next_state: str | None = None
    trigger: LifecycleTrigger | None = None
    missing_conditions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExitRequest:
    """An exit as the module judges it: the state aimed at, why, and at which counter.

    ``fate`` is what the caller says of the current revision. ``moved`` is the number of times the
    transaction has advanced the counter of the project already (the abandonment of the current
    revision does, once). ``no_task_running`` is what the module of the projects reads of the
    background tasks.
    """

    to_state: ExitState
    reason: str | None
    lock_version: int
    fate: RevisionFate | None = None
    moved: int = 0
    no_task_running: bool = True


@dataclass(frozen=True, slots=True)
class TransitionView:
    """A transition of a project; its author an account, ``None`` for the platform."""

    from_state: str | None
    to_state: str
    occurred_at: datetime
    author: UUID | None
    reason: str | None


def next_state(state: str, *, has_revision: bool, has_reference: bool, has_code: bool) -> NextState:
    """Give the next state of a project, its trigger and the conditions that remain (WF-CYC-0050).

    Created leads to Pricing at the first revision, with nothing else to ask; Pricing leads to In
    progress when the reference is designated and the code entered, whichever comes second, and
    names what is lacking, the code first; In progress and the terminal states lead nowhere by a
    fact (their exits are commands). ``has_revision`` is the first fact itself: it names no
    condition, the state is moved by ``advance`` when the fact is realised.
    """
    del has_revision
    if state == "created":
        return NextState(state, "pricing", "first_revision_created")
    if state == "pricing":
        lacking = (
            *(() if has_code else (PROJECT_CODE_SET,)),
            *(() if has_reference else (REFERENCE_DESIGNATED,)),
        )
        return NextState(state, "in_progress", "reference_designated_and_code_set", lacking)
    return NextState(state)


def _next_of(project: Project) -> NextState:
    return next_state(
        project.state,
        has_revision=project.current_revision_id is not None,
        has_reference=project.reference_revision_id is not None,
        has_code=project.code is not None,
    )


def read_next_state(session: Session, project_id: UUID) -> NextState:
    """Read where a project goes next (``getProjectNextState``); or refuse (404)."""
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(NOT_FOUND)
    return _next_of(project)


def _move(session: Session, project: Project, to_state: str, reason: str | None, act: Act) -> None:
    """Write the state of a project and the transition to it, at the instant of ``act``."""
    session.add(
        ProjectStateTransition(
            id=new_id(),
            project_id=project.id,
            from_state=project.state,
            to_state=to_state,
            occurred_at=act.at,
            actor_user_id=act.author,
            reason=reason,
        )
    )
    project.state = to_state


def advance(session: Session, project_id: UUID, trigger: LifecycleTrigger, act: Act) -> None:
    """Move a project locked by the caller to its next state, if the fact realised does.

    The state and the transition are written in the transaction of the fact, at its instant, its
    author the account that realised it. The counter of the project is not moved: the caller has
    written the project to realise the fact (the current revision, the code) and moved it already.
    """
    project = session.get_one(Project, project_id)
    following = _next_of(project)
    if following.next_state is None or following.trigger != trigger or following.missing_conditions:
        return
    _move(session, project, following.next_state, None, act)


def _lock(session: Session, project_id: UUID) -> Project:
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


def _judge_state(project: Project, request: ExitRequest) -> None:
    """Refuse an exit for the counter, then the conditions of its command: the first two checks."""
    stored = project.lock_version - request.moved
    if stored != request.lock_version:
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": stored})
    lacking = state_conditions(
        EXITS[request.to_state],
        project.state,
        project.current_revision_id,
        no_task_running=request.no_task_running,
    )
    if lacking:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": lacking[0]})


def judge_exit_unlocked(session: Session, project_id: UUID, request: ExitRequest) -> None:
    """Refuse an exit early, on the facts read without a lock; the judgment under the lock rules.

    A route that abandons the current revision before the exit calls this first, so that the first
    refusal of the contract (the counter, then the conditions of the state) is the one that is
    told, and the revision is not abandoned for an exit that was refused anyway. It takes no lock,
    and decides nothing: ``exit_project`` judges again under the lock of the project.
    """
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(NOT_FOUND)
    _judge_state(project, request)


def stored_lock_version(session: Session, project_id: UUID) -> int:
    """Read the counter of a project as the base keeps it now, not as the session saw it; or 404."""
    stored = session.scalar(select(Project.lock_version).where(Project.id == project_id))
    if stored is None:
        raise NotFoundError(NOT_FOUND)
    return stored


def _judge_exit(project: Project, request: ExitRequest) -> None:
    """Refuse an exit as the project, read under its lock, does; in the order of the contract."""
    _judge_state(project, request)
    if project.current_revision_id is None:
        return
    if request.fate is None:
        required = FieldError("/current_revision", VALUE_REQUIRED)
        raise UnprocessableError(VALIDATION_FAILED, fields=(required,))
    # A fate is given and the project still bears the revision: the caller did not abandon it.
    # The marking is the worker's (US-0970, US-0980/L2, #2204): until it serves the exit, a
    # project that bears a current revision cannot leave by marking it.
    raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": NO_CURRENT_REVISION})


def exit_project(session: Session, project_id: UUID, request: ExitRequest, act: Act) -> None:
    """Take a project out of its cycle, to a terminal state, with its reason (``exitProject``).

    The project is locked, then read under the lock, and judged there: at another counter (412),
    then by the conditions of the command of the exit, as the list says them (409), then for the
    current revision it still bears, which the caller must have abandoned (422 without a fate, 409
    ``no_current_revision`` with one). Then the state, the transition and its reason, and the
    counter are written, and the exit is inscribed in the journal with its state and its reason.
    """
    project = _lock(session, project_id)
    _judge_exit(project, request)
    _move(session, project, request.to_state, request.reason, act)
    project.updated_at = act.at
    project.updated_by = act.author
    project.lock_version += 1
    audited = AuditObject("project", project.id, project.label)
    # The journal names a project by its label, and by its code once it has one (#927, #2166).
    named = AuditProject(project.id, project.code, project.label)
    params = {"to_state": request.to_state, "reason": request.reason}
    actor = inscribed_actor(session, act.author)
    record(session, Inscription("project_exit", actor, audited, act.at, named, params))


def _rank(state: str) -> int:
    """Give the place of a state in the cycle; the terminal states share the last place."""
    return min(STATES.index(state), len(BEFORE_TERMINAL))


def list_state_transitions(session: Session, project_id: UUID) -> list[TransitionView]:
    """List the transitions of a project, in their order (``listProjectStateTransitions``)."""
    if session.get(Project, project_id) is None:
        raise NotFoundError(NOT_FOUND)
    rows = session.scalars(
        select(ProjectStateTransition)
        .where(ProjectStateTransition.project_id == project_id)
        .order_by(ProjectStateTransition.occurred_at)
    )
    # Two transitions can share an instant (the creation and the first revision of a project of the
    # witness): the cycle only goes forward, so the state reached ranks them, never the identifier.
    ranked = sorted(rows, key=lambda row: (row.occurred_at, _rank(row.to_state)))
    return [
        TransitionView(row.from_state, row.to_state, row.occurred_at, row.actor_user_id, row.reason)
        for row in ranked
    ]


def load_transitions(session: Session, project_id: UUID, act: Act) -> None:
    """Write the transitions of a project of the witness, at the instants it imposes."""
    msg = "load_transitions is filled by US-0990/L2"
    raise NotImplementedError(msg)


def no_background_task_running(session: Session, project_id: UUID) -> bool:
    """Tell whether no background task that writes in the project is queued or running.

    The tasks that aim at a project — its marking (US-0970), and the merges, occurrences and
    imports of later epics — are read in ``waterfall.platform.tasks``.
    """
    return not project_task_pending(session, project_id)
