# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/subprojects.py`` ask for: the subprojects of a project.

``test_access_evaluation.py`` gathers them; US-0940 declares each operation it serves, and
US-0910/L2 the qualities on the project its evaluation asks for besides.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {}
