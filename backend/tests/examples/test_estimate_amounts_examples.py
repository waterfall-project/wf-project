# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the amounts of the estimate grid, replayed without a database (US-2430).

The re-estimated amount of a line beside its budgeted one (WF-DEV-0020-A), its increase over the
amount at the rates of the reference year (WF-DEV-0050-A) and the total of a work package
(WF-DEV-0060-A): the inputs and the values of the sentences, from their fixtures under
``fixtures/pricing`` and ``fixtures/estimate``, on the pure module ``pricing`` and on the total of
a work package of ``indicating``, which the API reads too.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest

from waterfall.core.estimate.indicating import Row, work_package_amount
from waterfall.core.estimate.pricing import (
    Share,
    labour_base_amount,
    projected_amount,
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
    # The consumption year is the reference year: the inflation of the fixture has no hold, and
    # the amount re-estimated is the base amount of the production on the new effort.
    assert reestimated == labour_base_amount(quantity, _decimal(data, "effort"), rate)
    # The budgeted amount is that of the budgeted effort, a pure calculation having no entry to
    # make: that the entry of an effort leaves the stored budget alone is carried by the API tests
    # of the estimate lines, not replayed here.
    assert budgeted == _decimal(data, "budgeted_amount")
    assert budgeted == labour_base_amount(quantity, _decimal(data, "budgeted_effort"), rate)


@pytest.mark.requirement("WF-DEV-0050-A")
def test_two_years_later_at_2_percent_the_reestimated_amount_is_4_04_percent_over_the_base(
    example: Callable[[str], Example],
) -> None:
    # « ... une ligne dont la tâche se place deux ans après l'année de référence, avec une
    # inflation de 2 %, affiche un montant réestimé supérieur de 4,04 % à son montant aux taux de
    # l'année de référence. » Only this half is replayed here; that the quotation grid does not
    # show the budgeted amount is carried by the API and front tests of the grid.
    data = example("WF-DEV-0050-A#52fb4a7cb73b")
    effort = _decimal(data, "effort")
    base = labour_base_amount(_decimal(data, "quantity"), effort, _decimal(data, "hourly_rate"))
    reestimated = _reestimated(data, effort)
    assert base == _decimal(data, "base_amount")
    assert reestimated == _decimal(data, "reestimated_amount")
    increase = (reestimated / base - 1) * 100
    assert increase == _decimal(data, "increase_percent")


def _rows(leaves: dict[str, list[str]]) -> tuple[list[Row], dict[str, UUID]]:
    """Give the lines of the leaves as the indicators read them, and the node of each leaf."""
    nodes = {each: uuid4() for each in leaves}
    category = uuid4()
    rows = [
        Row(nodes[leaf], category, None, Decimal(line), is_labour=False)
        for leaf, lines in leaves.items()
        for line in lines
    ]
    return rows, nodes


def _lot_total(rows: list[Row], borne: set[UUID] | None) -> str | None:
    """Give the total of a work package as the indicators do, none if no task bears it."""
    amount = work_package_amount(rows, borne, {})
    return None if amount.value is None else str(amount.value)


@pytest.mark.requirement("WF-DEV-0060-A")
def test_a_lot_without_a_task_has_no_total_and_one_with_a_task_totals_its_subtree(
    example: Callable[[str], Example],
) -> None:
    # « Sur un planning importé dont aucune tâche n'est rattachée à un lot, les totaux par lot
    # sont absents plutôt que nuls ; après rattachement d'une récapitulative au lot 1, son total
    # apparaît, et il vaut celui de son sous-arbre ; après rattachement d'une feuille à un lot, le
    # total de ce lot est le montant des lignes de cette feuille. » The total is that of
    # ``work_package_amount``, which the API reads; that the tasks of a subtree are those the
    # planning gives is carried by ``test_estimate_indicators.py``.
    data = example("WF-DEV-0060-A#89b7fa39b765")
    rows, nodes = _rows(cast("dict[str, list[str]]", data["leaves"]))
    summary = {nodes[each] for each in cast("list[str]", data["summary_of"])}
    lot_1, lot_2 = cast("list[str]", data["work_packages"])
    assert {lot_1: _lot_total(rows, None), lot_2: _lot_total(rows, None)} == data["unattached"]
    assert {
        lot_1: _lot_total(rows, summary),
        lot_2: _lot_total(rows, None),
    } == data["summary_attached_to_lot_1"]
    assert {
        lot_1: _lot_total(rows, None),
        lot_2: _lot_total(rows, {nodes["c"]}),
    } == data["leaf_attached_to_lot_2"]
    # A work package whose tasks bear no line totals nought, which is not an absent total.
    assert work_package_amount(rows, {uuid4()}, {}).value == Decimal("0.00")
