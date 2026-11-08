# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the estimate share (EP-07, "Les tests du back"): rows, a reference, lines.

The rows of the estimate written around the service — a line and its node, a rate, the images of a
role, a calendar and a category —, each valid unless a test changes it, as ``planning_support``
writes those of the planning; and the reference a line names, a category of labour with a role.
The stories of EP-07 add here the structures with their tasks and their lines written through the
interface of the estimate, a reference designated, and the clock set; a story that needs another
helper writes it in its own file.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from planning_support import node_row
from project_rows import AT, STAMP
from sqlalchemy import insert

from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node
from waterfall.core.resource_settings.tables import Calendar, OrgNode, ResourceRole

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# The hours of a working day of the calendar of a role, from Monday to Friday.
WEEK = {
    "monday": Decimal(8),
    "tuesday": Decimal(8),
    "wednesday": Decimal(8),
    "thursday": Decimal(8),
    "friday": Decimal(8),
    "saturday": Decimal(0),
    "sunday": Decimal(0),
}


@dataclass(frozen=True)
class LineReference:
    """What a line of labour names of the reference: its category, its role and their parents."""

    cost_type: UUID
    category: UUID
    org_node: UUID
    calendar: UUID
    role: UUID


def write_reference(connection: Connection) -> LineReference:
    """Write, around the service, a category of labour and a role of it; give them."""
    reference = LineReference(*(uuid4() for _ in range(5)))
    connection.execute(
        insert(CostType).values(
            id=reference.cost_type,
            code="MO",
            label="Main-d'œuvre",
            kind="labor",
            is_active=True,
            **STAMP,
        )
    )
    connection.execute(
        insert(CostCategory).values(
            id=reference.category,
            code="ING",
            label="Ingénierie",
            accounting_code="641",
            cost_type_id=reference.cost_type,
            is_active=True,
            **STAMP,
        )
    )
    connection.execute(
        insert(OrgNode).values(
            id=reference.org_node, code="BE", label="Études", is_active=True, **STAMP
        )
    )
    connection.execute(
        insert(Calendar).values(
            id=reference.calendar,
            label="Semaine",
            is_default=False,
            is_active=True,
            **WEEK,
            **STAMP,
        )
    )
    connection.execute(
        insert(ResourceRole).values(
            id=reference.role,
            code="ING",
            label="Ingénieur",
            org_node_id=reference.org_node,
            cost_category_id=reference.category,
            calendar_id=reference.calendar,
            monthly_hours=Decimal(140),
            headcount=Decimal(2),
            is_active=True,
            **STAMP,
        )
    )
    return reference


def line_row(
    project_id: UUID, node_id: UUID, reference: LineReference, **overrides: object
) -> dict[str, object]:
    """Give the columns of a line of labour: two engineers for ten hours, priced in 2026."""
    return {
        "project_id": project_id,
        "node_id": node_id,
        "kind": "estimate_line",
        "label": "Conception — Ingénieur",
        "cost_category_id": reference.category,
        "resource_role_id": reference.role,
        "quantity": Decimal(2),
        "hours": Decimal(10),
        "unit_disbursement": None,
        "payment_delay_days": 0,
        "subproject_id": None,
        "base_amount": Decimal("1300.00"),
        "budgeted_amount": None,
        "reestimated_amount": Decimal("1300.00"),
        "consumption_year": 2026,
        **STAMP,
        **overrides,
    }


@dataclass(frozen=True)
class Bearer:
    """The task that bears a line: its project, its revision, its structure and its node."""

    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    task_id: UUID


def insert_line(
    connection: Connection, bearer: Bearer, reference: LineReference, *, rank: int = 1
) -> UUID:
    """Write a line of labour under a task, its node and its facet; give its node."""
    project_id = bearer.project_id
    node = node_row(project_id, bearer.revision_id, bearer.structure_id, rank=rank)
    node_id = node["id"]
    assert isinstance(node_id, UUID)
    connection.execute(
        insert(Node).values({**node, "kind": "estimate_line", "parent_id": bearer.task_id})
    )
    connection.execute(insert(EstimateLine).values(**line_row(project_id, node_id, reference)))
    return node_id


def rate_row(
    project_id: UUID, revision_id: UUID, category_id: UUID, **overrides: object
) -> dict[str, object]:
    """Give the columns of the rate of a category a revision keeps: 65.00, of the reference."""
    return {
        "project_id": project_id,
        "id": uuid4(),
        "revision_id": revision_id,
        "cost_category_id": category_id,
        "amount": Decimal("65.00"),
        "origin": "reference",
        **overrides,
    }


def imaged(project_id: UUID, revision_id: UUID) -> dict[str, object]:
    """Give the columns every image shares: its revision, the audit and the counter it copies."""
    return {
        "project_id": project_id,
        "id": uuid4(),
        "revision_id": revision_id,
        "is_active": True,
        "created_at": AT,
        "updated_at": AT,
        "lock_version": 1,
    }


def role_image_row(
    project_id: UUID, revision_id: UUID, reference: LineReference, **overrides: object
) -> dict[str, object]:
    """Give the columns of the image of the role of the reference."""
    return {
        **imaged(project_id, revision_id),
        "resource_role_id": reference.role,
        "code": "ING",
        "label": "Ingénieur",
        "org_node_id": reference.org_node,
        "org_node_label": "Études",
        "cost_category_id": reference.category,
        "cost_category_label": "Ingénierie",
        "calendar_id": reference.calendar,
        "calendar_label": "Semaine",
        "monthly_hours": Decimal(140),
        "headcount": Decimal(2),
        **overrides,
    }


def calendar_image_row(
    project_id: UUID, revision_id: UUID, reference: LineReference, **overrides: object
) -> dict[str, object]:
    """Give the columns of the image of the calendar of the reference."""
    return {
        **imaged(project_id, revision_id),
        "calendar_id": reference.calendar,
        "label": "Semaine",
        **WEEK,
        "is_default": False,
        **overrides,
    }


def category_image_row(
    project_id: UUID, revision_id: UUID, reference: LineReference, **overrides: object
) -> dict[str, object]:
    """Give the columns of the image of the category of the reference."""
    return {
        **imaged(project_id, revision_id),
        "cost_category_id": reference.category,
        "code": "ING",
        "label": "Ingénierie",
        "cost_type_id": reference.cost_type,
        "cost_type_label": "Main-d'œuvre",
        "cost_type_kind": "labor",
        "cost_type_is_active": True,
        "accounting_code": "641",
        **overrides,
    }
