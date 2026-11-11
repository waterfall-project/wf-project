# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writes of the facet of a line, private to the module (EP-07, US-1490).

Each runs in the frame the planning opens around a write of the tree — the revision judged, the
entry of the history open, the structure locked and read (``create_line_node``, ``write_facet``) —
and writes the facet with its amounts, computed in its transaction (EP-07, "Le calcul des
montants"): the line judged (``entries``), the hours of its task judged when its role is given
(``TASK_WITHOUT_WORKING_HOURS``), its rate found (``HOURLY_RATE_MISSING``), then priced on the
dates of its task (``costing``). The planning prices again, once it has redated the structure, the
lines of the tasks it moved and of the task the line is written under (``reprice``).

The budgeted amount of a line created is nought on a project that has a reference revision — a new
line has no lineage in it — and null otherwise, read as the re-estimated one (WF-DEV-0020).

What an import sends of a line comes as ``HoursJudged``: the hours of the tasks were judged on the
structure the whole import leaves (``importing``), which writes its lines in one write of the tree;
judged again line by line, against a structure half written, a role given before another could be
refused that the end accepts (US-1550).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.costing import (
    Basis,
    Figures,
    basis_of,
    calendar_hours,
    judge_working_hours,
    priced,
    product_of,
    rates_of,
    refuse_missing_rate,
)
from waterfall.core.estimate.entries import Draft, LineEntry, judged_line
from waterfall.core.estimate.pricing import CENT
from waterfall.core.estimate.recalling import recalled, remembers
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.resource_settings.interface import role_calendars

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.costing import Priced
    from waterfall.core.planning.interface import BearingTask, FacetCreation, FacetWrite

NOUGHT = CENT * 0


@dataclass(frozen=True, slots=True)
class HoursJudged:
    """What an import sends of a line, the hours of its task judged already (US-1550)."""

    entry: LineEntry


def _sent(entry: object) -> tuple[LineEntry, bool]:
    """Give the entry of a line, and whether the hours of its task are judged already."""
    judged = isinstance(entry, HoursJudged)
    sent = entry.entry if isinstance(entry, HoursJudged) else entry
    if not isinstance(sent, LineEntry):
        msg = "a line is written from what the API or an import read of its facet"
        raise TypeError(msg)
    return sent, judged


@dataclass(frozen=True, slots=True)
class Judging:
    """How the hours of the task of a line are judged.

    ``role_changes`` is true at the creation of a line given a role, and when a modification gives
    another role than the line had; ``earlier`` is the role the rows of a paste accepted before
    leave the lines of the task.
    """

    role_changes: bool
    earlier: Mapping[UUID, UUID | None] | None = None


def _priced_draft(
    session: Session,
    held: tuple[UUID, BearingTask, UUID | None],
    draft: Draft,
    basis: Basis,
    judging: Judging,
) -> Priced:
    """Judge the hours of the task of a line whose role changes, find its rate, price it.

    ``held`` is the project, the task that bears the line, and the line, none at its creation;
    ``judging`` says whether the role changes and what the paste has left the other lines.
    """
    project_id, bearer, _ = held
    week = None
    rate = None
    if draft.role is not None:
        if judging.role_changes:
            judge_working_hours(session, held, draft.role.resource_role_id, judging.earlier)
        calendar_id, category_id = draft.role.calendar_id, draft.cost_category_id
        week = recalled(
            session, ("calendar", calendar_id), lambda: calendar_hours(session, [calendar_id])
        )[calendar_id]
        rate = recalled(
            session,
            ("rate", basis, category_id),
            lambda: rates_of(session, project_id, basis, [category_id]),
        ).get(category_id)
        if rate is None:
            raise refuse_missing_rate((draft.cost_category_id, draft.category.label), basis)
    figures = Figures(
        draft.quantity,
        draft.hours,
        draft.unit_disbursement,
        draft.cost_category_id,
        None if draft.role is None else draft.role.calendar_id,
    )
    product = product_of(figures, rate)
    if product is None:
        raise refuse_missing_rate((draft.cost_category_id, draft.category.label), basis)
    return priced(product, bearer, basis, week)


def judged_priced(
    session: Session,
    held: tuple[UUID, BearingTask],
    entry: LineEntry,
    current: EstimateLine | None,
    earlier: Mapping[UUID, UUID | None] | None = None,
) -> Draft:
    """Judge what is sent of a line, created or changed, as far as its price; nothing is written.

    What ``create_line`` and ``change_line`` refuse before they write: the entry (``entries``), the
    hours of the task when the role is new, the rate of the category. A paste judges its cells so,
    at its preview and again at its confirmation. ``earlier`` is the role the lines of the task that
    the cells before it were accepted with leave them: the hours of the task are judged on them.
    """
    project_id, bearer = held
    draft = judged_line(session, held, entry, current)
    basis = basis_of(session, project_id, bearer.revision_id)
    line = None if current is None else current.node_id
    new_role = current is None or draft.resource_role_id != current.resource_role_id
    _priced_draft(
        session,
        (project_id, bearer, line),
        draft,
        basis,
        Judging(role_changes=new_role, earlier=earlier),
    )
    return draft


def create_line(creation: FacetCreation) -> None:
    """Write the facet of a line created under its task, priced (``createNode``); or refuse."""
    session, project_id = creation.session, creation.project_id
    entry, judged = _sent(creation.entry)
    draft = judged_line(session, (project_id, creation.bearer), entry, None)
    revision_id = creation.revision_id
    basis = recalled(
        session,
        ("basis", project_id, revision_id),
        lambda: basis_of(session, project_id, revision_id),
    )
    amounts = _priced_draft(
        session,
        (project_id, creation.bearer, None),
        draft,
        basis,
        Judging(role_changes=not judged),
    )
    act = creation.act
    session.add(
        EstimateLine(
            project_id=project_id,
            node_id=creation.node_id,
            kind="estimate_line",
            label=draft.label,
            cost_category_id=draft.cost_category_id,
            resource_role_id=draft.resource_role_id,
            quantity=draft.quantity,
            hours=draft.hours,
            unit_disbursement=draft.unit_disbursement,
            payment_delay_days=draft.payment_delay_days,
            subproject_id=draft.subproject_id,
            base_amount=amounts.base,
            budgeted_amount=NOUGHT if basis.has_reference else None,
            reestimated_amount=amounts.reestimated,
            consumption_year=amounts.consumption_year,
            lock_version=1,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    # A load of lines does not flush each one: the next statement that needs it, or the end of the
    # load, does (``recalling``); what it saves is the reads, which are remembered.
    if not remembers(session):
        session.flush()


def read_line(session: Session, project_id: UUID, node_id: UUID) -> EstimateLine:
    """Read the facet of a line under the lock its structure holds, as it is now."""
    return session.scalars(
        select(EstimateLine)
        .where(EstimateLine.project_id == project_id, EstimateLine.node_id == node_id)
        .execution_options(populate_existing=True)
    ).one()


def change_line(write: FacetWrite, sent: LineEntry | HoursJudged) -> None:
    """Write what is sent of the facet of a line, priced again (``updateEstimateLine``); or refuse.

    The budgeted amount is left as it is (WF-DEV-0020); the hours of the task are judged only when
    the role changes, and not for an import, which judged them (``HoursJudged``).
    """
    session, project_id = write.session, write.project_id
    entry, judged = _sent(sent)
    line = read_line(session, project_id, write.node_id)
    draft = judged_line(session, (project_id, write.bearer), entry, line)
    basis = basis_of(session, project_id, write.revision_id)
    amounts = _priced_draft(
        session,
        (project_id, write.bearer, write.node_id),
        draft,
        basis,
        Judging(role_changes=not judged and draft.resource_role_id != line.resource_role_id),
    )
    line.label = draft.label
    line.cost_category_id = draft.cost_category_id
    line.resource_role_id = draft.resource_role_id
    line.quantity = draft.quantity
    line.hours = draft.hours
    line.unit_disbursement = draft.unit_disbursement
    line.payment_delay_days = draft.payment_delay_days
    line.subproject_id = draft.subproject_id
    line.base_amount = amounts.base
    line.reestimated_amount = amounts.reestimated
    line.consumption_year = amounts.consumption_year
    line.lock_version += 1
    line.updated_at, line.updated_by = write.act.at, write.act.author
    session.flush()


def reprice(
    session: Session, project_id: UUID, lines: Mapping[UUID, BearingTask]
) -> frozenset[UUID]:
    """Price again the lines named on the dates of their tasks; give those whose amounts moved.

    A rate gone since — the reference never takes one away — leaves the base amount as it was, from
    which the shares are cut (EP-07, "Le calcul des montants").
    """
    if not lines:
        return frozenset()
    rows = list(
        session.scalars(
            select(EstimateLine)
            .where(EstimateLine.project_id == project_id, EstimateLine.node_id.in_(list(lines)))
            .execution_options(populate_existing=True)
        )
    )
    if not rows:
        return frozenset()
    basis = basis_of(session, project_id, next(iter(lines.values())).revision_id)
    roles = {row.resource_role_id for row in rows if row.resource_role_id is not None}
    calendars = role_calendars(session, roles)
    weeks = calendar_hours(session, calendars.values())
    labour = {row.cost_category_id for row in rows if row.resource_role_id is not None}
    rates = rates_of(session, project_id, basis, labour)
    changed: set[UUID] = set()
    for row in rows:
        role = row.resource_role_id
        calendar = None if role is None else calendars.get(role)
        figures = Figures(
            row.quantity, row.hours, row.unit_disbursement, row.cost_category_id, calendar
        )
        product = product_of(figures, rates.get(row.cost_category_id))
        week = None if calendar is None else weeks[calendar]
        amounts = priced(
            row.base_amount if product is None else product, lines[row.node_id], basis, week
        )
        before = (row.base_amount, row.reestimated_amount, row.consumption_year)
        after = (amounts.base, amounts.reestimated, amounts.consumption_year)
        if before != after:
            row.base_amount, row.reestimated_amount, row.consumption_year = after
            changed.add(row.node_id)
    session.flush()
    return frozenset(changed)
