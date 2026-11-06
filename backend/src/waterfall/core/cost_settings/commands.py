# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of a nature of cost, each available or not (WF-IHM-0090).

The list of commands the front presents and the call that exercises them are built from the same
values, so that a command said unavailable and the call refused say the same condition (EP-05,
"Modules"). Pure: nothing here reads the base.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandAvailability:
    """A command, and the conditions it lacks: none when it is available."""

    command: str
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


def state_command(*, is_active: bool, missing: tuple[str, ...] = ()) -> CommandAvailability:
    """Give the command that changes the state: the deactivation, or the reactivation."""
    if is_active:
        return CommandAvailability("deactivate")
    return CommandAvailability("reactivate", missing)


def cost_type_commands(*, is_active: bool, may_change: bool) -> tuple[CommandAvailability, ...]:
    """Give the commands of a nature its reader may exercise, in the order of the contract.

    None for a reader who may not change the cost settings. Else the one that changes its state,
    and the change of its kind: both available, no category yet binds the kind of a nature.
    """
    if not may_change:
        return ()
    return (state_command(is_active=is_active), CommandAvailability("change_kind"))
