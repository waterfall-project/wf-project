# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/actual_cost_mapping.py`` ask for: the mapping of the actual costs.

``test_access_evaluation.py`` gathers them; US-0870 declares each operation it serves.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {
    "getActualCostMapping": ("cost_settings.read",),
    "setActualCostMapping": ("cost_settings.write",),
}
# The permission a list asks for besides when it asks for deactivated objects.
INACTIVE: dict[str, str] = {}
