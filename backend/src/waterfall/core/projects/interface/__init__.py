# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the projects (FBS-4.2, §3.3.2) offer to the API, the other modules and the witness.

One file per subject, each filled by the story that serves it and re-exported here. Every function
the design names (EP-04, "Modules") is declared from US-0910/L1 on, so that no story reopens this
file to fill its own: it raises ``NotImplementedError`` naming the story that fills it, but for the
few the design leaves silent. A name a story adds besides joins the import of its file, below the
comment that names it, in the order Ruff keeps. Another module imports them from here, never from
the file.
"""

# ``commands`` (US-0920; exported by US-1380/L5 and US-1480/L4): the states that end the cycle of
# life and those before In progress, the condition a terminal project lacks and the one a running
# background task takes away, which the other modules judge by these names, never a copy (#2555);
# the entries of the risks and the two conditions a declaration lacks, written here once for the
# revisions and the risks, which would else drift apart (#3996).
from waterfall.core.projects.commands import (
    ACTIVE_PROVISION_CATEGORY,
    AT_LEAST_ONE_TASK,
    BEFORE_IN_PROGRESS,
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_BEFORE_IN_PROGRESS,
    PROJECT_NOT_TERMINAL,
    RISK_ENTRIES,
    TERMINAL,
)

# ``attachments`` (US-1380/L1, filled by US-1380/L3): the tasks attached to the work breakdown.
from waterfall.core.projects.interface.attachments import (
    Attachments,
    detach_item,
    hold_items,
    item_cited,
    register_attachments,
    share_items,
)

# ``contributors`` (US-0930; the kind and the existence, US-0910/L2): a project's contributors.
from waterfall.core.projects.interface.contributors import (
    ContributorColumn,
    ContributorEntry,
    ContributorFilters,
    ContributorKind,
    ContributorsLoad,
    ContributorSort,
    ContributorsRead,
    ContributorsToWrite,
    ContributorSuggestion,
    ContributorView,
    contributor_kind,
    contributors_present,
    list_contributor_suggestions,
    list_contributors,
    load_contributors,
    project_exists,
    require_project_manager,
    set_contributors,
)

# ``days`` (US-1380/L4): the current day of an instant, in the time zone of the installation.
from waterfall.core.projects.interface.days import current_day

# ``estimate_facts`` (US-1490/L4): what the estimate tells of its lines, by its registry.
from waterfall.core.projects.interface.estimate_facts import (
    EstimatedLine,
    EstimateFacts,
    register_estimate_facts,
)

# ``inventory`` (US-2930/L1): how many projects a backup counts, which its test compares.
from waterfall.core.projects.interface.inventory import count_projects

# ``lifecycle`` (US-0980): the cycle of life of a project.
from waterfall.core.projects.interface.lifecycle import (
    DesignationFacts,
    ExitRequest,
    ExitState,
    LifecycleTrigger,
    NextState,
    RevisionFate,
    TransitionView,
    advance,
    exit_project,
    judge_exit_unlocked,
    list_state_transitions,
    lock_counter,
    lock_for_designation,
    next_state,
    no_background_task_running,
    read_next_state,
    set_reference_revision,
    stored_lock_version,
)

# ``portfolio`` (US-2670/L1; US-2670/L3): what the portfolio reads of several projects at once.
from waterfall.core.projects.interface.portfolio import (
    ClosedOffer,
    ProjectAtDate,
    offers_closed_between,
    openable,
    projects_in_states_on,
)

# ``projects`` (US-0920): the project, its commands, its names for the journal.
from waterfall.core.projects.interface.projects import (
    NOBODY,
    CommandAvailability,
    ProjectChange,
    ProjectColumn,
    ProjectDraft,
    ProjectFacts,
    ProjectFilters,
    ProjectList,
    ProjectLoad,
    ProjectPage,
    ProjectSort,
    ProjectState,
    ProjectView,
    Viewer,
    compared_code,
    create_project,
    first_project,
    list_projects,
    load_project,
    lock_project,
    project_code,
    project_commands,
    project_facts,
    project_label,
    projects_named,
    projects_present,
    read_project,
    set_current_revision,
    update_project,
)

# ``risk_designations`` (US-3060/L4, #4208): the subprojects the provisions of the risks designate.
from waterfall.core.projects.interface.risk_designations import (
    RiskDesignations,
    register_risk_designations,
)

# ``skeleton`` (US-1460, #2541): whether the main structure of the revision a project would open
# carries a task.
from waterfall.core.projects.interface.skeleton import (
    opening_main_with_tasks,
    register_opening_main_question,
)

# ``subprojects`` (US-0940; the facts of the actual costs, US-1610/L3): the subprojects of a
# project.
from waterfall.core.projects.interface.subprojects import (
    CostFacts,
    SubprojectChange,
    SubprojectColumn,
    SubprojectCommandAvailability,
    SubprojectDeletion,
    SubprojectFilters,
    SubprojectLoad,
    SubprojectSort,
    SubprojectView,
    SubprojectWrite,
    code_faults,
    create_subproject,
    delete_subproject,
    list_subprojects,
    load_subprojects,
    project_subproject_labels,
    register_cost_facts,
    subproject_has_actual_costs,
    subproject_ids,
    subproject_labels,
    subprojects_by_code,
    subprojects_coded,
    subprojects_named,
    subprojects_present,
    subprojects_with_actual_costs,
    update_subproject,
)

# ``work_breakdown`` (US-0950; the elements a task bears, US-1380/L3): the work breakdown.
from waterfall.core.projects.interface.work_breakdown import (
    BORN_LOCK_VERSION,
    DeliverableEntry,
    DeliverableView,
    OrderItemEntry,
    OrderItemView,
    WorkBreakdownFilters,
    WorkBreakdownItem,
    WorkBreakdownLoad,
    WorkBreakdownRead,
    WorkBreakdownToWrite,
    WorkPackageEntry,
    WorkPackageView,
    load_work_breakdown,
    read_work_breakdown,
    set_work_breakdown,
    work_breakdown_items,
    work_breakdown_present,
)

# ``tables`` (US-3270/L2, BPR-09): the bound of the code of a subproject, which the API reads here
# rather than in the private tables.
from waterfall.core.projects.tables import SUBPROJECT_CODE_LENGTH

__all__ = [
    "ACTIVE_PROVISION_CATEGORY",
    "AT_LEAST_ONE_TASK",
    "BEFORE_IN_PROGRESS",
    "BORN_LOCK_VERSION",
    "NOBODY",
    "NO_BACKGROUND_TASK_RUNNING",
    "PROJECT_BEFORE_IN_PROGRESS",
    "PROJECT_NOT_TERMINAL",
    "RISK_ENTRIES",
    "SUBPROJECT_CODE_LENGTH",
    "TERMINAL",
    "Attachments",
    "ClosedOffer",
    "CommandAvailability",
    "ContributorColumn",
    "ContributorEntry",
    "ContributorFilters",
    "ContributorKind",
    "ContributorSort",
    "ContributorSuggestion",
    "ContributorView",
    "ContributorsLoad",
    "ContributorsRead",
    "ContributorsToWrite",
    "CostFacts",
    "DeliverableEntry",
    "DeliverableView",
    "DesignationFacts",
    "EstimateFacts",
    "EstimatedLine",
    "ExitRequest",
    "ExitState",
    "LifecycleTrigger",
    "NextState",
    "OrderItemEntry",
    "OrderItemView",
    "ProjectAtDate",
    "ProjectChange",
    "ProjectColumn",
    "ProjectDraft",
    "ProjectFacts",
    "ProjectFilters",
    "ProjectList",
    "ProjectLoad",
    "ProjectPage",
    "ProjectSort",
    "ProjectState",
    "ProjectView",
    "RevisionFate",
    "RiskDesignations",
    "SubprojectChange",
    "SubprojectColumn",
    "SubprojectCommandAvailability",
    "SubprojectDeletion",
    "SubprojectFilters",
    "SubprojectLoad",
    "SubprojectSort",
    "SubprojectView",
    "SubprojectWrite",
    "TransitionView",
    "Viewer",
    "WorkBreakdownFilters",
    "WorkBreakdownItem",
    "WorkBreakdownLoad",
    "WorkBreakdownRead",
    "WorkBreakdownToWrite",
    "WorkPackageEntry",
    "WorkPackageView",
    "advance",
    "code_faults",
    "compared_code",
    "contributor_kind",
    "contributors_present",
    "count_projects",
    "create_project",
    "create_subproject",
    "current_day",
    "delete_subproject",
    "detach_item",
    "exit_project",
    "first_project",
    "hold_items",
    "item_cited",
    "judge_exit_unlocked",
    "list_contributor_suggestions",
    "list_contributors",
    "list_projects",
    "list_state_transitions",
    "list_subprojects",
    "load_contributors",
    "load_project",
    "load_subprojects",
    "load_work_breakdown",
    "lock_counter",
    "lock_for_designation",
    "lock_project",
    "next_state",
    "no_background_task_running",
    "offers_closed_between",
    "openable",
    "opening_main_with_tasks",
    "project_code",
    "project_commands",
    "project_exists",
    "project_facts",
    "project_label",
    "project_subproject_labels",
    "projects_in_states_on",
    "projects_named",
    "projects_present",
    "read_next_state",
    "read_project",
    "read_work_breakdown",
    "register_attachments",
    "register_cost_facts",
    "register_estimate_facts",
    "register_opening_main_question",
    "register_risk_designations",
    "require_project_manager",
    "set_contributors",
    "set_current_revision",
    "set_reference_revision",
    "set_work_breakdown",
    "share_items",
    "stored_lock_version",
    "subproject_has_actual_costs",
    "subproject_ids",
    "subproject_labels",
    "subprojects_by_code",
    "subprojects_coded",
    "subprojects_named",
    "subprojects_present",
    "subprojects_with_actual_costs",
    "update_project",
    "update_subproject",
    "work_breakdown_items",
    "work_breakdown_present",
]
