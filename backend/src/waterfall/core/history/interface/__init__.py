# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the history (WF-IHM-0110, WF-IHM-0050) offers to the API, the worker and the planning.

One file per subject, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Another module imports them from here,
never from the file. The history registers, at the import of this interface, what it does before
a revision closes (``close_history`` in ``register_closing``, US-1450/L1).
"""

# ``purge`` (US-1380/L1; US-1450/L1): the purge of the history.
from waterfall.core.history.interface.purge import (
    purge as purge,
)
