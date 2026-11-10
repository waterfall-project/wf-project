# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The undoing and the redoing of the entries of a stack, and its depth (WF-IHM-0110).

``undo`` reads the last entry not undone of a stack, checks that each object of its ``after`` is
still at its version — else 409 ``UNDO_CONFLICT``, the object taken back named —, and gives back
the objects to restore (its ``before``), which the planning rewrites and redates; ``redo`` does the
same with the last entry undone, checking its ``before`` and giving back its ``after``. ``depth``
tells what each would find (EP-06, "L'historique annulable").

Each is a frame, like ``recording``: it locks the stack, reads the entry, has the caller lock the
structure the entry wrote (``StructureLocker``), and only then reads the objects as they are now and
judges the entry, so that no write of another stack slips between the judging and the restoring —
a judging before that lock would pass on a version a write holding the structure is about to move,
and the restoring would bring ``before`` back over it. The locks keep the order of a write: the
revision (the caller's, before the frame), the stack, the structure. The frame then gives the
caller what to restore; the caller restores it, under the rules of the entry and the lock it took,
and hands back the objects as the restoring left them (``keep_present``). Only then is the entry
marked, undone or redone.

A restoring is a write like any other, which moves the versions of what it writes: the history
carries the versions it left to the entries that will be judged on them next — the nearest entry
not undone that holds the object in its ``after``, the nearest undone one in its ``before`` —, so
that fifty entries on the same task undo one by one, then redo in order, and only a change made
outside the stack is a conflict.

Declared by US-1380/L1; filled by US-1450/L1.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from sqlalchemy import func, select

from waterfall.core.history.snapshots import decoded, encoded, with_versions
from waterfall.core.history.stacks import lock_stack, of_stack
from waterfall.core.history.tables import UndoEntry
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface.recording import UndoneKind, UndoStack
    from waterfall.core.history.snapshots import Snapshot

UNDO_CONFLICT = "UNDO_CONFLICT"
# The conditions of ``CommandCondition`` an empty stack misses.
UNDO_HISTORY_NOT_EMPTY = "undo_history_not_empty"
REDO_HISTORY_NOT_EMPTY = "redo_history_not_empty"

# What reads the objects named as they are now, absent ones left out: the planning's ``snapshot``.
# The frame calls it once, under the lock of the structure its ``StructureLocker`` took.
type SnapshotReader = Callable[[tuple[UUID, ...]], Snapshot]

# What locks, until the end of the transaction, the structure of the objects of an entry — those it
# left and those it wants back, one side empty for a creation or a deletion —, whose rows name it:
# the planning's lock of a structure (``cost_structure`` ``FOR UPDATE``), which every write of the
# structure takes. The frame calls it once, after the lock of the stack and before any reading.
type StructureLocker = Callable[[Snapshot], None]


@dataclass(frozen=True, slots=True)
class Depth:
    """How many entries of a stack may be undone, and how many redone."""

    undoable: int
    redoable: int


class Restoring:
    """The frame of an undoing or a redoing: what to restore, then what the restoring left.

    ``restored`` are the objects to bring back as they were; ``removed`` those to delete, which
    the entry undone created, or the entry redone deleted; ``node_ids`` and ``kind`` what the
    answer names, ``remaining_depth`` what remains to undo — or to redo — after this one.
    """

    __slots__ = ("_present", "kind", "node_ids", "remaining_depth", "removed", "restored")

    def __init__(
        self,
        kind: UndoneKind,
        node_ids: tuple[UUID, ...],
        restored: Snapshot,
        removed: tuple[UUID, ...],
        remaining_depth: int,
    ) -> None:
        """Open the frame on an entry judged."""
        self.kind: UndoneKind = kind
        self.node_ids = node_ids
        self.restored = restored
        self.removed = removed
        self.remaining_depth = remaining_depth
        self._present: Snapshot | None = None

    def keep_present(self, snapshot: Snapshot) -> None:
        """Keep the objects of the entry as the restoring left them, those removed left out."""
        self._present = snapshot

    def present(self) -> Snapshot:
        """Give what the restoring left; a caller that did not hand it is a defect."""
        if self._present is None:
            msg = "a restoring must hand the objects as it left them"
            raise RuntimeError(msg)
        return self._present


@contextmanager
def undo(
    session: Session, stack: UndoStack, *, lock: StructureLocker, read: SnapshotReader
) -> Generator[Restoring]:
    """Undo the last entry not undone of a stack, and give back the objects to restore.

    The stack is locked, then the structure of the entry by ``lock``; the objects are read by
    ``read`` under both, and the block restores them under both. Refused by 409
    ``STATE_FORBIDS_OPERATION``, ``undo_history_not_empty``, on a stack with no entry to undo; by
    409 ``UNDO_CONFLICT`` when an object the entry wrote is no longer at the version it left, the
    first such object of the entry named. Nothing is marked if the block raises.
    """
    with _turned(session, stack, lock, read, undoing=True) as restoring:
        yield restoring


@contextmanager
def redo(
    session: Session, stack: UndoStack, *, lock: StructureLocker, read: SnapshotReader
) -> Generator[Restoring]:
    """Redo the last entry undone of a stack, and give back the objects to restore.

    Locked and refused as ``undo`` is, ``redo_history_not_empty`` naming an empty stack of
    undoings.
    """
    with _turned(session, stack, lock, read, undoing=False) as restoring:
        yield restoring


def depth(session: Session, stack: UndoStack) -> Depth:
    """Tell how many entries of a stack may be undone, and how many redone."""
    rows = session.execute(
        select(UndoEntry.undone, func.count()).where(of_stack(stack)).group_by(UndoEntry.undone)
    )
    counted: dict[bool, int] = dict(rows.all())
    return Depth(undoable=counted.get(False, 0), redoable=counted.get(True, 0))


@contextmanager
def _turned(
    session: Session,
    stack: UndoStack,
    lock: StructureLocker,
    read: SnapshotReader,
    *,
    undoing: bool,
) -> Generator[Restoring]:
    """Undo or redo the entry on the edge of a stack: judged, restored by the block, marked.

    The entry is read under the lock of the stack, which no other writer of the stack passes; the
    objects it names, under the lock of their structure too, which a write of another stack —
    another contributor — holds while it moves them: judged there, they stay as judged until the
    block has restored them.
    """
    lock_stack(session, stack)
    # The last entry not undone, for an undoing; the last one undone — the lowest — for a redoing.
    edge = UndoEntry.rank.desc() if undoing else UndoEntry.rank.asc()
    entry = session.scalars(
        select(UndoEntry)
        .where(of_stack(stack), UndoEntry.undone == (not undoing))
        .order_by(edge)
        .limit(1)
    ).first()
    if entry is None:
        condition = UNDO_HISTORY_NOT_EMPTY if undoing else REDO_HISTORY_NOT_EMPTY
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": condition})
    left, wanted = (entry.after, entry.before) if undoing else (entry.before, entry.after)
    expected, restored = decoded(left), decoded(wanted)
    lock(expected + restored)
    _judge(expected, read)
    kept = {state.object_id for state in restored}
    available = depth(session, stack)
    restoring = Restoring(
        kind=cast("UndoneKind", entry.kind),
        node_ids=tuple(entry.node_ids),
        restored=restored,
        removed=tuple(state.object_id for state in expected if state.object_id not in kept),
        remaining_depth=(available.undoable if undoing else available.redoable) - 1,
    )
    yield restoring
    present = restoring.present()
    entry.undone = undoing
    session.flush()
    _follow(session, stack, {state.object_id: state.lock_version for state in present})


def _judge(expected: Snapshot, read: SnapshotReader) -> None:
    """Refuse an entry one of whose objects changed since: absent, or at another version."""
    present = {state.object_id: state for state in read(tuple(s.object_id for s in expected))}
    for state in expected:
        now = present.get(state.object_id)
        if now is None or now.lock_version != state.lock_version:
            label = state.label if now is None else now.label
            raise ConflictError(
                UNDO_CONFLICT,
                {"conflicting_object_id": str(state.object_id), "conflicting_object_label": label},
            )


def _follow(session: Session, stack: UndoStack, versions: dict[UUID, int]) -> None:
    """Carry the versions a restoring left to the entries that will be judged on them next.

    For each object, the nearest entry not undone that holds it in its ``after`` — the next
    undoing judges it there —, and the nearest entry undone that holds it in its ``before`` — the
    next redoing does.
    """
    for undone in (False, True):
        pending = dict(versions)
        edge = UndoEntry.rank.asc() if undone else UndoEntry.rank.desc()
        entries = session.scalars(
            select(UndoEntry).where(of_stack(stack), UndoEntry.undone == undone).order_by(edge)
        )
        for entry in entries:
            if not pending:
                break
            side = decoded(entry.before if undone else entry.after)
            found = {s.object_id: pending.pop(s.object_id) for s in side if s.object_id in pending}
            if not found:
                continue
            carried = encoded(with_versions(side, found))
            if undone:
                entry.before = carried
            else:
                entry.after = carried
    session.flush()
