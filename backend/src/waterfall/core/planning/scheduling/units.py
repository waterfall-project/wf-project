# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The units of a duration and of a lag, and their conversion into hours (WF-PLA-0160).

A duration or a lag keeps the unit of its entry; the engine turns it into hours only to place it.
The units of work convert by the three constants of the installation, the elapsed units without
a calendar — a day is twenty-four hours, a week seven days, a month thirty days —, and a lag in
percent is a share of the duration of its predecessor, in that duration's own unit (WF-PLA-0030).

Inside the engine the hours are fractions, exact whatever the division: twenty minutes are a third
of an hour, and three of them an hour, an equality the critical path and the conflicts rest on
(WF-PLA-0100). They become decimals again only where the engine renders them.
"""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

type DurationUnit = Literal["min", "h", "d", "w", "mo", "emin", "eh", "ed", "ew", "emo"]
"""The units of a duration, as the contract names them (`DurationUnit`)."""

type LagUnit = DurationUnit | Literal["percent"]
"""The units of a lag: those of a duration, and the percent of the predecessor's duration."""

MINUTES_PER_HOUR = 60
HOURS_PER_ELAPSED_DAY = 24
DAYS_PER_ELAPSED_WEEK = 7
DAYS_PER_ELAPSED_MONTH = 30
PERCENT = 100

ELAPSED_HOURS: dict[str, int] = {
    "eh": 1,
    "ed": HOURS_PER_ELAPSED_DAY,
    "ew": HOURS_PER_ELAPSED_DAY * DAYS_PER_ELAPSED_WEEK,
    "emo": HOURS_PER_ELAPSED_DAY * DAYS_PER_ELAPSED_MONTH,
}
"""The hours of one elapsed unit: converted without a calendar (WF-PLA-0160)."""

ELAPSED: frozenset[str] = frozenset({"emin", *ELAPSED_HOURS})
"""The elapsed units, placed without a calendar."""

MINUTES: frozenset[str] = frozenset({"min", "emin"})
"""Minutes, of work or elapsed: a sixtieth of an hour each."""


def decimal_of(hours: Fraction) -> Decimal:
    """Return a fraction as the engine renders it: exact when a decimal of the context holds it.

    A third of an hour is rendered to the precision of the context, the engine having compared
    it exactly before.
    """
    return Decimal(hours.numerator) / Decimal(hours.denominator)


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
class Span:
    """A duration or a lag in exact hours: of work, or elapsed, placed without a calendar."""

    hours: Fraction
    is_elapsed: bool

    def __neg__(self) -> Span:
        """Return the span the other way: a lag counted back from its successor."""
        return Span(-self.hours, self.is_elapsed)


@dataclass(frozen=True, slots=True)
class Duration:
    """A duration in the unit of its entry: nought for a milestone, negative only as a lead."""

    value: Decimal
    unit: DurationUnit

    @property
    def is_elapsed(self) -> bool:
        """Whether the duration is elapsed time, placed without a calendar."""
        return self.unit in ELAPSED

    def hours(self, constants: UnitConstants) -> Fraction:
        """Return the duration in exact hours: of work, or elapsed, as its unit says (WF-PLA-0160).

        The value is converted once, never summed unit by unit: sixty minutes are exactly an hour.
        """
        value = Fraction(self.value)
        if self.unit in MINUTES:
            return value / MINUTES_PER_HOUR
        if self.unit in ELAPSED_HOURS:
            return value * ELAPSED_HOURS[self.unit]
        per_unit = {
            "h": Fraction(1),
            "d": Fraction(constants.hours_per_day),
            "w": Fraction(constants.hours_per_week),
            "mo": Fraction(constants.hours_per_day) * Fraction(constants.days_per_month),
        }
        return value * per_unit[self.unit]

    def span(self, constants: UnitConstants) -> Span:
        """Return the duration as the engine places it: its hours, and whether they are elapsed."""
        return Span(self.hours(constants), self.is_elapsed)


@dataclass(frozen=True, slots=True)
class Lag:
    """The lag of a link in the unit of its entry, positive or negative — a lead (WF-PLA-0030)."""

    value: Decimal
    unit: LagUnit

    def span(self, predecessor: Span, constants: UnitConstants) -> Span:
        """Return the lag as the engine places it: in percent, that share of its predecessor's.

        Fifty percent of ten days are five days, of work as the ten are (WF-PLA-0030); the sign
        stays, a lead being a negative span. The share keeps the predecessor's kind of time, which
        the specification does not say: fifty percent of ten elapsed days are five elapsed days,
        placed without a calendar, as « in that duration's own unit » reads.
        """
        if self.unit == "percent":
            share = Fraction(self.value) / PERCENT
            return Span(predecessor.hours * share, predecessor.is_elapsed)
        return Duration(self.value, self.unit).span(constants)
