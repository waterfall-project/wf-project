# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the settings the installation shares (US-0810/L2), without a database.

What a new installation is delivered with (WF-EXP-0020), the level of a value on an axis of the
matrix of risks (WF-REF-0160) and the zone of an index (WF-REF-0170): the inputs and the values of
the sentences, from their fixtures under ``fixtures/reference``.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.bootstrap import EIGHT_HOURS
from waterfall.core.cost_settings.interface import (
    DELIVERED_MATRIX,
    DELIVERED_THRESHOLDS,
    DELIVERED_WEEKS,
)
from waterfall.core.indicator_settings.interface import index_zone
from waterfall.core.resource_settings.interface import DAYS
from waterfall.core.risk_settings.interface import level_of

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def decimals(values: object) -> tuple[Decimal, ...]:
    """Read a list of decimals written as the contract writes them."""
    return tuple(Decimal(value) for value in cast("list[str]", values))


@pytest.mark.requirement("WF-EXP-0020-A")
def test_a_new_installation_is_delivered_with_its_bounds_thresholds_delay_and_calendar(
    example: Callable[[str], Example],
) -> None:
    # « Sur une installation neuve, les bornes de probabilité valent 25 %, 50 % et 75 %, celles de
    # gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines, et le calendrier par
    # défaut compte huit heures du lundi au vendredi et aucune le week-end. »
    delivered = example("WF-EXP-0020-A#5f2bce6a634e")
    assert DELIVERED_MATRIX.probability_bounds == decimals(delivered["probability_bounds"])
    assert DELIVERED_MATRIX.severity_bounds == decimals(delivered["severity_bounds"])
    thresholds = cast("dict[str, str]", delivered["thresholds"])
    watch, alert = Decimal(thresholds["watch"]), Decimal(thresholds["alert"])
    assert (DELIVERED_THRESHOLDS.cost_watch, DELIVERED_THRESHOLDS.cost_alert) == (watch, alert)
    assert (DELIVERED_THRESHOLDS.schedule_watch, DELIVERED_THRESHOLDS.schedule_alert) == (
        watch,
        alert,
    )
    assert delivered["max_weeks_between_reviews"] == DELIVERED_WEEKS
    hours = cast("dict[str, str]", delivered["weekly_hours"])
    assert {day: EIGHT_HOURS.of(day) for day in DAYS} == {day: Decimal(hours[day]) for day in DAYS}


@pytest.mark.requirement("WF-REF-0160-A")
@pytest.mark.parametrize("key", ["WF-REF-0160-A#0fa3e0540e72", "WF-REF-0160-A#1470bfdbb110"])
def test_a_severity_is_at_the_level_of_the_bounds_it_reaches(
    example: Callable[[str], Example], key: str
) -> None:
    # « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité 60 est au troisième
    # niveau sur un projet de budget 1 000 (6 %) et au deuxième sur un projet de budget 2 000
    # (3 %) » ; « … un risque de gravité 50 sur un projet de budget 1 000 est au troisième
    # niveau » : a bound reached is a level reached.
    levels = example(key)
    bounds = decimals(levels["severity_bounds"])
    for case in cast("list[dict[str, object]]", levels["cases"]):
        fraction = Decimal(str(case["severity"])) / Decimal(str(case["budget"]))
        assert level_of(fraction, bounds) == case["level"]


@pytest.mark.requirement("WF-REF-0170-A")
@pytest.mark.parametrize("key", ["WF-REF-0170-A#828c34614a3f", "WF-REF-0170-A#8fb208c05af6"])
def test_an_index_decreasing_from_one_to_a_half_crosses_the_three_zones(
    example: Callable[[str], Example], key: str
) -> None:
    # « Un indice traverse les trois zones lorsque sa valeur décroît de 1 à 0,5, avec des seuils
    # fixés à 0,9 et 0,8 » ; « … un indice de 0,9 est nominal et un indice de 0,8 en vigilance. »
    zones = example(key)
    watch, alert = Decimal(str(zones["watch"])), Decimal(str(zones["alert"]))
    decreasing = cast("list[dict[str, str]]", zones["decreasing"])
    crossed = [index_zone(Decimal(case["index"]), watch, alert) for case in decreasing]
    assert crossed == [case["zone"] for case in decreasing]
    assert list(dict.fromkeys(crossed)) == ["nominal", "watch", "alert"]
