# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the revisions (FBS-4.1) offer to the API, the worker, the other modules and the witness.

One file per subject, each filled by the story that serves it and re-exported here. Every function
the design names (EP-04, "Modules") is declared from US-0910/L1 on, so that no story reopens this
file to fill its own: it raises ``NotImplementedError`` naming the story that fills it, but for the
few the design leaves silent. A name a story adds besides joins the import of its file, below the
comment that names it, in the order Ruff keeps. Another module imports them from here, never from
the file.

The later epics extend the revisions through eleven ordered registries, without this module
importing theirs: ``register_copy`` the copy of a revision opened from a marked one (EP-06 the
tasks and their links, EP-07 the lines and the rates, EP-08 the structures it adds),
``register_tasks_and_lines`` the questions the designation asks, the tasks (EP-06) and the lines
(EP-07), ``register_marking`` what a module keeps of a revision being marked (EP-07, the images
and the rates), ``register_indicators`` the indicators kept at the marking (EP-10),
``register_designation`` what follows the designation of a reference (EP-07, the budgeted amounts),
``register_merge`` the part of the planning and of the estimate in the merge of an amendment
(EP-08), and ``register_merge_end`` what is judged once all the parts are given (US-2560/L1),
``register_rebase`` and ``register_rebase_end`` the same for the update of a differential from the
main structure (US-3050/L3),
``register_rate_update`` whether the proposal of the rates of a revision presents a category
(EP-07), and ``register_closing`` what a module does before a revision is marked or abandoned,
under its stage (EP-06). Each registers its own by a call in the ``__init__`` of its module's
interface (``waterfall.core.<module>.interface``), at its import: that interface imports this one
first, so its copy comes after the structures', which this module registers itself, and after the
copies of the modules it imports, whose rows its rows name. A registry holds nothing for a module
its process never imported: the entry points that open or mark a revision — the API, the worker,
the loader of the witness — import the interface of each such module, by what they serve or
explicitly.
``RevisionCopy`` is what a copy receives.
"""

# ``commands`` (US-2550/L4): the conditions a structure that is not a differential to abandon, or
# not the main one, lacks.
from waterfall.core.revisions.commands import (
    MAIN_STRUCTURE,
    UNMERGED_AMENDMENT_EXISTS,
)

# ``bases`` (US-3050/L2): the base of a differential; the bases left out of a count, of a reading.
from waterfall.core.revisions.interface.bases import (
    base_differential,
    differential_base,
    differential_up_to_date,
    holds_its_lineages,
    not_a_base,
)

# ``closing`` (US-1380/L1): what the later modules do before a revision is marked or abandoned.
from waterfall.core.revisions.interface.closing import (
    CLOSING_STAGES,
    ClosingKind,
    ClosingStage,
    RevisionClosing,
    closers,
    register_closing,
)

# ``marking`` (US-0970; what EP-07 keeps, US-1490/L1, US-1500/L2; the indicators, EP-10).
from waterfall.core.revisions.interface.marking import (
    KEPT,
    MarkingRequest,
    RevisionMarking,
    compute_indicators,
    designated_at_marking,
    keep_project_ratios,
    load_marking,
    mark_revision,
    reference_at_marking,
    register_indicators,
    register_marking,
    run_marking,
    submit_marking,
)

# ``merge_applying`` (US-2560/L2): the merge applied, as a task of the worker, and for the witness.
from waterfall.core.revisions.interface.merge_applying import (
    MergeRequest,
    load_merge_at,
    run_merge,
    submit_merge,
)

# ``merging`` (US-2550/L1; US-2560): the parts of the modules in the merge of an amendment.
from waterfall.core.revisions.interface.merging import (
    MergePart,
    MergePartError,
    MergeReport,
    StructureMerging,
    merge_parts,
    merge_report,
    register_merge,
    register_merge_end,
)

# ``portfolio`` (US-2670/L1; US-2670/L3): the revisions of several projects the portfolio retains.
from waterfall.core.revisions.interface.portfolio import (
    RetainedRevisions,
    last_marked_at_instant,
    marked_revisions_of,
)

# ``rates`` (US-1500/L1): the update of the rates of a revision, as the revision frames it.
from waterfall.core.revisions.interface.rates import (
    RatesToUpdate,
    RevisionRating,
    rate_update_available,
    register_rate_update,
    revision_rating,
    update_rates,
)

# ``rebasing`` (US-3050/L3): the parts of the modules in the update of a differential.
from waterfall.core.revisions.interface.rebasing import (
    RebasePart,
    RebaseReport,
    StructureRebasing,
    rebase_parts,
    rebase_report,
    rebased_structure,
    rebasing_of,
    register_rebase,
    register_rebase_end,
)

# ``reference`` (US-0980/L2; what follows a designation, US-1490/L1): the reference revision.
from waterfall.core.revisions.interface.reference import (
    ReferenceDesignated,
    ReferenceToDesignate,
    RevisionPart,
    designate_reference,
    main_structure_has_task,
    reference_correctable,
    reference_history,
    register_designation,
    register_main_task_question,
    register_tasks_and_lines,
    revision_has_tasks_and_lines,
)

# ``revisions`` (US-0960; the partitions, US-0910/L1): the revisions of a project.
from waterfall.core.revisions.interface.revisions import (
    CopyImposed,
    RevisionAsked,
    RevisionCopy,
    RevisionFilters,
    RevisionList,
    RevisionPage,
    RevisionRead,
    RevisionStatus,
    RevisionToAbandon,
    RevisionView,
    abandon_revision,
    copy_revision,
    create_project_partitions,
    create_revision,
    current_revision,
    last_marked_revision,
    last_marked_revisions,
    list_revisions,
    load_revision,
    marked_revisions,
    marked_revisions_at,
    open_revision_by_task,
    read_revision,
    read_revision_for,
    reference_year_of,
    register_copy,
    revision_draft,
    revision_marked_at,
    revision_project,
    revision_version_names,
    revisions_present,
)

# ``shared`` (US-1500/L2): the current revision held before its project is locked.
from waterfall.core.revisions.interface.shared import MAIN, hold_current_revision

# ``structures`` (US-0960; the facts the planning reads, US-1380/L2; written, US-1390/L2).
from waterfall.core.revisions.interface.structures import (
    CurrentStructure,
    DifferentialName,
    OpenedDifferential,
    OwnEstimateCounted,
    StructureFacts,
    StructureView,
    abandon_structure,
    aimed_structure,
    consume_own_estimate,
    copy_consumed_estimate,
    create_differential,
    create_own_estimate,
    current_structures,
    delete_own_estimate,
    list_cost_structures,
    main_structures_of,
    read_cost_structure,
    register_own_estimate_counted,
    rename_own_estimate,
    rename_own_estimates,
    revision_structures,
    structure_commands,
    structure_counted,
    structure_counters,
    structure_facts,
    structure_in_revision,
    structure_phase_conditions,
    structure_rescheduled,
    write_structure,
)

__all__ = [
    "CLOSING_STAGES",
    "KEPT",
    "MAIN",
    "MAIN_STRUCTURE",
    "UNMERGED_AMENDMENT_EXISTS",
    "ClosingKind",
    "ClosingStage",
    "CopyImposed",
    "CurrentStructure",
    "DifferentialName",
    "MarkingRequest",
    "MergePart",
    "MergePartError",
    "MergeReport",
    "MergeRequest",
    "OpenedDifferential",
    "OwnEstimateCounted",
    "RatesToUpdate",
    "RebasePart",
    "RebaseReport",
    "ReferenceDesignated",
    "ReferenceToDesignate",
    "RetainedRevisions",
    "RevisionAsked",
    "RevisionClosing",
    "RevisionCopy",
    "RevisionFilters",
    "RevisionList",
    "RevisionMarking",
    "RevisionPage",
    "RevisionPart",
    "RevisionRating",
    "RevisionRead",
    "RevisionStatus",
    "RevisionToAbandon",
    "RevisionView",
    "StructureFacts",
    "StructureMerging",
    "StructureRebasing",
    "StructureView",
    "abandon_revision",
    "abandon_structure",
    "aimed_structure",
    "base_differential",
    "closers",
    "compute_indicators",
    "consume_own_estimate",
    "copy_consumed_estimate",
    "copy_revision",
    "create_differential",
    "create_own_estimate",
    "create_project_partitions",
    "create_revision",
    "current_revision",
    "current_structures",
    "delete_own_estimate",
    "designate_reference",
    "designated_at_marking",
    "differential_base",
    "differential_up_to_date",
    "hold_current_revision",
    "holds_its_lineages",
    "keep_project_ratios",
    "last_marked_at_instant",
    "last_marked_revision",
    "last_marked_revisions",
    "list_cost_structures",
    "list_revisions",
    "load_marking",
    "load_merge_at",
    "load_revision",
    "main_structure_has_task",
    "main_structures_of",
    "mark_revision",
    "marked_revisions",
    "marked_revisions_at",
    "marked_revisions_of",
    "merge_parts",
    "merge_report",
    "not_a_base",
    "open_revision_by_task",
    "rate_update_available",
    "read_cost_structure",
    "read_revision",
    "read_revision_for",
    "rebase_parts",
    "rebase_report",
    "rebased_structure",
    "rebasing_of",
    "reference_at_marking",
    "reference_correctable",
    "reference_history",
    "reference_year_of",
    "register_closing",
    "register_copy",
    "register_designation",
    "register_indicators",
    "register_main_task_question",
    "register_marking",
    "register_merge",
    "register_merge_end",
    "register_own_estimate_counted",
    "register_rate_update",
    "register_rebase",
    "register_rebase_end",
    "register_tasks_and_lines",
    "rename_own_estimate",
    "rename_own_estimates",
    "revision_draft",
    "revision_has_tasks_and_lines",
    "revision_marked_at",
    "revision_project",
    "revision_rating",
    "revision_structures",
    "revision_version_names",
    "revisions_present",
    "run_marking",
    "run_merge",
    "structure_commands",
    "structure_counted",
    "structure_counters",
    "structure_facts",
    "structure_in_revision",
    "structure_phase_conditions",
    "structure_rescheduled",
    "submit_marking",
    "submit_merge",
    "update_rates",
    "write_structure",
]
