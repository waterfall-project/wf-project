# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The occurrence of a risk applied, private to the module (``declareRiskOccurrence``; US-2620/L2).

One operation, one transaction, as a background task of the kind ``risk_occurrence`` (WF-ARC-0090):
the very computation of the report (``graft`` of the planning), applied under the locks, so that
what the report presented is what is written (WF-RIS-0060; EP-08, "La fusion et la survenance").

- **The request** judges the confirmation in the order of the contract, under the lock of the
  project, then of the two structures and of the risk (the order of ``enter``): the conditions of
  the project (409), the risk read (404), those of the risk (409), then the counters it read — the
  main structure, the risk — and ``creates_current_revision`` (412 ``STALE_LOCK_VERSION``,
  ``params.expected_lock_version`` the counter of the risk, whichever advanced). Nothing is written
  but the task.
- **The worker** judges the same again as it stands when the task runs, under the same locks; the
  project having no current revision, it opens one first, a copy of the last marked one at the
  rates it kept, projected (``open_revision_by_task``), after the counters were judged on the
  revision marked, whose structure the marking froze. Then the evaluation passes to occurred — the
  cost at occurrence frozen, the total of the own estimate at that instant, the provision line no
  longer named, which the graft removes —, the own estimate is grafted into the main structure, its
  tasks marked with the risk, marked merged, a review of the occurrence is written, and the counter
  of the risk advances. Nothing is marked, the reference does not move, nothing enters the history
  that can be undone. A refusal, or any failure, leaves nothing written.
- **The locks**, in one order: the natures of cost, the project, the own estimate, the main
  structure, then the risk.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.cost_settings.interface import share_natures
from waterfall.core.estimate.interface import structure_amount
from waterfall.core.planning.interface import Graft, bearing_of, graft
from waterfall.core.projects.interface import (
    current_day,
    lock_project,
    project_code,
    project_facts,
    project_label,
)
from waterfall.core.revisions.interface import (
    aimed_structure,
    consume_own_estimate,
    open_revision_by_task,
    revision_draft,
    structure_facts,
)
from waterfall.core.risks.commands import IDENTIFIED, OCCURRED, RISK_IDENTIFIED
from waterfall.core.risks.declaring import refuse
from waterfall.core.risks.occurring import judge_project, judge_risk
from waterfall.core.risks.reading import evaluation_of, found_risk, read_found
from waterfall.core.risks.tables import RiskReview
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditObject, AuditProject, AuditRevision, Inscription, record
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    NotFoundError,
    PreconditionFailedError,
)
from waterfall.platform.identifiers import new_id
from waterfall.platform.tasks import PROJECT, submit

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.tables import Risk, RiskEvaluation
    from waterfall.platform.audit import Act
    from waterfall.platform.queue import TaskQueue

# What the task of an occurrence carries besides its project: the risk, and what the report read.
RISK = "risk_id"
MAIN_LOCK_VERSION = "main_structure_lock_version"
RISK_LOCK_VERSION = "risk_lock_version"
CREATES_REVISION = "creates_current_revision"


@dataclass(frozen=True, slots=True)
class OccurrenceRequest:
    """An occurrence confirmed (``RiskOccurrence``): the risk, and what its report read."""

    project_id: UUID
    risk_id: UUID
    main_structure_lock_version: int
    risk_lock_version: int
    creates_current_revision: bool

    def payload(self) -> dict[str, Any]:
        """Give what the task carries of it."""
        return {
            PROJECT: str(self.project_id),
            RISK: str(self.risk_id),
            MAIN_LOCK_VERSION: self.main_structure_lock_version,
            RISK_LOCK_VERSION: self.risk_lock_version,
            CREATES_REVISION: self.creates_current_revision,
        }

    @classmethod
    def of(cls, payload: Mapping[str, Any]) -> OccurrenceRequest:
        """Read the request a task carries."""
        return cls(
            UUID(payload[PROJECT]),
            UUID(payload[RISK]),
            payload[MAIN_LOCK_VERSION],
            payload[RISK_LOCK_VERSION],
            payload[CREATES_REVISION],
        )


def _stale(risk: Risk) -> PreconditionFailedError:
    """Refuse a report that is no longer the state: the counter of the risk, whichever advanced."""
    return PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": risk.lock_version})


def _judge_counters(request: OccurrenceRequest, main_counter: int, risk: Risk) -> None:
    """Refuse (412) a main structure or a risk written since the report was read."""
    if main_counter != request.main_structure_lock_version:
        raise _stale(risk)
    if risk.lock_version != request.risk_lock_version:
        raise _stale(risk)


def _judge_creation(request: OccurrenceRequest, current: UUID | None, risk: Risk) -> None:
    """Refuse (412) a current revision born since the report, or gone."""
    if (current is None) != request.creates_current_revision:
        raise _stale(risk)


def _locked(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID
) -> tuple[Risk, RiskEvaluation, UUID, int]:
    """Lock the two structures and the risk of a revision, in order; read them under their locks.

    The own estimate, the main structure, then the risk. Give the risk, its evaluation in the
    revision, the main structure and its counter.
    """
    pending = evaluation_of(session, project_id, risk_id, revision_id)
    if pending is None:
        raise NotFoundError(NOT_FOUND)
    structure_facts(session, project_id, pending.structure_id, lock=True)
    main = aimed_structure(session, project_id, revision_id, None)
    if main is None:
        raise NotFoundError(NOT_FOUND)
    main_counter = structure_facts(session, project_id, main, lock=True).lock_version
    risk = found_risk(session, project_id, risk_id, lock=True)
    evaluation = evaluation_of(session, project_id, risk_id, revision_id)
    if evaluation is None:
        raise NotFoundError(NOT_FOUND)
    return risk, evaluation, main, main_counter


