# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The units of a duration and of a lag, and their conversion into hours (WF-PLA-0160).

A duration or a lag keeps the unit of its entry; the engine turns it into hours only to place it.
The units of work convert by the three constants of the installation, the elapsed units without
a calendar — a day is twenty-four hours, a week seven days, a month thirty days —, and a lag in
percent is a share of the duration of its predecessor, in that duration's own unit (WF-PLA-0030).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

type DurationUnit = Literal["min", "h", "d", "w", "mo", "emin", "eh", "ed", "ew", "emo"]
"""The units of a duration, as the contract names them (`DurationUnit`)."""

type LagUnit = DurationUnit | Literal["percent"]
"""The units of a lag: those of a duration, and the percent of the predecessor's duration."""

MINUTES_PER_HOUR = Decimal(60)
HOURS_PER_ELAPSED_DAY = Decimal(24)
DAYS_PER_ELAPSED_WEEK = Decimal(7)
DAYS_PER_ELAPSED_MONTH = Decimal(30)
PERCENT = Decimal(100)

ELAPSED_HOURS: dict[str, Decimal] = {
    "eh": Decimal(1),
    "ed": HOURS_PER_ELAPSED_DAY,
    "ew": HOURS_PER_ELAPSED_DAY * DAYS_PER_ELAPSED_WEEK,
    "emo": HOURS_PER_ELAPSED_DAY * DAYS_PER_ELAPSED_MONTH,
}
"""The hours of one elapsed unit: converted without a calendar (WF-PLA-0160)."""

ELAPSED: frozenset[str] = frozenset({"emin", *ELAPSED_HOURS})
"""The elapsed units, placed without a calendar."""

MINUTES: frozenset[str] = frozenset({"min", "emin"})
"""Minutes, of work or elapsed: divided by sixty rather than multiplied by a sixtieth, which no
decimal holds exactly."""


@dataclass(frozen=True, slots=True)
class UnitConstants:
    """The three constants of the installation the units of work convert by (WF-PLA-0160).

    The engine reads no setting: whoever calls it passes the constants of the installation, those
    a marked revision froze being the ones it computed with.
    """

    hours_per_day: Decimal
    hours_per_week: Decimal
    days_per_month: Decimal


@dataclass(frozen=True, slots=True)
class Duration:
    """A duration in the unit of its entry: nought for a milestone, negative only as a lead."""

    value: Decimal
    unit: DurationUnit

    @property
    def is_elapsed(self) -> bool:
        """Whether the duration is elapsed time, placed without a calendar."""
        return self.unit in ELAPSED

    def hours(self, constants: UnitConstants) -> Decimal:
        """Return the duration in hours: of work, or elapsed, as its unit says (WF-PLA-0160).

        The value is converted once, never summed unit by unit: sixty minutes are exactly an hour.
        """
        if self.unit in MINUTES:
            return self.value / MINUTES_PER_HOUR
        if self.unit in ELAPSED_HOURS:
            return self.value * ELAPSED_HOURS[self.unit]
        per_unit = {
            "h": Decimal(1),
            "d": constants.hours_per_day,
            "w": constants.hours_per_week,
            "mo": constants.hours_per_day * constants.days_per_month,
        }
        return self.value * per_unit[self.unit]


@dataclass(frozen=True, slots=True)
class Lag:
    """The lag of a link in the unit of its entry, positive or negative — a lead (WF-PLA-0030)."""

    value: Decimal
    unit: LagUnit

    def span(self, predecessor: Duration) -> Duration:
        """Return the lag as a duration: in percent, that share of its predecessor's duration.

        Fifty percent of ten days are five days, of work as the ten are (WF-PLA-0030); the sign
        stays, a lead being a negative span.
        """
        if self.unit == "percent":
            return Duration(predecessor.value * self.value / PERCENT, predecessor.unit)
        return Duration(self.value, self.unit)
