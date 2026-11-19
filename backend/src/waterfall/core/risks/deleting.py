# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk deleted, private to the module (``deleteRisk``; US-2590/L1).

An entry of the current revision, under ``edit_risks``, entered as every write of a risk is
(``enter``) and judged in the order the command ``delete`` lists its conditions (409
``STATE_FORBIDS_OPERATION``): a terminal project (``project_not_terminal``), a background task that
writes in the project (``no_background_task_running``), then, the risk read in its revision and the
counter it was read at (404, 412), a risk occurred (``risk_not_occurred``: no transition leaves it)
or cited by a marked revision (``risk_not_cited``: it is dismissed, WF-RIS-0020), the first that
lacks, then the permission to create the revision the project lacks (``may_create_revision``,
which a risk no marked revision cites never needs: it was declared in the current one).

A risk no marked revision cites is held by one revision, the current one: its reviews, its
evaluation, its provision line, its own estimate and the risk itself go, in that order, those that
name the others first (``remove``). The locks follow the order of ``enter``, the own estimate first.
The deletion is an entry of the history of its writer (US-2590/L2): the risk is kept whole before
it, its own estimate with its nodes, which its undoing writes back under their identifiers.

The abandonment of a revision deletes the same way each risk it declared (``erase``): one that no
other revision evaluates is held by it alone (M-04).
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete

from waterfall.core.planning.interface import delete_borne_line, delete_structure_nodes
from waterfall.core.revisions.interface import delete_own_estimate, marked_revisions_at
from waterfall.core.risks.commands import OCCURRED, RISK_NOT_CITED, RISK_NOT_OCCURRED
from waterfall.core.risks.declaring import refuse
from waterfall.core.risks.entering import Held, enter
from waterfall.core.risks.reading import cited_among
from waterfall.core.risks.recording import recorded
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReview

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Place, Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.entering import Judge
    from waterfall.core.risks.interface.deletion import RiskDeletion


def erase(session: Session, project_id: UUID, risk_id: UUID, structure_id: UUID) -> None:
    """Delete a risk and its own estimate, no evaluation nor review naming them any more.

    The nodes of the own estimate and its facets first, then the structure, which they name, then
    the risk, which the structure names. The structure is locked by the caller.
    """
    delete_structure_nodes(session, project_id, structure_id)
    delete_own_estimate(session, project_id, structure_id)
    session.execute(
        delete(Risk)
        .where(Risk.project_id == project_id, Risk.id == risk_id)
        .execution_options(synchronize_session=False)
    )


def _judging(session: Session, project_id: UUID, risk_id: UUID) -> Judge:
    """Give what the deletion judges of the risk it enters, after the counter (409)."""

    def judge(evaluation: RiskEvaluation, _revision_id: UUID) -> None:
        if evaluation.state == OCCURRED:
            raise refuse(RISK_NOT_OCCURRED)
        marked = marked_revisions_at(session, project_id)
        if cited_among(session, project_id, [risk_id], marked):
            raise refuse(RISK_NOT_CITED)

    return judge


def delete_current(
    session: Session, project_id: UUID, deletion: RiskDeletion, writer: Writer, viewer: Viewer
) -> None:
    """Delete a risk no marked revision cites, with its own estimate and its provision line.

    An entry of the history of its writer (``risk_delete``, US-2590/L2), which keeps the risk whole
    — its own estimate with its nodes — for its undoing.
    """
    judge = _judging(session, project_id, deletion.risk_id)
    risk_id = deletion.risk_id
    with recorded(session, project_id, writer, "risk_delete") as entry:
        counter = deletion.lock_version
        held = Held(risk_id, counter, judge, lock_own_estimate=True, opened=entry.open)
        entered = enter(session, project_id, held, writer, viewer)
        entry.before(risk_id, whole=True)
        remove(session, entered.place, (entered.risk, entered.evaluation), writer)
        entry.after(risk_id)


def remove(
    session: Session, place: Place, held: tuple[Risk, RiskEvaluation], writer: Writer
) -> None:
    """Delete a risk held by the current revision alone: its rows, its line, its own estimate.

    ``place`` the main structure that bears its line; the locks taken in the order of ``enter``.
    Its reviews and its evaluation, its provision line, its own estimate and the risk itself go, in
    that order, those that name the others first. What a deletion and the undoing of a declaration
    share (US-2590/L2).
    """
    risk, evaluation = held
    project_id, risk_id = place.project_id, risk.id
    line, structure_id = evaluation.provision_node_id, evaluation.structure_id
    for held_row in (evaluation, risk):
        session.expunge(held_row)
    for table in (RiskReview, RiskEvaluation):
        session.execute(
            delete(table)
            .where(table.project_id == project_id, table.risk_id == risk_id)
            .execution_options(synchronize_session=False)
        )
    if line is not None:
        delete_borne_line(session, place, line, writer)
    erase(session, project_id, risk_id, structure_id)
    session.flush()
