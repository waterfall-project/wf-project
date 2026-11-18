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
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from importlib import import_module
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from planning_support import DAY, node_row
from project_rows import AT, STAMP
from sqlalchemy import insert, select

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
    set_hourly_rate,
)
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node
from waterfall.core.resource_settings.tables import Calendar, OrgNode, ResourceRole
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest
    from nodes_support import Tree
    from projects_support import Person
    from sqlalchemy.engine import Connection

    from waterfall.platform.database import Database

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


def give_a_line(connection: Connection, task_id: UUID) -> UUID:
    """Give a task a line of labour of the role ``ING`` of a scene, around the service; its node.

    What the designation of the reference asks of the estimate (``revision_has_lines``), beside
    the task the planning asks for (``planning_support.give_a_task``).
    """
    task = connection.execute(
        select(Node.project_id, Node.revision_id, Node.structure_id).where(Node.id == task_id)
    ).one()
    role, category = connection.execute(
        select(ResourceRole.id, ResourceRole.cost_category_id).where(ResourceRole.code == "ING")
    ).one()
    reference = LineReference(uuid4(), category, uuid4(), uuid4(), role)
    bearer = Bearer(task.project_id, task.revision_id, task.structure_id, task_id)
    return insert_line(connection, bearer, reference)


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


# The year the revisions of the tests are priced at: that of their creation. ``YEAR`` and
# ``LAST_INSTANT`` are both taken once, when this module is loaded.
YEAR = utc_now().year
LAST_INSTANT = datetime(YEAR, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)


def monday_in(year: int) -> date:
    """Give a Monday of a year: that of the tests of the planning, moved whole weeks.

    ``planning_support.DAY`` is where a tree starts its planning: Monday 2 November 2026. Moved by
    52 weeks a year, the date drifts a day or so earlier in the calendar each year, which does not
    matter: it is a Monday, a working day, in the year asked. A task that must be consumed in
    ``YEAR`` or two years later is placed on the Monday ``monday_in`` gives, working whatever the
    year, where a date written in the test would fall on a day off.
    """
    return DAY + timedelta(weeks=52 * (year - DAY.year))


def task_in(year: int) -> dict[str, Any]:
    """Give the facts of a task set by hand on two days of a year, to consume its lines there."""
    first = monday_in(year)
    return {
        "scheduling_mode": "manual",
        "start": {"date": first.isoformat()},
        "finish": {"date": (first + timedelta(days=1)).isoformat()},
    }


# The modules whose reading of the clock gives a year or a day that a test compares to ``YEAR``:
# the year of a revision (the service, and the import that opens one), the day a structure starts
# on or a review is dated, the day the plans and the indicators are read at. ``api.lifecycle`` and
# ``api.subprojects`` read the clock only to date what they write (``Act``): no revision is opened
# through them, and none of their reads is a year or a day a test compares (#3739).
CLOCKED = (
    "waterfall.api.revisions",
    "waterfall.api.nodes",
    "waterfall.api.work_breakdown",
    "waterfall.api.workload",
    "waterfall.api.estimate_indicators",
    "waterfall.api.remaining_indicators",
    "waterfall.core.exchanges.running",
    "waterfall.core.exchanges.interface.exports",
    "waterfall.core.estimate.interface.remaining_excel",
    "waterfall.core.revisions.interface.reference",
)


# What is left of ``YEAR`` after the instant a pinned clock stops at: a clock that has stopped goes
# on by a microsecond a reading, and this is the number of readings it has before the year ends.
HEADROOM = timedelta(seconds=1)
CEILING = LAST_INSTANT - HEADROOM


def pinned_clock(read: Callable[[], datetime]) -> Callable[[], datetime]:
    """Give a clock that reads ``read`` but never leaves ``YEAR``, and never reads twice the same.

    It follows ``read`` until ``CEILING``, a second before the last instant of ``YEAR``. Past it,
    it advances by a microsecond at each reading: a test that compares two instants it reads (a
    review that must be after another) still finds them apart, where a clock stopped at one
    instant would give them equal (#3739).
    """
    last: list[datetime] = []

    def clock() -> datetime:
        instant = min(read(), CEILING)
        if last and instant <= last[0]:
            instant = last[0] + timedelta(microseconds=1)
        last[:] = [instant]
        return instant

    return clock


def read_clock() -> datetime:
    """Read ``utc_now`` of this module at each call: a test sets it to cross New Year."""
    return utc_now()


