# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and the rates it lacks, private to the module (US-1510).

The indicators are sums of the amounts the lines keep (EP-07, "Le calcul des montants"): nothing is
priced again here. The total is the re-estimated amount of the lines of the main structure of the
revision read, its breakdowns by cost type, by subproject and by work package — the subtree of the
task that bears it — the same lines sorted, the differences with the reference and the marked
revision before it the same total of theirs. An amount that depends on a labour line whose category
has no rate for the year of the revision is not computed (``hourly_rate_missing``), the categories
and the year named, never a budget wrongly at zero (WF-DEV-0010); a work package no task bears is
presented without a total (``work_package_without_task``, WF-DEV-0060). The provisions identified
are nought until EP-08.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from waterfall.core.cost_settings.interface import category_labels, cost_type_labels
from waterfall.core.estimate.costing import held_rates
from waterfall.core.estimate.keeping import labour_categories
from waterfall.core.estimate.shares import NOUGHT, distribution, share_of
from waterfall.core.estimate.tables import EstimateLine, RevisionCategory
from waterfall.core.planning.interface import lines_of_structure, work_package_lines
from waterfall.core.projects.interface import (
    WorkBreakdownFilters,
    read_work_breakdown,
    subproject_labels,
    work_breakdown_items,
)
from waterfall.core.revisions.interface import aimed_structure, read_revision_for
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionRead

HOURLY_RATE_MISSING = "hourly_rate_missing"
NO_TOTAL = "no_total"
WORK_PACKAGE_WITHOUT_TASK = "work_package_without_task"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
PROJECT = "project"
UNASSIGNED = "unassigned"
# An empty sum is written to the cent, as every amount is.
ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class MissingRate:
    """A category of labour a revision employs without an hourly rate for its year of reference."""

    cost_category_id: UUID
    label: str
    year: int


@dataclass(frozen=True, slots=True)
class Figure:
    """An amount or a share that may not be computed: its value, or its reason and what it names."""

    value: Decimal | None = None
    reason: str | None = None
    missing: tuple[MissingRate, ...] = ()


@dataclass(frozen=True, slots=True)
class AmountByKey:
    """An amount per key — nature, subproject, work package —, and its share of the total."""

    key: str
    label: str | None
    amount: Figure
    share: Figure


@dataclass(frozen=True, slots=True)
class IndicatorsAsked:
    """What a reading asks: a revision, a scope and the instant of the reading.

    No revision asks for the current one, or else the last one marked; the scope is ``project``,
    ``unassigned`` or the identifier of a subproject, as the query writes it.
    """

    revision_id: UUID | None
    scope: str
    at: datetime


@dataclass(frozen=True, slots=True)
class EstimateIndicators:
    """The indicators of an estimate (``EstimateIndicators``), the context of its computation."""

    revision_id: UUID
    marked: bool
    computed_at: datetime
    scope: str
    total: Figure
    by_cost_type: tuple[AmountByKey, ...]
    by_subproject: tuple[AmountByKey, ...]
    by_work_package: tuple[AmountByKey, ...]
    provisions_identified: Decimal
    delta_to_reference: Figure | None
    delta_to_previous_revision: Figure | None


@dataclass(frozen=True, slots=True)
class Row:
    """A line as the indicators read it: its category, its subproject, its amount, its labour."""

    node_id: UUID
    cost_category_id: UUID
    subproject_id: UUID | None
    amount: Decimal
    is_labour: bool


@dataclass(frozen=True, slots=True)
class Nature:
    """A nature of cost as a line shows it: its identifier, its label, its kind."""

    cost_type_id: UUID
    label: str
    kind: str


def missing_rates_of(
    session: Session, project_id: UUID, read: RevisionRead
) -> tuple[MissingRate, ...]:
    """Give the categories of labour a revision employs without a rate for its year, by label."""
    categories = labour_categories(session, project_id, read.revision_id)
    rates = held_rates(session, (project_id, read.revision_id, read.reference_year), categories)
    lacking = categories - rates.keys()
    labels = category_labels(session, lacking)
    named = [
        MissingRate(each, labels[each].label if each in labels else "", read.reference_year)
        for each in lacking
    ]
    return tuple(sorted(named, key=lambda each: (each.label, each.cost_category_id)))


def scope_of(session: Session, project_id: UUID, asked: str) -> UUID | str:
    """Read the scope asked: ``project``, ``unassigned`` or a subproject of the project; or 422.

    A subproject the project does not have, or an identifier that is none, is refused on its
    parameter (``UNKNOWN_SUBPROJECT``, WF-IND-0020).
    """
    if asked in {PROJECT, UNASSIGNED}:
        return asked
    try:
        subproject_id = UUID(asked)
    except ValueError:
        subproject_id = None
    if subproject_id is None or not subproject_labels(session, project_id, [subproject_id]):
        field = FieldError("/query/scope", UNKNOWN_SUBPROJECT)
        raise UnprocessableError(VALIDATION_FAILED, fields=(field,))
    return subproject_id


