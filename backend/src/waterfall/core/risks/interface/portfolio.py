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
- ``not_reviewed_since``, the identified risks of the revision of each of several projects that no
  review has re-examined since an instant of its own (US-2750, the signal ``risks_not_reviewed``).

The objects live in ``surveying``, which reads them. Filled by US-2680/L3.
"""

from typing import TYPE_CHECKING

from waterfall.core.risks.surveying import outcomes, survey, unreviewed

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.risks.surveying import PortfolioRisks, ReviewWindow, RiskOutcome


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


def not_reviewed_since(
    session: Session, windows: Mapping[UUID, ReviewWindow]
) -> dict[UUID, frozenset[UUID]]:
    """Give, by project, the risks its revision holds identified that no review re-examined since.

    Each project has its window: the revision it is read in, and the instant its reviews count from.
    Among the reviews the revision presents — its own, and those of the revisions marked before it
    —, the declaration of a risk its first review; one made at the instant or after re-examines it.
    A project with no such risk has no entry. Read for all the projects in a fixed number of
    queries, never one by project.
    """
    return unreviewed(session, windows)
