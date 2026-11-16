# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the update of the rates of a new revision (US-2430), without a database.

A revision created in 2027 from one that carried 2026 (WF-REV-0060-A): the rate kept projected by
the inflation of the project, the rate of the reference beside it, and the line priced at one or
the other, from the fixture under ``fixtures/pricing``, on the pure module ``pricing``. The
presentation, the refusal and the acceptance of an update are those of the API, which
``test_rate_update.py`` replays on a database.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.pricing import (
    Share,
    inflation_factor,
    projected_amount,
    unrounded_labour_amount,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
Category = dict[str, str | None]


def _categories(data: Example) -> list[Category]:
    return cast("list[Category]", data["categories"])


def _projected_rate(data: Example, previous: str) -> Decimal:
    """Project a rate of the previous year to the year of the revision, to the cent."""
    year = cast("int", data["reference_year"])
    share = Share(year, Decimal(previous))
    return projected_amount(
        (share,), cast("int", data["previous_year"]), Decimal(cast("str", data["inflation_rate"]))
    )


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
def test_a_revision_of_2027_over_one_of_2026_projects_the_rates_by_one_year_of_inflation(
    example: Callable[[str], Example],
) -> None:
    # « Une révision créée en 2027 porte l'année de référence 2027. » : one year elapses between
    # the year the previous revision carried, 2026, and that of the new one.
    data = example("WF-REV-0060-A#e0a3eb570e51")
    years = cast("int", data["previous_year"]), cast("int", data["reference_year"])
    assert years == (2026, 2027)
    rate = Decimal(cast("str", data["inflation_rate"]))
    assert inflation_factor(rate, *years) == 1 + rate


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
    # marquage, et l'accepter pour une catégorie la rechiffre au taux de 2027. » : the engineering
    # goes from 669,50 to 700,00, the commissioning, which has no rate of 2027, stays at 618,00.
    data = example("WF-REV-0060-A#c49cb122efe3")
    priced = {}
    for each in _categories(data):
        before = _priced_projected(data, each)
        after = _line_priced_at(data, each["reference_rate"]) if each["reference_rate"] else before
        priced[each["label"]] = (before, after)
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
    # révision en cours, qui est alors rechiffrée au taux de 2027 pour cette catégorie. »
    data = example("WF-REV-0060-A#964cab0bdd82")
    engineering = _categories(data)[0]
    refused = _priced_projected(data, engineering)
    accepted = _line_priced_at(data, cast("str", engineering["reference_rate"]))
    assert (refused, accepted) == (Decimal("669.50"), Decimal("700.00"))
    assert accepted == Decimal(cast("str", engineering["amount_updated"]))
