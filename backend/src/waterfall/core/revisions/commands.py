# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of a revision and of its structures, and the conditions each lacks (WF-IHM-0090).

Private to the module. One computation serves the list a revision or a structure carries
(``available_commands``) and the 409 of an operation sent in spite of it, so that a command said
unavailable and the call refused name the same condition. A command is listed to the caller who
holds its permission; the quality it asks on the project comes first among the conditions it
lacks (``is_contributor``, then ``is_project_manager`` for an action of its own permission,
WF-ADM-0100, WF-PRJ-0060), then the conditions of the phase of the project, then those of the
revision. A terminal project lists none: its revisions are all marked, and nothing modifies them
any more (WF-CYC-0100); their exports are the exception, and lack no condition (WF-CYC-0110).

This module knows the commands of EP-04 — the entries of a revision and of its structures, its
marking, its designation and its abandonment —; the later epics add theirs to ``REVISION_RULES``
in the order of ``RevisionCommand`` (the skeleton, the risks, the amendments, the update of the
rates — US-1500 —), with their conditions, and the exports to ``EXPORT_RULES``.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.projects.interface import (
    BEFORE_IN_PROGRESS,
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_BEFORE_IN_PROGRESS,
    PROJECT_NOT_TERMINAL,
    TERMINAL,
)

if TYPE_CHECKING:
    from collections.abc import Collection

IS_CONTRIBUTOR = "is_contributor"
IS_PROJECT_MANAGER = "is_project_manager"
PROJECT_IN_PROGRESS = "project_in_progress"
NO_CURRENT_REVISION = "no_current_revision"
REVISION_DRAFT = "revision_draft"
MAIN_STRUCTURE_WITHOUT_TASKS = "main_structure_without_tasks"
AT_LEAST_ONE_TASK = "at_least_one_task"
ACTIVE_PROVISION_CATEGORY = "active_provision_category"
REVISION_MARKED = "revision_marked"
REVISION_HAS_TASKS_AND_LINES = "revision_has_tasks_and_lines"
REFERENCE_CORRECTABLE = "reference_correctable"
RATE_UPDATE_AVAILABLE = "rate_update_available"
UNMERGED_AMENDMENT_EXISTS = "unmerged_amendment_exists"
MAY_CREATE_REVISION = "may_create_revision"


@dataclass(frozen=True, slots=True)
class Rule:
    """A command: the permission that guards it, and whether it is reserved to the managers."""

    command: str
    permission: str
    manager: bool = False


RISK_ENTRIES = ("edit_risks", "declare_risk")

# In the order of ``RevisionCommand``. The marking, the designation and the abandonment have a
# permission of their own, structuring actions reserved to the project managers (WF-ADM-0100).
REVISION_RULES: tuple[Rule, ...] = (
    Rule("edit_planning", "planning.write"),
    Rule("generate_skeleton", "planning.write"),
    Rule("edit_estimate", "estimate.write"),
    Rule("edit_remaining", "remaining.write"),
    # The entry of the risks and the declaration of one, listed on a revision in progress
    # alone: a marked revision is immutable, and carries neither (WF-DAT-0020).
    Rule("edit_risks", "risks.write"),
    Rule("declare_risk", "risks.write"),
    # The opening of a differential (WF-REV-0100): a write of the revision, guarded as its rate
    # update and its creation are, by the management of the revisions, and lacking the conditions
    # of the state of the revision alone (``createCostStructure``).
    Rule("create_structure", "revisions.write"),
    # A write of the revision, guarded by the permission to manage the revisions, that of
    # ``createRevision``, which applies it at the creation (WF-REV-0060; US-1500).
    Rule("apply_rate_update", "revisions.write"),
    Rule("mark", "revision_mark", manager=True),
    Rule("designate_reference", "reference_designate", manager=True),
    Rule("abandon", "revision_abandon", manager=True),
)
# The exports, listed after the other commands as ``RevisionCommand`` orders them: a matter of
# consultation, each guarded by the permission to view the function of its kind, lacking no
# condition (WF-CYC-0110). The planning's and the tree image's (US-1440) are here, the estimate's
# (US-1550) and the remaining to commit's (US-1630) between them as ``RevisionCommand`` orders
# them.
EXPORT_RULES: tuple[Rule, ...] = (
    Rule("export_planning", "planning.read"),
    Rule("export_estimate", "estimate.read"),
    Rule("export_remaining", "remaining.read"),
    Rule("export_task_tree_image", "planning.read"),
)
# In the order of ``StructureCommand``: each guarded by the permission of the command of the same
# name of the revision.
STRUCTURE_RULES: tuple[Rule, ...] = (
    Rule("edit_planning", "planning.write"),
    Rule("edit_estimate", "estimate.write"),
    Rule("edit_remaining", "remaining.write"),
)


@dataclass(frozen=True, slots=True)
class RevisionState:
    """What the conditions of a revision read: its status, its facts, its project's.

    ``rate_update_available`` whether its proposal of rates presents a category (US-1500), judged
    on a current revision alone; ``provision_category_active`` whether an active category of the
    provision kind exists, which the declaration of a risk asks (WF-RIS-0010), read for a revision
    in progress alone.
    """

    marked: bool
    no_task_running: bool
    has_tasks_and_lines: bool
    reference_correctable: bool
    has_main_task: bool = False
    rate_update_available: bool = False
    provision_category_active: bool = True


def quality_conditions(kind: str | None, *, manager: bool) -> list[str]:
    """Name the quality on the project that the caller lacks for a command, if it does."""
    if kind is None:
        return [IS_CONTRIBUTOR, IS_PROJECT_MANAGER] if manager else [IS_CONTRIBUTOR]
    if manager and kind != "project_manager":
        return [IS_PROJECT_MANAGER]
    return []


