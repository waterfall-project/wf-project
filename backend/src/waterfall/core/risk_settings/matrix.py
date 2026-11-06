# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rules of the matrix of risks (WF-REF-0160).

The three bounds of each axis are fractions, strictly increasing: a bound that is not above the one
before it is refused at its rank. A value is at the level of the bounds it reaches — the first below
the lowest bound, the fourth from the highest on —, and a cell of the matrix is the zone ranked by
its level of probability, then of severity. Pure functions: the settings are read by the interface
of ``cost_settings``, which keeps them.
"""

from typing import TYPE_CHECKING

from waterfall.platform.errors import FieldError, json_pointer

if TYPE_CHECKING:
    from collections.abc import Sequence
    from decimal import Decimal

    from waterfall.core.cost_settings.interface import RiskMatrix

BOUNDS_NOT_ORDERED = "BOUNDS_NOT_ORDERED"
# The levels of an axis: one more than its bounds.
LEVELS = 4


def matrix_faults(matrix: RiskMatrix) -> list[FieldError]:
    """Refuse each bound that is not strictly above the one before it, at its rank.

    On each axis, probability then severity: ``/risk_matrix/<axis>/<rank>``, the rank of the bound
    that breaks the order, counted from zero.
    """
    faults: list[FieldError] = []
    for axis, bounds in (
        ("probability_bounds", matrix.probability_bounds),
        ("severity_bounds", matrix.severity_bounds),
    ):
        faults.extend(
            FieldError(json_pointer("risk_matrix", axis, rank), BOUNDS_NOT_ORDERED)
            for rank in range(1, len(bounds))
            if bounds[rank] <= bounds[rank - 1]
        )
    return faults


def level_of(value: Decimal, bounds: Sequence[Decimal]) -> int:
    """Give the level, from 1 to 4, of a fraction on an axis: one more than the bounds it reaches.

    With bounds at 1, 5 and 10 %, a severity of 6 % — or of 5 % — is at the third level, of 3 % at
    the second (WF-REF-0160).
    """
    return 1 + sum(1 for bound in bounds if value >= bound)


def zone_of(matrix: RiskMatrix, probability: Decimal, severity: Decimal) -> str:
    """Give the zone of the cell of a probability and a severity, each a fraction (EP-08)."""
    row = level_of(probability, matrix.probability_bounds)
    column = level_of(severity, matrix.severity_bounds)
    return matrix.zones[LEVELS * (row - 1) + (column - 1)]
