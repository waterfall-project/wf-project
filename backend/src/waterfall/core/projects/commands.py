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
skeleton of the planning — to ``RULES`` with their conditions. The rescue of ``manage_contributors``
for a caller who is no contributor is the story of the contributors (US-0930).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

# The states that end the cycle of life (WF-CYC-0080), and those before the project is in progress.
TERMINAL = ("completed", "lost", "abandoned")
BEFORE_IN_PROGRESS = ("created", "pricing")

IS_CONTRIBUTOR = "is_contributor"
IS_PROJECT_MANAGER = "is_project_manager"
PROJECT_NOT_TERMINAL = "project_not_terminal"
PROJECT_IN_PROGRESS = "project_in_progress"
PROJECT_IN_PRICING = "project_in_pricing"
PROJECT_BEFORE_IN_PROGRESS = "project_before_in_progress"
NO_CURRENT_REVISION = "no_current_revision"
NO_BACKGROUND_TASK_RUNNING = "no_background_task_running"


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
)


def state_conditions(
    command: str, state: str, current_revision_id: UUID | None, *, no_task_running: bool
) -> list[str]:
    """Name the conditions of the state a command lacks, in the order the contract lists them."""
    missing: list[str] = []
    if command == "update_win_probability" and state not in BEFORE_IN_PROGRESS:
        missing.append(PROJECT_BEFORE_IN_PROGRESS)
    if command == "create_revision" and current_revision_id is not None:
        missing.append(NO_CURRENT_REVISION)
    if command == "complete" and state != "in_progress":
        missing.append(PROJECT_IN_PROGRESS)
    if command == "lose" and state == "created":
        missing.append(PROJECT_IN_PRICING)
    # A task of the background that writes in the current revision, or freezes it, suspends what
    # would move the project or its work breakdown (EP-04, "Le worker").
    if command in {"update_work_breakdown", "complete", "lose", "abandon"} and not no_task_running:
        missing.append(NO_BACKGROUND_TASK_RUNNING)
    return missing


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
    no_task_running: bool,
) -> list[tuple[str, tuple[str, ...]]]:
    """List the commands a caller holds on a project, each with the conditions it lacks."""
    if state in TERMINAL:
        return []
    listed: list[tuple[str, tuple[str, ...]]] = []
    for rule in RULES:
        # A project that has left Chiffrage cannot be declared lost any more (WF-CYC-0060).
        if rule.permission not in permissions or (
            rule.command == "lose" and state == "in_progress"
        ):
            continue
        missing = quality_conditions(kind, manager=rule.manager)
        missing += state_conditions(
            rule.command, state, current_revision_id, no_task_running=no_task_running
        )
        listed.append((rule.command, tuple(missing)))
    return listed
