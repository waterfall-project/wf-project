# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The snapshots of the nodes the history keeps, and their restitution.

Each write of the planning takes the snapshot of the nodes it creates, changes or deletes — their
rows of ``node``, ``task``, ``task_link`` and ``tracking_entry`` — before and after it, and hands
both to the history (``history.recording``), which keeps them without reading any table of the
planning (EP-06, "L'historique annulable"). An undoing or a redoing gives back a snapshot, which
the planning restores — rows created, changed or deleted — under the rules of the entry, then
redates the structure.

Declared by US-1380/L1; US-1380/L2 fills ``snapshot``, US-1450/L2 ``restore``, each giving its
arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def snapshot(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> None:
    """Give the rows of the nodes named, their facets, links and inscriptions, as they are."""
    msg = "snapshot is filled by US-1380/L2"
    raise NotImplementedError(msg)


def restore(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Restore the rows of a snapshot the history gives back, and redate the structure."""
    msg = "restore is filled by US-1450/L2"
    raise NotImplementedError(msg)
