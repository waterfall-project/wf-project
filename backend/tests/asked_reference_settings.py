# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/reference_settings.py`` ask for: the settings shared.

``test_access_evaluation.py`` gathers them; US-0810/L2 declares each operation it serves.
"""

# The permissions each operation asks for, in the order they are evaluated. The settings are read
# by any session; their writing asks for no permission of its own, but one per field it carries.
ASKED: dict[str, tuple[str, ...]] = {
    "getReferenceSettings": (),
    "updateReferenceSettings": (),
}
# The permission a list asks for besides when it asks for deactivated objects.
INACTIVE: dict[str, str] = {}
# The permission each field of a writing asks for, in the order they are judged (WF-ADM-0100).
BY_FIELD: dict[str, dict[str, str]] = {
    "updateReferenceSettings": {
        "company_name": "cost_settings.write",
        "risk_matrix": "risk_settings.write",
        "index_thresholds": "indicator_settings.write",
        "max_weeks_between_reviews": "indicator_settings.write",
    }
}
