# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands an account carries, each available or not, with what it lacks (WF-IHM-0090).

The front presents what the account says, and does not compare the roles of the accounts to know
which is the last administrator (WF-ARC-0020): the account says it.
"""

from dataclasses import dataclass

from waterfall.platform.errors import ConflictError

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
# The condition the deactivation of the last administrator lacks (WF-ADM-0120).
LAST_ADMINISTRATOR_CONDITION = "last_administrator"
# The condition the reactivation of an anonymised account lacks, and the change of its names: the
# anonymisation is irreversible (WF-ADM-0060).
NOT_ANONYMIZED_CONDITION = "is_not_anonymized"


def anonymized() -> ConflictError:
    """Refuse what would undo the anonymisation of an account (409, WF-ADM-0060)."""
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": NOT_ANONYMIZED_CONDITION})


@dataclass(frozen=True, slots=True)
class CommandAvailability:
    """A command of an account, and the conditions it lacks: none when it is available."""

    command: str
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


@dataclass(frozen=True, slots=True)
class AccountState:
    """What the commands of an account depend on: its state, and whether it is the last one."""

    is_active: bool
    is_anonymized: bool = False
    is_last_administrator: bool = False


def account_commands(
    state: AccountState, *, may_change: bool, may_attribute: bool
) -> tuple[CommandAvailability, ...]:
    """Give the commands of an account its reader may exercise, in the order of the contract.

    None for a reader who may not change the accounts (``users.write``, WF-ADM-0100). Else the one
    that changes its state — the deactivation of the last active account that holds the
    administration unavailable (WF-ADM-0120), the reactivation of an anonymised one too
    (WF-ADM-0060) —; the anonymisation of a deactivated account not anonymised yet; and, for a
    reader who may also change the roles (``may_attribute``, FBS-1.2, WF-ADM-0090), the
    attribution of its roles, always available: giving it more stays possible, and a withdrawal is
    refused by the roles sent (WF-IHM-0090).
    """
    if not may_change:
        return ()
    commands: list[CommandAvailability] = []
    if state.is_active:
        lacking = (LAST_ADMINISTRATOR_CONDITION,) if state.is_last_administrator else ()
        commands.append(CommandAvailability("deactivate", lacking))
    elif state.is_anonymized:
        commands.append(CommandAvailability("reactivate", (NOT_ANONYMIZED_CONDITION,)))
    else:
        commands += (CommandAvailability("reactivate"), CommandAvailability("anonymize"))
    if may_attribute:
        commands.append(CommandAvailability("set_access_roles"))
    return tuple(commands)
