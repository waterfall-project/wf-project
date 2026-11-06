# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources of the witness.

``resource_roles.json``, the deactivated ones included: each role, then those the witness says
deactivated (WF-REF-0080, WF-REF-0090).

A role is written by ``create_role`` of the resource settings, as the API writes one: created
active, under an active node, attached to an active category of labour and an active calendar.
The witness holds two roles the rules would not create as they are, and this slice writes them as
an installation would have come to hold them, through the same interfaces:

- a role attached to a calendar the calendars of the witness do not load — the deactivated one,
  which ``calendars.json`` does not give, read from ``calendars_with_inactive.json`` —: the
  calendar is created active, the role attached to it, then the calendar deactivated;
- a role under a node the witness says deactivated: the node is reactivated with its deactivated
  ancestors, from the highest down, the role created under it, then the highest deactivated again,
  in cascade, the role with it.

What the platform held before is left as it was: only the nodes reactivated here are deactivated
again, only the calendars created here deactivated.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import ResourceRole
from waterfall.api.resource_roles import category_admission
from waterfall.core.resource_settings.interface import (
    DAYS,
    CalendarContent,
    Capacity,
    RoleDraft,
    WeeklyHours,
    calendars_present,
    create_calendar,
    create_role,
    read_calendar,
    read_node,
    read_role,
    roles_present,
    set_activation,
    set_calendar_activation,
    set_role_activation,
)
from waterfall.witness.calendars import Calendars
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

FILE = "resource_roles.json"
# Every calendar of the witness, the deactivated ones included, which ``calendars.json`` lacks.
CALENDARS = "calendars_with_inactive.json"


class ResourceRoles(BaseModel):
    """The roles of the example ``resource_roles.json``, as ``listResourceRoles`` answers them."""

    items: list[ResourceRole]


def _missing_calendars(session: Session, witness: Witness, named: Collection[UUID]) -> list[UUID]:
    """Create, active, the calendars the roles name that the platform lacks; give those to close.

    Read from every calendar of the witness; those it says deactivated are given, to deactivate
    once their roles are attached.
    """
    lacking = set(named) - calendars_present(session, named)
    to_close: list[UUID] = []
    for each in witness.read(CALENDARS, Calendars).items:
        if each.calendar_id.root not in lacking:
            continue
        hours = WeeklyHours(*(Decimal(getattr(each.weekly_hours, day).root.root) for day in DAYS))
        content = CalendarContent(each.label, hours)
        create_calendar(session, content, witness.act, identifier=each.calendar_id.root)
        if not each.is_active:
            to_close.append(each.calendar_id.root)
    return to_close


def _open_node(session: Session, witness: Witness, node_id: UUID) -> UUID | None:
    """Reactivate a deactivated node with its deactivated ancestors; give the highest reopened.

    From the highest down, each under a parent active again; ``None`` for a node already active.
    """
    closed: list[UUID] = []
    node = read_node(session, node_id, may_change=False)
    while not node.is_active:
        closed.append(node.node_id)
        if node.parent_id is None:
            break
        node = read_node(session, node.parent_id, may_change=False)
    for each in reversed(closed):
        current = read_node(session, each, may_change=False)
        set_activation(
            session, each, is_active=True, lock_version=current.lock_version, act=witness.act
        )
    return closed[-1] if closed else None


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    roles = witness.read(FILE, ResourceRoles).items
    imposed = frozenset(role.resource_role_id.root for role in roles)
    if is_loaded(imposed, roles_present(session, imposed)):
        return False
    to_close = _missing_calendars(session, witness, {role.calendar_id.root for role in roles})
    reopened: list[UUID] = []
    for role in roles:
        opened = _open_node(session, witness, role.org_node_id.root)
        if opened is not None:
            reopened.append(opened)
        category_id = role.cost_category_id.root
        draft = RoleDraft(
            role.code,
            role.label,
            role.org_node_id.root,
            category_id,
            category_admission(session, category_id),
            role.calendar_id.root,
            Capacity(
                Decimal(role.capacity.monthly_hours.root.root),
                Decimal(role.capacity.headcount.root),
            ),
        )
        create_role(session, draft, witness.act, identifier=role.resource_role_id.root)
    for node_id in reopened:
        current = read_node(session, node_id, may_change=False)
        set_activation(
            session, node_id, is_active=False, lock_version=current.lock_version, act=witness.act
        )
    for role in roles:
        current = read_role(session, role.resource_role_id.root, may_change=False)
        if current.is_active and not role.is_active:
            set_role_activation(
                session,
                current.resource_role_id,
                is_active=False,
                lock_version=current.lock_version,
                act=witness.act,
            )
    for calendar_id in to_close:
        current = read_calendar(session, calendar_id)
        set_calendar_activation(
            session, calendar_id, current.lock_version, witness.act, is_active=False
        )
    return True
