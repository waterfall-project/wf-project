# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/projects.py`` ask for: the projects.

``test_access_evaluation.py`` gathers them; US-0920/L1 declares each operation it serves,
with the quality on its project each asks for besides (``ON_PROJECT``, declared by US-0910/L2).
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation`` — its contributor, or holding ``all_projects_read`` —,
# ``contributor``, the quality a write asks for, or ``project_manager`` (WF-ADM-0110, WF-PRJ-0060).
ON_PROJECT: dict[str, str] = {}
