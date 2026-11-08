# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The entries of the history: one per entry of the planning, kept in its transaction.

``recording(session, change)`` frames a write of the planning (EP-06, "L'historique annulable"):
the planning hands it the snapshot of the objects it touches before the write, then after it —
their rows of ``node``, ``task``, ``task_link`` and ``tracking_entry``, by its own ``snapshot`` —,
and the history keeps them in JSONB without reading any table of the planning. A stack is by
revision, by account and by session of connection (``UndoStack``); a new entry deletes the entries
undone of its stack. At least fifty entries are kept by stack (WF-IHM-0110): none is dropped but
by the closing of the revision or by the purge.

The frame locks its stack at its opening, and an undoing or a redoing locks it the same way: a
write opens its frame before it locks its structure, so that the locks are always taken in one
order — the revision, the stack, the structure — and an undoing, which reads the stack before it
knows the structure, then locks it before it judges anything, never waits for a write that waits
for it.

Declared by US-1380/L1; filled by US-1450/L1.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import delete, func, select

from waterfall.core.history.snapshots import encoded
from waterfall.core.history.stacks import lock_stack, of_stack
from waterfall.core.history.tables import UndoEntry
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Generator
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.snapshots import Snapshot

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
    """An entry of the planning about to be written: its stack, its kind, the nodes it touches.

    ``node_ids`` are those an undoing names (``UndoResult.undone.node_ids``): empty for a write of
    a structure, whose snapshot holds the structure. ``at`` is the moment of the write.
    """

    project_id: UUID
    stack: UndoStack
    kind: UndoneKind
    node_ids: tuple[UUID, ...]
    at: datetime


class Recording:
    """The frame of a write: the snapshots its caller takes, before the write then after it."""

    __slots__ = ("_after", "_before", "_named")

    def __init__(self) -> None:
        """Open the frame: nothing is taken yet."""
        self._before: Snapshot | None = None
        self._after: Snapshot | None = None
        self._named: tuple[UUID, ...] | None = None

    def name(self, node_ids: tuple[UUID, ...]) -> None:
        """Name the nodes the entry touches, when the write knows them only once judged."""
        self._named = node_ids

    def named(self, announced: tuple[UUID, ...]) -> tuple[UUID, ...]:
        """Give the nodes of the entry: those the write named, else those it announced."""
        return announced if self._named is None else self._named

    def keep_before(self, snapshot: Snapshot) -> None:
        """Keep the objects the write touches as they are before it, read under its locks."""
        self._before = snapshot

    def keep_after(self, snapshot: Snapshot) -> None:
        """Keep the objects the write touched as they are after it, redated."""
        self._after = snapshot

    def taken(self) -> tuple[Snapshot, Snapshot]:
        """Give both snapshots; a write that did not hand one is a defect of its caller."""
        if self._before is None or self._after is None:
            msg = "a write recorded must hand its snapshots before and after it"
            raise RuntimeError(msg)
        return self._before, self._after


@contextmanager
def recording(session: Session, change: RecordedChange) -> Generator[Recording]:
    """Frame a write of the planning, and keep its entry in the transaction of the write.

    The stack is locked at the opening. Once the block has handed both snapshots, the entries
    undone of the stack are deleted and the entry is kept on its top; a block that raises keeps
    nothing — its transaction is rolled back anyway.
    """
    stack = change.stack
    lock_stack(session, stack)
    frame = Recording()
    yield frame
    before, after = frame.taken()
    session.execute(delete(UndoEntry).where(of_stack(stack), UndoEntry.undone))
    top = session.scalar(select(func.max(UndoEntry.rank)).where(of_stack(stack)))
    session.add(
        UndoEntry(
            id=new_id(),
            project_id=change.project_id,
            revision_id=stack.revision_id,
            user_account_id=stack.user_account_id,
            session_id=stack.session_id,
            rank=(top or 0) + 1,
            kind=change.kind,
            node_ids=list(frame.named(change.node_ids)),
            before=encoded(before),
            after=encoded(after),
            undone=False,
            created_at=change.at,
        )
    )
    session.flush()
