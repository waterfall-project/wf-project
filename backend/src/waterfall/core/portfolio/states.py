# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The states of the cycle of life the portfolio tells apart, named once (EP-11).

A leaf of ``core/portfolio``: the rows, the documents, the scope and the views all read these names,
none of them imports another to have them. The set of states is that of ``core/projects``
(``ProjectState``), which offers no name for each.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from waterfall.core.projects.interface import ProjectState

PRICING: ProjectState = "pricing"
IN_PROGRESS: ProjectState = "in_progress"
COMPLETED: ProjectState = "completed"
