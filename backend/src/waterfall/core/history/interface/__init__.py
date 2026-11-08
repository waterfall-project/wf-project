# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the history (WF-IHM-0110, WF-IHM-0050) offers to the API, the worker and the planning.

One file per subject, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-06,
"Modules") is declared from US-1380/L1 on, and filled by US-1450/L1; the types of a snapshot live
beside the interface (``snapshots``), which ``recording`` and ``undo`` share. Another module imports
them from here, never from the file.

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
    PLAN_LIFETIME as PLAN_LIFETIME,
)
from waterfall.core.history.interface.plans import (
    KeptPlan as KeptPlan,
)
from waterfall.core.history.interface.plans import (
    NodeColumn as NodeColumn,
)
from waterfall.core.history.interface.plans import (
    PlanToKeep as PlanToKeep,
)
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
    Recording as Recording,
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
    REDO_HISTORY_NOT_EMPTY as REDO_HISTORY_NOT_EMPTY,
)
from waterfall.core.history.interface.undo import (
    UNDO_CONFLICT as UNDO_CONFLICT,
)
from waterfall.core.history.interface.undo import (
    UNDO_HISTORY_NOT_EMPTY as UNDO_HISTORY_NOT_EMPTY,
)
from waterfall.core.history.interface.undo import (
    Depth as Depth,
)
from waterfall.core.history.interface.undo import (
    Restoring as Restoring,
)
from waterfall.core.history.interface.undo import (
    SnapshotReader as SnapshotReader,
)
from waterfall.core.history.interface.undo import (
    StructureLocker as StructureLocker,
)
from waterfall.core.history.interface.undo import (
    depth as depth,
)
from waterfall.core.history.interface.undo import (
    redo as redo,
)
from waterfall.core.history.interface.undo import (
    undo as undo,
)

# ``snapshots``, beside the interface (US-1450/L1): the snapshots the planning hands the history.
from waterfall.core.history.snapshots import (
    JsonValue as JsonValue,
)
from waterfall.core.history.snapshots import (
    ObjectState as ObjectState,
)
from waterfall.core.history.snapshots import (
    Snapshot as Snapshot,
)

# The registry the history fills.
from waterfall.core.revisions.interface import register_closing

# The registration, once, at the import: its stage runs before the content of the revision.
register_closing("history", close_history)
