# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The predecessors of a task: its links replaced, the engine replayed (``setPredecessors``).

The links of a task to its predecessors are replaced at once, refused when they would make a loop
(``LINK_CYCLE``, the shortest chain named), link a summary task to its subordinate
(``LINK_FORBIDDEN``) or carry the end of the project beyond fifteen years
(``PROJECT_HORIZON_EXCEEDED``) (EP-06, US-1390).

Declared by US-1380/L1; US-1390/L2 fills it, and gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def set_predecessors(session: Session, project_id: UUID, node_id: UUID, act: Act) -> None:
    """Replace the predecessors of a task, and give the nodes written."""
    msg = "set_predecessors is filled by US-1390/L2"
    raise NotImplementedError(msg)
