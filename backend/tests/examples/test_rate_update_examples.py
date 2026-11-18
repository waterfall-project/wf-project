# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the update of the rates of a new revision (US-2430), without a database.

A revision created in 2027 from one that carried 2026 (WF-REV-0060-A): the rate kept projected by
the inflation of the project, the rate of the reference beside it, and the line priced at one or
the other, from the fixture under ``fixtures/pricing``, on ``projected_rate`` of ``keeping`` and
the pure module ``pricing``. The year a revision carries, the presentation, the refusal, the
acceptance of an update, its offer until it is marked and the keeping of the projected rate of a
category without a rate of reference are those of the API, which ``test_rate_update.py`` replays
on a database; this file cannot replay them.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.keeping import projected_rate
from waterfall.core.estimate.pricing import (
    Share,
    projected_amount,
    unrounded_disbursement_amount,
    unrounded_labour_amount,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
Category = dict[str, str | None]


def _categories(data: Example) -> list[Category]:
    return cast("list[Category]", data["categories"])


def _projected_rate(data: Example, previous: str) -> Decimal:
    """Project a rate of the previous year to the year of the revision, as the revision does."""
    years = cast("int", data["previous_year"]), cast("int", data["reference_year"])
    return projected_rate(Decimal(previous), Decimal(cast("str", data["inflation_rate"])), years)


def _priced_projected(data: Example, category: Category) -> Decimal:
    """Price the line of the example at the rate of a category projected by one year."""
    return _line_priced_at(data, str(_projected_rate(data, cast("str", category["previous_rate"]))))


def _line_priced_at(data: Example, rate: str) -> Decimal:
    """Price the line of the example, consumed in the year of the revision, at a rate."""
    year = cast("int", data["reference_year"])
    product = unrounded_labour_amount(
        Decimal(cast("str", data["quantity"])), Decimal(cast("str", data["effort"])), Decimal(rate)
    )
    return projected_amount((Share(year, product),), year, Decimal(0))


@pytest.mark.requirement("WF-REV-0060-A")
def test_one_year_of_inflation_projects_the_rates_of_2026_to_2027(
    example: Callable[[str], Example],
) -> None:
    # « Une révision créée en 2027 porte l'année de référence 2027. » This test proves only the
    # projection of one year that follows, 65,00 to 66,95 and 60,00 to 61,80; that a revision
    # created in 2027 carries 2027 is the attribution of the year, which ``test_rate_update.py``
    # carries on a database.
    data = example("WF-REV-0060-A#e0a3eb570e51")
    projected = [
        _projected_rate(data, cast("str", each["previous_rate"])) for each in _categories(data)
    ]
    assert projected == [Decimal("66.95"), Decimal("61.80")]


@pytest.mark.requirement("WF-REV-0060-A")
def test_the_proposal_shows_the_rate_projected_beside_the_rate_of_the_reference_per_category(
    example: Callable[[str], Example],
) -> None:
    # « À sa création, lorsque la précédente portait 2026, l'écart est présenté catégorie par
    # catégorie et la mise à jour peut être refusée. » : 66,95 beside 70,00 for the engineering,
    # 61,80 alone for the commissioning, which has no rate for 2027.
    data = example("WF-REV-0060-A#a31bf69eb132")
    shown = {
        each["label"]: (
            _projected_rate(data, cast("str", each["previous_rate"])),
            each["reference_rate"],
        )
        for each in _categories(data)
    }
    assert shown == {
        "Ingénierie": (Decimal("66.95"), "70.00"),
        "Mise en service": (Decimal("61.80"), None),
    }
    assert [each["projected_rate"] for each in _categories(data)] == ["66.95", "61.80"]


@pytest.mark.requirement("WF-REV-0060-A")
def test_a_category_refused_or_without_a_rate_is_priced_at_the_rate_of_2026_inflated_one_year(
    example: Callable[[str], Example],
) -> None:
    # « Une catégorie refusée ou sans taux pour 2027 est chiffrée au taux de 2026 corrigé d'une
    # année d'inflation. »
    data = example("WF-REV-0060-A#586554e118d8")
    for each in _categories(data):
        rate = _projected_rate(data, cast("str", each["previous_rate"]))
        assert _line_priced_at(data, str(rate)) == Decimal(cast("str", each["amount_projected"]))


@pytest.mark.requirement("WF-REV-0060-A")
def test_an_import_projects_the_rates_one_year_and_accepting_a_category_prices_it_at_2027(
    example: Callable[[str], Example],
) -> None:
    # « Une révision créée en 2027 par un import de reste à engager porte les taux de 2026
    # projetés d'une année ; la mise à jour catégorie par catégorie reste proposée jusqu'à son
    # marquage, et l'accepter pour une catégorie la rechiffre au taux de 2027. » : the whole
    # import, every category, before and after the update; the engineering goes from 669,50 to
    # 700,00, the commissioning stays at 618,00. That a category without a rate of 2027 keeps its
    # projected rate, and that the update stays offered until the marking, are rules of the
    # database, carried by ``test_rate_update.py``; the ``amount_updated`` of the fixture is what
    # they give, and what this test compares the pricing to.
    data = example("WF-REV-0060-A#c49cb122efe3")
    priced = {
        each["label"]: (
            _priced_projected(data, each),
            _line_priced_at(data, cast("str", each["reference_rate"] or each["projected_rate"])),
        )
        for each in _categories(data)
    }
    assert priced == {
        "Ingénierie": (Decimal("669.50"), Decimal("700.00")),
        "Mise en service": (Decimal("618.00"), Decimal("618.00")),
    }
    for each in _categories(data):
        assert priced[each["label"]][1] == Decimal(cast("str", each["amount_updated"]))


@pytest.mark.requirement("WF-REV-0060-A")
def test_an_update_refused_at_the_creation_then_accepted_reprices_the_line_at_the_rate_of_2027(
    example: Callable[[str], Example],
) -> None:
    # « Une mise à jour refusée à la création d'une révision est acceptée ensuite depuis la
    # révision en cours, qui est alors rechiffrée au taux de 2027 pour cette catégorie. » : the
    # one category with a rate, the engineering, alone; the order of the refusal and of the later
    # acceptance, and the revision in progress they act on, are carried by ``test_rate_update.py``.
    data = example("WF-REV-0060-A#964cab0bdd82")
    engineering = _categories(data)[0]
    refused = _priced_projected(data, engineering)
    accepted = _line_priced_at(data, cast("str", engineering["reference_rate"]))
    assert refused == Decimal(cast("str", engineering["amount_projected"]))
    assert accepted == Decimal(cast("str", engineering["amount_updated"]))


@pytest.mark.requirement("WF-REV-0060-A")
def test_a_disbursement_of_8000_consumed_in_2028_is_8487_20_in_the_revisions_of_2026_and_2027(
    example: Callable[[str], Example],
) -> None:
    # « Avec une inflation de 3 %, une ligne de débours 8 000 consommée en 2028 vaut 8 487,20 dans
    # la révision de 2026 comme dans celle créée en 2027, où son débours est de 8 240. » : the
    # disbursement of 2026 projected by one year is the 8 240 of the revision of 2027, and the line
    # consumed in 2028 is worth the same from either year of reference.
    data = example("WF-REV-0060-A#413d589bd41d")
    rate = Decimal(cast("str", data["inflation_rate"]))
    quantity = Decimal(cast("str", data["quantity"]))
    year = cast("int", data["consumption_year"])
    first, second = cast("int", data["first_year"]), cast("int", data["second_year"])
    disbursement = Decimal(cast("str", data["unit_disbursement"]))
    expected = Decimal(cast("str", data["projected_amount"]))
    in_first = projected_amount(
        (Share(year, unrounded_disbursement_amount(quantity, disbursement)),), first, rate
    )
    carried = projected_rate(disbursement, rate, (first, second))
    assert carried == Decimal(cast("str", data["second_unit_disbursement"]))
    in_second = projected_amount(
        (Share(year, unrounded_disbursement_amount(quantity, carried)),), second, rate
    )
    assert in_first == in_second == expected
