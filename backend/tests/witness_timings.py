# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time the fixtures of the witness take, summed over a run (#4653, temporary measure).

Each step a fixture times — the loading, the rows laid, the partitions dropped, the rows deleted —
is kept in the properties of the test, which pytest-xdist carries back to the controller; the
summary of the run sums them by step.
"""

import time
from collections import defaultdict
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    import pytest

PREFIX = "timing:"


@contextmanager
def timed(node: pytest.Item | None, step: str) -> Generator[None]:
    """Keep in the properties of the test the seconds the block took, under ``step``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        if node is not None:
            node.user_properties.append((PREFIX + step, time.perf_counter() - start))


def summary(reporter: pytest.TerminalReporter) -> None:
    """Write the sum, the count and the mean of each step the tests of the run timed."""
    totals: dict[str, list[float]] = defaultdict(list)
    for reports in reporter.stats.values():
        for report in reports:
            if getattr(report, "when", None) != "teardown":
                continue
            for name, value in getattr(report, "user_properties", ()):
                if isinstance(name, str) and name.startswith(PREFIX):
                    totals[name.removeprefix(PREFIX)].append(float(value))
    if not totals:
        return
    reporter.write_sep("=", "witness timings (#4653)")
    for step, values in sorted(totals.items()):
        total = sum(values)
        reporter.write_line(
            f"{step:<28} n={len(values):>5} total={total:9.2f}s "
            f"mean={total / len(values):7.3f}s max={max(values):7.3f}s"
        )
