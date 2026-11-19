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

from waterfall.core.estimate.interface import set_provision_bearing
from waterfall.core.planning.interface import (
    Place,
    first_task,
    lineages_of,
    move_borne_line,
    task_of,
    task_of_lineage,
)
from waterfall.core.projects.interface import subproject_labels
from waterfall.core.risks.commands import IDENTIFIED, RISK_IDENTIFIED
from waterfall.core.risks.declaring import (
    SUBPROJECT,
    TASK,
    UNKNOWN_SUBPROJECT,
    UNKNOWN_TASK,
    designated_category,
    refuse,
)
from waterfall.core.risks.entering import Held, enter
from waterfall.core.risks.views import OMITTED, Omitted
from waterfall.platform.errors import (
    NOT_FOUND,
    VALIDATION_FAILED,
    FieldError,
    NotFoundError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.interface.provisions import RiskProvisionChange
    from waterfall.core.risks.tables import RiskEvaluation


def _judge(evaluation: RiskEvaluation, _revision_id: UUID) -> None:
    """Judge the state of the risk the provision of which is changed (409, ``risk_identified``)."""
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

    Entered as every write of a risk is (``enter``, which says the order of the locks and the
    revision created): the counter and the state of the risk are judged under its lock.
    """
    act = writer.act
    held_risk = Held(change.risk_id, change.lock_version, _judge)
    entered = enter(session, project_id, held_risk, writer, viewer)
    place, risk, evaluation = entered.place, entered.risk, entered.evaluation
    revision_id, created = entered.revision_id, entered.created
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
