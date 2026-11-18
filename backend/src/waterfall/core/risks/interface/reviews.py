# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reviews of a risk, the changes of its state (``reviewRisk``, ``listRiskReviews``; US-2590).

A review confirms or changes the probability and the state of a risk, dated the day it is made
(WF-RIS-0010, WF-RIS-0020): a dismissed risk identified again has its provision line recreated, an
identified one dismissed loses it; the occurrence is no review's (US-2620). Each review is kept in
the revision it was made in, never copied: the history of a risk read in a revision is that of the
marked revisions before it and its own (EP-08, "Tables et migrations").

Declared by US-2550/L1, the socle of EP-08; filled by US-2590/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.interface.risks import RiskState, RiskView


@dataclass(frozen=True, slots=True)
class RiskReviewEntry:
    """A review sent (``RiskReviewWrite``), at the counter of the risk read.

    ``provision_cost_category_id`` the category a dismissed risk identified again takes when the one
    it designated is no longer active and of the provision kind; ``None`` when not sent.
    """

    risk_id: UUID
    probability: Decimal
    state: RiskState
    lock_version: int
    provision_cost_category_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RiskReviewView:
    """A review as it is read (``RiskReview``): its day, what it retained, who made it and when.

    ``actor`` is the account that made it, or the platform when null.
    """

    reviewed_on: date
    probability: Decimal
    severity: Decimal
    state: RiskState
    actor: UUID | None
    created_at: datetime


def review_risk(
    session: Session, project_id: UUID, entry: RiskReviewEntry, writer: Writer, viewer: Viewer
) -> RiskView:
    """Review a risk in the current revision, dated today; give it as the review leaves it."""
    msg = "review_risk is filled by US-2590/L1"
    raise NotImplementedError(msg)


def list_risk_reviews(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID | None, viewer: Viewer
) -> list[RiskReviewView]:
    """List the reviews of a risk read in a revision, the most recent first."""
    msg = "list_risk_reviews is filled by US-2590/L1"
    raise NotImplementedError(msg)
