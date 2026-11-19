# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve for risks: the shares of the reference, private to the module (US-2610/L1).

A revision becomes the reference of its project by a designation, or by a merge that designates the
revision it marks (``register_designation``): the module then writes, for each risk the revision
evaluates, the provision the risk bears in that reference (``risk_reference_share``, M-01) —

- identified in the revision, the provision its line carries: the severity weighted by the
  probability, to the cent (WF-RIS-0010);
- occurred or dismissed before it, the share it had in the reference before, nought when it had
  none: the reserve keeps what it owed to the risks that left the identified state, and an amendment
  never decreases it.

The reserve is their sum, and nothing writes it again: a review, a variance, an occurrence, the
entry of an own estimate do not move it. A designation that corrects the previous one (WF-REV-0040:
no revision was marked since) takes its shares back and writes the revision's own, from the
reference before the one it replaces; a revision designated again writes its shares anew.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select

from waterfall.core.estimate.interface import round_to_cent, structure_amounts
from waterfall.core.risks.commands import IDENTIFIED
from waterfall.core.risks.tables import RiskEvaluation, RiskReferenceShare

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import ReferenceDesignated

NOUGHT = Decimal("0.00")


def _delete_shares(session: Session, project_id: UUID, revision_id: UUID) -> None:
    session.execute(
        delete(RiskReferenceShare)
        .where(
            RiskReferenceShare.project_id == project_id,
            RiskReferenceShare.revision_id == revision_id,
        )
        .execution_options(synchronize_session=False)
    )


def _last_reference(session: Session, project_id: UUID) -> UUID | None:
    """Give the reference that holds shares and was designated last, none if no one does."""
    return session.scalar(
        select(RiskReferenceShare.revision_id)
        .where(RiskReferenceShare.project_id == project_id)
        .group_by(RiskReferenceShare.revision_id)
        .order_by(func.max(RiskReferenceShare.created_at).desc(), RiskReferenceShare.revision_id)
        .limit(1)
    )


def shares_of(session: Session, project_id: UUID, revision_id: UUID) -> dict[UUID, Decimal]:
    """Give the share of each risk in a reference revision, in one statement."""
    return dict(
        session.execute(
            select(RiskReferenceShare.risk_id, RiskReferenceShare.provision_amount).where(
                RiskReferenceShare.project_id == project_id,
                RiskReferenceShare.revision_id == revision_id,
            )
        ).all()
    )


def reserve_of(session: Session, project_id: UUID, reference_id: UUID | None) -> Decimal:
    """Give the reserve a reference revision conserves: its shares summed, nought without one."""
    if reference_id is None:
        return NOUGHT
    total = session.scalar(
        select(func.sum(RiskReferenceShare.provision_amount)).where(
            RiskReferenceShare.project_id == project_id,
            RiskReferenceShare.revision_id == reference_id,
        )
    )
    return NOUGHT if total is None else total


def write_shares(designation: ReferenceDesignated) -> None:
    """Write the shares of a revision that has just become the reference of its project.

    In the transaction of the designation, under the lock of the project: the revision is marked,
    its evaluations no longer change. A correction takes back the shares of the reference it
    replaces first, so that the previous reference is the one before.
    """
    session, project_id = designation.session, designation.project_id
    revision_id = designation.revision_id
    _delete_shares(session, project_id, revision_id)
    if designation.corrects and designation.previous_id is not None:
        _delete_shares(session, project_id, designation.previous_id)
    session.flush()
    evaluations = session.scalars(
        select(RiskEvaluation)
        .where(RiskEvaluation.project_id == project_id, RiskEvaluation.revision_id == revision_id)
        .order_by(RiskEvaluation.risk_id)
    ).all()
    if not evaluations:
        return
    before = _last_reference(session, project_id)
    held = {} if before is None else shares_of(session, project_id, before)
    identified = {each.structure_id for each in evaluations if each.state == IDENTIFIED}
    amounts = structure_amounts(session, project_id, identified)
    for each in evaluations:
        share = (
            round_to_cent(amounts[each.structure_id] * each.probability)
            if each.state == IDENTIFIED
            else held.get(each.risk_id, NOUGHT)
        )
        session.add(
            RiskReferenceShare(
                project_id=project_id,
                revision_id=revision_id,
                risk_id=each.risk_id,
                provision_amount=share,
                created_at=designation.at,
                created_by=designation.author,
            )
        )
    session.flush()
