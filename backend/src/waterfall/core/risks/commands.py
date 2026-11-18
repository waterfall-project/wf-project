# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of a risk and the conditions each lacks (WF-IHM-0090), private to the module.

One computation serves the list a risk carries (``available_commands``) and the 409 of an operation
sent in spite of it, so that a command said unavailable and the call refused name the same
condition. A command is listed to the caller who holds its permission, in the order of
``RiskCommand``: the entries under ``risks.write``, the occurrence under ``risk_occurrence`` alone,
which includes the merge it triggers (WF-ADM-0100). The risk names only what depends on it — its
state, its citation by a marked revision — and, for the occurrence, the revision the occurrence
would create; the conditions of the project and of the revision are on their commands. A terminal
project lists none (WF-CYC-0100).

An occurred risk has the change of its identity, the review and the deletion unavailable,
``risk_not_occurred`` missing, no transition leaving it (WF-RIS-0020); a risk that is not identified
has the change of its provision and its occurrence unavailable, ``risk_identified`` missing
(WF-RIS-0010, WF-RIS-0060); the deletion of a risk a marked revision cites names
``risk_not_cited``, after ``risk_not_occurred``.

Written by US-2570/L1; the lots that serve the other commands (US-2580, US-2590, US-2620) judge
their 409 by it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.projects.interface import TERMINAL, CommandAvailability

if TYPE_CHECKING:
    from collections.abc import Collection

    from waterfall.core.risks.views import RiskCommand, RiskState

WRITE = "risks.write"
OCCURRENCE = "risk_occurrence"
REVISIONS_WRITE = "revisions.write"
RISK_NOT_OCCURRED = "risk_not_occurred"
RISK_IDENTIFIED = "risk_identified"
RISK_NOT_CITED = "risk_not_cited"
MAY_CREATE_REVISION = "may_create_revision"
IDENTIFIED, OCCURRED = "identified", "occurred"

# In the order of ``RiskCommand``, each with the permission that guards it.
RULES: tuple[tuple[RiskCommand, str], ...] = (
    ("update", WRITE),
    ("update_provision", WRITE),
    ("review", WRITE),
    ("declare_occurrence", OCCURRENCE),
    ("delete", WRITE),
)


@dataclass(frozen=True, slots=True)
class RiskStanding:
    """What the commands of a risk read: its state, its citation, its project.

    ``state`` the state of the risk in the revision read; ``cited`` whether a marked revision holds
    an evaluation of it; ``terminal`` whether its project is; ``current`` whether its project has a
    current revision, which the occurrence creates otherwise.
    """

    state: RiskState
    cited: bool
    terminal: bool
    current: bool


def risk_conditions(
    command: RiskCommand, standing: RiskStanding, permissions: Collection[str]
) -> tuple[str, ...]:
    """Name the conditions of a risk a command lacks, in the order the contract lists them."""
    occurred = standing.state == OCCURRED
    missing: list[str] = []
    if command in {"update", "review", "delete"} and occurred:
        missing.append(RISK_NOT_OCCURRED)
    if command in {"update_provision", "declare_occurrence"} and standing.state != IDENTIFIED:
        missing.append(RISK_IDENTIFIED)
    if command == "delete" and standing.cited:
        missing.append(RISK_NOT_CITED)
    occurring = command == "declare_occurrence" and not standing.current
    if occurring and REVISIONS_WRITE not in permissions:
        missing.append(MAY_CREATE_REVISION)
    return tuple(missing)


def risk_commands(
    standing: RiskStanding, permissions: Collection[str]
) -> tuple[CommandAvailability, ...]:
    """List the commands a caller holds on a risk, each with the conditions it lacks."""
    if standing.terminal:
        return ()
    return tuple(
        CommandAvailability(command, risk_conditions(command, standing, permissions))
        for command, permission in RULES
        if permission in permissions
    )


def is_terminal(state: str) -> bool:
    """Tell whether a state of a project ends its cycle (WF-CYC-0080)."""
    return state in TERMINAL
