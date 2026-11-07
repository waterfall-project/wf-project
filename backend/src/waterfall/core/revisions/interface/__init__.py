# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the revisions (FBS-4.1) offer to the API, the worker, the other modules and the witness.

One file per subject, each filled by the story that serves it and re-exported here. Every function
the design names (EP-04, "Modules") is declared from US-0910/L1 on, so that no story reopens this
file to fill its own: it raises ``NotImplementedError`` naming the story that fills it, but for the
few the design leaves silent. A name a story adds besides joins the import of its file, below the
comment that names it, in the order Ruff keeps. Another module imports them from here, never from
the file.

The later epics extend the revisions through three ordered registries, without this module
importing theirs: ``register_copy`` the copy of a revision opened from a marked one (EP-06 the
tasks and their links, EP-07 the lines and the images, EP-08 the structures it adds),
``register_tasks_and_lines`` the question the designation asks (EP-06, EP-07), and
``register_indicators`` the indicators kept at the marking (EP-10). Each registers its own by a
call in the ``__init__`` of its module's interface (``waterfall.core.<module>.interface``), at its
import: that interface imports this one first, so its copy comes after the structures', which this
module registers itself, and after the copies of the modules it imports, whose rows its rows name.
A registry holds nothing for a module its process never imported: the entry points that open or
mark a revision — the API, the worker, the loader of the witness — import the interface of each
such module, by what they serve or explicitly. ``RevisionCopy`` is what a copy receives.
"""

# ``marking`` (US-0970; the indicators, EP-10): the marking of a revision.
from waterfall.core.revisions.interface.marking import (
    KEPT,
    MarkingRequest,
    compute_indicators,
    load_marking,
    mark_revision,
    register_indicators,
    run_marking,
    submit_marking,
)

# ``reference`` (US-0980/L2): the reference revision of a project.
from waterfall.core.revisions.interface.reference import (
    designate_reference,
    reference_correctable,
    register_tasks_and_lines,
    revision_has_tasks_and_lines,
)

# ``revisions`` (US-0960; the partitions, US-0910/L1): the revisions of a project.
from waterfall.core.revisions.interface.revisions import (
    RevisionCopy,
    RevisionFilters,
    RevisionList,
    RevisionPage,
    RevisionStatus,
    RevisionView,
    abandon_revision,
    copy_revision,
    create_project_partitions,
    create_revision,
    current_revision,
    list_revisions,
    load_revision,
    read_revision,
    register_copy,
    revision_draft,
    revisions_present,
)

# ``structures`` (US-0960): the cost structures of a revision.
from waterfall.core.revisions.interface.structures import (
    StructureView,
    list_cost_structures,
    load_cost_structures,
    structure_commands,
)

__all__ = [
    "KEPT",
    "MarkingRequest",
    "RevisionCopy",
    "RevisionFilters",
    "RevisionList",
    "RevisionPage",
    "RevisionStatus",
    "RevisionView",
    "StructureView",
    "abandon_revision",
    "compute_indicators",
    "copy_revision",
    "create_project_partitions",
    "create_revision",
    "current_revision",
    "designate_reference",
    "list_cost_structures",
    "list_revisions",
    "load_cost_structures",
    "load_marking",
    "load_revision",
    "mark_revision",
    "read_revision",
    "reference_correctable",
    "register_copy",
    "register_indicators",
    "register_tasks_and_lines",
    "revision_draft",
    "revision_has_tasks_and_lines",
    "revisions_present",
    "run_marking",
    "structure_commands",
    "submit_marking",
]
