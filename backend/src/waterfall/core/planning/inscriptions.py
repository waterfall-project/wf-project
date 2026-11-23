# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The inscriptions of the lineages no node holds any more, private to the module (US-3340).

An inscription (``tracking_entry``) follows its lineage from revision to revision and holds no key
to a node (WF-PLA-0060): what deletes the last node of a lineage — a task deleted, a revision
abandoned, a structure that goes with its owner — deletes its inscriptions too, or they stay in
the base, invisible (#4417). A lineage a marked revision still holds keeps its own.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.planning.tables import Node, TrackingEntry

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def delete_orphan_inscriptions(
    session: Session, project_id: UUID, lineages: Collection[UUID]
) -> None:
    """Delete the inscriptions of those of ``lineages`` that no node of the project holds.

    To be called after the nodes are deleted, in the same transaction.
    """
    if not lineages:
        return
    kept = set(
        session.scalars(
            select(Node.lineage_id).where(
                Node.project_id == project_id, Node.lineage_id.in_(lineages)
            )
        )
    )
    gone = set(lineages) - kept
    if gone:
        session.execute(
            delete(TrackingEntry)
            .where(TrackingEntry.project_id == project_id, TrackingEntry.lineage_id.in_(gone))
            .execution_options(synchronize_session=False)
        )
