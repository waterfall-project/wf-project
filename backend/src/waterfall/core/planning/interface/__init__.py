# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning (FBS-4.3) offers to the API, the worker, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names of a
file are imported in a statement of their own, below the comment that names the file, so that two
stories filling two files write two places of this one. Another module imports them from here,
never from the file; the engine (``scheduling``, US-1390/L1) is a subpackage of its own.

The planning fills, at the import of this interface, the registries of the modules below it
(EP-06, "Les points d'extension"): the copy of a revision and the question of its tasks (the
revisions), the guard of the idle tasks and the recalculation (the resource settings), the tasks
attached to the work breakdown (the projects). The entry points that copy, designate, close a
revision or change the reference — the API, the worker, the loader of the witness — import it,
by what they serve or explicitly (#2180).
"""

# ``facets`` (US-1380/L1; read by US-1380/L2): the facets of a node other than the task (EP-07).
from waterfall.core.planning.interface.facets import (
    FacetHooks as FacetHooks,
)
from waterfall.core.planning.interface.facets import (
    facets as facets,
)
from waterfall.core.planning.interface.facets import (
    register_facet as register_facet,
)

# ``nodes`` (US-1380/L1; US-1380/L2, L3): the nodes of a structure.
from waterfall.core.planning.interface.nodes import (
    copy_nodes as copy_nodes,
)
from waterfall.core.planning.interface.nodes import (
    revision_has_tasks as revision_has_tasks,
)

# ``reference`` (US-1380/L1; US-1390/L2): what the planning answers to the reference.
from waterfall.core.planning.interface.reference import (
    reschedule_current_structures as reschedule_current_structures,
)
from waterfall.core.planning.interface.reference import (
    tasks_left_idle as tasks_left_idle,
)

# ``work_breakdown`` (US-1380/L1; US-1380/L3): the tasks attached to the work breakdown.
from waterfall.core.planning.interface.work_breakdown import (
    detach_work_breakdown_item as detach_work_breakdown_item,
)
from waterfall.core.planning.interface.work_breakdown import (
    work_breakdown_item_cited as work_breakdown_item_cited,
)

# The registries the planning fills.
from waterfall.core.projects.interface import Attachments, register_attachments
from waterfall.core.resource_settings.interface import (
    register_idle_task_guard,
    register_recalculation,
)
from waterfall.core.revisions.interface import register_copy, register_tasks_and_lines

# The registrations, once, at the import: the copy of the nodes after the structures', whose
# module this one imports first.
register_copy(copy_nodes)
register_tasks_and_lines(revision_has_tasks)
register_idle_task_guard(tasks_left_idle)
register_recalculation(reschedule_current_structures)
register_attachments(Attachments(work_breakdown_item_cited, detach_work_breakdown_item))
