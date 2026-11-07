# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The closing of a revision: what the later modules do before it is marked or abandoned.

The common hook of the marking and of the abandonment (EP-06, "Les points d'extension"), called
under the lock of the revision, once it is judged and before it is written: each module does its
part in the order of its registration — the history and the plans of a paste first
(``close_history``, US-1450), then the nodes at an abandonment (``delete_nodes``, US-1380/L2) —,
and the structures of EP-04 are deleted after them (``delete_structures``), so that the
abandonment of a full revision leaves no row (WF-DAT-0010). The cascade of the keys keeps the same
order should a path forget it.

Declared by US-1380/L1; it holds nothing until a module registers.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

# Why a revision closes: it is marked, or it is abandoned.
type ClosingKind = Literal["marked", "abandoned"]


@dataclass(frozen=True, slots=True)
class RevisionClosing:
    """A revision about to be marked or abandoned, in the transaction that does it."""

    session: Session
    project_id: UUID
    revision_id: UUID
    kind: ClosingKind


# What each module does before a revision closes, in the order of their registration.
_CLOSINGS: Registry[Callable[[RevisionClosing], None]] = Registry("revisions.closing")


def register_closing(closer: Callable[[RevisionClosing], None]) -> Callable[[], None]:
    """Add what a module does before a revision closes, after those registered; give its withdrawal.

    A module registers at the import of its interface, which imports this one first.
    """
    return _CLOSINGS.register(closer)


def close_revision(
    session: Session, project_id: UUID, revision_id: UUID, kind: ClosingKind
) -> None:
    """Have each module registered do its part before the revision is marked or abandoned."""
    closing = RevisionClosing(session, project_id, revision_id, kind)
    for closer in _CLOSINGS.entries():
        closer(closing)
