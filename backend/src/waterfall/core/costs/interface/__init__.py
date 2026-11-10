# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the actual costs (FBS-4.7) offer to the API, the worker, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Every function the design names (EP-09,
"Modules") is declared from US-1580/L1 on: it raises ``NotImplementedError`` naming the story that
fills it, but for the format a registry calls before, without effect until then. A name a story
adds besides joins the import of its file, below the comment that names it. Another module imports
them from here, never from the file.

The actual costs fill, at the import of this interface, the registry of the formats of the
exchanges: the format ``actual_costs``, registered by the socle, which reads and analyses an
extraction from US-1610/L1 and applies it from US-1610/L2. US-1610/L3 declares
``register_cost_facts`` in the interface of the projects and registers there what they ask of a
subproject. The entry points that run an import of the actual costs, or load the witness — the API,
the loader of the witness, and the worker from US-1610/L2 on (EP-09, "Le worker") — import it
(#2180).
"""

# ``actual_costs`` (US-1580/L1; US-1610/L1, US-1610/L2): the format of an extraction of the ERP.
from waterfall.core.costs.interface.actual_costs import (
    ACTUAL_COSTS_FORMAT as ACTUAL_COSTS_FORMAT,
)
from waterfall.core.costs.interface.actual_costs import (
    ActualCostsFormat as ActualCostsFormat,
)

# ``cost_imports`` (US-1580/L1; US-1610/L2, US-1610/L3): the log of the imports.
from waterfall.core.costs.interface.cost_imports import (
    list_cost_imports as list_cost_imports,
)
from waterfall.core.costs.interface.cost_imports import (
    load_cost_import as load_cost_import,
)

# ``cost_lines`` (US-1580/L1; US-1620/L1, US-1610/L3): the lines read, excluded, loaded.
from waterfall.core.costs.interface.cost_lines import (
    list_actual_costs as list_actual_costs,
)
from waterfall.core.costs.interface.cost_lines import (
    load_cost_lines as load_cost_lines,
)
from waterfall.core.costs.interface.cost_lines import (
    load_exclusion as load_exclusion,
)
from waterfall.core.costs.interface.cost_lines import (
    set_tracked_scope as set_tracked_scope,
)

# ``subprojects`` (US-1580/L1; US-1610/L3): what the projects ask the actual costs of a subproject.
from waterfall.core.costs.interface.subprojects import (
    impute_waiting_lines as impute_waiting_lines,
)
from waterfall.core.costs.interface.subprojects import (
    subproject_has_actual_costs as subproject_has_actual_costs,
)

# ``tracked_costs`` (US-1580/L1; US-1600, US-1610/L2): the sums of the tracked lines, which the
# indicators read (EP-09, EP-10).
from waterfall.core.costs.interface.tracked_costs import (
    PROJECT as PROJECT,
)
from waterfall.core.costs.interface.tracked_costs import (
    UNASSIGNED as UNASSIGNED,
)
from waterfall.core.costs.interface.tracked_costs import (
    CostKey as CostKey,
)
from waterfall.core.costs.interface.tracked_costs import (
    CostScope as CostScope,
)
from waterfall.core.costs.interface.tracked_costs import (
    actual_cost_by_subproject as actual_cost_by_subproject,
)
from waterfall.core.costs.interface.tracked_costs import (
    actual_costs_until as actual_costs_until,
)

# The registry the actual costs fill.
from waterfall.core.exchanges.interface import register_format

# The registration, once, at the import: the format of an extraction.
register_format("actual_costs", ACTUAL_COSTS_FORMAT)
