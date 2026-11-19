# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operation of ``api/portfolio_pilot_health.py`` asks for (EP-11).

``test_access_evaluation.py`` gathers it; US-2750 declares the operation it serves. A view of the
portfolio names no project: it asks for no quality on one.
"""

# The permissions the operation asks for: the permission of its function in the catalogue alone.
ASKED: dict[str, tuple[str, ...]] = {}
