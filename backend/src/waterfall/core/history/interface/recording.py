# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The entries of the history: one per entry of the planning, kept in its transaction.

``recording(session, change)`` frames a write of the planning (EP-06, "L'historique annulable"):
the planning hands it the snapshot of the nodes it touches before the write, then after it — their
rows of ``node``, ``task``, ``task_link`` and ``tracking_entry``, by its own ``snapshot`` —, and
the history keeps them in JSONB without reading any table of the planning. A stack is by revision,
by account and by session of connection (``UndoStack``); a new entry deletes the entries undone of
its stack.

Declared by US-1380/L1; US-1450/L1 fills it, and gives ``recording`` the form of its frame.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

# The kinds of a change undone, as the contract says them (``UndoneKind``).
type UndoneKind = Literal[
    "cell",
    "node_create",
    "node_delete",
    "node_move",
    "paste",
    "link",
    "progress",
    "remaining",
    "tracking",
    "structure_update",
    "risk_create",
    "risk_update",
    "risk_review",
    "risk_delete",
]


@dataclass(frozen=True, slots=True)
class UndoStack:
    """The stack of a revision, of an account and of its session of connection (the ``sid``)."""

    revision_id: UUID
    user_account_id: UUID
    session_id: str


@dataclass(frozen=True, slots=True)
class RecordedChange:
    """An entry of the planning about to be written: its stack, its kind, the nodes it touches."""

    project_id: UUID
    stack: UndoStack
    kind: UndoneKind
    node_ids: tuple[UUID, ...]


def recording(session: Session, change: RecordedChange) -> None:
    """Frame a write of the planning, and keep its entry in the transaction of the write."""
    msg = "recording is filled by US-1450/L1"
    raise NotImplementedError(msg)
