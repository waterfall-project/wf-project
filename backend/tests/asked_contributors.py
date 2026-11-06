# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/contributors.py`` ask for: the contributors of a project.

``test_access_evaluation.py`` gathers them; US-0930 declares each operation it serves, and
US-0910/L2 the qualities on the project its evaluation asks for besides.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {}
