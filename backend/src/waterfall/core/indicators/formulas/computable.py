# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The envelope of a figure that may not be computed, and the reasons it gives (WF-IND-0010).

A figure the data do not allow is presented not computable, with the reason, never as zero or as
infinity. The reasons are the codes of ``NotComputableReason`` of the contract.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

NO_ACTUAL_COST = "no_actual_cost"
NO_EARNED_VALUE = "no_earned_value"
NO_PLANNED_VALUE = "no_planned_value"
NO_REFERENCE_BUDGET = "no_reference_budget"
NO_BUDGETED_AMOUNT = "no_budgeted_amount"
NO_ACTUAL_OR_REMAINING = "no_actual_or_remaining"


@dataclass(frozen=True, slots=True)
class Computable:
    """A figure, or the reason it is not computed; exactly one of the two is set."""

    value: Decimal | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        """Refuse a figure with both a value and a reason, or with neither."""
        if (self.value is None) == (self.reason is None):
            message = "A figure has a value or a reason, exactly one of the two."
            raise ValueError(message)

    @property
    def is_computable(self) -> bool:
        """Tell whether the figure has a value."""
        return self.value is not None

    @classmethod
    def of(cls, value: Decimal) -> Computable:
        """Make a computable figure."""
        return cls(value=value)

    @classmethod
    def not_computable(cls, reason: str) -> Computable:
        """Make a figure that is not computed, saying why."""
        return cls(reason=reason)
