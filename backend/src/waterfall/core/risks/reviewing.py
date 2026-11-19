# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk reviewed, and its reviews read, private to the module (US-2590/L1).

The review (``reviewRisk``) is an entry of the current revision, under ``edit_risks``, entered as
every write of a risk is (``enter``) and judged in the order the contract lists its conditions
(409 ``STATE_FORBIDS_OPERATION``): a terminal project (``project_not_terminal``), a background task
that writes in the project (``no_background_task_running``), then, the risk read in its revision
and the counter it was read at (404, 412), a risk occurred (``risk_not_occurred``: no transition
leaves it, WF-RIS-0020) and, for a dismissed risk that would be identified again, a main structure
without a task (``at_least_one_task``) and no active category of the provision kind
(``active_provision_category``), then, the project without a current revision, the permission to
create it (``may_create_revision``). Then the designations, each refused on its field (422): a
probability out of 0 to 1; for the return to the identified state, the category asked for when the
one the risk designated is no longer active nor of the provision kind. Nothing is written then.

It writes, whatever the review changes — its confirmation without change included (WF-RIS-0010) —,
a review dated of the day, which keeps the probability sent, the severity of the own estimate and
the state retained, and advances the counter of the risk. A risk identified that is dismissed loses
its provision line, for good; a risk dismissed that is identified again recovers it (WF-RIS-0020):
under the task it designated if that is still a task of the main structure, else under the first
task of the first level (WF-RIS-0010, #1227), of the category it designated if that is still active
and of the provision kind, else of the one the review asks for, and of the subproject it designated;
a risk that stays identified has its line written again at the probability, the severity weighted
by it, to the cent.

The reviews of a risk read in a revision are those of the marked revisions before it, and its own.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.cost_settings.interface import category_labels, provision_category_active
from waterfall.core.estimate.interface import (
    ProvisionEntry,
    round_to_cent,
    set_provision,
    structure_amount,
)
from waterfall.core.planning.interface import (
    create_borne_line,
    delete_borne_line,
    first_task,
    task_of_lineage,
)
from waterfall.core.projects.interface import current_day
from waterfall.core.revisions.interface import main_structure_has_task, marked_revisions_at
from waterfall.core.risks.commands import DISMISSED, IDENTIFIED, OCCURRED, RISK_NOT_OCCURRED
from waterfall.core.risks.declaring import (
    ACTIVE_PROVISION_CATEGORY,
    AT_LEAST_ONE_TASK,
    designated_category,
    probability_faults,
    refuse,
)
from waterfall.core.risks.entering import Held, enter
from waterfall.core.risks.reading import PROVISION_KIND, read_found, seen_revisions
from waterfall.core.risks.tables import RiskReview
from waterfall.core.risks.views import RiskReviewView
from waterfall.platform.errors import VALIDATION_FAILED, UnprocessableError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Place, Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.entering import Judge
    from waterfall.core.risks.tables import Risk, RiskEvaluation
    from waterfall.core.risks.views import RiskReviewEntry, RiskState
    from waterfall.platform.errors import FieldError


def _judging(session: Session, project_id: UUID, entry: RiskReviewEntry) -> Judge:
    """Give what the review judges of the risk it enters, after the counter (409).

    The structure that would bear the line is judged in the revision written in, or in the last
    marked one a creation would copy.
    """

    def judge(evaluation: RiskEvaluation, revision_id: UUID) -> None:
        if evaluation.state == OCCURRED:
            raise refuse(RISK_NOT_OCCURRED)
        if evaluation.state == IDENTIFIED or entry.state != IDENTIFIED:
            return
        if not main_structure_has_task(session, project_id, revision_id):
            raise refuse(AT_LEAST_ONE_TASK)
        if not provision_category_active(session):
            raise refuse(ACTIVE_PROVISION_CATEGORY)

    return judge


def _category_of_return(
    session: Session, evaluation: RiskEvaluation, entry: RiskReviewEntry, faults: list[FieldError]
) -> UUID:
    """Give the category of the line a dismissed risk recovers; or name the field refused.

    The one it designated if it is still active and of the provision kind; else the one the review
    asks for, as the declaration does (WF-RIS-0010): the only active one when none is asked, refused
    when several exist. A category sent while the designated one holds is ignored.
    """
    held = evaluation.provision_cost_category_id
    label = category_labels(session, [held], locked=True).get(held)
    if (
        label is not None
        and label.is_active
        and label.cost_type_is_active
        and label.cost_type_kind == PROVISION_KIND
    ):
        return held
    chosen = designated_category(session, entry.provision_cost_category_id, faults)
    return held if chosen is None else chosen


def _recovered_task(session: Session, place: Place, evaluation: RiskEvaluation) -> UUID:
    """Give the task that bears the line a dismissed risk recovers (WF-RIS-0010, #1227).

    The task it designated if that is still a task of the structure (its lineage is the same in
    every revision, WF-DAT-0030), else the first task of the first level, which the main structure
    holds: the conditions of the review judged it (``at_least_one_task``).
    """
    lineage = evaluation.provision_task_lineage_id
    project_id, structure_id = place.project_id, place.structure_id
    named = None if lineage is None else task_of_lineage(session, project_id, structure_id, lineage)
    named = named or first_task(session, project_id, structure_id)
    if named is None:
        raise refuse(AT_LEAST_ONE_TASK)
    return named.node_id


def _write_review(
    session: Session,
    entry: RiskReviewEntry,
    held: tuple[Risk, RiskEvaluation],
    figures: tuple[UUID | None, Decimal],
    writer: Writer,
) -> None:
    """Write the review row, the evaluation and the counter of the risk the entry leaves.

    ``figures`` the provision line the evaluation names from now on, and the severity the review
    keeps. No statement is sent between the two columns of the evaluation that its constraint ties
    together, the line and the state (``provision_when_identified``): the flush follows.
    """
    risk, evaluation = held
    line, severity = figures
    act = writer.act
    evaluation.provision_node_id = line
    evaluation.probability, evaluation.state = entry.probability, entry.state
    evaluation.updated_at, evaluation.updated_by = act.at, act.author
    risk.updated_at, risk.updated_by = act.at, act.author
    risk.lock_version += 1
    session.add(
        RiskReview(
            project_id=risk.project_id,
            id=new_id(),
            risk_id=risk.id,
            revision_id=evaluation.revision_id,
            reviewed_on=current_day(act.at),
            probability=entry.probability,
            severity=severity,
            state=entry.state,
            created_at=act.at,
            created_by=act.author,
        )
    )
    session.flush()


def review(
    session: Session, project_id: UUID, entry: RiskReviewEntry, writer: Writer, viewer: Viewer
) -> UUID:
    """Review a risk in the current revision, created if need be; give the revision it is in."""
    held = Held(entry.risk_id, entry.lock_version, _judging(session, project_id, entry))
    entered = enter(session, project_id, held, writer, viewer)
    place, risk, evaluation = entered.place, entered.risk, entered.evaluation
    returning = evaluation.state == DISMISSED and entry.state == IDENTIFIED
    faults = probability_faults(entry.probability)
    category = evaluation.provision_cost_category_id
    if returning:
        category = _category_of_return(session, evaluation, entry, faults)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    severity = structure_amount(session, project_id, evaluation.structure_id)
    amount = round_to_cent(severity * entry.probability)
    line = evaluation.provision_node_id
    dismissing = line is not None and entry.state == DISMISSED
    named = line
    if returning:
        task_id = _recovered_task(session, place, evaluation)
        provision = ProvisionEntry(risk.label, category, evaluation.provision_subproject_id, amount)
        named = create_borne_line(session, place, task_id, provision, writer)
        evaluation.provision_cost_category_id = category
    elif dismissing:
        named = None
    _write_review(session, entry, (risk, evaluation), (named, severity), writer)
    if dismissing and line is not None:
        # The evaluation no longer names the line, which can now go.
        delete_borne_line(session, place, line, writer)
    elif line is not None:
        set_provision(session, place, line, amount)
    return entered.revision_id


def _state_of(value: str) -> RiskState:
    """Give the state a review kept as the contract names it."""
    return "identified" if value == IDENTIFIED else "occurred" if value == OCCURRED else "dismissed"


def list_reviews(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID | None
) -> list[RiskReviewView]:
    """List the reviews of a risk read in a revision, the most recent first (WF-RIS-0030).

    The risk unknown, a revision of another project or one that holds no evaluation of it is not
    found (404). A review of the same day comes after the one made later.
    """
    found = read_found(session, project_id, risk_id, revision_id)
    seen = seen_revisions(marked_revisions_at(session, project_id), found.evaluation.revision_id)
    rows = session.scalars(
        select(RiskReview)
        .where(
            RiskReview.project_id == project_id,
            RiskReview.risk_id == risk_id,
            RiskReview.revision_id.in_(list(seen)),
        )
        .order_by(RiskReview.reviewed_on.desc(), RiskReview.created_at.desc(), RiskReview.id.desc())
    )
    return [
        RiskReviewView(
            reviewed_on=each.reviewed_on,
            probability=each.probability,
            severity=each.severity,
            state=_state_of(each.state),
            actor=each.created_by,
            created_at=each.created_at,
        )
        for each in rows
    ]