def rows_of(session: Session, project_id: UUID, revision_id: UUID, scope: UUID | str) -> list[Row]:
    """Read the lines of the main structure of a revision that the scope retains."""
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        return []
    nodes = lines_of_structure(session, project_id, structure_id)
    if not nodes:
        return []
    query = select(
        EstimateLine.node_id,
        EstimateLine.cost_category_id,
        EstimateLine.subproject_id,
        EstimateLine.reestimated_amount,
        EstimateLine.resource_role_id.is_not(None),
    ).where(EstimateLine.project_id == project_id, EstimateLine.node_id.in_(nodes))
    if scope == UNASSIGNED:
        query = query.where(EstimateLine.subproject_id.is_(None))
    elif isinstance(scope, UUID):
        query = query.where(EstimateLine.subproject_id == scope)
    return [Row(*each) for each in session.execute(query.order_by(EstimateLine.node_id))]


def natures_of(
    session: Session, project_id: UUID, read: RevisionRead, category_ids: Collection[UUID]
) -> dict[UUID, Nature]:
    """Give the nature of each category: on the images of a revision marked, else on the reference.

    A marked revision is read on the images it kept at its marking (EP-07, "L'instantané et les
    taux"); a category it kept none of is read on the reference.
    """
    found: dict[UUID, Nature] = {}
    if read.marked and category_ids:
        images = session.execute(
            select(
                RevisionCategory.cost_category_id,
                RevisionCategory.cost_type_id,
                RevisionCategory.cost_type_label,
                RevisionCategory.cost_type_kind,
            ).where(
                RevisionCategory.project_id == project_id,
                RevisionCategory.revision_id == read.revision_id,
                RevisionCategory.cost_category_id.in_(category_ids),
            )
        )
        found = {each[0]: Nature(each[1], each[2], each[3]) for each in images}
    rest = set(category_ids) - found.keys()
    labels = category_labels(session, rest)
    types = cost_type_labels(
        session, {each.cost_type_id for each in labels.values() if each.cost_type_id is not None}
    )
    for category_id, each in labels.items():
        if each.cost_type_id is not None:
            found[category_id] = Nature(
                each.cost_type_id, types.get(each.cost_type_id, ""), each.cost_type_kind
            )
    return found


def _not_computed(missing: Collection[MissingRate]) -> Figure:
    """Give an amount that a rate missing prevents from being computed, the rates named."""
    return Figure(None, HOURLY_RATE_MISSING, tuple(missing))


def _amount(rows: Sequence[Row], lacking: dict[UUID, MissingRate]) -> Figure:
    """Give the sum of lines, or the rates their labour lacks."""
    named = {
        lacking[each.cost_category_id].cost_category_id: lacking[each.cost_category_id]
        for each in rows
        if each.is_labour and each.cost_category_id in lacking
    }
    if named:
        return _not_computed(named.values())
    return Figure(sum((each.amount for each in rows), ZERO))


def _shares(amounts: Sequence[Figure], total: Figure) -> list[Figure]:
    """Give the shares of the amounts of a distribution of the total, which sum to one."""
    if total.value is None:
        return [_not_computed(total.missing) for _ in amounts]
    if total.value == 0:
        return [Figure(None, NO_TOTAL) for _ in amounts]
    values = [each.value or NOUGHT for each in amounts]
    return [Figure(each) for each in distribution(values)]


def _distributed(
    groups: Sequence[tuple[str, str | None, Sequence[Row]]],
    total: Figure,
    lacking: dict[UUID, MissingRate],
) -> tuple[AmountByKey, ...]:
    """Give the amount of each group of lines and its share, the shares summing to one."""
    amounts = [_amount(rows, lacking) for _, _, rows in groups]
    shares = _shares(amounts, total)
    return tuple(
        AmountByKey(key, label, amount, share)
        for (key, label, _), amount, share in zip(groups, amounts, shares, strict=True)
    )


def _by_cost_type(
    rows: Sequence[Row],
    natures: dict[UUID, Nature],
    total: Figure,
    lacking: dict[UUID, MissingRate],
) -> tuple[AmountByKey, ...]:
    """Ventilate the lines by the nature of their category, in the order of its identifiers."""
    held: dict[UUID, list[Row]] = {}
    for each in rows:
        held.setdefault(natures[each.cost_category_id].cost_type_id, []).append(each)
    types = {each.cost_type_id: each for each in natures.values()}
    groups = [(str(each), types[each].label, held[each]) for each in sorted(held)]
    return _distributed(groups, total, lacking)


