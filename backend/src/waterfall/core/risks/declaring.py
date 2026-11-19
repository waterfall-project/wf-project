# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk declared, and its identity changed, private to the module (US-2570/L1).

The declaration (``createRisk``) is an entry of the current revision, under ``edit_risks``, judged
in the order the command ``declare_risk`` lists its conditions (409 ``STATE_FORBIDS_OPERATION``):
a terminal project (``project_not_terminal``), a background task that writes in the project
(``no_background_task_running``), a main structure without a task (``at_least_one_task``), no
active category of the provision kind (``active_provision_category``), then, the project without a
current revision, the permission to create it (``may_create_revision``) — the conditions of the
structure judged on the revision the declaration writes in, or would create: a copy of the last
marked one. Then the designations of its provision, each refused on its field (422) with a
probability out of 0 to 1: a category omitted among several (``VALUE_REQUIRED``), unknown, of
another kind than the provision (``PROVISION_CATEGORY_REQUIRED``) or deactivated; a subproject the
project does not have; a node that is no task of the main structure (``UNKNOWN_TASK``). Nothing is
written then.

It creates, in that order, the current revision if the project has none (WF-REV-0010, its rates
kept and projected, WF-REV-0060), the risk, its own estimate (E-09), its provision line under the
task designated or the first of the first level, of nought while its own estimate is empty, and its
evaluation in the revision — its probability, the state identified, its own estimate, its line,
the category, the subproject and the lineage of the task it designates — with a first review dated
of the day (WF-RIS-0010). The natures of cost are shared first, then the revision is held ``FOR
SHARE``, as any write of the tree takes them; the entry of the history of the writer
(``risk_create``, US-2590/L2) is opened once the revision is known, which locks the stack, and
its main structure is locked by the write of the line.

