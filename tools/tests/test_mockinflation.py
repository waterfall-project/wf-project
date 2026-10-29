# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the amounts of a line, inflation included, on the witness (US-0701/L1, L-01).

The budgeted and the re-estimated amounts of a line are « exprimés inflation comprise, à l'année de
consommation de la ligne » (WF-DEV-0020); the amount at the rates of the reference year, before
inflation, is a value read (WF-DEV-0050); a line of provision is not projected (WF-DEV-0030).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockcore, mockdating, mockwitness
from wftools.mockstructure import CENT, REFERENCE_YEAR, Projection, described
from wftools.mockwitness import Line, Task


def _facet(row: mockcore.Row) -> dict[str, Any]:
    return cast("dict[str, Any]", row.node["estimate_line"])


@pytest.mark.requirement("WF-DEV-0050-A")
def test_a_line_two_years_after_the_reference_year_is_reestimated_4_04_percent_above() -> None:
    # Vérif : « une ligne dont la tâche se place deux ans après l'année de référence, avec une
    # inflation de 2 %, affiche un montant réestimé supérieur de 4,04 % à son montant aux taux de
    # l'année de référence ». The witness bears such lines, at its own 3 %: each is re-estimated
    # 1.03 x 1.03 its amount; priced at 2 %, the first of them, 1.0404 its amount.
    lines = {
        line.number: line for task in mockdating.tasks_in_order(described()) for line in task.lines
    }
    later = [
        row
        for row in mockcore.current()
        if row.kind == mockcore.ESTIMATE_LINE
        and _facet(row)["consumption_year"] == REFERENCE_YEAR + 2
        and not _facet(row)["is_computed"]
    ]
    assert len(later) == 1_608
    for row in later:
        base = Decimal(_facet(row)["base_amount"])
        assert Decimal(_facet(row)["reestimated_amount"]) == (base * Decimal("1.0609")).quantize(
            CENT
        )
    first = later[0]
    at_two = mockdating.price(
        lines[first.number], REFERENCE_YEAR + 2, projection=Projection(rate=Decimal("0.02"))
    )
    assert at_two.base == Decimal(_facet(first)["base_amount"])
    assert at_two.reestimated == (at_two.base * Decimal("1.0404")).quantize(CENT)
    assert at_two.reestimated > at_two.base


@pytest.mark.requirement("WF-DEV-0030-A")
def test_a_line_of_provision_two_years_after_the_reference_year_is_not_projected() -> None:
    # Vérif : « une ligne de provision portée par une tâche consommée deux ans après l'année de
    # référence vaut sa gravité pondérée par sa probabilité, sans autre projection », and « une
    # même ligne consommée deux ans après l'année de référence, avec un taux d'inflation de 3 %,
    # vaut 1,03 x 1,03 fois son montant de base ».
    on = date(REFERENCE_YEAR + 2, 1, 3)
    provision = Line(
        592, "Provision", mockwitness.PROVISIONS, unit=Decimal("250.00"), is_provision=True
    )
    equipment = Line(593, "Matériel", mockwitness.EQUIPMENT, unit=Decimal("100.00"))
    later = Task(591, "Plus tard", days=1, manual=(on, on), lines=(provision, equipment))
    rows = {row.number: _facet(row) for row in mockcore.core((later,)) if row.parent is not None}
    amounts = ("base_amount", "budgeted_amount", "reestimated_amount")
    assert [rows[592][key] for key in amounts] == ["250.00", "250.00", "250.00"]
    assert [rows[593][key] for key in amounts] == ["100.00", "106.09", "106.09"]
