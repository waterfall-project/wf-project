# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks do when a module below them writes, private to the module (US-2570/L1).

Registered at the import of the interface of the risks (EP-08, "Modules"):

- **an own estimate counted** (``register_own_estimate_counted``): whatever writes the tree of the
  own estimate of a risk — a cell, a paste, a move, a creation, a deletion, an import, an undoing —
  advances the counter of its risk with the structure's (#1453), and, the risk identified in that
  revision, writes its provision line again at the severity, the new total of the structure,
  weighted by its probability, to the cent (WF-RIS-0010). The locks come in the order of
  ``update_provision``: the own estimate, held by the write, then the main structure that bears the
  line, then the risk;
- **the copy of a revision** (``register_copy``): each evaluation of the source is taken up, its own
  estimate and its provision line by their copies, after the structures and the nodes whose copies
  it names; the reviews and the shares are not (EP-08, "Tables et migrations"). The own estimate of
  a risk that occurred is consumed by its occurrence: its content is not copied, but the evaluation,
  which keeps the cost at occurrence, names a structure of its revision, copied empty and merged
  (``copy_consumed_estimate``, US-2620/L2). ``copy_evaluations`` advances no counter itself: the counter of a risk
  advances at the opening because the planning redates each copied structure that holds a node
  (``redate_copy``), which counts it as any write of its tree — the own estimate of a risk that
  holds none is not redated, and its risk keeps its counter;
- **the provision lines moved** (``register_provision_owners``): the risk a line a deletion of its
  task, or an import that no longer carries it, moves under another task, is named when the
  deletion would leave the structure without a task, and its counter advances once the line is
  moved (US-2580/L1; the planning does not know the risks);
