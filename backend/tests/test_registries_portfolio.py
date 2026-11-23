# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The interface of the portfolio is imported by each entry point that marks a revision (EP-11).

Split from ``test_registries`` (US-2670/L1), which keeps within the thousand lines a file may hold.
The portfolio registers what a marking keeps for it from US-2680/L2 on: ``store_contribution``,
after ``store_indicators``, in every process that marks.
"""

import subprocess
import sys

import pytest
from test_registries import ENTRY_POINTS, registered_in

# The interface of the portfolio, which registers its part of a marking from US-2680/L2 on.
PORTFOLIO = "waterfall.core.portfolio.interface"
# What a marking computes and keeps, in the order it acts: the indicators (EP-10), then the
# portfolio (US-2680/L2).
INDICATORS = [
    "waterfall.core.indicators.interface.storing.store_indicators",
    f"{PORTFOLIO}.contribution.store_contribution",
]


@pytest.mark.parametrize("entry_point", sorted(ENTRY_POINTS))
def test_each_entry_point_imports_the_interface_of_the_portfolio(entry_point: str) -> None:
    # A tool of the registries, which covers no requirement. Each process that marks a revision —
    # the API, the worker, the loader — imports the interface of the portfolio from the socle on
    # (EP-11, "Modules"), so that none marks without its part.
    statement = f"import sys, {ENTRY_POINTS[entry_point]}; print({PORTFOLIO!r} in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", statement], capture_output=True, text=True, timeout=120, check=True
    )
    assert result.stdout.strip() == "True"


@pytest.mark.story("US-2680")
@pytest.mark.parametrize("entry_point", sorted(ENTRY_POINTS))
def test_each_entry_point_keeps_the_portfolio_after_the_indicators_at_a_marking(
    entry_point: str,
) -> None:
    # Propre à l'US : the documents of the portfolio are written in the transaction of the marking,
    # by the registry of the revisions, after the indicators of EP-10 — the API, the worker, which
    # runs the markings and the merges, and the loader of the witness (``load_marking``) alike.
    held = registered_in(ENTRY_POINTS[entry_point])
    assert held["revisions.indicators"] == INDICATORS
