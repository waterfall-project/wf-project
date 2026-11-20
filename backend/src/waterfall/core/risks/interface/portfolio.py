# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks as the portfolio reads them, and the changes of their state (EP-11, US-2680/L3).

A file of EP-11 in the interface of the risks (EP-11, "Modules"): what ``core/portfolio`` reads of
the risks of a project, the register, the matrix, the reserve and the coverage served as they are.

- ``portfolio_risks``, the risks of a revision, each with its probability, its severity, its
  provision and its state, the cost at occurrence and the re-estimated amount of an occurred one,
  and the base of the project (WF-DAT-0040, WF-PTF-0090): what the marking keeps in the document
  ``portfolio_risks``, and the current day computes the same;
- ``outcomes_between``, the provisions occurred and dismissed of a period, by the day of the review
  that changed the state of the risk (US-2730, ``period_outcome``);
- ``reviewed_since``, the identified risks of a revision reviewed since an instant (US-2750, the
  signal ``risks_not_reviewed``).

The objects live in ``surveying``, which reads them. Filled by US-2680/L3.
"""

from typing import TYPE_CHECKING

from waterfall.core.risks.surveying import outcomes, reviewed, survey

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.risks.surveying import PortfolioRisks, RiskOutcome


def portfolio_risks(session: Session, project_id: UUID, revision_id: UUID) -> PortfolioRisks:
    """Give the risks a revision of a project holds, in the order of their declaration; the base.

    Each read as the register reads it in that revision (``list_risks``); the base is the one the
    matrix relates a severity to, the budget of the reference — that of the revision itself while a
    merge marks it and designates it at once —, the total of the revision before a reference.
    """
    return survey(session, project_id, revision_id)


def outcomes_between(
    session: Session, project_ids: Collection[UUID], first: date, last: date
) -> list[RiskOutcome]:
    """Give the risks of the projects named moved to occurred or dismissed in a period of days.

    From ``first`` to ``last``, both included, by the day of the review that changed their state,
    whatever the revision it was made in; each with the share it holds in the reference of its
    project, nought without one.
    """
    return outcomes(session, project_ids, first, last)


def reviewed_since(
    session: Session, project_id: UUID, revision_id: UUID, since: datetime
) -> frozenset[UUID]:
    """Give the risks a revision holds identified that were reviewed at ``since`` or after.

    Among the reviews the revision presents — its own, and those of the revisions marked before it
    —, the declaration of a risk its first review.
    """
    return reviewed(session, project_id, revision_id, since)