- **the closing of a revision abandoned** (``register_closing``, ``evaluations``): its reviews and
  its evaluations are deleted before its nodes and its structures, which they name, and the counter
  of each risk it evaluated advances, never going back (H-02, #1783). A risk the revision declared
  keeps no evaluation: it is deleted with the revision, its own estimate with it (``erase``, M-04;
  US-2590/L1). Nothing is done at a marking.

A figure computed, not entered: the counter of the risk advances, its audit is left to its entries.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

from waterfall.core.estimate.interface import (
    rename_provisions,
    round_to_cent,
    set_provision,
    structure_amount,
)
from waterfall.core.planning.interface import Place, ProvisionOwner
from waterfall.core.revisions.interface import (
    aimed_structure,
    copy_consumed_estimate,
    rename_own_estimates,
    structure_facts,
)
from waterfall.core.risks.commands import IDENTIFIED
from waterfall.core.risks.deleting import erase
from waterfall.core.risks.reading import evaluation_of, found_risk
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReview

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import (
        OwnEstimateCounted,
        RevisionClosing,
        RevisionCopy,
    )


def advance_risks(session: Session, project_id: UUID, risk_ids: Collection[UUID]) -> None:
    """Advance the counter of each risk named, in the order of their identifiers, locked by it."""
    for risk_id in sorted(risk_ids):
        session.execute(
            update(Risk)
            .where(Risk.project_id == project_id, Risk.id == risk_id)
            .values(lock_version=Risk.lock_version + 1)
            .execution_options(synchronize_session=False)
        )


def follow_own_estimate(counted: OwnEstimateCounted) -> None:
    """Advance the counter of the risk of an own estimate written; write its provision again."""
    session, project_id = counted.session, counted.project_id
    main = aimed_structure(session, project_id, counted.revision_id, None)
    if main is not None:
        # The main structure before the risk: the order of ``update_provision``, which says why.
        structure_facts(session, project_id, main, lock=True)
    advance_risks(session, project_id, [counted.risk_id])
    evaluation = evaluation_of(session, project_id, counted.risk_id, counted.revision_id)
    if evaluation is None or evaluation.state != IDENTIFIED:
        return
    line = evaluation.provision_node_id
    if line is None or main is None:
        return
    severity = structure_amount(session, project_id, counted.structure_id)
    amount = round_to_cent(severity * evaluation.probability)
    set_provision(session, Place(project_id, counted.revision_id, main), line, amount)


def name_provision_owners(
    session: Session, project_id: UUID, revision_id: UUID, lines: Collection[UUID]
) -> tuple[ProvisionOwner, ...]:
    """Name the risks that bear these provision lines in a revision, by label then identifier."""
    rows = session.execute(
        select(Risk.id, Risk.label)
        .join(
            RiskEvaluation,
            (RiskEvaluation.project_id == Risk.project_id) & (RiskEvaluation.risk_id == Risk.id),
        )
        .where(
            RiskEvaluation.project_id == project_id,
            RiskEvaluation.revision_id == revision_id,
            RiskEvaluation.provision_node_id.in_(list(lines)),
        )
        .order_by(Risk.label, Risk.id)
    )
    return tuple(ProvisionOwner(risk_id, label) for risk_id, label in rows)


def follow_provision_lines(
    session: Session, project_id: UUID, revision_id: UUID, lines: Collection[UUID]
) -> None:
    """Advance the counter of the risks whose provision line a deletion or an import moved.

    Their provision task changes with the line (WF-RIS-0010; ``provision_moved``, #1665), and the
    counter a client carries with the risk (``updateRiskProvision``) with it.
    """
    named = name_provision_owners(session, project_id, revision_id, lines)
    advance_risks(session, project_id, [each.risk_id for each in named])


def copy_evaluations(copy: RevisionCopy) -> None:
    """Take up the evaluations of the source in the revision opened, under their copies' names.

    The own estimate and the provision line copied are named by the label of their risk as it is
    now, not as the source marked it: the identity is outside the history (H-02, #3980). The
    revisions marked keep their names (WF-DAT-0020). One statement reads the labels, one writes
    each kind of name.
    """
    session, ids = copy.session, copy.identifiers
    rows = session.execute(
        select(RiskEvaluation, Risk.label)
        .join(
            Risk,
            (Risk.project_id == RiskEvaluation.project_id) & (Risk.id == RiskEvaluation.risk_id),
        )
        .where(
            RiskEvaluation.project_id == copy.project_id,
            RiskEvaluation.revision_id == copy.source,
        )
        .order_by(RiskEvaluation.risk_id)
    ).all()
    estimates: dict[UUID, str] = {}
    provisions: dict[UUID, str] = {}
    structures = dict(ids)
    for row, label in rows:
        if row.structure_id not in structures:
            # The own estimate of a risk occurred was consumed: its content is not taken up, the
            # structure is, empty, for the evaluation to name (WF-RIS-0060). It stays out of the
            # identifiers the other copies follow: no node of it is copied.
            structures[row.structure_id] = copy_consumed_estimate(copy, row.structure_id)
        estimates[structures[row.structure_id]] = label
        if row.provision_node_id is not None:
            provisions[ids[row.provision_node_id]] = label
    for row, _ in rows:
        line = row.provision_node_id
        session.add(
            RiskEvaluation(
                project_id=copy.project_id,
                risk_id=row.risk_id,
                revision_id=copy.target,
                probability=row.probability,
                state=row.state,
                structure_id=structures[row.structure_id],
                provision_node_id=None if line is None else ids[line],
                provision_cost_category_id=row.provision_cost_category_id,
                provision_subproject_id=row.provision_subproject_id,
                provision_task_lineage_id=row.provision_task_lineage_id,
                occurrence_cost=row.occurrence_cost,
                created_at=copy.at,
                created_by=copy.author,
                updated_at=copy.at,
                updated_by=copy.author,
            )
        )
    session.flush()
    rename_own_estimates(session, copy.project_id, estimates)
    rename_provisions(session, copy.project_id, provisions)


def close_evaluations(closing: RevisionClosing) -> None:
    """Delete the reviews and the evaluations of a revision abandoned; advance their risks.

    A risk that no other revision evaluates was declared by this one, and goes with it, its own
    estimate with it (M-04); the others are given back as the last marked revision holds them, their
    counter advanced, never going back (H-02, #1783).
    """
    if closing.kind != "abandoned":
        return
    session, project_id, revision_id = closing.session, closing.project_id, closing.revision_id
    evaluated = dict(
        session.execute(
            select(RiskEvaluation.risk_id, RiskEvaluation.structure_id).where(
                RiskEvaluation.project_id == project_id, RiskEvaluation.revision_id == revision_id
            )
        ).all()
    )
    for table in (RiskReview, RiskEvaluation):
        session.execute(
            delete(table)
            .where(table.project_id == project_id, table.revision_id == revision_id)
            .execution_options(synchronize_session=False)
        )
    kept = set(
        session.scalars(
            select(RiskEvaluation.risk_id).where(
                RiskEvaluation.project_id == project_id,
                RiskEvaluation.risk_id.in_(list(evaluated)),
            )
        )
    )
    for risk_id, structure_id in sorted(evaluated.items()):
        if risk_id not in kept:
            structure_facts(session, project_id, structure_id, lock=True)
            # The risk last, after the structures, as every write of a risk takes them. No current
            # writer locks the risk without the revision or the project, which the abandonment
            # already holds; this lock protects a future writer that would.
            found_risk(session, project_id, risk_id, lock=True)
            erase(session, project_id, risk_id, structure_id)
    advance_risks(session, project_id, kept)
    session.flush()
