# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/reference.py`` ask for: the minimal reference.

``test_access_evaluation.py`` gathers them; US-0810/L2 declares each operation it serves.
"""

# The permissions each operation asks for, in the order they are evaluated: the minimal reference
# is read by any session.
ASKED: dict[str, tuple[str, ...]] = {"getReferenceReadiness": ()}
# The permission a list asks for besides when it asks for deactivated objects.
INACTIVE: dict[str, str] = {}
