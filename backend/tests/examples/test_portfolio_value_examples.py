# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the value and the indices of the portfolio (US-2670/L2), no database.

From their fixtures under ``fixtures/portfolio``: the rule of aggregation (WF-PTF-0020), the
pipeline and the conversion rate (WF-PTF-0050), the projection of a project (WF-PTF-0040), the
projection at the observed rate of the sums (WF-PTF-0070) and the weight of an offer (WF-PRJ-0090),
as ``core/portfolio/aggregation`` computes them.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.portfolio.aggregation import (
    ProjectFigures,
    aggregate,
    conversion_rate,
    total_of,
    weight_of,
    weighted_amount,
    weighted_hours,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
NOUGHT = Decimal("0.00")
FIELDS = ("reference_budget", "earned_value", "actual_cost", "planned_value", "remaining")


def _decimal(data: Example, name: str) -> Decimal:
    return Decimal(cast("str", data[name]))


def _figures(project: dict[str, str], **given: str) -> ProjectFigures:
    amounts = dict.fromkeys(FIELDS, "0.00") | project | given
    return ProjectFigures(**{name: Decimal(value) for name, value in amounts.items()})


@pytest.mark.requirement("WF-PTF-0020-A")
def test_two_projects_of_earned_value_100_and_1000_and_cost_200_and_1000_give_an_index_of_0_917(
    example: Callable[[str], Example],
) -> None:
    # « Deux projets de valeur acquise 100 et 1 000, de coût réel 200 et 1 000, donnent un indice de
    # coût de portefeuille de 0,917, et non de 0,75. »
    data = example("WF-PTF-0020-A#a4a5e110bdc6")
    projects = cast("list[dict[str, str]]", data["projects"])
    result = aggregate(_figures(project, planned_value="1.00") for project in projects)
    assert result.cost_index.value == _decimal(data, "cost_index")
    assert result.cost_index.value is not None
    assert result.cost_index.value.quantize(Decimal("0.001")) == _decimal(data, "cost_index_shown")
    # The mean of the indices of the projects, 0.5 and 1, is what the rule refuses.
    assert result.cost_index.value != _decimal(data, "mean_of_indices")


@pytest.mark.requirement("WF-PTF-0020-A")
def test_an_offer_at_40_percent_and_a_quote_of_100000_adds_40000_to_the_weighted_pipeline(
    example: Callable[[str], Example],
) -> None:
    # « Une offre à 40 % de probabilité et 100 000 de devis contribue pour 40 000 à la valeur du
    # pipeline. »
    data = example("WF-PTF-0020-A#c424fdc63fd8")
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    estimate = _decimal(data, "estimate")
    assert weighted_amount(estimate, weight) == _decimal(data, "pipeline_weighted")


@pytest.mark.requirement("WF-PTF-0050-A")
def test_an_offer_at_40_percent_counts_for_all_in_the_gross_pipeline_and_40_percent_in_the_weighted(
    example: Callable[[str], Example],
) -> None:
    # « Une offre à 40 % de probabilité contribue pour tout au pipeline brut et pour 40 % au
    # pipeline pondéré. »
    data = example("WF-PTF-0050-A#2495b6b38022")
    estimate = _decimal(data, "estimate")
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    # The raw pipeline applies no weight: it sums the quotes as they are.
    assert total_of([estimate]) == _decimal(data, "pipeline_gross")
    assert weighted_amount(estimate, weight) == _decimal(data, "pipeline_weighted")


@pytest.mark.requirement("WF-PTF-0050-A")
def test_four_offers_won_out_of_ten_out_of_pricing_give_a_conversion_rate_of_40_percent(
    example: Callable[[str], Example],
) -> None:
    # « Sur dix offres sorties de l'état Chiffrage dans la période vers En cours ou vers Perdu,
    # dont quatre passées à En cours, le taux de transformation vaut 40 % ; une onzième,
    # abandonnée dans la période, ne le change pas. »
    data = example("WF-PTF-0050-A#82adcb588823")
    won = ["in_progress"] * cast("int", data["won"])
    lost = ["lost"] * cast("int", data["lost"])
    abandoned = ["abandoned"] * cast("int", data["abandoned"])
    assert conversion_rate(won + lost).value == _decimal(data, "conversion_rate")
    assert conversion_rate(won + lost + abandoned).value == _decimal(data, "conversion_rate")


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_project_of_budget_1000_cost_500_and_remaining_550_projects_1050_with_a_variance_of_50(
    example: Callable[[str], Example],
) -> None:
    # « Un projet en cours de budget 1 000, de coût réel 500 et de reste à engager 550 affiche une
    # projection de 1 050 et un écart de 50. »
    data = example("WF-PTF-0040-A#b7dfea08ee32")
    figures = ProjectFigures(
        reference_budget=_decimal(data, "reference_budget"),
        earned_value=NOUGHT,
        actual_cost=_decimal(data, "actual_cost"),
        planned_value=NOUGHT,
        remaining=_decimal(data, "remaining"),
    )
    projections = aggregate([figures]).projections
    assert projections.project_manager == _decimal(data, "projection")
    assert projections.variance_project_manager == _decimal(data, "variance")


@pytest.mark.requirement("WF-PTF-0070-A")
def test_two_projects_of_budget_1000_give_an_aggregated_projection_at_the_observed_rate_of_2222(
    example: Callable[[str], Example],
) -> None:
    # « Sur deux projets de budget 1 000, de valeur acquise 400 et 500 et de coût réel 500 et 500,
    # la projection au rythme constaté agrégée vaut 2 222 et non 2 250. »
    data = example("WF-PTF-0070-A#107cfb595699")
    projects = cast("list[dict[str, str]]", data["projects"])
    result = aggregate(_figures(project) for project in projects)
    observed = result.projections.at_observed_rate.value
    assert observed == _decimal(data, "at_observed_rate")
    assert observed is not None
    assert observed.to_integral_value() == _decimal(data, "at_observed_rate_whole")
    assert observed != _decimal(data, "mean_of_indices_projection")


@pytest.mark.requirement("WF-PRJ-0090-A")
def test_an_offer_at_40_percent_of_a_quote_of_100000_weighs_40000_and_40_percent_of_its_load(
    example: Callable[[str], Example],
) -> None:
    # « Une offre à 40 % de probabilité et 100 000 € de devis pèse 40 000 € dans le pipeline
    # pondéré et 40 % de sa charge dans le plan de charge agrégé pondéré. »
    data = example("WF-PRJ-0090-A#0600dd236bf1")
    assert data["state"] == "pricing"
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    estimate = _decimal(data, "estimate")
    assert weighted_amount(estimate, weight) == _decimal(data, "pipeline_weighted")
    assert weighted_hours(_decimal(data, "hours"), weight) == _decimal(data, "weighted_hours")
