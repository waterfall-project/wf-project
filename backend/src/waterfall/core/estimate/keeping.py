# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rates a revision keeps, their proposal and their update, private to the module (US-1500).

A current revision follows the reference for its roles, its calendars and its categories, and
keeps its rates alone (``revision_rate``; EP-07, "L'instantané et les taux"). The first revision of
a project keeps none: its lines are priced at the rates of the reference for its year. A revision
opened from a marked one keeps, for each category of labour the lines of its source employ, the rate
its source was priced at — kept, or that of the reference for the year of the source —: copied at
an equal year (``reference``), projected by the rate of inflation of the project up to its own year
otherwise (``projected``), and replaced by the rate of the reference for its year for each category
that has one when its creation accepts the update (``RevisionCreate.apply_rate_update``); its lines
are then priced again (WF-REV-0010, WF-REV-0060).

The proposal of a current revision (``getRateUpdateProposal``) lists each category of labour its
lines employ whose rate is projected: the rate projected, beside the rate of the reference for the
year of the revision (``reference_rate``) or, without one, the rate projected again
(``inflated_previous``). The update (``applyRateUpdate``) keeps the rate of the reference for each
category accepted that has one (``reference_rate``), as of the reference, and prices again the
lines that employ it; a category accepted without one keeps its rate projected, and stays proposed,
so that the rate of the year, once entered in the reference, is proposed still (#2619, option 2); a
category the proposal does not present is refused (422 ``UNKNOWN_COST_CATEGORY`` on its rank,
#1756). A marked revision
proposes nothing: it keeps the rates it was priced at (WF-REF-0130).

A rate projected is rounded to the cent, a half going away from zero, as the contract rounds every
amount the server computes, a projected amount included (``Money``).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select

from waterfall.core.cost_settings.interface import category_labels
from waterfall.core.estimate.costing import held_rates, reference_rates
from waterfall.core.estimate.pricing import CENT, inflation_factor
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.interface import Holding, lines_of_revision, reschedule, structures_of
from waterfall.core.projects.interface import project_facts
from waterfall.core.revisions.interface import (
    RatesToUpdate,
    reference_year_of,
    revision_rating,
    revision_structures,
    structure_facts,
    update_rates,
)
from waterfall.platform.errors import FieldError, UnprocessableError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionClosing, RevisionCopy, RevisionRating
    from waterfall.platform.audit import Act

REFERENCE = "reference"
PROJECTED = "projected"
REFERENCE_RATE = "reference_rate"
INFLATED_PREVIOUS = "inflated_previous"
VALIDATION_FAILED = "VALIDATION_FAILED"
UNKNOWN_COST_CATEGORY = "UNKNOWN_COST_CATEGORY"
# The precision a projection is computed at, before its rounding to the cent.
PRECISION = 60


@dataclass(frozen=True, slots=True)
class ProposedRate:
    """A category the proposal presents: its rate projected, the rate proposed and where it is from.

    ``source`` is ``reference_rate`` when the reference rates the category for the year of the
    revision, ``inflated_previous`` otherwise, the rate proposed being then the rate projected.
    """

    cost_category_id: UUID
    label: str
    previous_amount: Decimal
    proposed_amount: Decimal
    source: str


@dataclass(frozen=True, slots=True)
class RateProposal:
    """The proposal of the rates of a revision: its year of reference, and the categories shown."""

    target_year: int
    categories: tuple[ProposedRate, ...]


@dataclass(frozen=True, slots=True)
class RateUpdate:
    """An update of the rates sent: the revision, the counter read, the categories accepted."""

    revision_id: UUID
    lock_version: int
    cost_category_ids: tuple[UUID, ...]


def projected_rate(amount: Decimal, inflation_rate: Decimal, years: tuple[int, int]) -> Decimal:
    """Project a rate from a year to another, once a year elapsed; rounded to the cent (Money).

    ``years`` is the year of the rate and the year it is projected to.
    """
    with localcontext() as context:
        context.prec = PRECISION
        projected = amount * inflation_factor(inflation_rate, *years)
        return projected.quantize(CENT, rounding=ROUND_HALF_UP)


def labour_categories(session: Session, project_id: UUID, revision_id: UUID) -> frozenset[UUID]:
    """Give the categories the lines of labour of a revision employ, every structure included."""
    nodes = list(lines_of_revision(session, project_id, revision_id).values())
    if not nodes:
        return frozenset()
    return frozenset(
        session.scalars(
            select(EstimateLine.cost_category_id)
            .where(
                EstimateLine.project_id == project_id,
                EstimateLine.node_id.in_(nodes),
                EstimateLine.resource_role_id.is_not(None),
            )
            .distinct()
        )
    )


def reprice_revision(
    session: Session,
    revision: tuple[UUID, UUID],
    at: datetime,
    categories: Collection[UUID] | None = None,
) -> None:
    """Price again the lines of a revision, of the categories named or all; each structure locked.

    ``revision`` is its project and itself. Each structure is replayed in the order of its
    identifier, its dates' instant moved on to ``at``, the lines named priced again on the dates of
    their tasks, whether these moved or not (``Holding.repriced``), as a write of the tree does.
    Only the structures that hold such a line are replayed: another keeps its counter and dates.
    Every structure of the revision is locked first, in the order of its identifier, and the lines
    are read under the locks: a line a write of the tree created meanwhile, under a task that had
    none of the category, is priced again with the others. The structures are read again after the
    locks, and those a ``createCostStructure`` (which holds the revision ``FOR SHARE`` alone) added
    meanwhile locked in their turn, until the list and the structures that bear the lines read are
    all held: ``reschedule`` locks the structures of the lines, but after they are read. A structure
    of a line that the list lacks is locked too, so that each pass progresses or stops. The order of
    the identifiers holds within a pass only: a structure created between two passes may bear a
    lower identifier than one held, so a deadlock is possible only with a writer that locks several
    structures, and PostgreSQL detects it.
    """
    project_id, revision_id = revision
    held_structures: set[UUID] = set()
    while True:
        missing = [
            each
            for each in revision_structures(session, project_id, revision_id)
            if each not in held_structures
        ]
        for structure_id in missing:
            structure_facts(session, project_id, structure_id, lock=True)
            held_structures.add(structure_id)
        nodes = list(lines_of_revision(session, project_id, revision_id).values())
        strangers = sorted(set(structures_of(session, project_id, nodes)) - held_structures)
        for structure_id in strangers:
            structure_facts(session, project_id, structure_id, lock=True)
            held_structures.add(structure_id)
        if not missing and not strangers:
            break
    if nodes and categories is not None:
        nodes = list(
            session.scalars(
                select(EstimateLine.node_id).where(
                    EstimateLine.project_id == project_id,
                    EstimateLine.node_id.in_(nodes),
                    EstimateLine.cost_category_id.in_(list(categories)),
                )
            )
        )
    if not nodes:
        return
    held = Holding(repriced=tuple(nodes))
    for structure_id in structures_of(session, project_id, nodes):
        reschedule(session, project_id, structure_id, at, held)


def copy_rates(copy: RevisionCopy) -> None:
    """Keep in the revision opened the rates its source was priced at, projected if the year moves.

    After the copy of the lines, which the planning makes with its nodes: their amounts follow.
    """
    session, project_id = copy.session, copy.project_id
    categories = labour_categories(session, project_id, copy.source)
    if not categories:
        return
    source_year = reference_year_of(session, copy.source)
    target_year = reference_year_of(session, copy.target)
    held = held_rates(session, (project_id, copy.source, source_year), categories)
    kept: dict[UUID, tuple[Decimal, str]] = {
        category: (amount, REFERENCE) for category, amount in held.items()
    }
    if source_year != target_year:
        inflation = project_facts(session, project_id).inflation_rate
        years = (source_year, target_year)
        kept = {
            category: (projected_rate(amount, inflation, years), PROJECTED)
            for category, amount in held.items()
        }
        if copy.apply_rate_update:
            for category, amount in reference_rates(session, kept, target_year).items():
                kept[category] = (amount, REFERENCE)
    if not kept:
        return
    session.execute(
        insert(RevisionRate),
        [
            {
                "project_id": project_id,
                "id": new_id(),
                "revision_id": copy.target,
                "cost_category_id": category,
                "amount": amount,
                "origin": origin,
            }
            for category, (amount, origin) in sorted(kept.items())
        ],
    )
    reprice_revision(session, (project_id, copy.target), copy.at)


def close_rates(closing: RevisionClosing) -> None:
    """Delete the rates of a revision abandoned, which would hold it; a marked one keeps them."""
    if closing.kind != "abandoned":
        return
    closing.session.execute(
        delete(RevisionRate)
        .where(
            RevisionRate.project_id == closing.project_id,
            RevisionRate.revision_id == closing.revision_id,
        )
        .execution_options(synchronize_session=False)
    )


def _projected(session: Session, project_id: UUID, revision_id: UUID) -> dict[UUID, RevisionRate]:
    """Give the rates a revision keeps projected, by category, read as they are now."""
    return {
        row.cost_category_id: row
        for row in session.scalars(
            select(RevisionRate)
            .where(
                RevisionRate.project_id == project_id,
                RevisionRate.revision_id == revision_id,
                RevisionRate.origin == PROJECTED,
            )
            .execution_options(populate_existing=True)
        )
    }


def proposal_of(session: Session, rating: RevisionRating) -> RateProposal:
    """Give the proposal of the rates of a revision, by the label of its categories, then by them.

    Empty for a marked revision, and for a current one whose lines employ no rate projected.
    """
    year = rating.reference_year
    if not rating.draft:
        return RateProposal(year, ())
    projected = _projected(session, rating.project_id, rating.revision_id)
    employed = labour_categories(session, rating.project_id, rating.revision_id)
    shown = employed & projected.keys()
    if not shown:
        return RateProposal(year, ())
    reference = reference_rates(session, shown, year)
    labels = category_labels(session, shown)
    categories = [
        ProposedRate(
            category,
            labels[category].label,
            projected[category].amount,
            reference.get(category, projected[category].amount),
            REFERENCE_RATE if category in reference else INFLATED_PREVIOUS,
        )
        for category in shown
        if category in labels
    ]
    categories.sort(key=lambda each: (each.label, each.cost_category_id))
    return RateProposal(year, tuple(categories))


def rate_proposal(session: Session, project_id: UUID, revision_id: UUID) -> RateProposal:
    """Give the proposal of the rates of a revision of a project (``getRateUpdateProposal``)."""
    return proposal_of(session, revision_rating(session, project_id, revision_id))


def rate_update_offered(session: Session, project_id: UUID, revision_id: UUID) -> bool:
    """Tell whether the proposal of a current revision presents a category (#1351).

    The question is the proposal's own, so that the command and the proposal never diverge.
    """
    return bool(rate_proposal(session, project_id, revision_id).categories)


def _faults(sent: tuple[UUID, ...], proposal: RateProposal) -> list[FieldError]:
    """Name the categories sent the proposal does not present, by their rank, and a repeated one."""
    shown = {each.cost_category_id for each in proposal.categories}
    faults: list[FieldError] = []
    seen: set[UUID] = set()
    for rank, category in enumerate(sent):
        pointer = f"/cost_category_ids/{rank}"
        if category not in shown:
            faults.append(FieldError(pointer, UNKNOWN_COST_CATEGORY))
        elif category in seen:
            # The contract asks the categories once each (``uniqueItems``).
            faults.append(FieldError(pointer, VALIDATION_FAILED))
        seen.add(category)
    return faults


def apply_update(session: Session, project_id: UUID, update: RateUpdate, act: Act) -> None:
    """Keep the rate of the reference for each category accepted, and price again its lines.

    Framed by the revision (``update_rates``): 404, 412, 409 first; then a category the proposal
    does not present is refused (422), nothing written; the contract asks one at least. A category
    accepted whose rate proposed is the rate projected (``inflated_previous``) is left as it is:
    projected, and proposed still (#2619).
    """

    def write(rating: RevisionRating) -> None:
        proposal = proposal_of(session, rating)
        faults = _faults(update.cost_category_ids, proposal)
        if faults:
            raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
        accepted = set(update.cost_category_ids)
        proposed = {
            each.cost_category_id: each.proposed_amount
            for each in proposal.categories
            if each.source == REFERENCE_RATE and each.cost_category_id in accepted
        }
        for category, row in _projected(session, project_id, rating.revision_id).items():
            if category in proposed:
                row.amount, row.origin = proposed[category], REFERENCE
        session.flush()
        reprice_revision(session, (project_id, rating.revision_id), act.at, frozenset(proposed))

    update_rates(
        session, project_id, RatesToUpdate(update.revision_id, update.lock_version), act, write
    )
