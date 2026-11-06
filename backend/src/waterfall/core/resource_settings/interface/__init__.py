# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the resource settings (FBS-3.2) offer to the API, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names
of a file are imported in a statement of their own, below the comment that names the file, so
that two stories filling two files write two places of this one. Another module imports them
from here, never from the file.
"""

# ``readiness`` (US-0810/L2): the questions of the minimal reference this module answers.

# ``org_nodes`` (US-0840): the tree of the organisation.
from waterfall.core.resource_settings.interface.org_nodes import (
    ACTIVE_ONLY as ACTIVE_ONLY,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeCommand as NodeCommand,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeFilters as NodeFilters,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeView as NodeView,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeWrite as NodeWrite,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    create_node as create_node,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    label_of as label_of,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    list_nodes as list_nodes,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    node_is_active as node_is_active,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    node_label as node_label,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    node_labels as node_labels,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    read_node as read_node,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    set_activation as set_activation,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    update_node as update_node,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    within_node as within_node,
)

# ``resource_roles`` (US-0850): the roles of resources and their capacity.

# ``calendars`` (US-0860): the calendars, one of them the default.

# ``duration_units`` (US-0860): the units of duration.
