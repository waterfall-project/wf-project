# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the cost settings (FBS-3.1) offer to the API, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names
of a file are imported in a statement of their own, below the comment that names the file, so
that two stories filling two files write two places of this one. Another module imports them
from here, never from the file.
"""

# ``reference_settings`` (US-0810/L2): the settings the installation shares.

# ``readiness`` (US-0810/L2): the questions of the minimal reference this module answers.

# ``cost_types`` (US-0820): the natures of cost.
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeDraft as CostTypeDraft,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeFilters as CostTypeFilters,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypePage as CostTypePage,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeSort as CostTypeSort,
)
from waterfall.core.cost_settings.interface.cost_types import (
    CostTypeView as CostTypeView,
)
from waterfall.core.cost_settings.interface.cost_types import (
    Page as Page,
)
from waterfall.core.cost_settings.interface.cost_types import (
    create_cost_type as create_cost_type,
)
from waterfall.core.cost_settings.interface.cost_types import (
    list_cost_types as list_cost_types,
)
from waterfall.core.cost_settings.interface.cost_types import (
    present_cost_types as present_cost_types,
)
from waterfall.core.cost_settings.interface.cost_types import (
    set_cost_type_activation as set_cost_type_activation,
)
from waterfall.core.cost_settings.interface.cost_types import (
    update_cost_type as update_cost_type,
)

# ``cost_categories`` (US-0820): the categories of cost.

# ``hourly_rates`` (US-0830): the hourly rates of the categories of labour, by year.

# ``actual_cost_mapping`` (US-0870): the mapping of the extraction of the actual costs.
