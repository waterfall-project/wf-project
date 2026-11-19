# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The documents of indicators: what a reading answers, a marking keeps and the cache holds.

A document is a JSON object, the answer of the contract of its kind for one scope — the indicators
of a project (``ProjectIndicators``), a curve (``CurveSeries``), the history of the indices
(``IndexHistory``), the time/time diagram (``MilestoneTracking``) —, the zone of each index null
until a reading classifies it on the thresholds of the day (EP-10, "Ce que le cadrage décide"). The
computation of the day, the marking (``revision_indicator``) and the cache (``platform.cache``)
write the same one, and the API answers it through the models of the contract.

Declared by US-1660/L1, the socle of EP-10, with the kinds a marking keeps.
"""

from typing import Any, Literal

# A document of indicators: a JSON object, its amounts in text as the contract's ``Money``.
type Document = dict[str, Any]
# The kinds of document a marking keeps (``revision_indicator.kind``): the indicators of the
# estimate and of the remaining to commit, those of the project, and its three curves; then the
# documents of a project the portfolio sums, of the scope ``project`` alone (EP-11, US-2670/L1),
# which ``keep_document`` writes for it from US-2680/L1 on.
type IndicatorKind = Literal[
    "estimate",
    "remaining",
    "project",
    "cost_curve",
    "cost_curve_payment_delays",
    "earned_value_curves",
    "portfolio_workload",
    "portfolio_cost_structure",
    "portfolio_risks",
    "portfolio_milestones",
    "portfolio_offer_curves",
]
