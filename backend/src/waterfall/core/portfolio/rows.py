# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rows of the list of the portfolio, formed of the documents, filtered and sorted (US-2690).

A row is formed of what a project is and of the documents it contributes (``project`` or
``estimate``), none of its lines (WF-PTF-0040): the filter, the sort and the paging are made on the
rows, in memory — three hundred projects, and columns that no table holds (EP-11, "Les vues"). The
row is a function of the document: the same row on the current day and at a past date, only the
documents differ. A column that does not apply to the project is null: an offer has no reference
budget, projection or index, a project in progress has no current estimate nor probability of
winning (WF-PTF-0040), and a project that no document reaches — no revision marked at the date — has
no figure at all. A null column is retained by no bound of that column (the contract's convention).
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.indicators.interface import Computable, zone_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from waterfall.core.cost_settings.interface import IndexThresholds
    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.core.portfolio.interface.projects import PortfolioListing
    from waterfall.core.portfolio.interface.scope import RetainedProject
    from waterfall.core.projects.interface import ProjectState

PRICING: ProjectState = "pricing"
IN_PROGRESS: ProjectState = "in_progress"
# The places of the states in the cycle of life, the order of ``ProjectState`` (WF-CYC-0010).
LIFECYCLE: tuple[ProjectState, ...] = (
    "created",
    "pricing",
    "in_progress",
    "completed",
    "lost",
    "abandoned",
)
# What a column is sorted by; ``NOTHING`` stands in for the absent value, which is placed apart.
type SortValue = str | int | Decimal | datetime
NOTHING = 0


@dataclass(frozen=True, slots=True)
class IndexCell:
    """An index of a row: its value, which the bounds and the sort read, and its contract document.

    ``number`` is null for an index that is not computed.
    """

    number: Decimal | None
    zone: str | None
    document: Document


@dataclass(frozen=True, slots=True)
class ProjectRow:
    """A row of the list: a project, and its columns at the date of calculation."""

    project_id: UUID
    label: str
    code: str | None
    state: ProjectState
    can_open: bool
    reference_budget: Decimal | None = None
    current_estimate: Decimal | None = None
    win_probability: Decimal | None = None
    project_manager_projection: Decimal | None = None
    delta_to_reference: Decimal | None = None
    cost_index: IndexCell | None = None
    schedule_index: IndexCell | None = None
    last_marked_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Named:
    """What names a project in the list, whatever the date: its label, its code, its opening."""

    project_id: UUID
    label: str
    code: str | None
    can_open: bool


def _index(index: Document, watch: Decimal, alert: Decimal) -> IndexCell:
    """Give an index of a document of the project, classified on the thresholds of the day."""
    value: Document = index["value"]
    number = None if value["value"] is None else Decimal(value["value"])
    figure = (
        Computable.of(number) if number is not None else Computable.not_computable(value["reason"])
    )
    zone = zone_of(figure, watch, alert)
    return IndexCell(number, zone, {"value": value, "zone": zone})


def _of_project(row: ProjectRow, document: Document, thresholds: IndexThresholds) -> ProjectRow:
    """Complete the row of a project In progress or Completed with its document ``project``.

    The projection of the project manager and its variance to the reference, positive beyond it,
    are those of a project In progress alone, as the contract says.
    """
    figures: dict[str, Decimal | None] = {"reference_budget": Decimal(document["reference_budget"])}
    if row.state == IN_PROGRESS:
        projections: Document = document["projections"]
        figures["project_manager_projection"] = Decimal(projections["project_manager"])
        figures["delta_to_reference"] = Decimal(projections["variance_project_manager"])
    return replace(
        row,
        **figures,
        cost_index=_index(document["cost_index"], thresholds.cost_watch, thresholds.cost_alert),
        schedule_index=_index(
            document["schedule_index"], thresholds.schedule_watch, thresholds.schedule_alert
        ),
    )


def row_of(
    named: Named,
    retained: RetainedProject,
    documents: Mapping[IndicatorKind, Document] | None,
    thresholds: IndexThresholds,
) -> ProjectRow:
    """Form the row of a project from what names it, what retains it and the documents it gives.

    ``documents`` is ``None`` for a project that contributes none: its state, its label and its
    code, no figure. An offer shows its current estimate — null if a missing rate prevents it —
    and the probability of winning its revision retained gives (the weight); another project, the
    figures of its indicators, and no probability (WF-PTF-0040).
    """
    row = ProjectRow(
        named.project_id,
        named.label,
        named.code,
        retained.state,
        named.can_open,
        last_marked_at=retained.marked_at,
    )
    if documents is None:
        return row
    if retained.state == PRICING:
        estimate = documents.get("estimate")
        if estimate is None:
            return row
        total: Document = estimate["total"]
        figure = Decimal(total["value"]) if total["is_computable"] else None
        return replace(row, current_estimate=figure, win_probability=retained.weight)
    indicators = documents.get("project")
    return row if indicators is None else _of_project(row, indicators, thresholds)


def _column(row: ProjectRow, name: str) -> Decimal | None:
    """Give the number a column of numbers holds, an index by its value; null when it has none."""
    held = getattr(row, name)
    return held.number if isinstance(held, IndexCell) else held


def _retained(row: ProjectRow, listing: PortfolioListing) -> bool:
    """Tell whether every filter by column retains the row: each one on its own, together."""
    bounded = (
        ("reference_budget", listing.reference_budget),
        ("current_estimate", listing.current_estimate),
        ("win_probability", listing.win_probability),
        ("project_manager_projection", listing.project_manager_projection),
        ("delta_to_reference", listing.delta_to_reference),
        ("cost_index", listing.cost_index),
        ("schedule_index", listing.schedule_index),
    )
    if not all(bounds.holds(_column(row, name)) for name, bounds in bounded):
        return False
    if listing.last_marked_from is not None or listing.last_marked_before is not None:
        moment = row.last_marked_at
        if moment is None:
            return False
        if listing.last_marked_from is not None and moment < listing.last_marked_from:
            return False
        if listing.last_marked_before is not None and moment >= listing.last_marked_before:
            return False
    if listing.zones:
        zones = {cell.zone for cell in (row.cost_index, row.schedule_index) if cell is not None}
        return bool(zones & set(listing.zones))
    return True


def filter_rows(
    rows: list[ProjectRow], listing: PortfolioListing, found: Callable[[ProjectRow], bool]
) -> list[ProjectRow]:
    """Keep the rows every filter retains: by column, by zone, and ``found`` (code and search).

    ``found`` is the text filters, which the database compares as a search does (README of the
    contract, "A search…"); the others are compared here.
    """
    return [row for row in rows if _retained(row, listing) and found(row)]


def _sort_value(row: ProjectRow, column: str) -> SortValue | None:
    """Give what a column is sorted by: texts by their code points, a state by its place."""
    match column:
        case "label" | "code":
            return getattr(row, column)
        case "state":
            return LIFECYCLE.index(row.state)
        case "last_marked_at":
            return row.last_marked_at
        case _:
            return _column(row, column)


def sort_rows(rows: list[ProjectRow], column: str, *, descending: bool) -> list[ProjectRow]:
    """Sort the rows by a column, in the direction asked.

    A tie is broken by the order of the unsorted list — the label by its code points — then by the
    identifier (README of the contract, "A tie in a sort…"), in both directions; a project without
    a value comes after the others in the ascending order, so before them in the descending one.
    """
    unsorted = sorted(rows, key=lambda row: (row.label, str(row.project_id)))
    return sorted(
        unsorted,
        key=lambda row: _placed(_sort_value(row, column)),
        reverse=descending,
    )


def _placed(value: SortValue | None) -> tuple[bool, SortValue]:
    """Put the absent value after the others, so that nothing is compared with it."""
    return (value is None, NOTHING if value is None else value)
