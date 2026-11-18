# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks do when a module below them writes, private to the module (US-2570/L1).

Registered at the import of the interface of the risks (EP-08, "Modules"):

- **an own estimate counted** (``register_own_estimate_counted``): whatever writes the tree of the
  own estimate of a risk — a cell, a paste, a move, a creation, a deletion, an import, an undoing —
  advances the counter of its risk with the structure's (#1453), and, the risk identified in that
  revision, writes its provision line again at the severity, the new total of the structure,
  weighted by its probability, to the cent (WF-RIS-0010). The locks come in one order: the own
  estimate, held by the write, then the risk, then the main structure that bears the line;
- **the copy of a revision** (``register_copy``): each evaluation of the source is taken up, its own
  estimate and its provision line by their copies, after the structures and the nodes whose copies
  it names; the reviews and the shares are not (EP-08, "Tables et migrations"). The own estimate of
  a risk that occurred is consumed by its occurrence, and not copied: US-2620 says what its
  evaluation becomes;
- **the closing of a revision abandoned** (``register_closing``, ``evaluations``): its reviews and
  its evaluations are deleted before its nodes and its structures, which they name, and the counter
  of each risk it evaluated advances, never going back (H-02, #1783). A risk the revision declared
  keeps no evaluation: its deletion with the revision is US-2590/L1's, with the rest of what the
  abandonment brings back. Nothing is done at a marking.

A figure computed, not entered: the counter of the risk advances, its audit is left to its entries.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

from waterfall.core.estimate.interface import round_to_cent, set_provision, structure_amount
from waterfall.core.planning.interface import Place
from waterfall.core.revisions.interface import aimed_structure
from waterfall.core.risks.commands import IDENTIFIED
from waterfall.core.risks.reading import evaluation_of
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
    advance_risks(session, project_id, [counted.risk_id])
    evaluation = evaluation_of(session, project_id, counted.risk_id, counted.revision_id)
    if evaluation is None or evaluation.state != IDENTIFIED:
        return
    line = evaluation.provision_node_id
    main = aimed_structure(session, project_id, counted.revision_id, None)
    if line is None or main is None:
        return
    severity = structure_amount(session, project_id, counted.structure_id)
    amount = round_to_cent(severity * evaluation.probability)
    set_provision(session, Place(project_id, counted.revision_id, main), line, amount)


def copy_evaluations(copy: RevisionCopy) -> None:
    """Take up the evaluations of the source in the revision opened, under their copies' names."""
    session, ids = copy.session, copy.identifiers
    rows = session.scalars(
        select(RiskEvaluation)
        .where(
            RiskEvaluation.project_id == copy.project_id,
            RiskEvaluation.revision_id == copy.source,
        )
        .order_by(RiskEvaluation.risk_id)
    ).all()
    for row in rows:
        line = row.provision_node_id
        session.add(
            RiskEvaluation(
                project_id=copy.project_id,
                risk_id=row.risk_id,
                revision_id=copy.target,
                probability=row.probability,
                state=row.state,
                structure_id=ids[row.structure_id],
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


def close_evaluations(closing: RevisionClosing) -> None:
    """Delete the reviews and the evaluations of a revision abandoned; advance their risks."""
    if closing.kind != "abandoned":
        return
    session, project_id, revision_id = closing.session, closing.project_id, closing.revision_id
    evaluated = session.scalars(
        select(RiskEvaluation.risk_id).where(
            RiskEvaluation.project_id == project_id, RiskEvaluation.revision_id == revision_id
        )
    ).all()
    for table in (RiskReview, RiskEvaluation):
        session.execute(
            delete(table)
            .where(table.project_id == project_id, table.revision_id == revision_id)
            .execution_options(synchronize_session=False)
        )
    advance_risks(session, project_id, evaluated)
    session.flush()
