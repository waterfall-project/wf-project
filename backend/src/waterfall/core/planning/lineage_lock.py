# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lock of the inscriptions of a lineage, taken by every write of them (#2499).

``tracking_entry`` is unique by lineage, kind and timeline in the project, and the lock of a
structure serializes the writes of one structure alone: two structures that share a lineage — the
main one and a differential copying it — would insert in parallel, and the violation of the
uniqueness would come out as a failure. ``setNodeTracking`` and the restoring of an entry of the
history take this lock, after that of their structure, so that their writes of one lineage come one
after the other whatever structure they are written under.
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, literal, select

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

# The first key of the advisory lock of the inscriptions of a lineage, the second being the hash of
# the project and the lineage: distinct from the keys of the other advisory locks of the service.
LINEAGE_LOCK = 3_700_040


def lock_lineage(session: Session, project_id: UUID, lineage_id: UUID) -> None:
    """Lock the inscriptions of a lineage until the end of the transaction."""
    key = f"{project_id}/{lineage_id}"
    session.execute(select(func.pg_advisory_xact_lock(LINEAGE_LOCK, func.hashtext(literal(key)))))