def revision_conditions(command: str, revision: RevisionState) -> list[str]:
    """Name the conditions of the revision a command lacks, in the order the contract lists them.

    A marked revision lacks ``revision_draft`` alone for what would modify it; the designation,
    which asks it marked, lacks ``revision_marked`` on the current one, then what it asks of it:
    tasks and lines, a designation still correctable, no background task (WF-CYC-0030, WF-REV-0040).
    The skeleton lacks, on a draft, a main structure without tasks before the background task; the
    update of the rates, a proposal that presents a category (WF-REV-0060, #1351). The declaration
    of a risk lacks, in the order ``createRisk`` judges them, the background task, a main
    structure without a task, then no active category of provision (WF-RIS-0010).
    """
    if command == "designate_reference":
        missing = [] if revision.marked else [REVISION_MARKED]
        if not revision.has_tasks_and_lines:
            missing.append(REVISION_HAS_TASKS_AND_LINES)
        if not revision.reference_correctable:
            missing.append(REFERENCE_CORRECTABLE)
        if not revision.no_task_running:
            missing.append(NO_BACKGROUND_TASK_RUNNING)
        return missing
    if revision.marked:
        return [REVISION_DRAFT]
    if command == "declare_risk":
        return [
            *([] if revision.no_task_running else [NO_BACKGROUND_TASK_RUNNING]),
            *([] if revision.has_main_task else [AT_LEAST_ONE_TASK]),
            *([] if revision.provision_category_active else [ACTIVE_PROVISION_CATEGORY]),
        ]
    # The skeleton asks a main structure without tasks first, its own condition (WF-PRJ-0030).
    skeleton = command == "generate_skeleton" and revision.has_main_task
    missing = [MAIN_STRUCTURE_WITHOUT_TASKS] if skeleton else []
    if command == "apply_rate_update" and not revision.rate_update_available:
        missing.append(RATE_UPDATE_AVAILABLE)
    return missing if revision.no_task_running else [*missing, NO_BACKGROUND_TASK_RUNNING]


def phase_conditions(command: str, state: str, *, main: bool) -> list[str]:
    """Name the condition of the phase of the project an entry of a structure lacks.

    On the main structure, the estimate is entered before In progress and the remaining in it
    (WF-DEV-0050, WF-RAE-0040); the planning has no phase.
    """
    if main and command == "edit_estimate" and state not in BEFORE_IN_PROGRESS:
        return [PROJECT_BEFORE_IN_PROGRESS]
    if main and command == "edit_remaining" and state != "in_progress":
        return [PROJECT_IN_PROGRESS]
    return []


def revision_commands(
    permissions: Collection[str], kind: str | None, state: str, revision: RevisionState
) -> list[tuple[str, tuple[str, ...]]]:
    """List the commands a caller holds on a revision, each with the conditions it lacks.

    A terminal project lists its exports alone.
    """
    exports: list[tuple[str, tuple[str, ...]]] = [
        (rule.command, ()) for rule in EXPORT_RULES if rule.permission in permissions
    ]
    if state in TERMINAL:
        return exports
    # A marked revision carries no entry of the risks: only the current one does.
    return [
        *(
            (
                rule.command,
                (
                    *quality_conditions(kind, manager=rule.manager),
                    *revision_conditions(rule.command, revision),
                ),
            )
            for rule in REVISION_RULES
            if rule.permission in permissions
            and not (rule.command in RISK_ENTRIES and revision.marked)
        ),
        *exports,
    ]


def structure_commands_of(
    permissions: Collection[str],
    kind: str | None,
    state: str,
    revision: RevisionState,
    *,
    main: bool,
) -> list[tuple[str, tuple[str, ...]]]:
    """List the commands a caller holds on a structure, each with the conditions it lacks.

    Only the main structure has a remaining to commit (WF-RAE-0040): the other kinds, EP-08's,
    never list it.
    """
    if state in TERMINAL:
        return []
    return [
        (
            rule.command,
            (
                *quality_conditions(kind, manager=rule.manager),
                *phase_conditions(rule.command, state, main=main),
                *revision_conditions(rule.command, revision),
            ),
        )
        for rule in STRUCTURE_RULES
        if rule.permission in permissions and (main or rule.command != "edit_remaining")
    ]


@dataclass(frozen=True, slots=True)
class MergeState:
    """What the merge of a structure judges: its project, its revision, the structure, the caller.

    ``current`` whether the revision is the current one; ``source`` whether it is the last marked
    revision of a project without a current revision, whose merge creates the current revision
    (#790); ``mergeable`` whether the structure is a differential not merged; ``creates`` whether
    the caller may create a revision (``revisions.write``).
    """

    terminal: bool
    current: bool
    source: bool
    no_task_running: bool
    mergeable: bool
    creates: bool


def merge_conditions(state: MergeState) -> list[str]:
    """Name the conditions the merge of a structure lacks, in the order of ``merge_structure``.

    ``project_not_terminal`` first; on a marked revision but the last of a project without a
    current revision, ``revision_draft`` alone; else ``no_background_task_running``,
    ``unmerged_amendment_exists``, then ``may_create_revision`` where the merge would create the
    current revision (``RevisionCommand.merge_structure``, WF-REV-0050; #790).
    """
    if state.terminal:
        return [PROJECT_NOT_TERMINAL]
    if not state.current and not state.source:
        return [REVISION_DRAFT]
    missing = [] if state.no_task_running else [NO_BACKGROUND_TASK_RUNNING]
    if not state.mergeable:
        missing.append(UNMERGED_AMENDMENT_EXISTS)
    if not state.current and not state.creates:
        missing.append(MAY_CREATE_REVISION)
    return missing
