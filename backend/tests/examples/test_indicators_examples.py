# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the indicators (US-1660/L2), no database.

From their fixtures under ``fixtures/indicators`` and ``fixtures/reference``: the progress, the
indices, the variances, the projections and the zone of an index, as ``core.indicators.formulas``
computes them; the physical progress of a summary task too (US-1680).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest

from waterfall.core.indicator_settings.interface import index_zone
from waterfall.core.indicators.formulas import (
    SummaryTask,
    budget_consumption,
    cost_index,
    cost_variance,
    financial_progress,
    physical_progress,
    projections,
    schedule_index,
    schedule_variance,
    summary_progress,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _decimal(data: Example, name: str) -> Decimal:
    return Decimal(cast("str", data[name]))


@pytest.mark.requirement("WF-IND-0040-A")
def test_a_subproject_of_budget_100_cost_70_and_remaining_70_is_at_50_percent_and_70_percent(
    example: Callable[[str], Example],
) -> None:
    # « Sur un sous-projet de budget 100, de coût réel 70 et de reste à engager 70, l'avancement
    # financier vaut 50 % et la consommation 70 %. »
    data = example("WF-IND-0040-A#2c0d13aef084")
    actual, remaining = _decimal(data, "actual_cost"), _decimal(data, "remaining")
    assert financial_progress(actual, remaining).value == _decimal(data, "financial_progress")
    assert budget_consumption(actual, _decimal(data, "budget")).value == _decimal(
        data, "budget_consumption"
    )


@pytest.mark.requirement("WF-IND-0050-A")
def test_a_project_of_budget_1000_earned_400_cost_500_remaining_550_projects_1100_1050_1250(
    example: Callable[[str], Example],
) -> None:
    # « Sur un projet de budget 1 000, de valeur acquise 400, de coût réel 500 et de reste à
    # engager 550, les projections valent 1 100 au budget, 1 050 pour le chef de projet et 1 250 au
    # rythme constaté. »
    data = example("WF-IND-0050-A#c6404fb0a5fe")
    shown = projections(
        _decimal(data, "budget"),
        _decimal(data, "earned_value"),
        _decimal(data, "actual_cost"),
        _decimal(data, "remaining"),
    )
    assert shown.at_budget == _decimal(data, "at_budget")
    assert shown.project_manager == _decimal(data, "project_manager")
    assert shown.at_observed_rate.value == _decimal(data, "at_observed_rate")
    assert shown.variance_at_budget == _decimal(data, "variance_at_budget")
    assert shown.variance_project_manager == _decimal(data, "variance_project_manager")
    assert shown.variance_at_observed_rate == _decimal(data, "variance_at_observed_rate")


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_budget_of_1000_with_400_on_finished_tasks_has_a_physical_progress_of_40_percent(
    example: Callable[[str], Example],
) -> None:
    # « Sur un budget de 1 000 dont 400 sont portés par des tâches terminées, l'avancement
    # physique vaut 40 %. »
    data = example("WF-IND-0060-A#f88169816950")
    assert physical_progress(
        _decimal(data, "earned_value"), _decimal(data, "budget")
    ).value == _decimal(data, "physical_progress")


def _summary_of(amounts: list[Decimal], completed: set[int]) -> Decimal | None:
    """Give the physical progress of a summary without own line over subordinates of amounts."""
    summary = uuid4()
    tasks = {summary: SummaryTask(None, completed=False, earnable=Decimal(0))}
    for rank, amount in enumerate(amounts):
        tasks[uuid4()] = SummaryTask(summary, completed=rank in completed, earnable=amount)
    return summary_progress(tasks, [summary])[summary].value


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_summary_of_subordinates_100_100_200_shows_50_then_75_percent(
    example: Callable[[str], Example],
) -> None:
    # « Une récapitulative sans ligne propre dont les deux premières de trois subordonnées, de
    # montants budgétés 100, 100 et 200, sont terminées affiche 50 % ; si la troisième est
    # terminée à la place de la deuxième, 75 %. » (US-1680)
    data = example("WF-IND-0060-A#40f59fb2a26d")
    amounts = [Decimal(each) for each in cast("list[str]", data["subordinates"])]
    assert _summary_of(amounts, {0, 1}) == _decimal(data, "first_two_completed")
    assert _summary_of(amounts, {0, 2}) == _decimal(data, "first_and_third_completed")


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_subordinate_started_at_90_percent_of_its_time_adds_nothing_to_its_summary(
    example: Callable[[str], Example],
) -> None:
    # « Une tâche démarrée à 90 % de son temps ne contribue pas. » A summary whose subtree bears
    # 1 000, 400 on a subordinate completed, shows 40 % (US-1680).
    data = example("WF-IND-0060-A#61c43a87da0a")
    amounts = [_decimal(data, "completed"), _decimal(data, "started")]
    assert _summary_of(amounts, {0}) == _decimal(data, "physical_progress")


@pytest.mark.requirement("WF-IND-0070-A")
def test_an_earned_value_of_400_for_an_actual_cost_of_500_gives_an_index_of_0_8(
    example: Callable[[str], Example],
) -> None:
    # « Une valeur acquise de 400 pour un coût réel de 500 donne 0,8. »
    data = example("WF-IND-0070-A#c2dde0dac2a2")
    assert cost_index(_decimal(data, "earned_value"), _decimal(data, "actual_cost")).value == (
        _decimal(data, "cost_index")
    )


@pytest.mark.requirement("WF-IND-0070-A")
def test_an_earned_value_of_400_for_an_actual_cost_of_500_gives_a_cost_variance_of_minus_100(
    example: Callable[[str], Example],
) -> None:
    # « Une valeur acquise de 400 pour un coût réel de 500 donne un écart de coût de -100. »
    data = example("WF-IND-0070-A#039eed3b60cd")
    assert cost_variance(_decimal(data, "earned_value"), _decimal(data, "actual_cost")) == (
        _decimal(data, "cost_variance")
    )


@pytest.mark.requirement("WF-IND-0080-A")
def test_an_earned_value_of_400_for_a_planned_value_of_500_gives_an_index_of_0_8(
    example: Callable[[str], Example],
) -> None:
    # « Une valeur acquise de 400 pour une valeur planifiée de 500 donne 0,8. »
    data = example("WF-IND-0080-A#aa6a94ba94fd")
    assert schedule_index(
        _decimal(data, "earned_value"), _decimal(data, "planned_value")
    ).value == _decimal(data, "schedule_index")


@pytest.mark.requirement("WF-IND-0080-A")
def test_an_earned_value_of_400_for_a_planned_value_of_500_gives_a_schedule_variance_of_minus_100(
    example: Callable[[str], Example],
) -> None:
    # « Une valeur acquise de 400 pour une valeur planifiée de 500 donne un écart de délai de
    # -100. »
    data = example("WF-IND-0080-A#9e5aed044b39")
    assert schedule_variance(_decimal(data, "earned_value"), _decimal(data, "planned_value")) == (
        _decimal(data, "schedule_variance")
    )


@pytest.mark.requirement("WF-REF-0170-A")
def test_an_index_decreasing_from_1_to_0_5_crosses_the_three_zones_at_thresholds_0_9_and_0_8(
    example: Callable[[str], Example],
) -> None:
    # « Un indice traverse les trois zones lorsque sa valeur décroît de 1 à 0,5, avec des seuils
    # fixés à 0,9 et 0,8. »
    data = example("WF-REF-0170-A#828c34614a3f")
    watch, alert = _decimal(data, "watch"), _decimal(data, "alert")
    steps = cast("list[dict[str, str]]", data["decreasing"])
    assert [index_zone(Decimal(step["index"]), watch, alert) for step in steps] == [
        step["zone"] for step in steps
    ]


@pytest.mark.requirement("WF-REF-0170-A")
def test_with_thresholds_0_9_and_0_8_an_index_of_0_9_is_nominal_and_one_of_0_8_in_watch(
    example: Callable[[str], Example],
) -> None:
    # « Avec des seuils à 0,9 et 0,8, un indice de 0,9 est nominal et un indice de 0,8 en
    # vigilance. »
    data = example("WF-REF-0170-A#8fb208c05af6")
    watch, alert = _decimal(data, "watch"), _decimal(data, "alert")
    assert index_zone(Decimal("0.9"), watch, alert) == "nominal"
    assert index_zone(Decimal("0.8"), watch, alert) == "watch"
