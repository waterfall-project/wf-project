# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources of the witness.

``resource_roles.json``, the deactivated ones included: each role, then those the witness says
deactivated (WF-REF-0080, WF-REF-0090).

A role is written by ``create_role`` of the resource settings, as the API writes one: created
active, under an active node, attached to an active category of labour and an active calendar.
The witness holds roles the rules would not create as they are, and this slice writes them as an
installation would have come to hold them, through the same interfaces:

- a role attached to a calendar the calendars of the witness say deactivated: the calendar is
  reactivated, the role created, then the calendar deactivated again;
- a role under a node the witness says deactivated: the node is reactivated with its deactivated
  ancestors, from the highest down, the role created under it, then the highest deactivated again,
  in cascade, the role with it.

What the platform held before is left as it was: only the nodes and the calendars reopened here
are deactivated again.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import ResourceRole
from waterfall.api.resource_roles import category_admission
from waterfall.core.resource_settings.interface import (
    Capacity,
    RoleDraft,
    create_role,
    read_calendar,
    read_node,
    read_role,
    roles_present,
    set_activation,
    set_calendar_activation,
    set_role_activation,
)
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

FILE = "resource_roles.json"


class ResourceRoles(BaseModel):
    """The roles of the example ``resource_roles.json``, as ``listResourceRoles`` answers them."""

    items: list[ResourceRole]


def _open_calendar(session: Session, witness: Witness, calendar_id: UUID) -> bool:
    """Reactivate a deactivated calendar; tell whether it was reopened."""
    current = read_calendar(session, calendar_id)
    if current.is_active:
        return False
    set_calendar_activation(session, calendar_id, current.lock_version, witness.act, is_active=True)
    return True


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
    reopened: list[UUID] = []
    calendars: list[UUID] = []
    for role in roles:
        calendar_id = role.calendar_id.root
        if calendar_id not in calendars and _open_calendar(session, witness, calendar_id):
            calendars.append(calendar_id)
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
    for calendar_id in calendars:
        current = read_calendar(session, calendar_id)
        set_calendar_activation(
            session, calendar_id, current.lock_version, witness.act, is_active=False
        )
    return True
