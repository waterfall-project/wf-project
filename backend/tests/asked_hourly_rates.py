# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/hourly_rates.py`` ask for: the hourly rates.

``test_access_evaluation.py`` gathers them; US-0830 declares each operation it serves.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {}
# The permission a list asks for besides when it asks for deactivated objects.
INACTIVE: dict[str, str] = {}
