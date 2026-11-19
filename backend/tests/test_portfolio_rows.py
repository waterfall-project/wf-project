# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rows of the list of the portfolio, formed, filtered and sorted without a database (US-2690).

What a row is made of the documents of a project, its columns null where they do not apply, the
bound of each column, the zones, and the sort on every column in both directions: the pure part of
the list, which the tests of the service (``test_portfolio_projects``) read through the API.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest

from waterfall.core.cost_settings.interface import IndexThresholds
from waterfall.core.portfolio.interface import Bounds, PortfolioListing, RetainedProject
from waterfall.core.portfolio.rows import (
    IndexCell,
    Named,
    ProjectRow,
    filter_rows,
    row_of,
    sort_rows,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from waterfall.core.indicators.interface import Document
    from waterfall.core.projects.interface import ProjectState

THRESHOLDS = IndexThresholds(Decimal("0.9"), Decimal("0.8"), Decimal("0.9"), Decimal("0.8"))
COLUMNS = (
    "label",
    "code",
    "state",
    "reference_budget",
    "current_estimate",
    "win_probability",
    "project_manager_projection",
    "delta_to_reference",
    "cost_index",
    "schedule_index",
    "last_marked_at",
)
BOUNDED = (
    "reference_budget",
    "current_estimate",
    "win_probability",
    "project_manager_projection",
    "delta_to_reference",
    "cost_index",
    "schedule_index",
)
INSTANT = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


def identifier(number: int) -> UUID:
    """Give an identifier of its own to each row of a test."""
    return UUID(int=number)


def index(value: str | None, zone: str | None = None) -> IndexCell:
    """Give the cell of an index of a row: a value, or an index not computed."""
    figure = {"is_computable": value is not None, "value": value, "reason": None}
    number = None if value is None else Decimal(value)
    return IndexCell(number, zone, {"value": figure, "zone": zone})


def row(number: int, **columns: Any) -> ProjectRow:
    """Give a row of a project In progress, labelled by its number, with the columns given."""
    label = columns.pop("label", f"Projet {number}")
    state = columns.pop("state", "in_progress")
    return ProjectRow(
        identifier(number), label, columns.pop("code", None), state, can_open=True, **columns
    )


def listing(**filters: Any) -> PortfolioListing:
    """Give a listing that asks for the filters given, a page of fifty."""
    return PortfolioListing(limit=50, offset=0, **filters)


def labels(rows: Sequence[ProjectRow]) -> list[str]:
    """Give the labels of the rows, in their order."""
    return [each.label for each in rows]


def project_document(**changes: Any) -> Document:
    """Give the document ``project`` of a project In progress: 1 000 of budget, 500 spent."""
    document: Document = {
        "reference_budget": "1000.00",
        "actual_cost": "500.00",
        "projections": {"project_manager": "1050.00", "variance_project_manager": "50.00"},
        "cost_index": {"value": {"is_computable": True, "value": "0.85", "reason": None}},
        "schedule_index": {
            "value": {"is_computable": False, "value": None, "reason": "no_planned_value"}
        },
    }
    return document | changes


OFFER_DOCUMENT: Document = {"total": {"is_computable": True, "value": "100000.00", "reason": None}}
NAMED = Named(identifier(1), "Extension du dépôt", "PRJ-1", can_open=False)


def formed(state: ProjectState, documents: Any, weight: str | None = "0.4") -> ProjectRow:
    """Form the row of a project of a state from the documents given, marked on 2 March."""
    held = None if weight is None else Decimal(weight)
    retained = RetainedProject(state, identifier(9), held, INSTANT)
    return row_of(NAMED, retained, documents, THRESHOLDS)


@pytest.mark.requirement("WF-PTF-0040-A")
def test_an_offer_shows_its_estimate_and_its_probability_where_a_project_shows_its_budget() -> None:
    # « Un projet en chiffrage affiche son devis et sa probabilité là où un projet en cours
    # affiche son budget de référence » : the other column is null, the indices and the projection
    # of a project that is not In progress too.
    offer = formed("pricing", {"estimate": OFFER_DOCUMENT})
    assert (offer.current_estimate, offer.win_probability) == (Decimal("100000.00"), Decimal("0.4"))
    assert offer.reference_budget is None
    assert (offer.project_manager_projection, offer.delta_to_reference) == (None, None)
    assert (offer.cost_index, offer.schedule_index) == (None, None)
    assert (offer.last_marked_at, offer.can_open) == (INSTANT, False)
    running = formed("in_progress", {"project": project_document()}, weight="1")
    assert running.reference_budget == Decimal("1000.00")
    assert (running.current_estimate, running.win_probability) == (None, None)
    assert running.project_manager_projection == Decimal("1050.00")
    assert running.delta_to_reference == Decimal("50.00")


@pytest.mark.requirement("WF-PTF-0040-A")
def test_the_indices_are_classified_on_the_thresholds_and_one_not_computed_has_no_zone() -> None:
    # « Les indices de coût et de délai avec leur zone » : 0.85 is under the watch threshold 0.9
    # and over the alert threshold 0.8; an index not computed has no zone, and no number.
    running = formed("in_progress", {"project": project_document()}, weight="1")
    assert running.cost_index is not None
    assert (running.cost_index.number, running.cost_index.zone) == (Decimal("0.85"), "watch")
    assert running.cost_index.document["zone"] == "watch"
    assert running.schedule_index is not None
    assert (running.schedule_index.number, running.schedule_index.zone) == (None, None)
    assert running.schedule_index.document["value"]["reason"] == "no_planned_value"


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_project_completed_shows_its_budget_and_its_indices_but_no_projection() -> None:
    # The contract: the projection and the variance are null outside a project In progress.
    done = formed("completed", {"project": project_document()}, weight="1")
    assert done.reference_budget == Decimal("1000.00")
    assert done.cost_index is not None
    assert (done.project_manager_projection, done.delta_to_reference) == (None, None)


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_project_no_document_reaches_has_a_row_without_a_figure() -> None:
    # « Un projet sans révision marquée à cette date est retenu selon son état, figure dans la
    # liste sans montant » — and a revision that kept no document of the kind: nothing is taken up.
    other: dict[ProjectState, str] = {"in_progress": "estimate", "pricing": "project"}
    for state, kind in other.items():
        nothing: tuple[dict[str, Document] | None, ...] = (None, {}, {kind: {}})
        for documents in nothing:
            empty = formed(state, documents)
            assert (empty.reference_budget, empty.current_estimate) == (None, None)
            assert (empty.project_manager_projection, empty.cost_index) == (None, None)
            assert (empty.last_marked_at, empty.label) == (INSTANT, "Extension du dépôt")
    # An estimate a missing rate prevents from computing is no figure either, the probability shown.
    lacking = {"estimate": {"total": {"is_computable": False, "value": None, "reason": "rates"}}}
    offer = formed("pricing", lacking)
    assert (offer.current_estimate, offer.win_probability) == (None, Decimal("0.4"))
    assert formed("pricing", {"estimate": OFFER_DOCUMENT}, weight=None).win_probability is None


@pytest.mark.requirement("WF-PTF-0040-A")
@pytest.mark.parametrize("column", COLUMNS)
def test_the_list_sorts_on_every_column_in_both_directions_a_project_without_value_last_ascending(
    column: str,
) -> None:
    # « La liste se trie sur chaque colonne dans les deux sens, par le serveur » : a project
    # without a value comes after the others in the ascending order, before them in the other.
    values: dict[str, tuple[Any, Any]] = {
        "label": ("Alpha", "Zèbre"),
        "code": ("PRJ-1", "PRJ-2"),
        "state": ("pricing", "completed"),
        "reference_budget": (Decimal(10), Decimal(20)),
        "current_estimate": (Decimal(10), Decimal(20)),
        "win_probability": (Decimal("0.2"), Decimal("0.9")),
        "project_manager_projection": (Decimal(10), Decimal(20)),
        "delta_to_reference": (Decimal(-5), Decimal(5)),
        "cost_index": (index("0.7"), index("1.1")),
        "schedule_index": (index("0.7"), index("1.1")),
        "last_marked_at": (INSTANT, INSTANT.replace(month=5)),
    }
    low, high = values[column]
    rows = [row(3, **{column: high}), row(1, **{column: low}), row(2)]
    if column in {"label", "state"}:
        rows[2] = row(2, **{column: "Mi" if column == "label" else "in_progress"})
        middle = [rows[1], rows[2], rows[0]]
        assert [r.project_id for r in sort_rows(rows, column, descending=False)] == [
            each.project_id for each in middle
        ]
        assert [r.project_id for r in sort_rows(rows, column, descending=True)] == [
            each.project_id for each in reversed(middle)
        ]
        return
    ascending = sort_rows(rows, column, descending=False)
    descending = sort_rows(rows, column, descending=True)
    assert [each.project_id for each in ascending] == [identifier(1), identifier(3), identifier(2)]
    assert [each.project_id for each in descending] == [identifier(2), identifier(3), identifier(1)]


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_tie_is_broken_by_the_label_in_code_points_then_by_the_identifier_both_ways() -> None:
    # README of the contract, « A tie in a sort… »: the order of the unsorted list — the label,
    # compared in code points: « Zoé » before « émile » — then the identifier.
    rows = [
        row(4, label="émile", code="X"),
        row(2, label="Zoé", code="X"),
        row(3, label="Zoé", code="X"),
        row(1, label="Anne", code="Y"),
    ]
    ascending = [each.project_id for each in sort_rows(rows, "code", descending=False)]
    descending = [each.project_id for each in sort_rows(rows, "code", descending=True)]
    assert ascending == [identifier(2), identifier(3), identifier(4), identifier(1)]
    assert descending == [identifier(1), identifier(2), identifier(3), identifier(4)]
    by_label = [each.project_id for each in sort_rows(rows, "label", descending=False)]
    assert by_label == [identifier(1), identifier(2), identifier(3), identifier(4)]


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_state_is_sorted_by_its_place_in_the_cycle_of_life() -> None:
    states = ("completed", "pricing", "in_progress")
    rows = [row(number, state=state) for number, state in enumerate(states)]
    ordered = sort_rows(rows, "state", descending=False)
    assert [each.state for each in ordered] == ["pricing", "in_progress", "completed"]


@pytest.mark.requirement("WF-PTF-0040-A")
@pytest.mark.parametrize("column", BOUNDED)
def test_a_bound_is_inclusive_and_a_project_without_the_column_is_retained_by_no_bound(
    column: str,
) -> None:
    # README, « A column of numbers… » : inclusive bounds; a null column, or an index not computed,
    # is retained by no bound of that column; a column without a bound retains everything.
    cell = column.endswith("index")
    make = index if cell else Decimal
    rows = [row(1, **{column: make("10")}), row(2, **{column: make("20")}), row(3)]
    if cell:
        rows.append(row(4, **{column: index(None)}))

    def kept(minimum: str | None = None, maximum: str | None = None) -> list[UUID]:
        bounds = Bounds(
            None if minimum is None else Decimal(minimum),
            None if maximum is None else Decimal(maximum),
        )
        found = filter_rows(rows, listing(**{column: bounds}), lambda _: True)
        return [each.project_id for each in found]

    assert kept("10", "20") == [identifier(1), identifier(2)]
    assert kept("10.01") == [identifier(2)]
    assert kept(maximum="19.99") == [identifier(1)]
    assert kept("21") == []
    assert len(filter_rows(rows, listing(), lambda _: True)) == len(rows)


@pytest.mark.requirement("WF-PTF-0040-A")
def test_the_period_of_the_last_marking_includes_its_start_and_excludes_its_end() -> None:
    # README, « A period… » : an instant has its end excluded; a project never marked is retained by
    # no bound of the period.
    rows = [
        row(1, last_marked_at=INSTANT),
        row(2, last_marked_at=INSTANT.replace(day=3)),
        row(3),
    ]

    def kept(since: datetime | None, until: datetime | None) -> list[UUID]:
        asked = listing(last_marked_from=since, last_marked_before=until)
        return [each.project_id for each in filter_rows(rows, asked, lambda _: True)]

    assert kept(INSTANT, INSTANT.replace(day=3)) == [identifier(1)]
    assert kept(INSTANT.replace(day=3), None) == [identifier(2)]
    assert kept(None, INSTANT.replace(day=3, minute=1)) == [identifier(1), identifier(2)]
    assert kept(INSTANT.replace(day=4), None) == []


@pytest.mark.requirement("WF-PTF-0040-A")
def test_the_zones_retain_the_projects_whose_cost_index_or_schedule_index_is_in_one_of_them() -> (
    None
):
    rows = [
        row(1, cost_index=index("0.7", "alert"), schedule_index=index("1.1", "nominal")),
        row(2, cost_index=index("1.1", "nominal"), schedule_index=index("0.85", "watch")),
        row(3, cost_index=index("1.1", "nominal")),
        row(4),
    ]

    def kept(*zones: str) -> list[UUID]:
        return [each.project_id for each in filter_rows(rows, listing(zones=zones), lambda _: True)]

    assert kept("alert") == [identifier(1)]
    assert kept("watch", "alert") == [identifier(1), identifier(2)]
    assert kept("nominal") == [identifier(1), identifier(2), identifier(3)]
    assert kept() == [identifier(1), identifier(2), identifier(3), identifier(4)]


@pytest.mark.requirement("WF-PTF-0040-A")
def test_the_text_filters_and_the_other_filters_retain_together() -> None:
    rows = [row(1, reference_budget=Decimal(10)), row(2, reference_budget=Decimal(10))]
    asked = listing(reference_budget=Bounds(Decimal(10), None))
    found = filter_rows(rows, asked, lambda each: each.project_id == identifier(2))
    assert [each.project_id for each in found] == [identifier(2)]
