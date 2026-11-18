# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk as a revision freezes it, private to the module (``getRisk``; US-2570/L1).

Its identity is the project's (``risk``), its evaluation the revision's (``risk_evaluation``): the
probability, the state, the own estimate and the provision line the revision read holds
(WF-RIS-0030). What is computed is computed at the reading:

- its severity, the total of its own estimate in that revision (WF-RIS-0010);
- its provision: identified, the severity weighted by the probability, to the cent, which its line
  carries; occurred or dismissed, the share it held in the reference revision, nought without one
  (WF-RIS-0040, WF-RIS-0050; H-03);
- the labels of the category, of the subproject and of the task of its provision, the category
  told active when it and its nature are, and its nature of the provision kind (#747);
- its cell in the matrix of the reference settings: its probability, and its severity as a share of
  the base of the project — the lowest level on a base of nought (WF-REF-0160, #1240);
- the day of its last review, among the reviews of the revision read and of the marked revisions
  before it (EP-08, "Tables et migrations");
- its commands for the reader (``commands``).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import exists, func, select

from waterfall.core.cost_settings.interface import category_labels, read_reference_settings
from waterfall.core.estimate.interface import (
    lines_for_indicators,
    risk_base,
    round_to_cent,
    structure_amount,
)
from waterfall.core.planning.interface import bearing_of
from waterfall.core.projects.interface import project_facts, subproject_labels
from waterfall.core.revisions.interface import marked_revisions_at, read_revision_for
from waterfall.core.risk_settings.interface import level_of, zone_of
from waterfall.core.risks.commands import (
    IDENTIFIED,
    OCCURRED,
    RiskStanding,
    is_terminal,
    risk_commands,
)
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReferenceShare, RiskReview
from waterfall.core.risks.views import ProvisionTask, RiskMatrixCell, RiskView
from waterfall.platform.errors import NOT_FOUND, NotFoundError

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.views import RiskState

PROVISION_KIND = "provision"
NOUGHT = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class Found:
    """A risk and its evaluation in a revision, as read in the transaction."""

    risk: Risk
    evaluation: RiskEvaluation


def found_risk(session: Session, project_id: UUID, risk_id: UUID, *, lock: bool) -> Risk:
    """Read a risk of a project, locked when asked; or refuse (404)."""
    query = select(Risk).where(Risk.project_id == project_id, Risk.id == risk_id)
    if lock:
        query = query.with_for_update()
    risk = session.scalars(query.execution_options(populate_existing=True)).first()
    if risk is None:
        raise NotFoundError(NOT_FOUND)
    return risk


def evaluation_of(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID
) -> RiskEvaluation | None:
    """Read the evaluation of a risk in a revision, none if the revision holds none."""
    return session.scalars(
        select(RiskEvaluation)
        .where(
            RiskEvaluation.project_id == project_id,
            RiskEvaluation.risk_id == risk_id,
            RiskEvaluation.revision_id == revision_id,
        )
        .execution_options(populate_existing=True)
    ).first()


def _reference_share(
    session: Session, project_id: UUID, risk_id: UUID, reference_id: UUID | None
) -> Decimal:
    """Give the provision a risk held in the reference revision, nought without one (H-03)."""
    if reference_id is None:
        return NOUGHT
    share = session.scalar(
        select(RiskReferenceShare.provision_amount).where(
            RiskReferenceShare.project_id == project_id,
            RiskReferenceShare.revision_id == reference_id,
            RiskReferenceShare.risk_id == risk_id,
        )
    )
    return NOUGHT if share is None else share


def _last_review(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID
) -> date | None:
    """Give the day of the last review of a risk the revision read sees, none without one.

    The reviews of the revision read and of the marked revisions marked before it: a review is not
    copied, and the history of a risk read in a revision is that of the marked ones before it and
    its own (EP-08, "Tables et migrations").
    """
    marked = marked_revisions_at(session, project_id)
    until = marked.get(revision_id)
    seen = {revision for revision, at in marked.items() if until is None or at < until} | {
        revision_id
    }
    return session.scalar(
        select(func.max(RiskReview.reviewed_on)).where(
            RiskReview.project_id == project_id,
            RiskReview.risk_id == risk_id,
            RiskReview.revision_id.in_(seen),
        )
    )


def risk_cited(session: Session, project_id: UUID, risk_id: UUID) -> bool:
    """Tell whether a marked revision holds an evaluation of a risk (``risk_not_cited``)."""
    marked = marked_revisions_at(session, project_id)
    if not marked:
        return False
    return bool(
        session.scalar(
            select(
                exists().where(
                    RiskEvaluation.project_id == project_id,
                    RiskEvaluation.risk_id == risk_id,
                    RiskEvaluation.revision_id.in_(list(marked)),
                )
            )
        )
    )


def _cell(
    session: Session, project_id: UUID, revision_id: UUID, values: tuple[Decimal, Decimal]
) -> RiskMatrixCell:
    """Place a probability and a severity in the matrix of the reference settings (WF-REF-0160).

    The severity as a share of the base of the project; on a base of nought, at the lowest level.
    """
    probability, severity = values
    matrix = read_reference_settings(session).risk_matrix
    base = risk_base(session, project_id, revision_id)
    ratio = severity / base if base > 0 else Decimal(0)
    return RiskMatrixCell(
        level_of(probability, matrix.probability_bounds),
        level_of(ratio, matrix.severity_bounds),
        zone_of(matrix, probability, ratio),
    )


def _provision_task(
    session: Session, project_id: UUID, evaluation: RiskEvaluation
) -> ProvisionTask | None:
    """Name the task that bears the provision line of a risk, none without a line."""
    line = evaluation.provision_node_id
    if line is None:
        return None
    task = bearing_of(session, project_id, [line]).get(line)
    return None if task is None else ProvisionTask(task.node_id, task.label)


def risk_view(session: Session, project_id: UUID, found: Found, viewer: Viewer) -> RiskView:
    """Describe a risk as the revision of its evaluation freezes it, with its commands."""
    risk, evaluation = found.risk, found.evaluation
    revision_id = evaluation.revision_id
    facts = project_facts(session, project_id)
    state: RiskState = (
        "identified"
        if evaluation.state == IDENTIFIED
        else "occurred"
        if evaluation.state == OCCURRED
        else "dismissed"
    )
    severity = structure_amount(session, project_id, evaluation.structure_id)
    provision = (
        round_to_cent(severity * evaluation.probability)
        if state == IDENTIFIED
        else _reference_share(session, project_id, risk.id, facts.reference_revision_id)
    )
    category_id = evaluation.provision_cost_category_id
    category = category_labels(session, [category_id])[category_id]
    subproject = evaluation.provision_subproject_id
    labels = {} if subproject is None else subproject_labels(session, project_id, [subproject])
    standing = RiskStanding(
        state,
        risk_cited(session, project_id, risk.id),
        is_terminal(facts.state),
        facts.current_revision_id is not None,
    )
    return RiskView(
        risk_id=risk.id,
        revision_id=revision_id,
        label=risk.label,
        description=risk.description,
        mitigation_notes=risk.mitigation_notes,
        probability=evaluation.probability,
        severity=severity,
        provision_amount=provision,
        occurrence_cost=evaluation.occurrence_cost,
        occurred_reestimated_amount=_occurred_reestimated(
            session, project_id, revision_id, risk.id, state
        ),
        state=state,
        structure_id=evaluation.structure_id,
        provision_node_id=evaluation.provision_node_id,
        provision_cost_category_id=category_id,
        provision_cost_category_label=category.label,
        provision_cost_category_is_active=(
            category.is_active
            and category.cost_type_is_active
            and category.cost_type_kind == PROVISION_KIND
        ),
        provision_subproject_id=subproject,
        provision_subproject_label=None if subproject is None else labels.get(subproject),
        provision_task=_provision_task(session, project_id, evaluation),
        matrix_cell=_cell(session, project_id, revision_id, (evaluation.probability, severity)),
        last_review_on=_last_review(session, project_id, risk.id, revision_id),
        commands=risk_commands(standing, viewer.permissions),
        created_at=risk.created_at,
        created_by=risk.created_by,
        updated_at=risk.updated_at,
        updated_by=risk.updated_by,
        lock_version=risk.lock_version,
    )


def _occurred_reestimated(
    session: Session, project_id: UUID, revision_id: UUID, risk_id: UUID, state: RiskState
) -> Decimal | None:
    """Give the re-estimated amount of the lines an occurrence merged, none unless occurred.

    The lines of the revision read whose task names the risk (``origin_risk_id``), which the
    occurrence merges (WF-RIS-0060): nought while it has merged none.
    """
    if state != OCCURRED:
        return None
    lines = lines_for_indicators(session, project_id, revision_id)
    return sum(
        (line.reestimated_amount for line in lines if line.task_origin_risk_id == risk_id), NOUGHT
    )


def read_found(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID | None
) -> Found:
    """Read a risk in a revision: the one named, else the current, else the last marked; or 404.

    A revision of another project, or one that holds no evaluation of the risk, is not found.
    """
    risk = found_risk(session, project_id, risk_id, lock=False)
    read = read_revision_for(session, project_id, revision_id).revision_id
    evaluation = evaluation_of(session, project_id, risk_id, read)
    if evaluation is None:
        raise NotFoundError(NOT_FOUND)
    return Found(risk, evaluation)
