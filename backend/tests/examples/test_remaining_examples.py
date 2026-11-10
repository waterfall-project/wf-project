# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the remaining to commit of a line reestimated (US-1580/L2), no database.

From their fixtures under ``fixtures/remaining``: the remaining summed over the lines of the tasks
not completed (``remaining.summing``), the re-estimated amount priced from the figures entered and
the rate kept by the revision (``pricing``), as ``setLineRemaining`` writes them.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest

from waterfall.core.estimate.pricing import (
    Share,
    labour_base_amount,
    projected_amount,
    unrounded_labour_amount,
)
from waterfall.core.estimate.remaining.summing import LineAmount, remaining_sum

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _decimal(data: Example, name: str) -> Decimal:
    return Decimal(cast("str", data[name]))


def _reestimated(data: Example, effort: Decimal, rate: Decimal) -> Decimal:
    """Price a labour line of the example on its consumption year, at the rate given."""
    quantity = _decimal(data, "quantity")
    share = Share(
        cast("int", data["consumption_year"]), unrounded_labour_amount(quantity, effort, rate)
    )
    return projected_amount(
        (share,), cast("int", data["reference_year"]), _decimal(data, "inflation_rate")
    )


@pytest.mark.requirement("WF-RAE-0010-A")
def test_a_line_budgeted_at_100_reestimated_at_120_moves_the_remaining_from_100_to_120(
    example: Callable[[str], Example],
) -> None:
    # « La réestimation à 120 d'une ligne budgétée à 100 sur une tâche non démarrée, saisie depuis
    # la grille, porte le reste à engager de 100 à 120. »
    data = example("WF-RAE-0010-A#05923b0a3a8f")
    node = uuid4()
    before, _ = remaining_sum([LineAmount(node, _decimal(data, "budgeted_amount"), False)])
    after, by_line = remaining_sum([LineAmount(node, _decimal(data, "reestimated_amount"), False)])
    assert before == _decimal(data, "remaining_before")
    assert after == _decimal(data, "remaining_after")
    assert by_line == {node: _decimal(data, "remaining_after")}


@pytest.mark.requirement("WF-RAE-0040-A")
def test_80_hours_entered_give_80_times_the_rate_projected_on_the_year_of_consumption(
    example: Callable[[str], Example],
) -> None:
    # « La saisie d'une charge de 80 heures sur une ligne de quantité 1 budgétée à 100 heures donne
    # un montant réestimé de 80 fois le taux, projeté sur l'année de consommation de la ligne
    # (WF-DEV-0030) ; le montant n'est pas saisissable. »
    data = example("WF-RAE-0040-A#a27e44651c10")
    effort, rate = _decimal(data, "effort"), _decimal(data, "hourly_rate")
    assert labour_base_amount(_decimal(data, "quantity"), effort, rate) == _decimal(
        data, "base_amount"
    )
    assert _reestimated(data, effort, rate) == _decimal(data, "reestimated_amount")
    assert _reestimated(data, _decimal(data, "budgeted_effort"), rate) != _decimal(
        data, "reestimated_amount"
    )


@pytest.mark.requirement("WF-RAE-0010-A")
def test_a_line_counts_at_the_rate_its_revision_accepted_not_the_previous_one_inflated(
    example: Callable[[str], Example],
) -> None:
    # « Dans une révision créée en 2027 où le taux de 2027 d'une catégorie a été accepté, une tâche
    # non démarrée dont une ligne relève de cette catégorie compte pour sa charge au taux de 2027,
    # et non au taux de 2026 corrigé d'une année d'inflation. »
    data = example("WF-RAE-0010-A#0d404554bc50")
    effort = _decimal(data, "effort")
    accepted = _reestimated(data, effort, _decimal(data, "rate_of_2027"))
    total, _ = remaining_sum([LineAmount(uuid4(), accepted, False)])
    assert total == _decimal(data, "remaining")
    inflated = _decimal(data, "rate_of_2026") * (1 + _decimal(data, "inflation_rate"))
    assert _reestimated(data, effort, inflated) == _decimal(data, "remaining_at_2026_projected")
    assert total != _decimal(data, "remaining_at_2026_projected")