The identity (``updateRisk``) is a datum of the project (H-02, #1783): the label, the description
and the notes of mitigation, written at the counter of the risk read (412), refused on a terminal
project then on a risk occurred in the revision read (409), without creating a revision nor
entering the history, which no abandonment undoes. The project is locked, then the risk.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import (
    categories_of_kind,
    category_labels,
    provision_category_active,
    share_natures,
)
from waterfall.core.estimate.interface import ProvisionEntry, rename_provision
from waterfall.core.planning.interface import Place, create_borne_line, first_task, task_of
from waterfall.core.projects.interface import (
    ACTIVE_PROVISION_CATEGORY,
    AT_LEAST_ONE_TASK,
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_NOT_TERMINAL,
    current_day,
    lock_project,
    no_background_task_running,
    project_facts,
    subproject_labels,
)
from waterfall.core.revisions.interface import (
    aimed_structure,
    create_own_estimate,
    create_revision,
    last_marked_revision,
    main_structure_has_task,
    rename_own_estimate,
    revision_draft,
    structure_facts,
)
from waterfall.core.risks.commands import (
    IDENTIFIED,
    MAY_CREATE_REVISION,
    OCCURRED,
    REVISIONS_WRITE,
    RISK_NOT_OCCURRED,
    is_terminal,
)
from waterfall.core.risks.reading import (
    NOUGHT,
    PROVISION_KIND,
    evaluation_of,
    found_risk,
    read_found,
)
from waterfall.core.risks.recording import recorded
from waterfall.core.risks.tables import PROBABILITY_SCALE, Risk, RiskEvaluation, RiskReview
from waterfall.core.risks.views import Omitted
from waterfall.platform.errors import (
    STALE_LOCK_VERSION,
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import TaskNamed, Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.views import RiskEntry, RiskIdentityChange
    from waterfall.platform.audit import Act

VALUE_REQUIRED = "VALUE_REQUIRED"
UNKNOWN_COST_CATEGORY = "UNKNOWN_COST_CATEGORY"
INACTIVE_REFERENCE_OBJECT = "INACTIVE_REFERENCE_OBJECT"
PROVISION_CATEGORY_REQUIRED = "PROVISION_CATEGORY_REQUIRED"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
UNKNOWN_TASK = "UNKNOWN_TASK"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
PROBABILITY = "/probability"
# The pointers of the designations of a declaration (``RiskWrite``).
CATEGORY, SUBPROJECT, TASK = (
    "/provision_cost_category_id",
    "/provision_subproject_id",
    "/provision_task_id",
)


def refuse(condition: str) -> ConflictError:
    """Give the refusal of a write a condition of the state lacks (409)."""
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": condition})


def _judge_state(
    session: Session, project_id: UUID, revision_id: UUID | None, running: UUID | None
) -> None:
    """Refuse a declaration by the conditions of ``declare_risk`` after the terminal project.

    ``revision_id`` the revision written in, or the one a creation would copy, none for a project
    that has neither, whose revision would be born without a task; ``running`` the background task
    that declares, which suspends no write of its own.
    """
    if not no_background_task_running(session, project_id, running):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)
    if revision_id is None or not main_structure_has_task(session, project_id, revision_id):
        raise refuse(AT_LEAST_ONE_TASK)
    if not provision_category_active(session):
        raise refuse(ACTIVE_PROVISION_CATEGORY)


def probability_faults(probability: Decimal) -> list[FieldError]:
    """Refuse a probability out of 0 to 1, naming the bound crossed, or more precise than kept.

    A ratio (WF-RIS-0010); one of more decimals than the column keeps, which the base would round,
    is a plain failure of its field, as the probability of winning of a project is.
    """
    if not Decimal(0) <= probability <= Decimal(1):
        bound = {"minimum": "0"} if probability < 0 else {"maximum": "1"}
        return [FieldError(PROBABILITY, VALUE_OUT_OF_RANGE, bound)]
    exponent = probability.normalize().as_tuple().exponent
    if isinstance(exponent, int) and -exponent > PROBABILITY_SCALE:
        return [FieldError(PROBABILITY, VALIDATION_FAILED)]
    return []


def designated_category(
    session: Session, category_id: UUID | None, faults: list[FieldError]
) -> UUID | None:
    """Judge the category of a provision: the only active one of the kind when none is named.

    The natures are shared first (``category_labels``, ``locked``): a deactivation waits for the
    declaration, or is waited for.
    """
    if category_id is None:
        provisions = category_labels(
            session, categories_of_kind(session, PROVISION_KIND), locked=True
        )
        active = [
            each.cost_category_id
            for each in provisions.values()
            if each.is_active and each.cost_type_is_active
        ]
        if len(active) == 1:
            return active[0]
        faults.append(FieldError(CATEGORY, VALUE_REQUIRED))
        return None
    category = category_labels(session, [category_id], locked=True).get(category_id)
    if category is None:
        faults.append(FieldError(CATEGORY, UNKNOWN_COST_CATEGORY))
    elif category.cost_type_kind != PROVISION_KIND:
        faults.append(FieldError(CATEGORY, PROVISION_CATEGORY_REQUIRED))
    elif not (category.is_active and category.cost_type_is_active):
        faults.append(FieldError(CATEGORY, INACTIVE_REFERENCE_OBJECT))
    else:
        return category_id
    return None


def _designated(
    session: Session, place: Place, entry: RiskEntry
) -> tuple[UUID, UUID | None, TaskNamed]:
    """Judge what a declaration designates for its provision; give the category, subproject, task.

    ``place`` the main structure of the revision written in. Every field refused is named at once
    (422); nothing is written.
    """
    project_id = place.project_id
    faults = probability_faults(entry.probability)
    category = designated_category(session, entry.provision_cost_category_id, faults)
    subproject = entry.provision_subproject_id
    if subproject is not None and not subproject_labels(
        session, project_id, [subproject], held=True
    ):
        faults.append(FieldError(SUBPROJECT, UNKNOWN_SUBPROJECT))
    designated = entry.provision_task_id
    task = (
        first_task(session, project_id, place.structure_id)
        if designated is None
        else task_of(session, project_id, place.structure_id, designated)
    )
    if task is None:
        faults.append(FieldError(TASK, UNKNOWN_TASK))
    if faults or category is None or task is None:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return category, subproject, task


def declare(
    session: Session, project_id: UUID, entry: RiskEntry, writer: Writer, viewer: Viewer
) -> tuple[UUID, UUID]:
    """Declare a risk in the current revision, created if needed; give the risk and the revision.

    An entry of the history of its writer (``risk_create``, US-2590/L2), opened once the revision
    is known and before the main structure is locked, whose undoing takes the risk away.
    """
    # The natures first, as every write of the tree takes them (#2615), before the stack.
    share_natures(session)
    facts = project_facts(session, project_id)
    if is_terminal(facts.state):
        raise refuse(PROJECT_NOT_TERMINAL)
    revision_id = facts.current_revision_id
    if revision_id is not None:
        revision_draft(session, revision_id)
    judged = revision_id or last_marked_revision(session, project_id)
    _judge_state(session, project_id, judged, writer.running)
    if revision_id is None:
        if REVISIONS_WRITE not in viewer.permissions:
            raise refuse(MAY_CREATE_REVISION)
        revision_id = create_revision(session, project_id, writer.act, viewer).revision_id
    with recorded(session, project_id, writer, "risk_create") as recording:
        recording.open(revision_id)
        recording.before(None)
        risk_id = _declared(session, (project_id, revision_id), entry, writer)
        recording.after(risk_id, whole=True)
    return risk_id, revision_id


def _declared(
    session: Session, revision: tuple[UUID, UUID], entry: RiskEntry, writer: Writer
) -> UUID:
    """Write a risk declared in a revision: its row, its own estimate, its line, its evaluation."""
    act = writer.act
    project_id, revision_id = revision
    main = aimed_structure(session, project_id, revision_id, None)
    if main is None:
        raise refuse(AT_LEAST_ONE_TASK)
    place = Place(project_id, revision_id, main)
    category, subproject, task = _designated(session, place, entry)
    risk_id = new_id()
    session.add(
        Risk(
            id=risk_id,
            project_id=project_id,
            label=entry.label,
            description=entry.description,
            mitigation_notes=entry.mitigation_notes,
            lock_version=1,
            **_stamp(act),
        )
    )
    session.flush()
    structure_id = create_own_estimate(
        session, (project_id, revision_id), (risk_id, entry.label), act
    )
    provision = ProvisionEntry(entry.label, category, subproject, NOUGHT)
    line = create_borne_line(session, place, task.node_id, provision, writer)
    session.add(
        RiskEvaluation(
            project_id=project_id,
            risk_id=risk_id,
            revision_id=revision_id,
            probability=entry.probability,
            state=IDENTIFIED,
            structure_id=structure_id,
            provision_node_id=line,
            provision_cost_category_id=category,
            provision_subproject_id=subproject,
            provision_task_lineage_id=None if entry.provision_task_id is None else task.lineage_id,
            occurrence_cost=None,
            **_stamp(act),
        )
    )
    session.add(
        RiskReview(
            project_id=project_id,
            id=new_id(),
            risk_id=risk_id,
            revision_id=revision_id,
            reviewed_on=current_day(act.at),
            probability=entry.probability,
            severity=NOUGHT,
            state=IDENTIFIED,
            created_at=act.at,
            created_by=act.author,
        )
    )
    session.flush()
    return risk_id


def change_identity(
    session: Session, project_id: UUID, change: RiskIdentityChange, act: Act
) -> None:
    """Write the identity of a risk at the counter read, a datum of the project (H-02, #1783).

    Refused if the risk is unknown or has no evaluation to read (404), at another version (412),
    on a terminal project, then on a risk occurred in the revision read (409). A change that
    changes nothing writes nothing; a description or notes not sent stay the risk's.

    A new label renames the own estimate and the provision line of the risk in the current
    revision, if the risk is evaluated there, as the declaration named them: outside the history,
    like the identity (H-02), the revisions marked keeping the names they were marked with (#3980).
    Without a current revision it writes the identity alone: the revision opened next names them
    by the label of the risk (``copy_evaluations``).
    The own estimate is locked before the risk, as every write of its tree locks them.
    """
    facts = lock_project(session, project_id)
    current = (
        None
        if facts.current_revision_id is None
        else evaluation_of(session, project_id, change.risk_id, facts.current_revision_id)
    )
    if current is not None:
        structure_facts(session, project_id, current.structure_id, lock=True)
    risk = found_risk(session, project_id, change.risk_id, lock=True)
    evaluation = read_found(session, project_id, risk.id, None).evaluation
    if risk.lock_version != change.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": risk.lock_version}
        )
    if is_terminal(facts.state):
        raise refuse(PROJECT_NOT_TERMINAL)
    if evaluation.state == OCCURRED:
        raise refuse(RISK_NOT_OCCURRED)
    written = (
        change.label,
        risk.description if isinstance(change.description, Omitted) else change.description,
        (
            risk.mitigation_notes
            if isinstance(change.mitigation_notes, Omitted)
            else change.mitigation_notes
        ),
    )
    if written == (risk.label, risk.description, risk.mitigation_notes):
        return
    renamed = written[0] != risk.label
    risk.label, risk.description, risk.mitigation_notes = written
    risk.updated_at, risk.updated_by = act.at, act.author
    risk.lock_version += 1
    session.flush()
    if renamed and current is not None:
        _rename_in_revision(session, (project_id, current), written[0], act)


def _rename_in_revision(
    session: Session, held: tuple[UUID, RiskEvaluation], label: str, act: Act
) -> None:
    """Name the own estimate and the provision line an evaluation holds by the label of its risk."""
    project_id, evaluation = held
    rename_own_estimate(session, project_id, evaluation.structure_id, label, act)
    line = evaluation.provision_node_id
    main = aimed_structure(session, project_id, evaluation.revision_id, None)
    if line is not None and main is not None:
        rename_provision(session, Place(project_id, evaluation.revision_id, main), line, label, act)


def _stamp(act: Act) -> dict[str, object]:
    """Give the audit columns of a row the act writes (WF-DAT-0070)."""
    return {
        "created_at": act.at,
        "created_by": act.author,
        "updated_at": act.at,
        "updated_by": act.author,
    }
