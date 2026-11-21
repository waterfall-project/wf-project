# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of a differential before the guards of the calendars and the redating (US-3060/L9).

The base is redated with the other structures of its revision (#4210): a task of it must keep an
hour in its week, and the guards of the calendars count its tasks (#4213). A refusal that
concerns a task of the base names the task of the differential of the same lineage, never a node
of the base, which no operation serves. Every answer is checked against the contract
(``ContractClient``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from amendments_support import deleted, node_labelled, on, opened_amendment
from estimate_support import Costing, Lines, add_role, costing
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed
from sqlalchemy import select, update

from waterfall.core.planning.interface.reference import tasks_left_idle
from waterfall.core.planning.rescheduling import replayed
from waterfall.core.planning.tables import Node, Task
from waterfall.core.resource_settings.interface import CalendarChange, IdleProject
from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.core.revisions.interface import differential_base
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient, ReferenceSessions

    from waterfall.platform.database import Database

CALENDARS = "/api/v1/reference/calendars"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# Far beyond the fifteen years of the horizon (WF-PLA-0150), in days of work.
BEYOND = Decimal(5000)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


def base_of(project: Costed, differential: str) -> UUID:
    """Give the base of a differential."""
    with project.stage.database.transaction() as session:
        base = differential_base(session, project.project_id, UUID(differential))
    assert base is not None
    return base


@pytest.mark.story("US-3060")
def test_a_task_of_the_base_left_without_an_hour_refuses_the_calendar_of_its_role(
    api: ContractClient, project: Costed, reference_sessions: ReferenceSessions
) -> None:
    # [US-3060] The guards count the tasks of the base (#4213, with #4210): the line of a role
    # whose calendar works the week leaves it, in the main structure and in the differential, after
    # the opening; the base alone keeps it. Its calendar emptied of its hours would leave the task
    # of the base without an hour, which its redating could not place: refused, the project named
    # as WF-ADM-0110 names it, without identifier nor task.
    database = project.stage.database
    role = add_role(database, "SOUD", (8, 8, 8, 8, 8, 0, 0))
    task = node_labelled(project.tree, STUDY)
    labour = {"label": "Soudure", "quantity": "1", "resource_role_id": str(role), "hours": "4"}
    Lines(project.tree).made(task, **labour)
    differential = opened_amendment(api, project)
    amendment = on(project.tree, differential)
    for tree in (project.tree, amendment):
        node = node_labelled(tree, "Soudure")
        Lines(tree).changed(node, resource_role_id=str(project.costs.role))
    with database.transaction() as session:
        calendar = session.scalars(
            select(Calendar)
            .join(ResourceRole, ResourceRole.calendar_id == Calendar.id)
            .where(ResourceRole.id == role)
        ).one()
        held = (calendar.id, calendar.label, calendar.lock_version)
    sent = {"label": held[1], "weekly_hours": dict.fromkeys(DAYS, "0"), "lock_version": held[2]}
    changing = reference_sessions("resource_settings").changing
    answer = api.patch(f"{CALENDARS}/{held[0]}", headers=changing, json=sent)
    assert answer.status_code == 422, answer.text
    body: dict[str, Any] = answer.json()
    named = project.stage.project
    assert body["code"] == "TASK_WITHOUT_WORKING_HOURS"
    assert body["params"]["projects"] == [
        {"project_label": named["label"], "project_code": named.get("code")}
    ]
    assert [each["resource_role_id"] for each in body["params"]["resource_roles"]] == [str(role)]


@pytest.mark.story("US-3060")
def test_a_task_of_the_base_alone_on_the_default_calendar_refuses_its_week_emptied(
    api: ContractClient, project: Costed
) -> None:
    # [US-3060] The guard of the default calendar counts the tasks of the base too (#4213): the
    # main structure and the differential delete their tasks after the opening, the base keeps
    # them, on the default calendar, which a week without an hour would leave idle.
    differential = opened_amendment(api, project)
    for tree in (project.tree, on(project.tree, differential)):
        for label in (STUDY, MAKING):
            deleted(tree, label, project.stage.manager)
    empty = CalendarChange(uuid4(), dict.fromkeys(DAYS, Decimal(0)), default=True)
    with project.stage.database.transaction() as session:
        idle = tasks_left_idle(session, empty)
    named = project.stage.project
    assert idle == (IdleProject(named["label"], named.get("code")),)


@pytest.mark.story("US-3060")
def test_the_redating_of_the_base_names_the_task_of_the_differential_of_the_same_lineage(
    api: ContractClient, project: Costed
) -> None:
    # [US-3060] A refusal of the redating of the base names the task of the differential of the
    # same lineage, never a node of the base (#4213): the studies of the base carried beyond the
    # horizon, the refusal names the studies as the differential has renamed them; once the
    # differential has deleted them, by their label, their node null.
    database = project.stage.database
    differential = opened_amendment(api, project)
    amendment = on(project.tree, differential)
    studies = node_labelled(amendment, STUDY)
    amendment.changed(studies, label="Études revues")
    base = base_of(project, differential)
    with database.transaction() as session:
        session.execute(
            update(Task)
            .where(
                Task.project_id == project.project_id,
                Task.structure_id == base,
                Task.label == STUDY,
            )
            .values(duration_value=BEYOND, duration_unit="d")
        )
        held = session.scalar(
            select(Node.id).where(
                Node.project_id == project.project_id,
                Node.structure_id == base,
                Node.lineage_id == UUID(studies["lineage_id"]),
            )
        )
    assert held is not None

    def refused() -> dict[str, Any]:
        with pytest.raises(UnprocessableError) as caught, database.transaction() as session:
            replayed(session, project.project_id, base, utc_now())
        assert caught.value.code == "PROJECT_HORIZON_EXCEEDED"
        return dict(caught.value.params)

    renamed = {"node_id": studies["node_id"], "label": "Études revues"}
    assert refused() == {"task": renamed}
    deleted(amendment, "Études revues", project.stage.manager)
    assert refused() == {"task": {"node_id": None, "label": STUDY}}
    assert str(held) != studies["node_id"]
