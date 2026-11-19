# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The interface of the portfolio is imported by each entry point that marks a revision (EP-11).

Split from ``test_registries`` (US-2670/L1), which keeps within the thousand lines a file may hold.
"""

import subprocess
import sys

import pytest
from test_registries import ENTRY_POINTS

# The interface of the portfolio, which registers its part of a marking from US-2680/L2 on.
PORTFOLIO = "waterfall.core.portfolio.interface"


@pytest.mark.parametrize("entry_point", sorted(ENTRY_POINTS))
def test_each_entry_point_imports_the_interface_of_the_portfolio(entry_point: str) -> None:
    # A tool of the registries, which covers no requirement. The portfolio fills no registry before
    # US-2680/L2, which registers at ``register_indicators``
    # what a marking keeps for it: the comparison above cannot tell yet whether an entry point
    # imports it. Each that marks a revision — the API, the worker, the loader — does from the
    # socle on (EP-11, "Modules"), so that none marks without its part once it registers.
    statement = f"import sys, {ENTRY_POINTS[entry_point]}; print({PORTFOLIO!r} in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", statement], capture_output=True, text=True, timeout=120, check=True
    )
    assert result.stdout.strip() == "True"
