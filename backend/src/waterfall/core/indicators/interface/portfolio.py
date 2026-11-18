# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The documents of the projects the portfolio sums, kept and of the day (EP-11, US-2680/L1).

The portfolio never reads the lines of a project: it sums documents (EP-11, "Ce que le cadrage
décide"). At the marking, ``keep_document`` writes in ``revision_indicator`` a document of a kind of
the portfolio that ``core/portfolio`` computed, at the ``Act`` of the marking, of the scope
``project``. At a past date, ``kept_documents_of`` reads those of several revisions, in one
query. On the current day, ``day_documents_of`` gives those of several projects by the cache of the
day, under the fingerprint of each project; ``contribute`` computes what an entry lacks. An offer
gives its curves of the month (``offer_curves``), by the series of its estimate.

Declared by US-2670/L1, the socle of EP-11; filled by US-2680/L1.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document, IndicatorKind
    from waterfall.platform.audit import Act

# What computes the documents of the portfolio of a project on the current day, its revision of the
# day given: the computation of ``core/portfolio``, the same as at the marking.
type Contribute = Callable[[Session, UUID, UUID, datetime], Mapping[IndicatorKind, Document]]


def keep_document(
    session: Session, revision_id: UUID, kind: IndicatorKind, document: Document, act: Act
) -> None:
    """Keep a document of the portfolio of a revision, in the transaction of its marking."""
    msg = "keep_document is filled by US-2680/L1"
    raise NotImplementedError(msg)


def kept_documents_of(
    session: Session, revision_ids: Collection[UUID], kinds: Collection[IndicatorKind]
) -> dict[UUID, dict[IndicatorKind, Document]]:
    """Give the documents of these kinds that marked revisions kept, by revision, in one query."""
    msg = "kept_documents_of is filled by US-2680/L1"
    raise NotImplementedError(msg)


def day_documents_of(
    session: Session, project_ids: Collection[UUID], at: datetime, contribute: Contribute
) -> dict[UUID, dict[IndicatorKind, Document]]:
    """Give the documents of the day of projects, by project, from the cache or computed."""
    msg = "day_documents_of is filled by US-2680/L1"
    raise NotImplementedError(msg)


def offer_curves(session: Session, revision_id: UUID, at: datetime) -> Document:
    """Give the series of the month of the estimate of an offer, provisions and delays apart."""
    msg = "offer_curves is filled by US-2680/L1"
    raise NotImplementedError(msg)
