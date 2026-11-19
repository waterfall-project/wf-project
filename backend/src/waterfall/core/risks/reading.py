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

from sqlalchemy import func, select

from waterfall.core.cost_settings.interface import category_labels, read_reference_settings
from waterfall.core.estimate.interface import (
    lines_for_indicators,
    risk_base,
    round_to_cent,
    share_of,
    structure_amounts,
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
    from collections.abc import Collection, Sequence
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import CategoryLabel, RiskMatrix
    from waterfall.core.planning.interface import TaskNamed
    from waterfall.core.projects.interface import ProjectFacts, Viewer
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


@dataclass(frozen=True, slots=True)
class ReadContext:
    """What the reading of a set of risks shares, read once for all of them (US-2600/L1).

    ``risk_view`` describes a risk from it and from nothing else the database holds, so that a
    register costs the same statements whatever the number of its risks, and ``getRisk`` is the
    register of one: the two never read a column two ways.
    """

    facts: ProjectFacts
    matrix: RiskMatrix
    cited: frozenset[UUID]
    amounts: dict[UUID, Decimal]
    shares: dict[UUID, Decimal]
    categories: dict[UUID, CategoryLabel]
    subprojects: dict[UUID, str]
    tasks: dict[UUID, TaskNamed]
    bases: dict[UUID, Decimal]
    reestimated: dict[UUID, dict[UUID, Decimal]]
    reviews: dict[tuple[UUID, UUID], date]


def cited_among(
    session: Session, project_id: UUID, risk_ids: Collection[UUID], marked: Collection[UUID]
) -> set[UUID]:
    """Give the risks among those named that a marked revision holds an evaluation of (WF-RIS-0020).

    ``marked`` the marked revisions of the project: a risk they cite can no longer be deleted.
    """
    if not marked or not risk_ids:
        return set()
    return set(
        session.scalars(
            select(RiskEvaluation.risk_id)
            .where(
                RiskEvaluation.project_id == project_id,
                RiskEvaluation.risk_id.in_(list(risk_ids)),
                RiskEvaluation.revision_id.in_(list(marked)),
            )
            .distinct()
        )
    )


def _shares(
    session: Session, project_id: UUID, reference_id: UUID | None, risk_ids: Collection[UUID]
) -> dict[UUID, Decimal]:
    """Give the provision each risk held in the reference revision (H-03), in one statement."""
    if reference_id is None:
        return {}
    rows = session.execute(
        select(RiskReferenceShare.risk_id, RiskReferenceShare.provision_amount).where(
            RiskReferenceShare.project_id == project_id,
            RiskReferenceShare.revision_id == reference_id,
            RiskReferenceShare.risk_id.in_(list(risk_ids)),
        )
    )
    return dict(rows.all())


def seen_revisions(marked: dict[UUID, datetime], revision_id: UUID) -> set[UUID]:
    """Give the revisions whose reviews a revision read presents: its own and the marked before it.

    A review is not copied: the history of a risk read in a revision is that of the revisions
    marked before it, and its own (EP-08, "Tables et migrations"); those that follow its marking
    do not belong to what it freezes (WF-RIS-0030). A revision not marked, the current one, sees
    them all.
    """
    until = marked.get(revision_id)
    return {revision for revision, at in marked.items() if until is None or at < until} | {
        revision_id
    }


def _reviews(
    session: Session,
    project_id: UUID,
    marked: dict[UUID, datetime],
    founds: Sequence[Found],
) -> dict[tuple[UUID, UUID], date]:
    """Give the day of the last review of each risk, by revision read, in one statement each.

    The reviews of the revision read and of the marked revisions marked before it: a review is not
    copied, and the history of a risk read in a revision is that of the marked ones before it and
    its own (EP-08, "Tables et migrations").
    """
    found: dict[tuple[UUID, UUID], date] = {}
    for revision_id in {each.evaluation.revision_id for each in founds}:
        seen = seen_revisions(marked, revision_id)
        risk_ids = {each.risk.id for each in founds if each.evaluation.revision_id == revision_id}
        rows = session.execute(
            select(RiskReview.risk_id, func.max(RiskReview.reviewed_on))
            .where(
                RiskReview.project_id == project_id,
                RiskReview.risk_id.in_(list(risk_ids)),
                RiskReview.revision_id.in_(list(seen)),
            )
            .group_by(RiskReview.risk_id)
        )
        found.update({(revision_id, risk): day for risk, day in rows})
    return found


def occurred_amounts(session: Session, project_id: UUID, revision_id: UUID) -> dict[UUID, Decimal]:
    """Give the re-estimated amount of the lines each risk's occurrence merged, in a revision.

    The lines of the revision read whose task names the risk (``origin_risk_id``), which the
    occurrence merges (WF-RIS-0060).
    """
    amounts: dict[UUID, Decimal] = {}
    for line in lines_for_indicators(session, project_id, revision_id):
        origin = line.task_origin_risk_id
        if origin is not None:
            amounts[origin] = amounts.get(origin, NOUGHT) + line.reestimated_amount
    return amounts


def read_context(session: Session, project_id: UUID, founds: Sequence[Found]) -> ReadContext:
    """Read once what the description of the risks given shares, a fixed number of statements."""
    facts = project_facts(session, project_id)
    marked = marked_revisions_at(session, project_id)
    risk_ids = [each.risk.id for each in founds]
    evaluations = [each.evaluation for each in founds]
    revisions = {each.revision_id for each in evaluations}
    categories = {each.provision_cost_category_id for each in evaluations}
    subprojects = {
        each.provision_subproject_id
        for each in evaluations
        if each.provision_subproject_id is not None
    }
    lines = [each.provision_node_id for each in evaluations if each.provision_node_id is not None]
    cited = cited_among(session, project_id, risk_ids, marked)
    occurred = {each.revision_id for each in evaluations if each.state == OCCURRED}
    return ReadContext(
        facts=facts,
        matrix=read_reference_settings(session).risk_matrix,
        cited=frozenset(cited),
        amounts=structure_amounts(session, project_id, {each.structure_id for each in evaluations}),
        shares=_shares(session, project_id, facts.reference_revision_id, risk_ids),
        categories=category_labels(session, categories),
        subprojects=subproject_labels(session, project_id, subprojects),
        tasks=bearing_of(session, project_id, lines),
        bases={each: risk_base(session, project_id, each) for each in revisions},
        reestimated={each: occurred_amounts(session, project_id, each) for each in occurred},
        reviews=_reviews(session, project_id, marked, founds),
    )


def _cell(
    context: ReadContext, revision_id: UUID, values: tuple[Decimal, Decimal]
) -> RiskMatrixCell:
    """Place a probability and a severity in the matrix of the reference settings (WF-REF-0160).

    The severity as a share of the base of the project; on a base of nought, at the lowest level.
    """
    probability, severity = values
    matrix = context.matrix
    base = context.bases[revision_id]
    ratio = severity / base if base > 0 else Decimal(0)
    return RiskMatrixCell(
        level_of(probability, matrix.probability_bounds),
        level_of(ratio, matrix.severity_bounds),
        zone_of(matrix, probability, ratio),
    )


def severity_share(context: ReadContext, revision_id: UUID, severity: Decimal) -> Decimal | None:
    """Give a severity as a share of the base of the project, to four places; none on a base of 0.

    The share the matrix draws; the cell of the risk is that of the exact share (``_cell``).
    """
    base = context.bases[revision_id]
    return share_of(severity, base) if base > 0 else None


def _provision_task(context: ReadContext, evaluation: RiskEvaluation) -> ProvisionTask | None:
    """Name the task that bears the provision line of a risk, none without a line."""
    line = evaluation.provision_node_id
    task = None if line is None else context.tasks.get(line)
    return None if task is None else ProvisionTask(task.node_id, task.label)


def risk_view(
    session: Session,
    project_id: UUID,
    found: Found,
    viewer: Viewer,
    context: ReadContext | None = None,
) -> RiskView:
    """Describe a risk as the revision of its evaluation freezes it, with its commands.

    From the context of the risks read together, which a register builds once for all of its
    risks; a risk read alone is read in the context of that one.
    """
    if context is None:
        context = read_context(session, project_id, [found])
    risk, evaluation = found.risk, found.evaluation
    revision_id = evaluation.revision_id
    facts = context.facts
    state: RiskState = (
        "identified"
        if evaluation.state == IDENTIFIED
        else "occurred"
        if evaluation.state == OCCURRED
        else "dismissed"
    )
    severity = context.amounts[evaluation.structure_id]
    provision = (
        round_to_cent(severity * evaluation.probability)
        if state == IDENTIFIED
        else context.shares.get(risk.id, NOUGHT)
    )
    category_id = evaluation.provision_cost_category_id
    category = context.categories[category_id]
    subproject = evaluation.provision_subproject_id
    standing = RiskStanding(
        state,
        risk.id in context.cited,
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
        occurred_reestimated_amount=(
            context.reestimated[revision_id].get(risk.id, NOUGHT) if state == OCCURRED else None
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
        provision_subproject_label=(
            None if subproject is None else context.subprojects.get(subproject)
        ),
        provision_task=_provision_task(context, evaluation),
        matrix_cell=_cell(context, revision_id, (evaluation.probability, severity)),
        last_review_on=context.reviews.get((revision_id, risk.id)),
        commands=risk_commands(standing, viewer.permissions),
        created_at=risk.created_at,
        created_by=risk.created_by,
        updated_at=risk.updated_at,
        updated_by=risk.updated_by,
        lock_version=risk.lock_version,
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
