# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The undoing and the redoing of the entries of a stack, and its depth (WF-IHM-0110).

``undo`` reads the last entry not undone of a stack, checks that each node of its ``after`` is
still at its version — else 409 ``UNDO_CONFLICT``, the object taken back named —, marks it undone
and gives back the nodes to restore (its ``before``), which the planning rewrites and redates;
``redo`` does the same with ``after``. ``depth`` tells what each would find (EP-06, "L'historique
annulable").

Declared by US-1380/L1; US-1450/L1 fills it, and gives each its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.history.interface.recording import UndoStack


def undo(session: Session, stack: UndoStack) -> None:
    """Undo the last entry not undone of a stack, and give back the nodes to restore."""
    msg = "undo is filled by US-1450/L1"
    raise NotImplementedError(msg)


def redo(session: Session, stack: UndoStack) -> None:
    """Redo the last entry undone of a stack, and give back the nodes to restore."""
    msg = "redo is filled by US-1450/L1"
    raise NotImplementedError(msg)


def depth(session: Session, stack: UndoStack) -> None:
    """Tell how many entries of a stack may be undone, and how many redone."""
    msg = "depth is filled by US-1450/L1"
    raise NotImplementedError(msg)
