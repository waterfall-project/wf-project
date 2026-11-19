# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Where the provision lines of the tasks a write removes go, private to the module (US-2580/L1).

A provision line is the risk's, never the task's (WF-PLA-0070, WF-RIS-0010): the deletion of the
task that bears it, or an import that no longer carries it, does not take the line with it. It
passes to the parent of the task removed, to the first task of the first level left for a task of
the first level, and the total of the estimate is unchanged. A main structure left without a task
refuses the deletion, naming the risks whose provision it would carry.

The planning does not know the risks (EP-08, "Modules"): they register what names a line's risk
and what a line reported does to it (``register_provision_owners``) — the counter of the risk
advances, its provision task changing — and the planning asks them, as it asks the estimate which
lines are provisions (``Tree.provisions``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.tree import Tree


@dataclass(frozen=True, slots=True)
class ProvisionOwner:
    """The risk a provision line belongs to, as the contract names it: its identifier, its label."""

    risk_id: UUID
    label: str


@dataclass(frozen=True, slots=True)
class ProvisionOwners:
    """What a module that owns provision lines tells the planning about them.

    Each is given the session, the project, the revision and the lines: ``named`` the risks they
    belong to, in the order the refusal names them; ``reported`` what a line moved under another
    task does to its risk, written in the transaction of the move.
    """

    named: Callable[[Session, UUID, UUID, Collection[UUID]], tuple[ProvisionOwner, ...]]
    reported: Callable[[Session, UUID, UUID, Collection[UUID]], None]


_OWNERS: Registry[ProvisionOwners] = Registry("planning.provision_owners")


def register_provision_owners(owners: ProvisionOwners) -> Callable[[], None]:
    """Add what names the risk of a provision line and follows its report; give its withdrawal."""
    return _OWNERS.register(owners)


def owners_named(
    session: Session, project_id: UUID, revision_id: UUID, lines: Collection[UUID]
) -> list[ProvisionOwner]:
    """Name the risks the lines belong to, each once, as the modules that own them tell."""
    found: dict[UUID, ProvisionOwner] = {}
    for owners in _OWNERS.entries():
        for owner in owners.named(session, project_id, revision_id, lines):
            found.setdefault(owner.risk_id, owner)
    return list(found.values())


def lines_reported(
    session: Session, project_id: UUID, revision_id: UUID, lines: Collection[UUID]
) -> None:
    """Tell the modules that own provision lines that these were moved under another task."""
    for owners in _OWNERS.entries():
        owners.reported(session, project_id, revision_id, lines)


def first_left(tree: Tree, gone: Iterable[UUID]) -> UUID | None:
    """Give the first task of the first level that the nodes removed leave, none if none."""
    removed = set(gone)
    return next((each for each in tree.subtasks(None) if each not in removed), None)


def provision_moves(
    tree: Tree, gone: Iterable[UUID], first: UUID | None
) -> dict[UUID, UUID | None]:
    """Give the task each provision line under a task removed passes to, by line.

    ``gone`` the nodes removed; a line passes to the nearest ancestor of its task that stays, and
    to ``first`` — the first task of the first level that stays — when none does: none if the
    structure is left without a task, which the caller refuses. The lines in the order of the plan.
    """
    removed = set(gone)
    moves: dict[UUID, UUID | None] = {}
    for line in tree.ordered(tree.provisions):
        parent = tree.nodes[line].parent_id
        if parent not in removed:
            continue
        while parent is not None and parent in removed:
            parent = tree.nodes[parent].parent_id
        moves[line] = first if parent is None else parent
    return moves
