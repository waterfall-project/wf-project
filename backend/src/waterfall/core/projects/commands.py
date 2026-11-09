# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of a project and the conditions each lacks (WF-IHM-0090), private to the module.

One computation serves the list a project carries (``available_commands``) and the 409 of an
operation sent in spite of it, so that a command said unavailable and the call refused name the
same condition. A command is listed to the caller who holds its permission; the quality it asks
on the project comes first among the conditions it lacks (``is_contributor``, then
``is_project_manager`` for an action reserved to the project managers), the conditions of the
state after (WF-PRJ-0060). A terminal project lists none: nothing modifies it any more, and only
the 409 of a direct call names ``project_not_terminal`` (WF-CYC-0100).

This module knows the commands of EP-04; the later EPICs add theirs — the risks, the imports, the
skeleton of the planning — to ``RULES`` with their conditions: the imports of a planning
(US-1430/L4) and of an estimate (US-1550/L3). The rescue of ``manage_contributors`` for a caller
who is no contributor is the story of the contributors (US-0930).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

# The states that end the cycle of life (WF-CYC-0080), and those before the project is in progress.
TERMINAL = ("completed", "lost", "abandoned")
BEFORE_IN_PROGRESS = ("created", "pricing")
# The commands that take a project out of its cycle, and the terminal state each reaches
# (``exitProject``, WF-CYC-0060).
EXITS = {"completed": "complete", "lost": "lose", "abandoned": "abandon"}

IS_CONTRIBUTOR = "is_contributor"
IS_PROJECT_MANAGER = "is_project_manager"
PROJECT_NOT_TERMINAL = "project_not_terminal"
PROJECT_IN_PROGRESS = "project_in_progress"
PROJECT_IN_PRICING = "project_in_pricing"
PROJECT_BEFORE_IN_PROGRESS = "project_before_in_progress"
NO_CURRENT_REVISION = "no_current_revision"
NO_BACKGROUND_TASK_RUNNING = "no_background_task_running"
MAIN_STRUCTURE_WITHOUT_TASKS = "main_structure_without_tasks"
MAY_CREATE_REVISION = "may_create_revision"


@dataclass(frozen=True, slots=True)
class Rule:
    """A command: the permission that guards it, and whether it is reserved to the managers."""

    command: str
    permission: str
    manager: bool = False


# In the order of ``ProjectCommand``. The probability and the work breakdown go with ``update``:
# they are parts of the settings of the project (WF-PRJ-0060, WF-PRJ-0090).
RULES: tuple[Rule, ...] = (
    Rule("update", "project_settings.write", manager=True),
    Rule("update_win_probability", "project_settings.write", manager=True),
    Rule("update_work_breakdown", "project_settings.write", manager=True),
    Rule("manage_contributors", "project_settings.write", manager=True),
    Rule("manage_timelines", "planning.write"),
    Rule("create_revision", "revisions.write"),
    Rule("complete", "project_exit", manager=True),
    Rule("lose", "project_exit", manager=True),
    Rule("abandon", "project_exit", manager=True),
    Rule("generate_skeleton", "planning.write"),
    Rule("import_planning", "planning.write"),
    Rule("import_estimate", "estimate.write"),
)
# The imports a project carries, which create the current revision if it has none (WF-INTF-0090).
IMPORTS = ("import_planning", "import_estimate")


def state_conditions(
    command: str, state: str, current_revision_id: UUID | None, *, no_task_running: bool
) -> list[str]:
    """Name the conditions of the state a command lacks, in the order the contract lists them."""
    # No exit leaves a terminal project, which lists none: only the 409 of a direct call says it.
    if state in TERMINAL and command in EXITS.values():
        return [PROJECT_NOT_TERMINAL]
    missing: list[str] = []
    if command == "update_win_probability" and state not in BEFORE_IN_PROGRESS:
        missing.append(PROJECT_BEFORE_IN_PROGRESS)
    if command == "create_revision" and current_revision_id is not None:
        missing.append(NO_CURRENT_REVISION)
    if command == "complete" and state != "in_progress":
        missing.append(PROJECT_IN_PROGRESS)
    # Created or In progress: the list omits the command from the second, the 409 names it.
    if command == "lose" and state != "pricing":
        missing.append(PROJECT_IN_PRICING)
    # A task of the background that writes in the current revision, or freezes it, suspends what
    # would move the project or its work breakdown (EP-04, "Le worker").
    if (
        command in {"update_work_breakdown", "complete", "lose", "abandon", *IMPORTS}
        and not no_task_running
    ):
        missing.append(NO_BACKGROUND_TASK_RUNNING)
    return missing


