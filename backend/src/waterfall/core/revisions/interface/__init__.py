# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the revisions (FBS-4.1) offer to the API, the worker, the other modules and the witness.

One file per subject, each filled by the story that serves it and re-exported here. Every function
the design names (EP-04, "Modules") is declared from US-0910/L1 on, so that no story reopens this
file to fill its own: it raises ``NotImplementedError`` naming the story that fills it, but for the
few the design leaves silent. A name a story adds besides is imported in a statement of its own,
below the comment that names its file. Another module imports them from here, never from the
file.
"""

# ``marking`` (US-0970; the indicators, EP-10): the marking of a revision.
from waterfall.core.revisions.interface.marking import (
    compute_indicators,
    load_marking,
    mark_revision,
)

# ``reference`` (US-0980/L2): the reference revision of a project.
from waterfall.core.revisions.interface.reference import (
    designate_reference,
    revision_has_tasks_and_lines,
)

# ``revisions`` (US-0960; the partitions, US-0910/L1): the revisions of a project.
from waterfall.core.revisions.interface.revisions import (
    RevisionStatus,
    abandon_revision,
    copy_revision,
    create_project_partitions,
    create_revision,
    current_revision,
    list_revisions,
    load_revision,
    read_revision,
    revision_draft,
)

# ``structures`` (US-0960): the cost structures of a revision.
from waterfall.core.revisions.interface.structures import (
    list_cost_structures,
    load_cost_structures,
    structure_commands,
)

__all__ = [
    "RevisionStatus",
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
    "revision_draft",
    "revision_has_tasks_and_lines",
    "structure_commands",
]
