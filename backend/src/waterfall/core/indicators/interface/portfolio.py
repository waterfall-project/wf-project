# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The documents of the projects the portfolio sums, kept and of the day (EP-11, US-2680/L1).

The portfolio never reads the lines of a project: it sums documents (EP-11, "Ce que le cadrage
décide"). Each is a JSON object of a kind of ``revision_indicator``, of the scope ``project``; its
form is that of the computation of ``core/portfolio`` that gives it, which these functions neither
read nor change.

- ``keep_document`` writes a document of one of the five kinds of the portfolio
  (``PORTFOLIO_KINDS``) for a revision being marked, in the transaction of its marking, at the
  ``Act`` of the marking: ``computed_at`` and ``created_at`` its instant, ``created_by`` its
  requester. The row is flushed at once, while the revision is still current; the triggers of the
  table refuse it otherwise — a revision already marked, a transaction that does not mark it, an
  instant that is not its ``marked_at`` (#3549) —, and refuse any change or deletion after
  (WF-DAT-0020). A kind of EP-10 is the marking's own (``store_indicators``) and is refused here.
- ``kept_documents_of`` reads, in one statement, the documents of the kinds asked that marked
  revisions kept for the project — those of the portfolio, and those of EP-10 (``project``,
  ``estimate``, ``remaining``, the curves) —, by revision. A revision that kept no document of a
  kind — marked before EP-11, an offer without the indicators of a project — lacks that kind:
  it does not contribute (EP-11, "La contribution d'un projet"). Every revision asked has its
  entry, empty when it kept none.
- ``day_documents_of`` gives the documents of the day of several projects, each on the revision
  of its day that the caller selected, from the cache of the indicators under the fingerprint of the
  project, those not kept computed by ``contribute`` and written (``contributions``).
- ``offer_curves``, the series of the month of the estimate of an offer, provision lines apart
  and included: still declared, the reading of the provision lines of an estimate being undecided
  (no interface of ``core/estimate`` gives them with their task).

Declared by US-2670/L1, the socle of EP-11; filled by US-2680/L1.
"""

from typing import TYPE_CHECKING, Protocol, cast

from sqlalchemy import select

from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.contributions import contributions
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.revisions.interface import revision_project
from waterfall.platform.database import among
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document, IndicatorKind
    from waterfall.platform.audit import Act
    from waterfall.platform.cache import IndicatorsCache

# The kinds of a document of the portfolio (EP-11, "Tables et migrations"), which ``keep_document``
# alone writes; the other kinds are those of the marking of EP-10.
PORTFOLIO_KINDS: frozenset[IndicatorKind] = frozenset(
    {
        "portfolio_workload",
        "portfolio_cost_structure",
        "portfolio_risks",
        "portfolio_milestones",
        "portfolio_offer_curves",
    }
)


class Contribute(Protocol):
    """What computes the documents of the portfolio of a project on the current day.

    The revision of the day is given, never chosen here: the computation of ``core/portfolio``, the
    same as at the marking. Named parameters, so that a project and a revision cannot be swapped.
    """

    def __call__(
        self, session: Session, *, project_id: UUID, revision_id: UUID, at: datetime
    ) -> Mapping[IndicatorKind, Document]:
        """Give the documents of the portfolio of ``revision_id``, a revision of ``project_id``."""
        ...


def keep_document(
    session: Session, revision_id: UUID, kind: IndicatorKind, document: Document, act: Act
) -> None:
    """Keep a document of the portfolio of a revision, in the transaction of its marking.

    For the scope ``project``, at the instant and by the requester of ``act``, the act of the
    marking (``register_indicators``). A kind that is not of the portfolio is a fault of the caller
    (``ValueError``), as is a second document of a kind for the revision, which the table refuses.
    """
    if kind not in PORTFOLIO_KINDS:
        msg = f"{kind} is not a kind of the portfolio: the marking of EP-10 keeps it"
        raise ValueError(msg)
    session.add(
        RevisionIndicator(
            project_id=revision_project(session, revision_id),
            id=new_id(),
            revision_id=revision_id,
            kind=kind,
            scope=str(PROJECT),
            document=document,
            computed_at=act.at,
            created_at=act.at,
            created_by=act.author,
        )
    )
    session.flush()


def kept_documents_of(
    session: Session, revision_ids: Collection[UUID], kinds: Collection[IndicatorKind]
) -> dict[UUID, dict[IndicatorKind, Document]]:
    """Give the documents of these kinds that marked revisions kept, by revision, in one query.

    The documents of the scope ``project``; every revision asked has its entry, empty when it kept
    none of the kinds. No statement for no revision or no kind.
    """
    kept: dict[UUID, dict[IndicatorKind, Document]] = {each: {} for each in revision_ids}
    if not kept or not kinds:
        return kept
    rows = session.execute(
        select(RevisionIndicator.revision_id, RevisionIndicator.kind, RevisionIndicator.document)
        .where(
            among(RevisionIndicator.revision_id, kept),
            RevisionIndicator.kind.in_(sorted(set(kinds))),
            RevisionIndicator.scope == str(PROJECT),
        )
        .order_by(RevisionIndicator.revision_id, RevisionIndicator.kind)
    )
    for revision_id, kind, document in rows:
        kept[revision_id][cast("IndicatorKind", kind)] = document
    return kept


def day_documents_of(
    session: Session,
    revisions: Mapping[UUID, UUID],
    at: datetime,
    contribute: Contribute,
    cache: IndicatorsCache | None,
) -> dict[UUID, dict[IndicatorKind, Document]]:
    """Give the documents of the day of projects, by project, from the cache or computed.

    ``revisions`` maps each project to the revision of its day, which the caller selected: the
    current revision, else the last marked (``RetainedProject.revision_id``, from
    ``last_marked_at_instant``). This function never selects it, so that the choice exists once.
    The caller drops the projects with no retained revision (``RetainedProject.revision_id`` is
    then null): they contribute to no sum. ``at`` is the instant of the reading, its day that of
    the key. Given ``cache``, the cache of the process, the entries of the projects are read in one
    exchange and those missing computed by ``contribute`` and written; without it, every project is
    computed. Every project asked has its entry, in the order given.
    """
    return contributions(session, revisions, at, contribute, cache)


def offer_curves(session: Session, revision_id: UUID, at: datetime) -> Document:
    """Give the series of the month of the estimate of an offer, provisions and delays apart."""
    msg = "offer_curves is filled by US-2680/L1"
    raise NotImplementedError(msg)
