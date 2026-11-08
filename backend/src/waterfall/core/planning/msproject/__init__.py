# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A planning of MS Project in MSPDI: its model, its reader and its writer (US-1430/L1).

Pure: bytes in, a model out, and back, without a database, a setting or a clock (WF-QUA-0080).
The format and the exporter of ``interface/msproject.py`` (US-1430/L3, L4) read and write through
them, the reader by the hardened parser of the exchanges. The names are imported from here, never
from the file that defines them.
"""

# ``model``: the planning in memory, what it carried besides, and the refusal of a file.
from waterfall.core.planning.msproject.model import (
    LINEAGE_ALIAS as LINEAGE_ALIAS,
)
from waterfall.core.planning.msproject.model import (
    ConstraintType as ConstraintType,
)
from waterfall.core.planning.msproject.model import (
    Ignored as Ignored,
)
from waterfall.core.planning.msproject.model import (
    IgnoredKind as IgnoredKind,
)
from waterfall.core.planning.msproject.model import (
    MsCalendar as MsCalendar,
)
from waterfall.core.planning.msproject.model import (
    MsProject as MsProject,
)
from waterfall.core.planning.msproject.model import (
    MsTask as MsTask,
)
from waterfall.core.planning.msproject.model import (
    PredecessorLink as PredecessorLink,
)
from waterfall.core.planning.msproject.model import (
    ReadProject as ReadProject,
)
from waterfall.core.planning.msproject.model import (
    UnreadableProjectError as UnreadableProjectError,
)
from waterfall.core.planning.msproject.model import (
    WorkingDay as WorkingDay,
)

# ``reader``: an MSPDI file into the model.
from waterfall.core.planning.msproject.reader import (
    read_project as read_project,
)

# ``translation`` (US-1430/L3): a planning of the file in the hours, units and instants of work.
from waterfall.core.planning.msproject.translation import (
    FileCalendar as FileCalendar,
)
from waterfall.core.planning.msproject.translation import (
    calendar_of as calendar_of,
)
from waterfall.core.planning.msproject.translation import (
    calendars_of as calendars_of,
)
from waterfall.core.planning.msproject.translation import (
    constants_of as constants_of,
)
from waterfall.core.planning.msproject.translation import (
    duration_of as duration_of,
)
from waterfall.core.planning.msproject.translation import (
    hours_of as hours_of,
)
from waterfall.core.planning.msproject.translation import (
    lag_of as lag_of,
)

# ``tree``: the namespaces of MSPDI.
from waterfall.core.planning.msproject.tree import (
    NAMESPACE as NAMESPACE,
)
from waterfall.core.planning.msproject.tree import (
    NAMESPACES as NAMESPACES,
)

# ``writer``: the model into an MSPDI file, in the order of the schema.
from waterfall.core.planning.msproject.writer import (
    write_project as write_project,
)
