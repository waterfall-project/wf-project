# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the history does before a revision is marked or abandoned: its stacks and plans removed.

Registered at the import of the interface in the closing of the revisions (``register_closing``),
under the stage ``history``, which runs first: the planning deletes its nodes after it, under the
stage ``content`` (EP-06, "Les points d'extension"). The entries and the plans of the revision are
deleted, as no write of it will be undone any more (WF-IHM-0110): every stack of every account and
every session, under the lock of the revision the closing holds.

``forget_structure`` does the same for one structure, a differential abandoned
(``deleteCostStructure``, US-2550/L4): the entries that touch it, in every stack, and the plans of
a paste that aim at it.

Declared by US-1380/L1; filled by US-1450/L1.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.history.snapshots import decoded
from waterfall.core.history.tables import PastePlan, UndoEntry

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionClosing


def close_history(closing: RevisionClosing) -> None:
    """Delete the entries and the plans of a revision about to be marked or abandoned."""
    session = closing.session
    session.execute(delete(UndoEntry).where(UndoEntry.revision_id == closing.revision_id))
    session.execute(delete(PastePlan).where(PastePlan.revision_id == closing.revision_id))


def forget_structure(
    session: Session, revision_id: UUID, structure_id: UUID, node_ids: Collection[UUID]
) -> None:
    """Delete the entries and the plans of a structure about to be deleted, in every stack.

    An entry belongs to the structure when it names one of its nodes (``node_ids``) or, an entry of
    a write of the structure itself, which names none, when its snapshot holds the structure. No
    write of it will be undone or redone any more (WF-IHM-0110); the stacks of the others keep
    their entries, their ranks left with a gap, which the order of the stack does not mind. To be
    called under the lock of the structure.
    """
    named = list(node_ids)
    touching = UndoEntry.kind == "structure_update"
    if named:
        touching = touching | UndoEntry.node_ids.overlap(named)
    entries = session.scalars(
        select(UndoEntry).where(UndoEntry.revision_id == revision_id, touching)
    ).all()
    for entry in entries:
        if set(entry.node_ids) & set(named) or any(
            state.object_id == structure_id
            for state in (*decoded(entry.before), *decoded(entry.after))
        ):
            session.delete(entry)
    session.execute(delete(PastePlan).where(PastePlan.structure_id == structure_id))
    session.flush()