def _by_subproject(
    session: Session,
    project_id: UUID,
    rows: Sequence[Row],
    scope: UUID | str,
) -> list[tuple[str, str | None, list[Row]]]:
    """Group the lines by subproject, by identifier, the set out of any subproject last."""
    held: dict[UUID | None, list[Row]] = {}
    if isinstance(scope, UUID):
        held[scope] = []
    for each in rows:
        held.setdefault(each.subproject_id, []).append(each)
    if scope == UNASSIGNED:
        held.setdefault(None, [])
    named = sorted(each for each in held if each is not None)
    labels = subproject_labels(session, project_id, named)
    groups: list[tuple[str, str | None, list[Row]]] = [
        (str(each), labels.get(each), held[each]) for each in named
    ]
    if None in held:
        groups.append((UNASSIGNED, None, held[None]))
    return groups


def _by_work_package(
    session: Session,
    revision: tuple[UUID, UUID],
    rows: Sequence[Row],
    total: Figure,
    lacking: dict[UUID, MissingRate],
) -> tuple[AmountByKey, ...]:
    """Give the total of each work package of the work breakdown, through the task that bears it.

    In the order entered, those marked deleted that a task of the revision still bears after; a
    work package no task bears has neither a total nor a share. Its share, as every share of a
    part that carries only some of the lines, receives no remainder of the roundings.
    """
    project_id, revision_id = revision
    structure_id = aimed_structure(session, project_id, revision_id, None)
    borne = {} if structure_id is None else work_package_lines(session, project_id, structure_id)
    entered = read_work_breakdown(session, project_id, WorkBreakdownFilters()).work_packages
    named = [(each.work_package_id, each.label) for each in entered]
    kept = {each for each, _ in named}
    deleted = [each for each in borne if each not in kept]
    if deleted:
        items = work_breakdown_items(session, project_id)
        named += [(each, items[each].label if each in items else "") for each in deleted]
    found: list[AmountByKey] = []
    for package_id, label in named:
        if package_id not in borne:
            reason = Figure(None, WORK_PACKAGE_WITHOUT_TASK)
            found.append(AmountByKey(str(package_id), label, reason, reason))
            continue
        under = [each for each in rows if each.node_id in borne[package_id]]
        amount = _amount(under, lacking)
        found.append(AmountByKey(str(package_id), label, amount, _part(amount, total)))
    return tuple(found)


def _part(amount: Figure, total: Figure) -> Figure:
    """Give the share of an amount that is part of the total, none of the remainder carried."""
    if total.value is None or amount.value is None:
        return _not_computed(total.missing or amount.missing)
    if total.value == 0:
        return Figure(None, NO_TOTAL)
    return Figure(share_of(amount.value, total.value))


def _difference(total: Figure, other: Figure | None) -> Figure | None:
    """Give the estimate read minus another, none without it; not computed if either is not."""
    if other is None:
        return None
    if total.value is None:
        return _not_computed(total.missing)
    if other.value is None:
        return _not_computed(other.missing)
    return Figure(total.value - other.value)


def _total_of(
    session: Session, project_id: UUID, revision_id: UUID | None, scope: UUID | str
) -> Figure | None:
    """Give the total of the main structure of another revision, on its own rates; none without."""
    if revision_id is None:
        return None
    other = read_revision_for(session, project_id, revision_id)
    lacking = {each.cost_category_id: each for each in missing_rates_of(session, project_id, other)}
    return _amount(rows_of(session, project_id, revision_id, scope), lacking)


def estimate_indicators_of(
    session: Session, project_id: UUID, asked: IndicatorsAsked
) -> EstimateIndicators:
    """Compute the indicators of the estimate of a revision, as the contract reads them.

    The revision unknown is refused (404), then the scope (422).
    """
    read = read_revision_for(session, project_id, asked.revision_id)
    scope = scope_of(session, project_id, asked.scope)
    rows = rows_of(session, project_id, read.revision_id, scope)
    lacking = {each.cost_category_id: each for each in missing_rates_of(session, project_id, read)}
    natures = natures_of(session, project_id, read, {each.cost_category_id for each in rows})
    total = _amount(rows, lacking)
    return EstimateIndicators(
        revision_id=read.revision_id,
        marked=read.marked,
        computed_at=asked.at,
        scope=scope if isinstance(scope, str) else str(scope),
        total=total,
        by_cost_type=_by_cost_type(rows, natures, total, lacking),
        by_subproject=_distributed(
            _by_subproject(session, project_id, rows, scope), total, lacking
        ),
        by_work_package=_by_work_package(
            session, (project_id, read.revision_id), rows, total, lacking
        ),
        provisions_identified=Decimal("0.00"),
        delta_to_reference=_difference(
            total, _total_of(session, project_id, read.reference_revision_id, scope)
        ),
        delta_to_previous_revision=_difference(
            total, _total_of(session, project_id, read.previous_marked_id, scope)
        ),
    )
