# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the amounts of the estimate grid, replayed without a database (US-2430).

The re-estimated amount of a line beside its budgeted one (WF-DEV-0020-A), its increase over the
amount at the rates of the reference year (WF-DEV-0050-A) and the total of a work package
(WF-DEV-0060-A): the inputs and the values of the sentences, from their fixtures under
``fixtures/pricing`` and ``fixtures/estimate``, on the pure modules ``pricing`` and ``shares``.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.pricing import (
    Share,
    labour_base_amount,
    projected_amount,
    sum_amounts,
    unrounded_labour_amount,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _decimal(data: Example, name: str) -> Decimal:
    return Decimal(cast("str", data[name]))


def _reestimated(data: Example, effort: Decimal) -> Decimal:
    """Price a labour line of the example on its consumption year."""
    quantity, rate = _decimal(data, "quantity"), _decimal(data, "hourly_rate")
    share = Share(
        cast("int", data["consumption_year"]), unrounded_labour_amount(quantity, effort, rate)
    )
    return projected_amount(
        (share,), cast("int", data["reference_year"]), _decimal(data, "inflation_rate")
    )


@pytest.mark.requirement("WF-DEV-0020-A")
def test_80_hours_entered_on_a_line_budgeted_at_100_give_80_times_the_rate_and_keep_the_budget(
    example: Callable[[str], Example],
) -> None:
    # « La saisie d'une charge de 80 heures sur une ligne de quantité 1 budgétée à 100 heures,
    # consommée dans l'année de référence, donne un montant réestimé de 80 fois le taux et laisse
    # le montant budgété inchangé. »
    data = example("WF-DEV-0020-A#378d44187659")
    quantity, rate = _decimal(data, "quantity"), _decimal(data, "hourly_rate")
    budgeted = _reestimated(data, _decimal(data, "budgeted_effort"))
    reestimated = _reestimated(data, _decimal(data, "effort"))
    assert reestimated == _decimal(data, "reestimated_amount")
    assert reestimated == round(80 * rate, 2)
    assert budgeted == _decimal(data, "budgeted_amount")
    assert budgeted == labour_base_amount(quantity, _decimal(data, "budgeted_effort"), rate)


@pytest.mark.requirement("WF-DEV-0050-A")
def test_two_years_later_at_2_percent_the_reestimated_amount_is_4_04_percent_over_the_base(
    example: Callable[[str], Example],
) -> None:
    # « ... une ligne dont la tâche se place deux ans après l'année de référence, avec une
    # inflation de 2 %, affiche un montant réestimé supérieur de 4,04 % à son montant aux taux de
    # l'année de référence. »
    data = example("WF-DEV-0050-A#52fb4a7cb73b")
    effort = _decimal(data, "effort")
    base = labour_base_amount(_decimal(data, "quantity"), effort, _decimal(data, "hourly_rate"))
    reestimated = _reestimated(data, effort)
    assert base == _decimal(data, "base_amount")
    assert reestimated == _decimal(data, "reestimated_amount")
    increase = (reestimated / base - 1) * 100
    assert increase == _decimal(data, "increase_percent")


def _lot_total(leaves: dict[str, list[str]], tasks: list[str] | None) -> str | None:
    """Give the total of a work package: the lines of the tasks of its subtree, none if unborne."""
    if tasks is None:
        return None
    return str(sum_amounts(Decimal(line) for each in tasks for line in leaves[each]))


@pytest.mark.requirement("WF-DEV-0060-A")
def test_a_lot_without_a_task_has_no_total_and_one_with_a_task_totals_its_subtree(
    example: Callable[[str], Example],
) -> None:
    # « Sur un planning importé dont aucune tâche n'est rattachée à un lot, les totaux par lot
    # sont absents plutôt que nuls ; après rattachement d'une récapitulative au lot 1, son total
    # apparaît, et il vaut celui de son sous-arbre ; après rattachement d'une feuille à un lot, le
    # total de ce lot est le montant des lignes de cette feuille. »
    data = example("WF-DEV-0060-A#89b7fa39b765")
    leaves = cast("dict[str, list[str]]", data["leaves"])
    summary = cast("list[str]", data["summary_of"])
    unattached = dict.fromkeys(cast("list[str]", data["work_packages"]), None)
    assert unattached == data["unattached"]
    assert {
        "Lot 1": _lot_total(leaves, summary),
        "Lot 2": None,
    } == data["summary_attached_to_lot_1"]
    assert {
        "Lot 1": None,
        "Lot 2": _lot_total(leaves, ["c"]),
    } == data["leaf_attached_to_lot_2"]
    # The summary's total is the sum of its leaves' totals, none of them nought.
    assert Decimal(cast("str", _lot_total(leaves, summary))) == sum_amounts(
        Decimal(cast("str", _lot_total(leaves, [each]))) for each in summary
    )
