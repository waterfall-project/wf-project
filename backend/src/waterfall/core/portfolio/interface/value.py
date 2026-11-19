# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio is worth (``getPortfolioValue``; US-2690).

The order book of the projects In progress, the pipeline of the offers, gross and weighted by their
probabilities of winning, the value delivered by the projects completed in the period, and the rate
of conversion of the offers closed in it (WF-PTF-0050, WF-PTF-0020): the documents ``project`` and
``estimate`` of the indicators, summed.

- the order book is the sum of the reference budgets of the projects In progress;
- the pipeline, the sum of the current estimates of the offers — gross as it is, weighted by each
  offer's probability of winning, each part rounded once, to the cent (``weighted_amount``);
- the delivered, the sum of the actual costs of the projects Completed in the period;
- the rate of conversion, the offers that left Pricing in the period for In progress over those
  that left it for In progress or Lost, in scope or not; an abandoned one counts in neither, and
  none out of pricing gives ``no_offer_out_of_pricing``.

Each project adds what its documents hold, and nothing without a revision to contribute by.

Declared by US-2670/L1, the socle of EP-11; filled by US-2690/L2.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.portfolio.aggregation import (
    conversion_rate,
    total_of,
    weighted_amount,
)
from waterfall.core.portfolio.documents import documents_of
from waterfall.core.portfolio.interface.scope import period_instants, resolve_scope
from waterfall.core.portfolio.shaping import computable, money, scope_document
from waterfall.core.projects.interface import offers_closed_between

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.documents import Documents
    from waterfall.core.portfolio.interface.scope import (
        PortfolioAsked,
        PortfolioReading,
        RetainedProject,
    )
    from waterfall.core.projects.interface import ProjectState

# The states the value counts: the order book In progress, the pipeline In pricing, the delivered
# Completed in the period.
COUNTED: frozenset[ProjectState] = frozenset({"in_progress", "pricing", "completed"})


def _figure(documents: Documents, name: str) -> Decimal | None:
    """Read an amount of the document ``project``, none when the revision kept no such document.

    A revision marked before the project was In progress holds none: nothing is taken up, and the
    project adds to no sum (WF-DAT-0040).
    """
    document = documents.get("project")
    return None if document is None else Decimal(document[name])


def _total(documents: Documents) -> Decimal | None:
    """Read the total of the document ``estimate``, none when a missing rate prevents it."""
    document = documents.get("estimate")
    if document is None or not document["total"]["is_computable"]:
        return None
    return Decimal(document["total"]["value"])


def _weighted(offers: Iterable[tuple[RetainedProject, Decimal]]) -> list[Decimal]:
    """Weigh each estimate by its offer's probability, none for an offer whose weight is unknown."""
    return [
        weighted_amount(estimate, offer.weight)
        for offer, estimate in offers
        if offer.weight is not None
    ]


def read_portfolio_value(
    session: Session, asked: PortfolioAsked, reading: PortfolioReading
) -> Document:
    """Give the values of the portfolio of the scope at the instant of ``reading``."""
    resolved = resolve_scope(session, asked, reading.at, counted=COUNTED, period=True)
    documents = documents_of(session, resolved, reading)
    in_progress: list[Decimal] = []
    delivered: list[Decimal] = []
    offers: list[tuple[RetainedProject, Decimal]] = []
    for project_id, held in documents.items():
        retained = resolved.projects[project_id]
        if retained.state == "in_progress":
            budget = _figure(held, "reference_budget")
            in_progress += [] if budget is None else [budget]
        elif retained.state == "completed":
            cost = _figure(held, "actual_cost")
            delivered += [] if cost is None else [cost]
        elif (estimate := _total(held)) is not None:
            offers.append((retained, estimate))
    bounds = period_instants(resolved.scope)
    closed = [] if bounds is None else offers_closed_between(session, *bounds)
    return {
        "scope": scope_document(resolved.scope),
        "order_book": money(total_of(in_progress)),
        "pipeline_gross": money(total_of(estimate for _, estimate in offers)),
        "pipeline_weighted": money(total_of(_weighted(offers))),
        "delivered": money(total_of(delivered)),
        "conversion_rate": computable(conversion_rate(each.to_state for each in closed)),
    }
