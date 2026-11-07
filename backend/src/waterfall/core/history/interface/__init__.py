# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the history (WF-IHM-0110, WF-IHM-0050) offers to the API, the worker and the planning.

One file per subject, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-06,
"Modules") is declared from US-1380/L1 on: it raises ``NotImplementedError`` naming the story that
fills it, but for those a caller relies on before (``close_history``, ``purge``), without effect
until then. Another module imports them from here, never from the file.

The history registers, at the import of this interface, what it does before a revision closes
(``close_history`` in ``register_closing``), under the stage ``history``: the stacks and the plans
go before the nodes of the planning, whatever the order in which a process imports the modules.
"""

# ``closing`` (US-1380/L1; US-1450/L1): the stacks and the plans of a revision that closes.
from waterfall.core.history.interface.closing import (
    close_history as close_history,
)

# ``plans`` (US-1380/L1; US-1450/L1): the plans of a paste.
from waterfall.core.history.interface.plans import (
    drop_plan as drop_plan,
)
from waterfall.core.history.interface.plans import (
    keep_plan as keep_plan,
)
from waterfall.core.history.interface.plans import (
    read_plan as read_plan,
)

# ``purge`` (US-1380/L1; US-1450/L1): the purge of the history.
from waterfall.core.history.interface.purge import (
    purge as purge,
)

# ``recording`` (US-1380/L1; US-1450/L1): the entries, one per entry of the planning.
from waterfall.core.history.interface.recording import (
    RecordedChange as RecordedChange,
)
from waterfall.core.history.interface.recording import (
    UndoneKind as UndoneKind,
)
from waterfall.core.history.interface.recording import (
    UndoStack as UndoStack,
)
from waterfall.core.history.interface.recording import (
    recording as recording,
)

# ``undo`` (US-1380/L1; US-1450/L1): the undoing, the redoing and the depth of a stack.
from waterfall.core.history.interface.undo import (
    depth as depth,
)
from waterfall.core.history.interface.undo import (
    redo as redo,
)
from waterfall.core.history.interface.undo import (
    undo as undo,
)

# The registry the history fills.
from waterfall.core.revisions.interface import register_closing

# The registration, once, at the import: its stage runs before the content of the revision.
register_closing("history", close_history)
