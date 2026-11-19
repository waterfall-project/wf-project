# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The list of the projects of the portfolio (``getPortfolioProjects``; US-2690).

One row by project retained, formed of the documents ``project``, ``estimate`` and ``remaining``
of the indicators (WF-PTF-0040): its label, its code, its state, its reference budget or its current
estimate and its probability, the projection of its manager, its variance to the reference and its
indices for a project In progress, and the instant of its last marked revision. The filter, the
sort and the paging are made on the rows formed, in memory (EP-11, "Les vues"). A project the
reader cannot open is listed under its label and its code, ``can_open`` false (WF-PTF-0030).

The projects the list retains are those In progress, those In pricing, and those Completed in the
period (``PortfolioStates``); a list read without ``from`` nor ``to`` has no period in which a
project would have been completed, so it retains no Completed project, whether or not the state
is asked: ``PortfolioStates`` applies, and a created, lost or abandoned project, asked, has no
effect (the author's decision of 2026-11-19, #4020). The scope it gives says no period then.

The document ``remaining`` is not read: the projection of the project manager and its variance
come from the document ``project``, which holds them with the reference budget and the indices.

Declared by US-2670/L1, the socle of EP-11; filled by US-2690/L2.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.portfolio.documents import documents_of
from waterfall.core.portfolio.folding import holding
from waterfall.core.portfolio.interface.scope import resolve_scope
from waterfall.core.portfolio.rows import Named, ProjectRow, filter_rows, row_of, sort_rows
from waterfall.core.portfolio.shaping import row_document, scope_document
from waterfall.core.projects.interface import openable, projects_named

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked, PortfolioReading
    from waterfall.core.projects.interface import ProjectState, Viewer

# The states the list counts: In progress, In pricing, and Completed in a period. Without a period,
# none is Completed in it: the state is not counted (#4020).
IN_PERIOD: frozenset[ProjectState] = frozenset({"in_progress", "pricing", "completed"})
WITHOUT_PERIOD: frozenset[ProjectState] = frozenset({"in_progress", "pricing"})


@dataclass(frozen=True, slots=True)
class Bounds:
    """The two bounds of a column of numbers, inclusive, either absent (WF-IHM-0130).

    A row whose column is null is retained by no bound of that column, whichever is set.
    """

    minimum: Decimal | None = None
    maximum: Decimal | None = None

    def holds(self, value: Decimal | None) -> bool:
        """Tell whether a value is between the bounds set; a null one is, if none is set."""
        if self.minimum is None and self.maximum is None:
            return True
        if value is None:
            return False
        return (self.minimum is None or value >= self.minimum) and (
            self.maximum is None or value <= self.maximum
        )


@dataclass(frozen=True, slots=True)
class PortfolioListing:
    """How the list is searched, filtered by column and by zone, sorted and paged.

    As the query says it: ``sort_by`` a column of the contract, the label by default; ``search``
    the text the label holds, ``code`` the text the code holds, compared as a search is; a pair of
    ``Bounds`` for each column of numbers — the two indices by their value —; the period of the last
    marked revision, its start included and its end excluded (an instant); ``zones``, those the cost
    index or the schedule index is in.
    """

    limit: int
    offset: int
    search: str | None = None
    zones: tuple[str, ...] = ()
    sort_by: str = "label"
    descending: bool = False
    code: str | None = None
    reference_budget: Bounds = field(default_factory=Bounds)
    current_estimate: Bounds = field(default_factory=Bounds)
    win_probability: Bounds = field(default_factory=Bounds)
    project_manager_projection: Bounds = field(default_factory=Bounds)
    delta_to_reference: Bounds = field(default_factory=Bounds)
    cost_index: Bounds = field(default_factory=Bounds)
    schedule_index: Bounds = field(default_factory=Bounds)
    last_marked_from: datetime | None = None
    last_marked_before: datetime | None = None


def _text_filter(
    session: Session, rows: list[ProjectRow], listing: PortfolioListing
) -> dict[UUID, bool]:
    """Tell, for each project, whether its label and its code hold the texts searched.

    The search is on the label, the code filter on the code, which a project without one does not
    hold: each by one statement, none when the filter is not asked.
    """
    kept = dict.fromkeys((row.project_id for row in rows), True)
    if listing.search is not None:
        labels = holding(session, [row.label for row in rows], listing.search)
        for row, held in zip(rows, labels, strict=True):
            kept[row.project_id] = kept[row.project_id] and held
    if listing.code is not None:
        coded = [row for row in rows if row.code is not None]
        found = holding(session, [row.code or "" for row in coded], listing.code)
        held_by = {row.project_id: held for row, held in zip(coded, found, strict=True)}
        for row in rows:
            kept[row.project_id] = kept[row.project_id] and held_by.get(row.project_id, False)
    return kept


def read_portfolio_projects(
    session: Session,
    asked: PortfolioAsked,
    listing: PortfolioListing,
    reading: PortfolioReading,
    viewer: Viewer,
) -> Document:
    """Give the page of the projects of the scope read by ``reading``, as the contract says it.

    ``meta.total`` counts the projects every filter retains, whatever the page; the scope counts
    those the states and the period retain (``PortfolioScope.project_count``).
    """
    period = asked.period_from is not None or asked.period_to is not None
    resolved = resolve_scope(
        session, asked, reading.at, counted=IN_PERIOD if period else WITHOUT_PERIOD, period=period
    )
    identifiers = list(resolved.projects)
    names = projects_named(session, identifiers)
    can_open = openable(session, identifiers, viewer)
    documents = documents_of(session, resolved, reading)
    thresholds = read_reference_settings(session).index_thresholds
    rows = [
        row_of(
            Named(project_id, names[project_id][1], names[project_id][0], project_id in can_open),
            retained,
            documents.get(project_id),
            thresholds,
        )
        for project_id, retained in resolved.projects.items()
        if project_id in names
    ]
    kept = _text_filter(session, rows, listing)
    found = filter_rows(rows, listing, lambda row: kept[row.project_id])
    ordered = sort_rows(found, listing.sort_by, descending=listing.descending)
    page = ordered[listing.offset : listing.offset + listing.limit]
    return {
        "scope": scope_document(resolved.scope),
        "items": [row_document(row) for row in page],
        "meta": {"limit": listing.limit, "offset": listing.offset, "total": len(ordered)},
    }
