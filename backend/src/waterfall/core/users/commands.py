# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands an account carries, each available or not, with what it lacks (WF-IHM-0090).

The front presents what the account says, and does not compare the roles of the accounts to know
which is the last administrator (WF-ARC-0020): the account says it.
"""

from dataclasses import dataclass

# The condition the deactivation of the last administrator lacks (WF-ADM-0120).
LAST_ADMINISTRATOR = "last_administrator"


@dataclass(frozen=True, slots=True)
class CommandAvailability:
    """A command of an account, and the conditions it lacks: none when it is available."""

    command: str
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


def account_commands(
    *, is_active: bool, is_last_administrator: bool, may_change: bool
) -> tuple[CommandAvailability, ...]:
    """Give the commands of an account its reader may exercise, in the order of the contract.

    None for a reader who may not change the accounts (``users.write``, WF-ADM-0100). Else the one
    that changes its state — the deactivation of the last active account that holds the
    administration unavailable (WF-ADM-0120) — and the attribution of its roles, always available:
    giving it more stays possible, and a withdrawal is refused by the roles sent (WF-IHM-0090).
    """
    if not may_change:
        return ()
    if not is_active:
        state = CommandAvailability("reactivate")
    elif is_last_administrator:
        state = CommandAvailability("deactivate", (LAST_ADMINISTRATOR,))
    else:
        state = CommandAvailability("deactivate")
    return (state, CommandAvailability("set_access_roles"))
