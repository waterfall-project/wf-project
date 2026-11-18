# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision of an identified risk changed, private to the module (``updateRiskProvision``).

An entry of the current revision, under ``edit_risks``, judged in the order the command
``update_provision`` lists its conditions (409 ``STATE_FORBIDS_OPERATION``): a terminal project
(``project_not_terminal``), a background task that writes in the project
(``no_background_task_running``), then, the risk read in its revision and the counter it was read
at (404, 412), a risk that is not identified (``risk_identified``) and, the project without a
current revision, the permission to create it (``may_create_revision``). Then each designation, a
category changed, a subproject, a task, refused on its field (422): the 409 comes first, a category
sent for a risk that is not identified being refused with ``risk_identified`` (#747). Nothing is
written then.

It then writes the category and the subproject on the line, whatever the state of its task
and the costs its subproject received (WF-PRJ-0050), moves the line under the task designated, the
total of the estimate unchanged (WF-RIS-0010), and the evaluation of the risk in the revision: its
category, its subproject and the lineage of the task it designates, none for the first task of the
first level. The counter of the risk advances. Nothing enters the history before US-2590/L2, which
undoes and redoes the entries of the risks; the abandonment of the revision brings the evaluation
and the line back with it (WF-RIS-0020).
"""

from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import share_natures
from waterfall.core.estimate.interface import set_provision_bearing
from waterfall.core.planning.interface import (
    Place,
    first_task,
    lineages_of,
    move_borne_line,
    task_of,
    task_of_lineage,
)
from waterfall.core.projects.interface import (
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_NOT_TERMINAL,
    lock_project,
    no_background_task_running,
    project_facts,
    subproject_labels,
)
from waterfall.core.revisions.interface import (
    aimed_structure,
    create_revision,
    revision_draft,
    structure_facts,
)
from waterfall.core.risks.commands import (
    IDENTIFIED,
    MAY_CREATE_REVISION,
    REVISIONS_WRITE,
    RISK_IDENTIFIED,
    is_terminal,
)
from waterfall.core.risks.declaring import (
    SUBPROJECT,
    TASK,
    UNKNOWN_SUBPROJECT,
    UNKNOWN_TASK,
    designated_category,
    refuse,
)
from waterfall.core.risks.reading import evaluation_of, found_risk, read_found
from waterfall.core.risks.views import OMITTED, Omitted
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.interface.provisions import RiskProvisionChange
    from waterfall.core.risks.tables import Risk, RiskEvaluation


def _read_before(
    session: Session, project_id: UUID, change: RiskProvisionChange, viewer: Viewer
) -> None:
    """Judge a change that would create the revision, on the risk of the last marked one.

    The risk unknown or held by no revision (404), the counter read (412), a risk that is not
    identified (``risk_identified``), the creation of the revision a permission of its own
    (``may_create_revision``). The risk is locked first, and held until the commit, so that the
    counter judged is the one the opening of the revision starts from.
    """
    found_risk(session, project_id, change.risk_id, lock=True)
    found = read_found(session, project_id, change.risk_id, None)
    _judge_held(change, found.risk, found.evaluation)
    if REVISIONS_WRITE not in viewer.permissions:
        raise refuse(MAY_CREATE_REVISION)


def _judge_held(change: RiskProvisionChange, risk: Risk, evaluation: RiskEvaluation) -> None:
    """Judge the counter and the state of the risk read under its lock (412, 409)."""
    if risk.lock_version != change.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": risk.lock_version}
        )
    if evaluation.state != IDENTIFIED:
        raise refuse(RISK_IDENTIFIED)


def _designated(
    session: Session,
    place: Place,
    change: RiskProvisionChange,
    held: tuple[RiskEvaluation, bool],
) -> tuple[UUID, UUID | None, UUID | Omitted, UUID | None]:
    """Judge what the change designates; give the category, the subproject, the task, its lineage.

    A field ``OMITTED`` is the risk's: its category, deactivated since, accepted as it is. The task
    is ``OMITTED`` as well when the line is to stay where it is, its lineage the evaluation's.
    ``held`` the evaluation and whether this entry created the revision: a task named is then one
    of the revision it copied, found in the copy by its lineage (WF-DAT-0030). Every field refused
    is named at once (422); nothing is written.
    """
    evaluation, created = held
    project_id = place.project_id
    faults: list[FieldError] = []
    category = evaluation.provision_cost_category_id
    sent = change.provision_cost_category_id
    if not isinstance(sent, Omitted) and sent != category:
        judged = designated_category(session, sent, faults)
        category = category if judged is None else judged
    subproject = evaluation.provision_subproject_id
    designated = change.provision_subproject_id
    if not isinstance(designated, Omitted):
        subproject = designated
        if designated is not None and not subproject_labels(
            session, project_id, [designated], held=True
        ):
            faults.append(FieldError(SUBPROJECT, UNKNOWN_SUBPROJECT))
    sent_task = change.provision_task_id
    target: UUID | Omitted = OMITTED
    lineage = evaluation.provision_task_lineage_id
    if not isinstance(sent_task, Omitted):
        named = (
            first_task(session, project_id, place.structure_id)
            if sent_task is None
            else task_of(session, project_id, place.structure_id, sent_task)
        )
        if named is None and created and sent_task is not None:
            copied = lineages_of(session, project_id, [sent_task]).get(sent_task)
            named = (
                None
                if copied is None
                else task_of_lineage(session, project_id, place.structure_id, copied)
            )
        if named is None:
            faults.append(FieldError(TASK, UNKNOWN_TASK))
        else:
            target, lineage = named.node_id, None if sent_task is None else named.lineage_id
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return category, subproject, target, lineage


def update_provision(
    session: Session, project_id: UUID, change: RiskProvisionChange, writer: Writer, viewer: Viewer
) -> UUID:
    """Change the provision of an identified risk in the current revision; give the revision.

    The order of the locks, which every write that touches a risk and its line follows (a deletion,
    an import, a write of the own estimate; see ``follow_own_estimate``): the lock of the natures
    of cost first, as every write of the tree does (#2615); the main structure that bears the
    line; then the risk, whose counter advances under it. The opening of a revision by this entry is
    the one exception: the project, then the risk, then the main structure of the revision opened,
    which no other transaction sees before the commit. The current revision is created, if the
    project has none, a copy of the last marked one that copies the evaluation of the risk and its
    line; the counter and the state of the risk are judged under its lock, in both cases.
    """
    act = writer.act
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
        # The project locked first, as the opening of a revision does: another opening waits for it
        # before it advances this risk, and the revision it opened is the one we write in.
        facts = lock_project(session, project_id)
        if is_terminal(facts.state):
            raise refuse(PROJECT_NOT_TERMINAL)
        revision_id = facts.current_revision_id
        if revision_id is not None:
            revision_draft(session, revision_id)
    created = revision_id is None
    if revision_id is None:
        _read_before(session, project_id, change, viewer)
        revision_id = create_revision(session, project_id, act, viewer).revision_id
    main = aimed_structure(session, project_id, revision_id, None)
    if main is None:
        raise NotFoundError(NOT_FOUND)
    place = Place(project_id, revision_id, main)
    structure_facts(session, project_id, main, lock=True)
    risk = found_risk(session, project_id, change.risk_id, lock=True)
    evaluation = evaluation_of(session, project_id, risk.id, revision_id)
    if evaluation is None:
        raise NotFoundError(NOT_FOUND)
    if not created:
        # A revision we created advanced the counter at its opening, which was judged before it,
        # under the lock of the risk held since.
        _judge_held(change, risk, evaluation)
    line = evaluation.provision_node_id
    if line is None:
        raise NotFoundError(NOT_FOUND)
    designated = _designated(session, place, change, (evaluation, created))
    category, subproject, task, lineage = designated
    moved = not isinstance(task, Omitted) and move_borne_line(session, place, line, task, writer)
    changed = set_provision_bearing(session, place, line, (category, subproject))
    held = (
        evaluation.provision_cost_category_id,
        evaluation.provision_subproject_id,
        evaluation.provision_task_lineage_id,
    )
    if not (moved or changed or (category, subproject, lineage) != held):
        return revision_id
    evaluation.provision_cost_category_id = category
    evaluation.provision_subproject_id = subproject
    evaluation.provision_task_lineage_id = lineage
    evaluation.updated_at, evaluation.updated_by = act.at, act.author
    risk.updated_at, risk.updated_by = act.at, act.author
    risk.lock_version += 1
    session.flush()
    return revision_id
