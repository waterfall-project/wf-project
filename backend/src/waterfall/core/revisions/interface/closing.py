# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The closing of a revision: what the later modules do before it is marked or abandoned.

The common hook of the marking and of the abandonment (EP-06, "Les points d'extension"), called
under the lock of the revision, once it is judged and before it is written. Each module registers
its part under a stage, and the stages run in their declared order (``CLOSING_STAGES``), whatever
the order in which a process imported the modules: the history and the plans of a paste first
(``history``: ``close_history``, US-1450/L1), then the content of the revision (``content``: the
nodes at an abandonment, ``delete_nodes``, US-1380/L2; the images of EP-07), the parts of a stage
in the order of their registration; the structures of EP-04 are deleted after them
(``delete_structures``), so that the abandonment of a full revision leaves no row (WF-DAT-0010).
The cascade of the keys keeps the same order should a path forget it.

Declared by US-1380/L1, with what the history and the planning register, each without effect until
its story fills it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from waterfall.core.revisions.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

# Why a revision closes: it is marked, or it is abandoned.
type ClosingKind = Literal["marked", "abandoned"]
# The stages of a closing, in the order they run: the history, then the content of the revision.
type ClosingStage = Literal["history", "content"]
CLOSING_STAGES: tuple[ClosingStage, ...] = ("history", "content")


@dataclass(frozen=True, slots=True)
class RevisionClosing:
    """A revision about to be marked or abandoned, in the transaction that does it."""

    session: Session
    project_id: UUID
    revision_id: UUID
    kind: ClosingKind


# What each module does before a revision closes, under its stage, in the order of registration.
_CLOSINGS: Registry[tuple[ClosingStage, Callable[[RevisionClosing], None]]] = Registry(
    "revisions.closing"
)


def register_closing(
    stage: ClosingStage, closer: Callable[[RevisionClosing], None]
) -> Callable[[], None]:
    """Add what a module does before a revision closes, under a stage; give its withdrawal.

    A module registers at the import of its interface, which imports this one first.
    """
    return _CLOSINGS.register((stage, closer))


def closers() -> tuple[Callable[[RevisionClosing], None], ...]:
    """Give what runs before a revision closes: stage by stage, each in its registration order."""
    registered = _CLOSINGS.entries()
    return tuple(closer for stage in CLOSING_STAGES for held, closer in registered if held == stage)


def close_revision(
    session: Session, project_id: UUID, revision_id: UUID, kind: ClosingKind
) -> None:
    """Have each module registered do its part before the revision is marked or abandoned."""
    closing = RevisionClosing(session, project_id, revision_id, kind)
    for closer in closers():
        closer(closing)
