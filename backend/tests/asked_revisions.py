# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/revisions.py`` ask for: the revisions and their structures.

``test_access_evaluation.py`` gathers them; US-0960 and US-0970 declare each operation they serve,
and US-0910/L2 the qualities on the project its evaluation asks for besides.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {}
