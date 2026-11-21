# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects the provisions of the risks designate, as the projects ask them (#4208).

Private to the module, registered at the import of its interface (``register_risk_designations``):

- **cited by a marked revision**: the evaluation of a risk in a marked revision that designates a
  subproject cites it, as a line of that revision does — every revision of a project but its current
  one is marked, an abandoned one keeping no evaluation (``close_evaluations``) —; its deletion is
  refused, ``subproject_not_cited`` (WF-DAT-0020: a marked revision is never written);
- **set to null in the current revision**: once the deletion holds, the evaluations of the current
  revision that designated it lose the designation — none is identified, the provision line of one
  bearing the subproject refuses the deletion first (``subproject_without_estimate_lines``) —; a
  risk identified again carries its provision outside any subproject (WF-RIS-0010, #732).

The designation set to null is a write of the risk, outside the history: no entry restores it, as no
entry restores a deletion of a subproject. Its counter advances and its audit names the author of
the deletion (``deleteSubproject``), so that a screen that read it reads it again (WF-IHM-0110); the
new counter is carried to every stack of the project (``carry_everywhere``), as the change of the
identity carries it, so that it is no conflict of an undoing. An entry that would give the
subproject back is refused by the rules of the entry instead, ``restored_subproject_exists``
(``undoing``, #732), and one that gives back another designation, or none, is undone as before.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.history.interface import carry_everywhere
from waterfall.core.projects.interface import project_facts
from waterfall.core.risks.tables import Risk, RiskEvaluation

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def marked_designations(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects of a project named, those a risk of a marked revision designates."""
    current = project_facts(session, project_id).current_revision_id
    query = select(RiskEvaluation.provision_subproject_id).where(
        RiskEvaluation.project_id == project_id,
        RiskEvaluation.provision_subproject_id.in_(list(subproject_ids)),
    )
    if current is not None:
        query = query.where(RiskEvaluation.revision_id != current)
    return frozenset(each for each in session.scalars(query.distinct()) if each is not None)


def undesignate(session: Session, project_id: UUID, subproject_id: UUID, act: Act) -> None:
    """Set to null the designation of a subproject in the evaluations of the current revision.

    Under the lock of the project and of the subproject, which the deletion holds: each risk is
    written in the order of its identifier, its counter carried to the stacks of the project.
    """
    current = project_facts(session, project_id).current_revision_id
    if current is None:
        return
    of_current = (
        RiskEvaluation.project_id == project_id,
        RiskEvaluation.revision_id == current,
        RiskEvaluation.provision_subproject_id == subproject_id,
    )
    risk_ids = sorted(session.scalars(select(RiskEvaluation.risk_id).where(*of_current)))
    if not risk_ids:
        return
    moved: dict[UUID, tuple[int, int]] = {}
    for risk_id in risk_ids:
        counter = session.scalar(
            update(Risk)
            .where(Risk.project_id == project_id, Risk.id == risk_id)
            .values(lock_version=Risk.lock_version + 1, updated_at=act.at, updated_by=act.author)
            .returning(Risk.lock_version)
            .execution_options(synchronize_session="fetch")
        )
        if counter is not None:
            moved[risk_id] = (counter - 1, counter)
    session.execute(
        update(RiskEvaluation)
        .where(*of_current, RiskEvaluation.risk_id.in_(risk_ids))
        .values(provision_subproject_id=None, updated_at=act.at, updated_by=act.author)
        .execution_options(synchronize_session="fetch")
    )
    carry_everywhere(session, project_id, moved)
