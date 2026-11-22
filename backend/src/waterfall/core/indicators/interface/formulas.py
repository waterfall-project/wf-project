# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The formulas of the indicators, which the portfolio applies to sums (EP-11, US-2670/L2).

The portfolio sums amounts, then divides: a portfolio index is the ratio of sums, never a mean of
indices (WF-PTF-0020). It applies the formulas of ``formulas/`` as they are, never writes them
again; this file offers them to a module that may import nothing but an interface.
"""

from waterfall.core.indicators.formulas import (
    NO_REFERENCE_BUDGET,
    Computable,
    Projections,
    cost_index,
    cost_variance,
    projections,
    schedule_index,
    schedule_variance,
    zone_of,
)

# The types and the functions are the interface's own to give: only a name in ``__all__`` is
# re-exported.
__all__ = [
    "NO_REFERENCE_BUDGET",
    "Computable",
    "Projections",
    "cost_index",
    "cost_variance",
    "projections",
    "schedule_index",
    "schedule_variance",
    "zone_of",
]
