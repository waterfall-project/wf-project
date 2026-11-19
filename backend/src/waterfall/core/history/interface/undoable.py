# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The kinds of entry another module than the planning undoes and redoes (EP-08).

The history keeps the entries of every module that writes in a revision, by their snapshots, and
reads no table of theirs: an undoing or a redoing gives back the objects to restore (``undo``,
``redo``), which the module that wrote them restores. The planning restores its own (``node``,
``task``, ``task_link``, ``tracking_entry``); a module above it says, by this registry, how it
restores the entries of its kinds — the risks their four (``risk_create``, ``risk_update``,
``risk_review``, ``risk_delete``; EP-08, "Modules") —, so that the frame of an undoing locks, reads
and restores them by that module and not by the planning. One module at most by kind; a kind none
registers is the planning's.

A write of the planning may move the version of an object of such a module aside from what it
writes, as a side effect: the deletion of a task, or its undoing, that carries the provision line
of a risk under another task advances the counter of the risk (US-2580/L1, #4010), and so does a
write of the own estimate of a risk. The module that moves it tells the history
(``moved_aside``), in the transaction of the write; the frame of an undoing or a redoing carries
those versions, with the ones it restored, to the entries of the stack that will be judged on them
next, so that the entry of the risk under it is not refused for a change its own stack made and
took back (``undo``).

Declared by US-2550/L1, the socle of EP-08, with nothing registered; filled by US-2590/L2, which
registers the kinds of the risks and has the undoing ask this registry.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface.recording import UndoneKind
    from waterfall.core.history.interface.undo import Restoring
    from waterfall.core.history.snapshots import Snapshot
    from waterfall.platform.audit import Act

# Where a transaction keeps the versions moved aside until the frame of an undoing takes them.
_MOVED = "history.moved_aside"


@dataclass(frozen=True, slots=True)
class Undoable:
    """How a module locks, reads and restores the objects of an entry of its kinds.

    ``asks`` the permissions the write of the entry asked for, one at least of which an undoing or
    a redoing asks for in turn (#2774). Each callable is given the session and the project of the
    entry. ``lock`` locks, until the end of the transaction, what the objects an entry left and
    wants back name, under the lock of the stack and before any reading (the frame's
    ``StructureLocker``); ``read`` reads the objects named as they are now, absent ones left out
    (``SnapshotReader``); ``restore`` brings back ``Restoring.restored``, deletes
    ``Restoring.removed`` under the act of the undoing, and hands the objects as it left them
    (``Restoring.keep_present``).
    """

    asks: tuple[str, ...]
    lock: Callable[[Session, UUID, Snapshot], None]
    read: Callable[[Session, UUID, tuple[UUID, ...]], Snapshot]
    restore: Callable[[Session, UUID, Restoring, Act], None]


# How each kind registered is undone and redone, by kind, in the order of registration.
_UNDOABLE: Registry[tuple[UndoneKind, Undoable]] = Registry("history.undoable")


def register_undoable(kind: UndoneKind, undoable: Undoable) -> Callable[[], None]:
    """Add how the entries of a kind are undone and redone; give its withdrawal; refused if held."""
    if kind in undoables():
        msg = f"the kind {kind} is undone by a module already"
        raise ValueError(msg)
    return _UNDOABLE.register((kind, undoable))


def undoables() -> dict[UndoneKind, Undoable]:
    """Give how each kind registered is undone and redone, by kind; none is the planning's."""
    return dict(_UNDOABLE.entries())


def moved_aside(session: Session, versions: Mapping[UUID, int]) -> None:
    """Tell the history the versions a write moved of objects it does not restore, by object.

    Kept in the transaction until the frame of an undoing or a redoing takes them (``taken_aside``);
    a write outside such a frame leaves them, which the next frame drops before it restores.
    """
    kept = cast("dict[UUID, int]", session.info.setdefault(_MOVED, {}))
    kept.update(versions)


def taken_aside(session: Session) -> dict[UUID, int]:
    """Give the versions moved aside since the last taking, and forget them."""
    return cast("dict[UUID, int]", session.info.pop(_MOVED, {}))