@dataclass(frozen=True, slots=True)
class Running:
    """What the commands read of the background and of the revision an opening would create.

    ``no_task_running`` tells that no task of the background writes in the project;
    ``opening_has_tasks`` that the revision its opening would create carries a task.
    """

    no_task_running: bool
    opening_has_tasks: bool = False


def skeleton_conditions(running: Running) -> list[str]:
    """Name the conditions the generation of the skeleton lacks, judged on the revision to open.

    A running import, occurrence or merge creates another revision; the revision to open is a copy
    of the last marked one (WF-PRJ-0030, WF-REV-0010).
    """
    missing = [] if running.no_task_running else [NO_BACKGROUND_TASK_RUNNING]
    return [*missing, MAIN_STRUCTURE_WITHOUT_TASKS] if running.opening_has_tasks else missing


def quality_conditions(kind: str | None, *, manager: bool) -> list[str]:
    """Name the quality on the project that the caller lacks for a command, if it does."""
    if kind is None:
        return [IS_CONTRIBUTOR, IS_PROJECT_MANAGER] if manager else [IS_CONTRIBUTOR]
    if manager and kind != "project_manager":
        return [IS_PROJECT_MANAGER]
    return []


def commands_of(
    permissions: Collection[str],
    kind: str | None,
    state: str,
    current_revision_id: UUID | None,
    *,
    running: Running,
) -> list[tuple[str, tuple[str, ...]]]:
    """List the commands a caller holds on a project, each with the conditions it lacks.

    The skeleton is listed only while the project has no current revision, to whoever holds the
    planning permission, ``may_create_revision`` missing to whoever cannot open one (WF-PRJ-0030).
    An import is listed whatever the revision, to whoever holds the permission of its kind; without
    a current revision, ``may_create_revision`` missing to whoever cannot create the one it would
    (WF-INTF-0090). An estimate stays available In progress: its import on the main structure is
    refused by the import itself, which the structure states (``edit_estimate``; C-358). The
    conditions of an import are those ``openImport`` refuses by, in its order.
    """
    if state in TERMINAL:
        return []
    listed: list[tuple[str, tuple[str, ...]]] = []
    for rule in RULES:
        # A project that has left Chiffrage cannot be declared lost any more (WF-CYC-0060).
        if rule.permission not in permissions or (
            rule.command == "lose" and state == "in_progress"
        ):
            continue
        if rule.command == "generate_skeleton":
            if current_revision_id is None:
                listed.append((rule.command, _skeleton_lacks(permissions, kind, running)))
            continue
        missing = quality_conditions(kind, manager=rule.manager)
        missing += state_conditions(
            rule.command, state, current_revision_id, no_task_running=running.no_task_running
        )
        # An import creates the current revision when there is none: who cannot is told so.
        if (
            rule.command in IMPORTS
            and current_revision_id is None
            and "revisions.write" not in permissions
        ):
            missing.append(MAY_CREATE_REVISION)
        listed.append((rule.command, tuple(missing)))
    return listed


def _skeleton_lacks(
    permissions: Collection[str], kind: str | None, running: Running
) -> tuple[str, ...]:
    """Name what the skeleton of a project without a current revision lacks (WF-IHM-0090)."""
    missing = [*quality_conditions(kind, manager=False), *skeleton_conditions(running)]
    if "revisions.write" not in permissions:
        missing.append(MAY_CREATE_REVISION)
    return tuple(missing)
