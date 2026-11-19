# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reviews of a risk, the changes of its state (``reviewRisk``, ``listRiskReviews``; US-2590).

A review confirms or changes the probability and the state of a risk, dated the day it is made
(WF-RIS-0010, WF-RIS-0020): a dismissed risk identified again has its provision line recreated, an
identified one dismissed loses it; the occurrence is no review's (US-2620). Each review is kept in
the revision it was made in, never copied: the history of a risk read in a revision is that of the
marked revisions before it and its own (EP-08, "Tables et migrations").

Refused by the conditions of ``review`` (409), the risk unknown (404) or read at another counter
(412), then by the designations (422), nothing written; the current revision created first when
the project has none. Declared by US-2550/L1, the socle of EP-08; filled by US-2590/L1.
"""

from typing import TYPE_CHECKING

from waterfall.core.risks.reading import read_found, risk_view
from waterfall.core.risks.reviewing import list_reviews, review

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.views import RiskReviewEntry, RiskReviewView, RiskView


def review_risk(
    session: Session, project_id: UUID, entry: RiskReviewEntry, writer: Writer, viewer: Viewer
) -> RiskView:
    """Review a risk in the current revision, dated today; give it as the review leaves it."""
    revision_id = review(session, project_id, entry, writer, viewer)
    return risk_view(
        session, project_id, read_found(session, project_id, entry.risk_id, revision_id), viewer
    )


def list_risk_reviews(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID | None
) -> list[RiskReviewView]:
    """List the reviews of a risk read in a revision, the most recent first."""
    return list_reviews(session, project_id, risk_id, revision_id)
