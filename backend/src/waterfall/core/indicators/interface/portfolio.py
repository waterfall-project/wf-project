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
  project, those not kept computed by ``contributing`` and written (``contributions``); an entry
  answers every kind the caller names, and one that lacks one is computed again (#4193).
- ``offer_curves`` (US-2680/L1b, #4156) gives the series of the month of the estimate of an offer,
  as the two ``CurveSeries`` of a project, ``cost_curve`` and ``cost_curve_payment_delays``: the
  reference budget on its lines without the provision lines, no actual cost, the projection of the
  project manager provisions included, spread from the day of the computation on a base of nought,
  the cash-out by month with the delays only. The provision lines are read as EP-08 reads them for
  the curves of a project (``lines_for_indicators(provisions=True)``, US-2630/L1): one rule of the
  provisions in the curves. The portfolio sums an offer as a project (US-2740).

Declared by US-2670/L1, the socle of EP-11; filled by US-2680/L1, and by US-2680/L1b (#4156) for
``offer_curves``, whose context a marking keeps since US-2680/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from sqlalchemy import select

from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.computing import Basis
from waterfall.core.indicators.contributions import contributions
from waterfall.core.indicators.curving import read_curve_sources
from waterfall.core.indicators.offering import offer_curves_document
from waterfall.core.indicators.shaping import Context
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import current_day
from waterfall.core.revisions.interface import revision_marked_at, revision_project
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


# The bound of the statements the fingerprint of one project reads (``day_documents_of``): nine
# before the provisions and the occurrences of the risks (US-2630/L1, EP-08), eleven since.
STATEMENTS_PER_PROJECT = 11
# The statements a reading of the day reads once, whatever its projects: the stamp of the roles
# (US-2680/L2, #4158).
STATEMENTS_PER_READING = 1


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


@dataclass(frozen=True, slots=True)
class Contributing:
    """What gives the contribution of a project of the day: its computation, the kinds it answers.

    ``kinds`` are the kinds every entry of the cache answers, a document or none: an entry kept that
    lacks one of them is partial, and is computed again (#4193). A kind ``compute`` does not give
    for a project is absent from what is served for it.
    """

    compute: Contribute
    kinds: tuple[IndicatorKind, ...]


def keep_document(
    session: Session, revision_id: UUID, kind: IndicatorKind, document: Document, act: Act
) -> None:
    """Keep a document of the portfolio of a revision, in the transaction of its marking.

    For the scope ``project``, at the instant and by the requester of ``act``, the act of the
    marking (``register_indicators``). A kind that is not of the portfolio is a fault of the caller
    (``ValueError``). A second document of a kind for the revision is refused by the table, at the
    flush here: an ``IntegrityError`` (unique constraint).
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
    contributing: Contributing,
    cache: IndicatorsCache | None = None,
) -> dict[UUID, dict[IndicatorKind, Document]]:
    """Give the documents of the day of projects, by project, from the cache or computed.

    ``revisions`` maps each project to the revision of its day, which the caller selected: the
    current revision, else the last marked (``RetainedProject.revision_id``, from
    ``last_marked_at_instant``). This function never selects it, so that the choice exists once.
    The caller drops the projects with no retained revision (``RetainedProject.revision_id`` is
    then null): they contribute to no sum. ``at`` is the instant of the reading, its day that of
    the key. Given ``cache``, the cache of the process, the entries of the projects are read in one
    exchange and those missing computed by ``contributing`` and written; without it, every project
    is computed. Every project asked has its entry, in the order given; an entry kept that lacks one
    of the kinds of ``contributing`` is computed again (#4193).

    Cost: the fingerprint of a project is read by about eleven statements, project after project,
    even when Redis answers all: a number of statements that grows with the number of projects,
    bounded per project (``STATEMENTS_PER_PROJECT``), and one more for the reading, the stamp of
    the roles (``STATEMENTS_PER_READING``); the exchanges with Redis do not grow (one to read, one
    to write). A document that is not JSON, as computed — a ``NaN`` included —, raises
    ``UnserializableContributionError``, with a cache or without.
    """
    return contributions(session, revisions, at, contributing, cache)


def offer_curves(
    session: Session, revision_id: UUID, at: datetime, *, marking: bool = False
) -> Document:
    """Give the series of the month of the estimate of an offer, provisions apart and included.

    The document has two ``CurveSeries``, ``cost_curve`` and ``cost_curve_payment_delays``, on the
    day of ``at``: see ``offer_curves_document``. Of the day, the context is ``marked`` for a
    revision marked, ``draft`` otherwise, ``is_stored`` false; for ``marking``, the revision being
    marked at ``at``, the instant of its act, the context is the one a marking keeps — ``marked``,
    ``is_stored`` true —, as ``store_indicators`` writes its curves (US-2680/L2).
    """
    project_id = revision_project(session, revision_id)
    sources = read_curve_sources(session, Basis(project_id, revision_id, revision_id))
    marked = marking or revision_marked_at(session, revision_id) is not None
    status = "marked" if marked else "draft"
    context = Context(revision_id, status, at, PROJECT, is_stored=marking)
    return offer_curves_document(
        sources.reference, sources.lines, sources.remaining, current_day(at), context
    )
