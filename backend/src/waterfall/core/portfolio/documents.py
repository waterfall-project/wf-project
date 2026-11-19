# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The documents of EP-10 that the list and the value of the portfolio sum (US-2690).

The portfolio never reads the lines of a project (EP-11, "Ce que le cadrage décide"): of each
project it retains and that contributes, it reads the document ``project`` — the indicators of a
project In progress or Completed — or the document ``estimate`` — the total of the quote of an
offer —, by its revision. On the current day they are computed by the computation of the
indicators and of the estimate, once, and kept by the cache of the indicators under the
fingerprint of the project (``day_documents_of``); at a past date, they are those the last
revision marked by the end of the day kept, in one statement for all the projects
(``kept_documents_of``), no line of a task or of a quote being read (WF-DAT-0040). The document
``remaining`` is not read: the projection of the project manager and its variance are in the
document ``project``.

Not a part of the interface of the portfolio: the views of this story read through it.
"""

from typing import TYPE_CHECKING

from waterfall.core.costs.interface import PROJECT
from waterfall.core.estimate.interface import IndicatorsAsked, estimate_indicators
from waterfall.core.indicators.interface import (
    current_day_reading,
    day_documents_of,
    day_indicators,
    estimate_document,
    kept_documents_of,
)
from waterfall.core.projects.interface import project_facts

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.core.portfolio.interface.scope import PortfolioReading, ResolvedScope

PRICING = "pricing"
# The kinds the list and the value read: a project In progress or Completed has its ``project``, an
# offer its ``estimate``.
KINDS: tuple[IndicatorKind, ...] = ("project", "estimate")

type Documents = Mapping[IndicatorKind, Document]


def day_contribution(
    session: Session, *, project_id: UUID, revision_id: UUID, at: datetime
) -> Documents:
    """Give the document of the day a project contributes: its estimate if an offer, else its own.

    The same documents as the readings of the project give (``getEstimateIndicators``,
    ``getProjectIndicators``), on the revision of the day, zones null: they are classified when
    the list is read, on the thresholds of that day (WF-REF-0170).
    """
    if project_facts(session, project_id).state == PRICING:
        asked = IndicatorsAsked(revision_id, str(PROJECT), at)
        return {"estimate": estimate_document(estimate_indicators(session, project_id, asked))}
    reading = current_day_reading(session, project_id, at)
    return {"project": day_indicators(session, reading, (PROJECT,), None)[PROJECT]}


def documents_of(
    session: Session, resolved: ResolvedScope, reading: PortfolioReading
) -> Mapping[UUID, Documents]:
    """Give the documents of the projects a scope retains and that contribute, by project.

    A project with no revision to contribute by (``RetainedProject.revision_id`` null) has no
    entry: it figures in a list without a figure and adds to no sum. On the current day, the
    documents are those of the day, from the cache of ``reading`` if it has one; at a past date,
    those kept.
    """
    revisions = {
        project_id: each.revision_id
        for project_id, each in resolved.projects.items()
        if each.revision_id is not None
    }
    if resolved.on_current_day:
        return day_documents_of(session, revisions, reading.at, day_contribution, reading.cache)
    kept = kept_documents_of(session, set(revisions.values()), KINDS)
    return {project_id: kept[revision_id] for project_id, revision_id in revisions.items()}
