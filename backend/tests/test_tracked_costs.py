# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The sums of the tracked lines of a project, which the indicators read (EP-09, EP-10).

The socle of EP-09 fixes how they name a scope: the whole project and the project alone by a word,
as the contract does, never by ``None``, whose sense would change from one function to the other.
US-1600 and US-1610/L2 write their tests where they fill them.
"""

from annotationlib import Format, call_evaluate_function, get_annotations

from waterfall.core.costs.interface import (
    PROJECT,
    UNASSIGNED,
    CostKey,
    CostScope,
    actual_cost_by_subproject,
    actual_costs_until,
)


def test_the_sums_name_the_project_alone_alike_and_the_whole_project_by_a_word() -> None:
    assert (PROJECT, UNASSIGNED) == ("project", "unassigned")
    assert get_annotations(actual_costs_until, format=Format.FORWARDREF)["scope"] is CostScope
    assert (
        call_evaluate_function(CostScope.evaluate_value, Format.STRING)
        == "UUID | Literal['project', 'unassigned']"
    )
    # The key of the project alone in a sum by subproject is the scope that sums it alone.
    assert (
        get_annotations(actual_cost_by_subproject, format=Format.STRING)["return"]
        == "Mapping[CostKey, Decimal]"
    )
    assert (
        call_evaluate_function(CostKey.evaluate_value, Format.STRING)
        == "UUID | Literal['unassigned']"
    )
