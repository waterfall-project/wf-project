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
    set_contributors,
)

# ``lifecycle`` (US-0980): the cycle of life of a project.
from waterfall.core.projects.interface.lifecycle import (
    ExitRequest,
    ExitState,
    LifecycleTrigger,
    NextState,
    RevisionFate,
    TransitionView,
    advance,
    exit_project,
    list_state_transitions,
    load_transitions,
    next_state,
    read_next_state,
)

# ``projects`` (US-0920): the project, its commands, its names for the journal.
from waterfall.core.projects.interface.projects import (
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
    create_project,
    list_projects,
    load_project,
    lock_project,
    missing_prerequisites,
    no_background_task_running,
    project_code,
    project_commands,
    project_facts,
    project_label,
    projects_present,
    read_project,
    set_current_revision,
    update_project,
)

# ``subprojects`` (US-0940): the subprojects of a project.
from waterfall.core.projects.interface.subprojects import (
    create_subproject,
    delete_subproject,
    list_subprojects,
    load_subprojects,
    update_subproject,
)

# ``work_breakdown`` (US-0950): the work breakdown of a project.
from waterfall.core.projects.interface.work_breakdown import (
    load_work_breakdown,
    read_work_breakdown,
    set_work_breakdown,
)

__all__ = [
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
    "ExitRequest",
    "ExitState",
    "LifecycleTrigger",
    "NextState",
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
    "TransitionView",
    "Viewer",
    "advance",
    "contributor_kind",
    "contributors_present",
    "create_project",
    "create_subproject",
    "delete_subproject",
    "exit_project",
    "list_contributor_suggestions",
    "list_contributors",
    "list_projects",
    "list_state_transitions",
    "list_subprojects",
    "load_contributors",
    "load_project",
    "load_subprojects",
    "load_transitions",
    "load_work_breakdown",
    "lock_project",
    "missing_prerequisites",
    "next_state",
    "no_background_task_running",
    "project_code",
    "project_commands",
    "project_exists",
    "project_facts",
    "project_label",
    "projects_present",
    "read_next_state",
    "read_project",
    "read_work_breakdown",
    "set_contributors",
    "set_current_revision",
    "set_work_breakdown",
    "update_project",
    "update_subproject",
]