def submit_occurrence_task(
    session: Session, queue: TaskQueue, request: OccurrenceRequest, act: Act, viewer: Viewer
) -> UUID:
    """Judge an occurrence confirmed, then submit its task, in the transaction of the request.

    Under the lock of the project, the conditions of the project (409), the risk read (404), those
    of the risk (409), then, under the locks of the structures and of the risk, the counters and
    ``creates_current_revision`` (412), as the report read them. Nothing is written then.
    """
    project_id = request.project_id
    lock_project(session, project_id)
    judge_project(session, project_id)
    found = judge_risk(session, project_id, request.risk_id, viewer)
    revision_id = found.evaluation.revision_id
    risk, _, _, main_counter = _locked(session, project_id, request.risk_id, revision_id)
    _judge_creation(request, project_facts(session, project_id).current_revision_id, risk)
    _judge_counters(request, main_counter, risk)
    return submit(session, queue, "risk_occurrence", act.author, request.payload())


def _opened(
    session: Session, request: OccurrenceRequest, revision_id: UUID, running: tuple[Act, UUID]
) -> UUID:
    """Open the current revision the occurrence creates, the counters judged on the marked one.

    ``revision_id`` the revision marked the risk is read in, ``running`` the act and the task that
    open it. The risk locked first, as ``enter`` does for a revision it creates: the counter judged
    is the one the opening starts from, which advances it. The structure marked is frozen.
    """
    project_id = request.project_id
    act, task_id = running
    risk = found_risk(session, project_id, request.risk_id, lock=True)
    main = aimed_structure(session, project_id, revision_id, None)
    if main is None:
        raise NotFoundError(NOT_FOUND)
    main_counter = structure_facts(session, project_id, main, lock=False).lock_version
    _judge_counters(request, main_counter, risk)
    return open_revision_by_task(session, project_id, act, task_id)


def run_occurrence_task(
    session: Session, payload: Mapping[str, Any], act: Act, task_id: UUID
) -> None:
    """Apply the occurrence a task names, in the transaction of the task (the worker's).

    Judged again under the locks as the request judged it, the task itself not counting as a task
    that writes in the project; refused, it fails with its code and nothing is written. The
    revision is created first if the project has none.
    """
    request = OccurrenceRequest.of(payload)
    project_id, risk_id = request.project_id, request.risk_id
    share_natures(session)
    facts = lock_project(session, project_id)
    judge_project(session, project_id, task_id)
    found = read_found(session, project_id, risk_id, None)
    current = facts.current_revision_id
    _judge_creation(request, current, found.risk)
    if found.evaluation.state != IDENTIFIED:
        raise refuse(RISK_IDENTIFIED)
    if current is None:
        revision_id = _opened(session, request, found.evaluation.revision_id, (act, task_id))
    else:
        revision_draft(session, current)
        revision_id = current
    risk, evaluation, main, main_counter = _locked(session, project_id, risk_id, revision_id)
    if current is not None:
        _judge_counters(request, main_counter, risk)
    _apply(session, (risk, evaluation, main), act)
    _inscribe(session, risk, revision_id, act)


def _apply(session: Session, held: tuple[Risk, RiskEvaluation, UUID], act: Act) -> None:
    """Write the occurrence of a risk judged, under the locks of its structures and of the risk.

    The cost at occurrence is the total of the own estimate before it is grafted; the evaluation
    stops naming the provision line before the graft deletes it (its key and its constraint refuse
    otherwise); the structure grafted into is redated by the graft, which advances its counter.
    """
    risk, evaluation, main = held
    project_id = risk.project_id
    line = evaluation.provision_node_id
    if line is None:
        msg = "an identified risk bears its provision line in the main structure"
        raise ValueError(msg)
    own = evaluation.structure_id
    cost = structure_amount(session, project_id, own)
    bearer = bearing_of(session, project_id, (line,))[line].node_id
    evaluation.state = OCCURRED
    evaluation.provision_node_id = None
    evaluation.occurrence_cost = cost
    evaluation.updated_at, evaluation.updated_by = act.at, act.author
    session.flush()
    graft(session, Graft(project_id, own, main, bearer, (line,), risk.id), act)
    consume_own_estimate(session, project_id, own)
    risk.updated_at, risk.updated_by = act.at, act.author
    risk.lock_version += 1
    session.add(
        RiskReview(
            project_id=project_id,
            id=new_id(),
            risk_id=risk.id,
            revision_id=evaluation.revision_id,
            reviewed_on=current_day(act.at),
            probability=evaluation.probability,
            severity=cost,
            state=OCCURRED,
            created_at=act.at,
            created_by=act.author,
        )
    )
    session.flush()


def _inscribe(session: Session, risk: Risk, revision_id: UUID, act: Act) -> None:
    """Inscribe the occurrence in the journal: the risk, its revision, its project (WF-SEC-0030)."""
    project_id = risk.project_id
    label = project_label(session, project_id)
    code = project_code(session, project_id)
    named = None if label is None else AuditProject(project_id, code, label)
    audited = AuditObject("risk", risk.id, risk.label, AuditRevision(revision_id, None))
    actor = inscribed_actor(session, act.author)
    record(session, Inscription("risk_occurrence", actor, audited, act.at, project=named))
