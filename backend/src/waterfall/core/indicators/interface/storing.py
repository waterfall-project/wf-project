# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a revision keeps of its indicators at its marking (WF-DAT-0040, WF-IND-0010; US-1670/L1).

``store_indicators`` is the entry of the indicators in ``register_indicators`` of the revisions:
called in the transaction of the marking, after what the estimate keeps (its images and its rates,
which its amounts read) and before the revision is written, it reads the state of the project —
locked by ``run_marking`` before the marking; read without a lock by the loader of the witness, in
one transaction — and its reference, then writes the documents of the revision (EP-10, "La
conservation au marquage"):

- ``estimate``, the indicators of the estimate of the revision (``estimate_indicators``, EP-07),
  for the project, the lines out of any subproject (``unassigned``) and each subproject of the
  project;
- ``remaining``, the indicators of its remaining to commit (``remaining_indicators``, EP-09), the
  coverage of the risks included (EP-08), once, for the project: the contract reads them on no
  other scope, each subproject having its balance in the document;
- ``project``, the project In progress alone, its earned value indicators on each of those scopes,
  computed in one pass on the day of the marking in the time zone of the installation, on the
  reference of the project and the actual cost known then (WF-IND-0010): a line of cost dated
  after that day counts nought, and a line imported after the marking never enters. A project
  before In progress keeps none (an offer in pricing keeps its estimate alone);
- the three curves — ``cost_curve``, ``cost_curve_payment_delays``, ``earned_value_curves`` —, of
  the project In progress, on each scope too, drawn on the same day and the same lines of cost
  known then (WF-IND-0100, WF-IND-0110; US-1690/L3).

Each document is the answer of the contract of its kind for its scope, its context the revision
``marked``, ``computed_at`` the instant of the marking (``act.at``), ``is_stored`` true, and the
zone of each index null, classified at each reading on the thresholds of that day (WF-REF-0130).
The rows bear the instant of the marking and its requester, and are written at once, while the
revision is still current: the triggers of the table refuse any row after (WF-DAT-0020).

Nothing is caught: a computation that raises fails the marking, nothing being written
(``compute_indicators``, #2180).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.costs.interface import PROJECT, UNASSIGNED
from waterfall.core.estimate import interface as estimate
from waterfall.core.estimate.interface import IndicatorsAsked, estimate_indicators
from waterfall.core.indicators.computing import Basis, day_documents
from waterfall.core.indicators.curving import (
    cost_curve_document,
    curves_of_scope,
    earned_value_curves_document,
    read_curve_sources,
)
from waterfall.core.indicators.interface.estimate_documents import (
    estimate_document,
    remaining_document,
)
from waterfall.core.indicators.shaping import Context, instant
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import (
    SubprojectFilters,
    SubprojectSort,
    Viewer,
    current_day,
    list_subprojects,
    project_facts,
)
from waterfall.core.revisions.interface import reference_at_marking, revision_project
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.interface.documents import Document, IndicatorKind
    from waterfall.platform.audit import Act

IN_PROGRESS = "in_progress"
MARKED = "marked"
# Who reads the subprojects of the project for the marking: no account, no permission.
NOBODY = Viewer(UUID(int=0), ())


@dataclass(frozen=True, slots=True)
class Kept:
    """A document a marking keeps: its kind, its scope, and the document."""

    kind: IndicatorKind
    scope: CostScope
    document: Document


def _subprojects(session: Session, project_id: UUID) -> list[UUID]:
    """Give the subprojects of the project, by their code.

    Read by no one, without permission: the list is read for its identifiers, not its commands.
    """
    views = list_subprojects(session, project_id, NOBODY, SubprojectFilters(), SubprojectSort())
    return [view.subproject_id for view in views]


def _as_kept(document: Document, act: Act) -> Document:
    """Give a document computed as the marking keeps it: marked, at its instant, stored."""
    context: dict[str, Any] = {
        **document["context"],
        "revision_status": MARKED,
        "computed_at": instant(act.at),
        "is_stored": True,
    }
    return {**document, "context": context}


def _curves(session: Session, basis: Basis, act: Act, scopes: list[CostScope]) -> list[Kept]:
    """Compute the three curves of each scope, on the day of the marking and the costs known now."""
    day = current_day(act.at)
    sources = read_curve_sources(session, basis)
    kept: list[Kept] = []
    for scope in scopes:
        reading = curves_of_scope(session, basis.project_id, sources, day, scope)
        context = Context(basis.revision_id, MARKED, act.at, scope, is_stored=True)
        kept += [
            Kept("cost_curve", scope, cost_curve_document(reading, context, payment_delays=False)),
            Kept(
                "cost_curve_payment_delays",
                scope,
                cost_curve_document(reading, context, payment_delays=True),
            ),
            Kept("earned_value_curves", scope, earned_value_curves_document(reading, context)),
        ]
    return kept


def _documents(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> list[Kept]:
    """Compute the documents a revision being marked keeps, each kind for its scopes."""
    facts = project_facts(session, project_id)
    scopes: list[CostScope] = [PROJECT, UNASSIGNED, *_subprojects(session, project_id)]
    kept: list[Kept] = []
    for scope in scopes:
        asked = IndicatorsAsked(revision_id, str(scope), act.at)
        found = estimate_document(estimate_indicators(session, project_id, asked))
        kept.append(Kept("estimate", scope, _as_kept(found, act)))
    # Read on the interface itself: ``remaining_indicators`` names a file of it too.
    remaining = estimate.remaining_indicators(session, project_id, revision_id, act.at)
    kept.append(Kept("remaining", PROJECT, _as_kept(remaining_document(remaining), act)))
    if facts.state == IN_PROGRESS:
        reference = reference_at_marking(session, revision_id, facts.reference_revision_id)
        if reference == revision_id:
            # A merge marks and designates at once: the document is drawn on the new reference.
            basis = Basis(project_id, revision_id, revision_id, act.at)
        else:
            basis = Basis(project_id, revision_id, reference)
        context = Context(revision_id, MARKED, act.at, PROJECT, is_stored=True)
        documents = day_documents(session, basis, context, scopes)
        kept.extend(Kept("project", scope, documents[scope]) for scope in scopes)
        kept.extend(_curves(session, basis, act, scopes))
    return kept


def store_indicators(session: Session, revision_id: UUID, act: Act) -> None:
    """Keep the indicators of a revision being marked, at the instant and by the author of ``act``.

    Every document is computed before the first is written; the rows are flushed at once, while
    the revision is current.
    """
    project_id = revision_project(session, revision_id)
    kept = _documents(session, project_id, revision_id, act)
    session.add_all(
        RevisionIndicator(
            project_id=project_id,
            id=new_id(),
            revision_id=revision_id,
            kind=each.kind,
            scope=str(each.scope),
            document=each.document,
            computed_at=act.at,
            created_at=act.at,
            created_by=act.author,
        )
        for each in kept
    )
    session.flush()