def pin_year(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the services that read the year or the day in ``YEAR``, though the run crosses New Year.

    The year a revision is born with is the one its clock reads at the request (WF-REV-0060), by
    the service or by the import that opens it; the rates of ``costing`` are for ``YEAR``, read
    once. The clock of each module of ``CLOCKED`` still runs, but stops near the end of ``YEAR``
    (``pinned_clock``): an instant after midnight, when the run has crossed it, falls there,
    on the 31 December, and each reading is after the one before. It runs before every test (the
    fixture ``pinned_year`` of ``conftest.py``), so that a test or a fixture that sets a clock of
    its own sets it over this one; a clock already set when it runs would be pinned over, or
    left, and fails the test instead.
    """
    clock = pinned_clock(read_clock)
    for module in CLOCKED:
        assert import_module(module).utc_now is utc_now, f"the clock of {module} is already set"
        monkeypatch.setattr(f"{module}.utc_now", clock)


@dataclass(frozen=True)
class Costing:
    """What the lines of a scene name, their categories rated for ``YEAR``.

    Its role and its category of labour, a category of material, and the category of provision the
    installation is delivered with.
    """

    role: UUID
    labour: UUID
    material: UUID
    provision: UUID


def costing(database: Database, rate: str = "65.00") -> Costing:
    """Rate the category of labour of a completed reference, and add a category of material."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        role, labour = session.execute(
            select(ResourceRole.id, ResourceRole.cost_category_id).where(ResourceRole.code == "ING")
        ).one()
        set_hourly_rate(session, (labour, YEAR), Decimal(rate), None, act)
        nature = create_cost_type(session, CostTypeDraft("MAT", "Matériel", "non_labor"), act)
        draft = CostCategoryDraft("MAT-001", "Matériel électrique", "606001", nature.cost_type_id)
        material = create_cost_category(session, draft, act).cost_category_id
        provision = session.scalars(
            select(CostCategory.id)
            .join(CostType, CostType.id == CostCategory.cost_type_id)
            .where(CostType.kind == "provision")
        ).first()
    assert provision is not None
    return Costing(role, labour, material, provision)


def add_role(
    database: Database, code: str, hours: tuple[int, ...], category: UUID | None = None
) -> UUID:
    """Write a role of the category of labour of the scene, on a calendar of its own hours."""
    calendar = uuid4()
    days = dict(zip(WEEK, (Decimal(each) for each in hours), strict=True))
    with database.transaction() as session:
        held = session.execute(
            select(ResourceRole.org_node_id, ResourceRole.cost_category_id).where(
                ResourceRole.code == "ING"
            )
        ).one()
        session.execute(
            insert(Calendar).values(
                id=calendar,
                label=f"Semaine {code}",
                is_default=False,
                is_active=True,
                **days,
                **STAMP,
            )
        )
        role = uuid4()
        session.execute(
            insert(ResourceRole).values(
                id=role,
                code=code,
                label=f"Rôle {code}",
                org_node_id=held[0],
                cost_category_id=category or held[1],
                calendar_id=calendar,
                headcount=Decimal(1),
                is_active=True,
                **STAMP,
            )
        )
    return role


class Lines:
    """The lines of the main structure of a tree, written and read through the service."""

    def __init__(self, tree: Tree) -> None:
        self.tree = tree

    def create(self, task: dict[str, Any] | str, who: Person | None = None, /, **line: Any) -> Any:
        """Ask for a line under a task, as the manager does by default; give the answer."""
        place = {key: line.pop(key) for key in ("after_node_id",) if key in line}
        parent = task if isinstance(task, str) else task["node_id"]
        sent = {"kind": "estimate_line", "parent_id": parent, "estimate_line": line, **place}
        headers = (who or self.tree.stage.manager).headers
        return self.tree.api.post(f"{self.tree.path}/nodes", headers=headers, json=sent)

    def made(
        self, task: dict[str, Any] | str, who: Person | None = None, /, **line: Any
    ) -> dict[str, Any]:
        """Create a line that must be created; give what is answered."""
        answer = self.create(task, who, **line)
        assert answer.status_code == 201, answer.text
        return answer.json()

    def change(self, node: dict[str, Any], who: Person | None = None, /, **body: Any) -> Any:
        """Change a line at the counter read; give the answer."""
        sent = {"lock_version": node["lock_version"], **body}
        headers = (who or self.tree.stage.manager).headers
        path = f"{self.tree.path}/nodes/{node['node_id']}/estimate-line"
        return self.tree.api.patch(path, headers=headers, json=sent)

    def changed(self, node: dict[str, Any], **body: Any) -> dict[str, Any]:
        """Change a line that must be changed; give what is answered."""
        answer = self.change(node, **body)
        assert answer.status_code == 200, answer.text
        return answer.json()
