# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the workload, the cost structure and the S-curve of the portfolio.

US-2670/L2, no database. From their fixtures under ``fixtures/portfolio``: the aggregated workload
(WF-PTF-0060), the weighted offer in the structure of the costs (WF-PTF-0080) and in the curves
(WF-PTF-0100), as ``core/portfolio/aggregation`` computes them.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.interface import Month
from waterfall.core.portfolio.aggregation import (
    CostLine,
    included_hours,
    load_ratio,
    load_zone,
    sum_by_key,
    sum_by_month,
    sum_by_nature,
    weight_of,
    weighted_amount,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
ROLE = "electrician"


def _decimal(data: Example, name: str) -> Decimal:
    return Decimal(cast("str", data[name]))


def _quote_lines(data: Example) -> list[CostLine]:
    lines = cast("list[dict[str, object]]", data["quote_lines"])
    return [
        CostLine(
            nature=cast("str", each["nature"]),
            amount=Decimal(cast("str", each["amount"])),
            provision=cast("bool", each["provision"]),
        )
        for each in lines
    ]


def _aggregated(data: Example, weight: Decimal) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Sum an offer's weighted quote by nature, in the budget and in the remaining to commit."""
    lines = _quote_lines(data)
    return (
        sum_by_nature(lines, weight, with_provisions=False),
        sum_by_nature(lines, weight, with_provisions=True),
    )


@pytest.mark.requirement("WF-PTF-0060-A")
def test_two_projects_in_progress_of_100_and_150_hours_of_a_role_give_250_hours_the_same_month(
    example: Callable[[str], Example],
) -> None:
    # « Sur deux projets en cours dont les restes à engager portent 100 et 150 heures d'un même
    # rôle le même mois, le plan agrégé porte 250 heures. »
    data = example("WF-PTF-0060-A#45748fe78d7c")
    march = Month(2026, 3)
    projects = [{ROLE: Decimal(hours)} for hours in cast("list[str]", data["in_progress_hours"])]
    by_role = sum_by_key(projects)
    assert by_role == {ROLE: _decimal(data, "aggregated_hours")}
    assert sum_by_month([{march: hours} for hours in by_role.values()], [march]) == [
        _decimal(data, "aggregated_hours")
    ]


@pytest.mark.requirement("WF-PTF-0060-A")
def test_an_offer_at_50_percent_of_100_hours_adds_50_hours_when_included_and_none_otherwise(
    example: Callable[[str], Example],
) -> None:
    # « Une offre à 50 % avec 100 heures ajoute 50 heures quand le chiffrage est inclus, rien
    # sinon. »
    data = example("WF-PTF-0060-A#dd1733488885")
    offer = cast("dict[str, str]", data["offer"])
    weight = weight_of("pricing", Decimal(offer["win_probability"]))
    hours = Decimal(offer["hours"])
    in_progress = [{ROLE: Decimal(each)} for each in cast("list[str]", data["in_progress_hours"])]
    for included, expected in ((True, "with_offer_hours"), (False, "aggregated_hours")):
        offer_hours = included_hours(hours, weight, included=included)
        assert sum_by_key([*in_progress, {ROLE: offer_hours}])[ROLE] == _decimal(data, expected)
    assert included_hours(hours, weight, included=True) == _decimal(data, "offer_hours")


@pytest.mark.requirement("WF-PTF-0060-A")
def test_a_month_at_120_percent_of_the_capacity_is_in_the_alert_zone(
    example: Callable[[str], Example],
) -> None:
    # « Un mois à 120 % de la capacité est signalé. »
    data = example("WF-PTF-0060-A#9bd0b92b0168")
    month = cast("dict[str, str]", data["overloaded"])
    hours, capacity = Decimal(month["hours"]), Decimal(month["capacity"])
    threshold = _decimal(data, "under_load_threshold")
    assert load_ratio(hours, capacity).value == Decimal(month["load_ratio"])
    assert load_zone(hours, capacity, threshold) == month["zone"]


@pytest.mark.requirement("WF-PTF-0080-A")
def test_an_offer_at_40_percent_of_100_of_labour_adds_40_to_the_labour_of_the_aggregated_budget(
    example: Callable[[str], Example],
) -> None:
    # « Une offre à 40 % dont le devis porte 100 de main-d'œuvre ajoute 40 à la main-d'œuvre du
    # budget agrégé lorsqu'elle est incluse. »
    data = example("WF-PTF-0080-A#304cd560fe09")
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    budget, _ = _aggregated(data, weight)
    assert budget["labour"] == Decimal(cast("dict[str, str]", data["aggregated_budget"])["labour"])


@pytest.mark.requirement("WF-PTF-0080-A")
def test_a_provision_line_of_50_of_an_offer_at_40_percent_adds_20_to_the_remaining_only(
    example: Callable[[str], Example],
) -> None:
    # « Une offre incluse, à 40 %, dont le devis porte une ligne de provision pour risques de 50
    # n'ajoute rien à la nature de cette ligne dans le budget agrégé, et ajoute 20 à cette nature
    # dans le reste à engager agrégé. »
    data = example("WF-PTF-0080-A#c53a7c6ba53d")
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    # The quote holds the provision line: the budget leaves it out, the remaining keeps it.
    budget, remaining = _aggregated(data, weight)
    aggregated_remaining = cast("dict[str, str]", data["aggregated_remaining"])
    assert "risk_provision" not in budget
    assert remaining["risk_provision"] == Decimal(aggregated_remaining["risk_provision"])
    assert budget == {
        nature: Decimal(amount)
        for nature, amount in cast("dict[str, str]", data["aggregated_budget"]).items()
    }


@pytest.mark.requirement("WF-PTF-0080-A")
def test_a_line_of_50_of_another_nature_adds_20_to_its_nature_in_the_budget_and_in_the_remaining(
    example: Callable[[str], Example],
) -> None:
    # « Une ligne de 50 d'une nature hors main-d'œuvre, une provision pour aléas par exemple, ajoute
    # 20 à sa nature dans l'un et dans l'autre. »
    data = example("WF-PTF-0080-A#47418792a9e5")
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    budget, remaining = _aggregated(data, weight)
    assert budget["other"] == Decimal(cast("dict[str, str]", data["aggregated_budget"])["other"])
    assert remaining["other"] == Decimal(
        cast("dict[str, str]", data["aggregated_remaining"])["other"]
    )


@pytest.mark.requirement("WF-PTF-0100-A")
def test_an_offer_at_40_percent_contributes_40_percent_of_its_curve_to_each_month_of_the_sum(
    example: Callable[[str], Example],
) -> None:
    # « Un projet en chiffrage à 40 % contribue pour 40 % de ses courbes lorsqu'il est inclus. »
    data = example("WF-PTF-0100-A#b4875ef04969")
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    months = [Month(2026, 1), Month(2026, 2)]
    curve = {
        month: weighted_amount(Decimal(point), weight)
        for month, point in zip(months, cast("list[str]", data["budget_curve"]), strict=True)
    }
    expected = [Decimal(point) for point in cast("list[str]", data["weighted_budget_curve"])]
    assert sum_by_month([curve], months) == expected


@pytest.mark.requirement("WF-PTF-0100-A")
def test_an_offer_of_100_and_a_provision_of_50_adds_40_to_the_budget_and_60_to_the_projection(
    example: Callable[[str], Example],
) -> None:
    # « Une offre incluse à 40 %, dont le devis porte 100 hors provisions et une provision de 50,
    # apporte 40 au budget cumulé final et 60 à la projection. »
    data = example("WF-PTF-0100-A#faac2b71539d")
    weight = weight_of("pricing", _decimal(data, "win_probability"))
    budget = cast("list[str]", data["budget_curve"])
    projection = cast("list[str]", data["projection_curve"])
    assert weighted_amount(Decimal(budget[-1]), weight) == _decimal(data, "final_budget")
    assert weighted_amount(Decimal(projection[-1]), weight) == _decimal(data, "final_projection")
