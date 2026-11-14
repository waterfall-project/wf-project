# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The figures of a measure: the median, the worst and the spread of a few runs."""

from dataclasses import dataclass
from statistics import median
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class Summary:
    """What a series of identical runs says of an operation, in seconds.

    The spread is the worst run less the best one: a difference between two measures smaller than
    it is no gain.
    """

    runs: int
    median: float
    worst: float
    spread: float


def summarise(durations: Sequence[float]) -> Summary:
    """Summarise the durations of identical runs; none is a defect of the caller."""
    if not durations:
        message = "a summary needs at least one run"
        raise ValueError(message)
    return Summary(
        runs=len(durations),
        median=median(durations),
        worst=max(durations),
        spread=max(durations) - min(durations),
    )


def ratio(numerator: float, denominator: float) -> float:
    """Divide one duration by another; zero when the second is zero, which no run gives."""
    return numerator / denominator if denominator else 0.0
