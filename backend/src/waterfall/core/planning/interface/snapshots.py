# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The snapshots of the nodes the history keeps, and the last change of a caller undone or redone.

Each write of the planning takes the snapshot of the nodes it creates, changes or deletes — their
rows of ``node``, ``task``, ``task_link`` and ``tracking_entry`` — before and after it, and hands
both to the history (``history.recording``), which keeps them without reading any table of the
planning (EP-06, "L'historique annulable"). An undoing or a redoing gives back a snapshot, which
the planning restores — rows created, changed or deleted — under the rules of the entry, then
redates the structure (``restore``, ``restoring``).

Declared by US-1380/L1; ``snapshot`` filled by US-1380/L2: each node present, in the order named,
at its version, named by the label of its task, its rows written as JSON holds them (see
``snapshotting``). A node absent is left out: one a write creates is absent before it, one it
deletes after it. ``restore``, ``undo_last_change`` and ``redo_last_undo`` are US-1450/L2's.

An undoing is a write like any other (WF-IHM-0110): its revision judged under its lock (409), the
stack of the caller locked by the frame of the history (``history.undo``), then the structure of the
entry, found from the objects the entry names — the nodes it created or the ones it deleted, a
structure for the planning start —, and locked by that frame and by it alone (``lock``, #2476).
The entry is then judged on the objects as they are (409 ``UNDO_CONFLICT``), the permission of its
kind checked (403 ``PERMISSION_MISSING``), and its objects restored (``restoring``), the structure
redated. A caller whose token carries no session of sign-in has no stack: refused by 403
``SESSION_ID_MISSING`` (#2472), whereas a write it makes passes, without an entry.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.history import interface as history
from waterfall.core.history.interface import UndoStack
from waterfall.core.planning.restoring import bring_back, read_objects, structure_of
from waterfall.core.planning.snapshotting import taken
from waterfall.core.planning.writing import Place, facts_of, judge_revision
from waterfall.platform.errors import ForbiddenError

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import Restoring, Snapshot, UndoneKind
    from waterfall.core.planning.writing import NodesWritten, Writer
    from waterfall.core.revisions.interface import StructureFacts

PERMISSION_MISSING = "PERMISSION_MISSING"
SESSION_ID_MISSING = "SESSION_ID_MISSING"
PLANNING_WRITE = "planning.write"
# The permission an entry of each kind asks for, beyond the planning (WF-ADM-0100): the state of
# a task is an entry of the remaining to commit.
ASKS = {"progress": "remaining.write", "remaining": "remaining.write"}


def snapshot(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> Snapshot:
    """Give the rows of the nodes named, their facets, links and inscriptions, as they are."""
    return taken(session, project_id, node_ids)


def restore(
    session: Session, place: Place, facts: StructureFacts, restoring: Restoring, writer: Writer
) -> NodesWritten:
    """Restore the objects an entry of the history gives back, and redate its structure.

    Called inside the frame of the history, which holds the lock of the structure (``facts`` are
    those it read under that lock): the nodes the entry's undoing deletes first, those it brings
    back rewritten or written again, with their facet, their links and their inscriptions
    (``restoring``). Refused by 409 ``UNDO_CONFLICT`` when another change holds what the entry
    would take back; nothing is written then.
    """
    return bring_back(session, place, facts, restoring, writer)


@dataclass(frozen=True, slots=True)
class UndoDone:
    """What an undoing or a redoing did: the kind and the nodes of the entry, what it wrote.

    ``remaining_depth`` is what remains to undo — to redo, for a redoing — after this one.
    """

    kind: UndoneKind
    node_ids: tuple[UUID, ...]
    written: NodesWritten
    remaining_depth: int


def _stack(revision_id: UUID, writer: Writer) -> UndoStack:
    """Give the stack of a writer in a revision, or refuse a writer that has none (403)."""
    author, session_id = writer.act.author, writer.session_id
    if author is None or session_id is None:
        raise ForbiddenError(SESSION_ID_MISSING)
    return UndoStack(revision_id, author, session_id)


def _turned(
    session: Session,
    revision: tuple[UUID, UUID],
    writer: Writer,
    permissions: Collection[str],
    *,
    undoing: bool,
) -> UndoDone:
    """Undo or redo the entry on the edge of the stack of a writer, in the frame of the history.

    ``revision`` is its project and itself.
    """
    project_id, revision_id = revision
    stack = _stack(revision_id, writer)
    judge_revision(session, project_id, revision_id)
    held: list[tuple[Place, StructureFacts]] = []

    def lock(states: Snapshot) -> None:
        """Lock the structure the objects of the entry name, and read it under that lock."""
        place = Place(project_id, revision_id, structure_of(states))
        held.append((place, facts_of(session, place, lock=True)))

    def read(object_ids: tuple[UUID, ...]) -> Snapshot:
        return read_objects(session, project_id, object_ids)

    frame = history.undo if undoing else history.redo
    with frame(session, stack, lock=lock, read=read) as restoring:
        asked = ASKS.get(restoring.kind, PLANNING_WRITE)
        if asked not in permissions:
            raise ForbiddenError(PERMISSION_MISSING, {"missing_permission": asked})
        place, facts = held[0]
        written = restore(session, place, facts, restoring, writer)
    return UndoDone(restoring.kind, restoring.node_ids, written, restoring.remaining_depth)


def undo_last_change(
    session: Session,
    project_id: UUID,
    revision_id: UUID,
    writer: Writer,
    permissions: Collection[str],
) -> UndoDone:
    """Undo the last change of the caller in a revision, and give the nodes written.

    Refused by 403 ``SESSION_ID_MISSING`` for a writer without a session of sign-in, 409 on a
    revision that no longer accepts a write, on an empty stack (``undo_history_not_empty``) or a
    change another contributor took up since (``UNDO_CONFLICT``), 403 ``PERMISSION_MISSING`` for
    whoever no longer holds the permission of the entry; nothing is undone then.
    """
    return _turned(session, (project_id, revision_id), writer, permissions, undoing=True)


def redo_last_undo(
    session: Session,
    project_id: UUID,
    revision_id: UUID,
    writer: Writer,
    permissions: Collection[str],
) -> UndoDone:
    """Redo the last undoing of the caller in a revision, refused as ``undo_last_change`` is."""
    return _turned(session, (project_id, revision_id), writer, permissions, undoing=False)
