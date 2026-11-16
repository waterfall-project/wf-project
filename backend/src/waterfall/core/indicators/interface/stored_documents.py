# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A document a marked revision kept, read as it was kept (WF-DAT-0040; US-1670/L1).

What the readings of a marked revision answer: those of EP-10, and those of the indicators of the
estimate (EP-07) and of the remaining to commit (EP-09), which keep their computation for the
current revision (EP-10, "La conservation au marquage"; US-1670/L2). None for a kind and a scope the
marking did not keep: the indicators of the project, for a revision marked before In progress; a
subproject created after the marking.

Declared by US-1660/L1, the socle of EP-10; filled by US-1670/L1, which keeps the documents.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.revisions.interface import revision_project

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.interface.documents import Document, IndicatorKind


def stored_document(
    session: Session, revision_id: UUID, kind: IndicatorKind, scope: CostScope
) -> Document | None:
    """Give the document of a kind and a scope a revision kept at its marking, or none.

    The table is partitioned by project: the project of the revision is read first and named in the
    filter, so that only its partition is probed (404 for a revision that does not exist).
    """
    project_id = revision_project(session, revision_id)
    return session.scalar(
        select(RevisionIndicator.document).where(
            RevisionIndicator.project_id == project_id,
            RevisionIndicator.revision_id == revision_id,
            RevisionIndicator.kind == kind,
            RevisionIndicator.scope == str(scope),
        )
    )
