# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the witness, kept and of the day, compared with the examples.

Laid by US-1660/L1, the socle of EP-10, so that no two stories create the same file;
US-1740 writes its tests here (EP-10, "Les tests du back").
"""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from test_witness_projects import REVISION_100, REVISION_101

from waterfall.core.indicators.tables import RevisionIndicator

if TYPE_CHECKING:
    from uuid import UUID

    from waterfall.platform.database import Database


def kinds_of(database: Database, revision_id: UUID) -> set[str]:
    """Give the kinds of document a revision of the witness kept."""
    with database.transaction() as session:
        found = session.scalars(
            select(RevisionIndicator.kind).where(RevisionIndicator.revision_id == revision_id)
        )
        return set(found)


@pytest.mark.requirement("WF-DAT-0040-A")
def test_the_witness_loaded_keeps_the_indicators_of_its_marked_revisions(witness: Database) -> None:
    # ``load_marking`` marks each revision of the witness by the transaction of the worker, so that
    # ``compute_indicators`` keeps its documents: the offer 100, marked in pricing, its estimate and
    # its remaining; the amendment 101, marked In progress, those two and its project indicators.
    # The three curves are US-1690/L3's, which adds their kinds here; no slice is kept.
    assert kinds_of(witness, REVISION_100) == {"estimate", "remaining"}
    assert kinds_of(witness, REVISION_101) == {"estimate", "remaining", "project"}
