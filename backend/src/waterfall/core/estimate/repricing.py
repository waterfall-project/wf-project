# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What prices a current revision again outside a write of its tree, private to the module.

Three changes beside the tree move the amounts of the lines of a current revision (EP-07, "Le
calcul des montants"), each in its own transaction, under the lock of each structure it prices:

- the designation of a reference (``refresh_budgeted``, by ``register_designation``): the budgeted
  amount of each line of the current revision becomes that of the line of the same lineage in the
  new reference, nought without one (WF-DEV-0020, WF-REV-0070);
- a new rate of inflation of the project (``reinflate_project``, by ``register_estimate_facts``,
  ``updateProject``): its current revision is priced again (WF-PRJ-0040) — a marked one keeps the
  rate of its marking, and its amounts;
- a rate of the reference written for a category of labour and a year (``reprice_after_rate``, by
  ``register_employment``, ``setHourlyRate``): each current revision of that year whose lines of
  the category are priced at the rate of the reference, keeping none of its own, is priced again
  (WF-REF-0050); one that keeps a rate is not, and a marked one keeps the rates of its marking.

The order of the locks, one for every write of the service, so that no two are ever awaited both
ways (#2104, #2615):

1. the lock of the natures of cost (``NATURES_LOCK``), for a rate written: ``setHourlyRate`` takes
   it before anything else, and no path that holds the lock of a revision or of a structure takes
   it after;
2. the current revision, shared (``FOR SHARE``): a rate written reads the current revisions so
   (``current_structures``), the designation and the change of the rate of inflation share it
   before they lock the project (``hold_current_revision``), as a write of the tree does before
   its structure; the marking and the abandonment, which lock it ``FOR UPDATE``, wait for it, or
   are waited for;
3. the project, for the designation and the change of the rate of inflation, after the revision —
   the order of the marking and of the abandonment;
4. each structure of the revision, ``FOR UPDATE``, in the order of its identifier, the revisions in
   the order of their project: the lines are read under it, then priced.

Written by US-1500/L2.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.keeping import reprice_revision
from waterfall.core.estimate.reading import budgeted_of, rows_of
from waterfall.core.estimate.tables import RevisionRate
from waterfall.core.planning.interface import lines_of_revision
from waterfall.core.projects.interface import project_facts
from waterfall.core.revisions.interface import (
    current_structures,
    hold_current_revision,
    revision_structures,
    structure_facts,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import RateWritten
    from waterfall.core.revisions.interface import ReferenceDesignated

NOUGHT = Decimal("0.00")


def refresh_budgeted(designation: ReferenceDesignated) -> None:
    """Give the lines of the current revision the budgeted amount of their lineage in the reference.

    In the transaction of the designation, the current revision held before the project: its
    structures locked, its lines read under the locks, then written where the amount moves. A
    budgeted amount is computed by the server: it advances no counter.
    """
    session, project_id = designation.session, designation.project_id
    current = project_facts(session, project_id).current_revision_id
    if current is None:
        return
    for structure_id in revision_structures(session, project_id, current):
        structure_facts(session, project_id, structure_id, lock=True)
    # Read under the locks: a line created meanwhile is there, a line deleted is not.
    held = lines_of_revision(session, project_id, current)
    reference = lines_of_revision(session, project_id, designation.revision_id)
    budgets = {
        line.node_id: budgeted_of(line)
        for line in rows_of(session, project_id, list(reference.values()))
    }
    lineages = {node: lineage for lineage, node in held.items()}
    for line in rows_of(session, project_id, list(held.values())):
        node = reference.get(lineages[line.node_id])
        budgeted = NOUGHT if node is None else budgets.get(node, NOUGHT)
        if line.budgeted_amount != budgeted:
            line.budgeted_amount = budgeted
    session.flush()


def hold_revision(session: Session, project_id: UUID) -> None:
    """Share the lock of the current revision of a project, before its project is locked."""
    hold_current_revision(session, project_id)


def reinflate_project(session: Session, project_id: UUID, at: datetime) -> None:
    """Price the current revision of a project again, its rate of inflation changed (WF-PRJ-0040).

    Under the lock of the project, the revision held before it (``hold_revision``); a revision
    opened since is held here. Each structure that holds a line is replayed, its dates' instant
    moved on to ``at``.
    """
    current = hold_current_revision(session, project_id)
    if current is not None:
        reprice_revision(session, (project_id, current), at)


def reprice_after_rate(session: Session, written: RateWritten) -> None:
    """Price again the current revisions a rate of the reference just written changes.

    Those of the year of the rate whose lines of the category keep no rate of their own: those of
    the year alone are read ``FOR SHARE`` (the year is judged in the query) after the lock of the
    natures, then priced under the lock of each structure. The employment of the category is
    judged under the locks, not before: a line created meanwhile would escape a judgement made
    without them.
    """
    revisions: dict[UUID, UUID] = {}
    for each in current_structures(session, lock=True, reference_year=written.year):
        revisions.setdefault(each.revision_id, each.project_id)
    for revision_id, project_id in revisions.items():
        kept = session.scalar(
            select(RevisionRate.id).where(
                RevisionRate.project_id == project_id,
                RevisionRate.revision_id == revision_id,
                RevisionRate.cost_category_id == written.cost_category_id,
            )
        )
        if kept is None:
            reprice_revision(
                session, (project_id, revision_id), written.at, {written.cost_category_id}
            )
