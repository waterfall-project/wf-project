# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks of the portfolio (``getPortfolioRisks``; US-2730).

The documents ``portfolio_risks``, without weighting: the total of the identified provisions — an
offer In pricing counts, as it is (WF-PTF-0020) —, the ten heaviest risks of all the projects each
with its project and ``can_open`` (WF-PTF-0030), the matrix classified on the bounds of the day
(each identified risk once, in the cell of its levels on the base of its own project); the
coverage summed from the projects In progress and Completed alone — a project In pricing has no
reference —, a project Completed in the period counting in it; the provisions occurred and
dismissed in the period (WF-PTF-0090). What a project contributes is read as the other views read
it (``documents_of``); the sums are those of the aggregation, and the forming of the answer is
``risking``.

- On the current day the risks are those of the day, from the cache, and the coverage of each
  project that of its revision of the day, computed; at a past date they are those the last
  revision marked by the end of the day kept (``portfolio_risks``), and the coverage that its
  document ``remaining`` kept (US-2680), with the reserve the reference conserves; one kept
  incomplete adds none, a past view reading no line of an estimate (WF-DAT-0040).
- ``period_outcome`` is read by ``outcomes_between``, which no marking keeps: the provision of a
  risk that left the identified state is the share it holds in the reference the project has
  **today**, nought without one (WF-RIS-0040). At a past ``as_of``, the outcomes of the period are
  therefore those of the history of the reviews, valued on the reference of the current day, not
  on the one the project had then (#4294).

Declared by US-2670/L1, the socle of EP-11; filled by US-2730.
"""

from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.portfolio.documents import documents_of
from waterfall.core.portfolio.interface.scope import resolve_scope
from waterfall.core.portfolio.risking import (
    REMAINING,
    coverage_document,
    coverages_of,
    heaviest_document,
    held_risks,
    identified_total,
    matrix_document,
    outcome_document,
    reserve_of,
)
from waterfall.core.portfolio.shaping import money, scope_document
from waterfall.core.portfolio.states import COMPLETED, IN_PROGRESS, PRICING
from waterfall.core.projects.interface import openable, projects_named
from waterfall.core.risks.interface import outcomes_between

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.core.portfolio.interface.scope import PortfolioAsked, PortfolioReading
    from waterfall.core.portfolio.risking import HeldRisk
    from waterfall.core.projects.interface import ProjectState, Viewer

# The states the view counts: the projects In progress, the offers In pricing, those Completed in
# the period.
COUNTED: frozenset[ProjectState] = frozenset({IN_PROGRESS, PRICING, COMPLETED})
# The kinds read at a past date: the risks the markings kept, and the remaining that holds the
# coverage.
KINDS: tuple[IndicatorKind, ...] = ("portfolio_risks", REMAINING)


def read_portfolio_risks(
    session: Session, asked: PortfolioAsked, reading: PortfolioReading, viewer: Viewer
) -> Document:
    """Give the risks of the scope read by ``reading``, the projects the reader opens told."""
    resolved = resolve_scope(session, asked, reading.at, counted=COUNTED, period=True)
    identifiers = list(resolved.projects)
    names = projects_named(session, identifiers)
    can_open = openable(session, identifiers, viewer)
    documents = documents_of(session, resolved, reading, KINDS)
    held: list[HeldRisk] = []
    # By label then identifier, so that the points of the matrix come out in one order.
    for project_id in sorted(documents, key=lambda each: (names[each][1], str(each))):
        document = documents[project_id].get("portfolio_risks")
        if document is not None:
            held += held_risks(
                project_id, names[project_id][1], can_open=project_id in can_open, document=document
            )
    covered = coverages_of(session, resolved, documents)
    scope = resolved.scope
    outcomes = (
        []
        if scope.period_from is None or scope.period_to is None
        else outcomes_between(session, identifiers, scope.period_from, scope.period_to)
    )
    return {
        "scope": scope_document(scope),
        "identified_total": money(identified_total(held)),
        "heaviest": heaviest_document(held),
        "matrix": matrix_document(
            read_reference_settings(session).risk_matrix, held, reserve_of(covered)
        ),
        "coverage": coverage_document(covered),
        "period_outcome": outcome_document(outcomes),
    }
