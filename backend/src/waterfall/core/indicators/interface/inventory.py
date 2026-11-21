# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The digest of what a marked revision kept of its indicators, which a backup and its test compare.

The manifest of a backup gives it for a sample of the marked revisions, and the test of a
restoration computes it again in the database restored: kept indicators are never computed again
(WF-DAT-0140), so a digest that differs says a document changed or lost (US-2930, WF-EXP-0060). A
digest stands for the documents, which the head of an archive, where the manifest is, could not
hold.
"""

import hashlib
import json
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.indicators.tables import RevisionIndicator

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def kept_indicators_digest(session: Session, project_id: UUID, revision_id: UUID) -> str:
    """Give the SHA-256 of the documents a revision kept, each with its kind, scope and instant.

    Read in the partition of the project, in the order of their kind then their scope, and written
    in a form that does not depend on that of the database. A revision that kept none, or that is
    not there, gives the digest of nothing, which a revision that kept some never gives.
    """
    kept = session.execute(
        select(
            RevisionIndicator.kind,
            RevisionIndicator.scope,
            RevisionIndicator.computed_at,
            RevisionIndicator.document,
        )
        .where(
            RevisionIndicator.project_id == project_id,
            RevisionIndicator.revision_id == revision_id,
        )
        .order_by(RevisionIndicator.kind, RevisionIndicator.scope)
    )
    written = [
        [kind, scope, computed_at.isoformat(), document]
        for kind, scope, computed_at, document in kept
    ]
    canonical = json.dumps(written, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
