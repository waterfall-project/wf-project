# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The stacks of the history, private to the module: their lock and their rows.

A stack is the entries of a revision, of an account and of its session of sign-in (``UndoStack``).
Whatever writes it — a new entry, an undoing, a redoing — locks it first, by an advisory lock of
the transaction keyed by the stack: two writes of one stack never interleave, and two stacks never
wait for each other but by a collision of the hash, which only delays.
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, literal, select

from waterfall.core.history.tables import UndoEntry

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

    from waterfall.core.history.interface.recording import UndoStack

# The first key of the advisory lock of a stack, the second being the hash of the stack: distinct
# from the keys of one number of the service (the pair and the single key are two spaces anyway).
STACK_LOCK = 3_700_030


def lock_stack(session: Session, stack: UndoStack) -> None:
    """Lock a stack until the end of the transaction: its writers come one after the other."""
    key = f"{stack.revision_id}/{stack.user_account_id}/{stack.session_id}"
    session.execute(select(func.pg_advisory_xact_lock(STACK_LOCK, func.hashtext(literal(key)))))


def of_stack(stack: UndoStack) -> ColumnElement[bool]:
    """Select the entries of a stack."""
    return (
        (UndoEntry.revision_id == stack.revision_id)
        & (UndoEntry.user_account_id == stack.user_account_id)
        & (UndoEntry.session_id == stack.session_id)
    )
