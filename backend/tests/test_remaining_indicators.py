# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1600 writes its tests here ("Les tests du back"). The socle fixes the results EP-10 reads.
"""

from annotationlib import Format, get_annotations
from dataclasses import fields

from waterfall.core.estimate.interface import (
    CalculationContext,
    RemainingIndicators,
    RevisionRemaining,
    SubprojectBalance,
    remaining_indicators,
    remaining_of_revision,
)


def test_the_indicators_and_the_remaining_of_a_revision_answer_their_results() -> None:
    # What EP-10 reads from the socle on (EP-09, "Ce que le cadrage laisse à EP-10"): the results
    # are fixed before US-1600 fills them.
    assert (
        get_annotations(remaining_indicators, format=Format.FORWARDREF)["return"]
        is RemainingIndicators
    )
    assert (
        get_annotations(remaining_of_revision, format=Format.FORWARDREF)["return"]
        is RevisionRemaining
    )
    assert [field.name for field in fields(RevisionRemaining)] == ["total", "by_line"]
    assert [field.name for field in fields(CalculationContext)] == [
        "revision_id",
        "revision_status",
        "computed_at",
        "scope",
        "is_stored",
    ]
    assert [field.name for field in fields(RemainingIndicators)] == [
        "context",
        "total",
        "by_cost_type",
        "by_subproject",
        "coverage",
        "delta_to_reference",
        "delta_to_previous_revision",
    ]
    assert [field.name for field in fields(SubprojectBalance)] == [
        "key",
        "label",
        "budget",
        "actual_cost",
        "remaining",
        "variance",
        "is_over_budget",
        "zone",
    ]
