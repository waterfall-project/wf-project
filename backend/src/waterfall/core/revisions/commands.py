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
rates), with their conditions, and the exports to ``EXPORT_RULES``.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

# The states that end the cycle of life (WF-CYC-0080), and those before the project is in progress.
TERMINAL = ("completed", "lost", "abandoned")
BEFORE_IN_PROGRESS = ("created", "pricing")

IS_CONTRIBUTOR = "is_contributor"
IS_PROJECT_MANAGER = "is_project_manager"
PROJECT_NOT_TERMINAL = "project_not_terminal"
PROJECT_IN_PROGRESS = "project_in_progress"
PROJECT_BEFORE_IN_PROGRESS = "project_before_in_progress"
NO_CURRENT_REVISION = "no_current_revision"
NO_BACKGROUND_TASK_RUNNING = "no_background_task_running"
REVISION_DRAFT = "revision_draft"
REVISION_MARKED = "revision_marked"
REVISION_HAS_TASKS_AND_LINES = "revision_has_tasks_and_lines"
REFERENCE_CORRECTABLE = "reference_correctable"


@dataclass(frozen=True, slots=True)
class Rule:
    """A command: the permission that guards it, and whether it is reserved to the managers."""

    command: str
    permission: str
    manager: bool = False


# In the order of ``RevisionCommand``. The marking, the designation and the abandonment have a
# permission of their own, structuring actions reserved to the project managers (WF-ADM-0100).
REVISION_RULES: tuple[Rule, ...] = (
    Rule("edit_planning", "planning.write"),
    Rule("edit_estimate", "estimate.write"),
    Rule("edit_remaining", "remaining.write"),
    Rule("mark", "revision_mark", manager=True),
    Rule("designate_reference", "reference_designate", manager=True),
    Rule("abandon", "revision_abandon", manager=True),
)
# The exports, listed after the other commands as ``RevisionCommand`` orders them: a matter of
# consultation, each guarded by the permission to view the function of its kind, lacking no
# condition (WF-CYC-0110). The planning's is here; the tree image (US-1440), the estimate (EP-07)
# and the remaining to commit (EP-09) add theirs.
EXPORT_RULES: tuple[Rule, ...] = (Rule("export_planning", "planning.read"),)
# In the order of ``StructureCommand``: each guarded by the permission of the command of the same
# name of the revision.
STRUCTURE_RULES: tuple[Rule, ...] = (
    Rule("edit_planning", "planning.write"),
    Rule("edit_estimate", "estimate.write"),
    Rule("edit_remaining", "remaining.write"),
)


@dataclass(frozen=True, slots=True)
class RevisionState:
    """What the conditions of a revision read: its status, its facts, its project's."""

    marked: bool
    no_task_running: bool
    has_tasks_and_lines: bool
    reference_correctable: bool


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
    return [] if revision.no_task_running else [NO_BACKGROUND_TASK_RUNNING]


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
