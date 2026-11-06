# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of a nature and of a category of cost, each available or not (WF-IHM-0090).

What a nature or a category lacks to change its kind is decided here, once, from values: the
list of commands the front presents and the 409 that refuses the call anyway are built from the
same functions, so that a command said unavailable and the call refused say the same condition
(EP-05, "Modules"). Pure: nothing here reads the base.
"""

from dataclasses import dataclass

# The condition the reactivation of a category lacks under a nature that is deactivated.
COST_TYPE_ACTIVE = "cost_type_active"


@dataclass(frozen=True, slots=True)
class CommandAvailability:
    """A command, and the conditions it lacks: none when it is available."""

    command: str
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


@dataclass(frozen=True, slots=True)
class Holdings:
    """What binds a nature or a category: employed by a line, bearing a rate, held by a role."""

    employed: bool = False
    rated: bool = False
    with_roles: bool = False


def kind_change_missing(owner: str, holdings: Holdings) -> tuple[str, ...]:
    """Give the conditions a change of kind lacks, in the order the contract refuses by.

    ``owner`` is ``cost_type`` or ``cost_category``: the conditions are named after it
    (``cost_type_unused``, ``cost_category_unrated``…).
    """
    lacking = (
        ("unused", holdings.employed),
        ("unrated", holdings.rated),
        ("without_role", holdings.with_roles),
    )
    return tuple(f"{owner}_{name}" for name, held in lacking if held)


def state_command(*, is_active: bool, missing: tuple[str, ...] = ()) -> CommandAvailability:
    """Give the command that changes the state: the deactivation, or the reactivation."""
    if is_active:
        return CommandAvailability("deactivate")
    return CommandAvailability("reactivate", missing)


def cost_type_commands(
    *, is_active: bool, holdings: Holdings, may_change: bool
) -> tuple[CommandAvailability, ...]:
    """Give the commands of a nature its reader may exercise, in the order of the contract.

    None for a reader who may not change the cost settings. Else the one that changes its state,
    always available, and the change of its kind, which lacks what its categories hold.
    """
    if not may_change:
        return ()
    return (
        state_command(is_active=is_active),
        CommandAvailability("change_kind", kind_change_missing("cost_type", holdings)),
    )


def cost_category_commands(
    *, is_active: bool, type_is_active: bool, holdings: Holdings, may_change: bool
) -> tuple[CommandAvailability, ...]:
    """Give the commands of a category its reader may exercise, in the order of the contract.

    None for a reader who may not change the cost settings. Else the one that changes its state —
    its reactivation lacks an active nature (WF-REF-0010) — and the change of its nature to one of
    another kind, which lacks what the category holds.
    """
    if not may_change:
        return ()
    missing = () if type_is_active else (COST_TYPE_ACTIVE,)
    return (
        state_command(is_active=is_active, missing=missing),
        CommandAvailability("change_cost_type", kind_change_missing("cost_category", holdings)),
    )
