# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A task without an hour is refused where the engine is replayed, the task and its roles named.

A calendar changed while a project is at rest — its last revision marked, none current — can leave
a task of the copy without an hour in its week: the opening of a revision refuses it
(``createRevision``, 422 ``TASK_WITHOUT_WORKING_HOURS``), and so does any other write that replays
the engine (US-3330, #4413), the task by its project, its node and its label, its roles by those
of its labour lines. Every answer is checked against the contract.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, add_role, costing
from installed_reference import holding
from nodes_support import Tree, mark, opened, refusal
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select, update

from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.core.revisions.tables import Revision

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

CALENDARS = "/api/v1/reference/calendars"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
WEEKDAYS = (8, 8, 8, 8, 8, 0, 0)
WEEKEND = (0, 0, 0, 0, 0, 8, 8)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def worked(role: UUID, **line: Any) -> dict[str, Any]:
    """Give a labour line of a role: one person for ten hours."""
    return {"quantity": "1", "resource_role_id": str(role), "hours": "10", **line}


def set_week(database: Database, calendar_id: UUID, hours: tuple[int, ...]) -> None:
    """Write the hours of a calendar around the service, as a change of the reference does."""
    days = dict(zip(DAYS, (Decimal(each) for each in hours), strict=True))
    with database.transaction() as session:
        session.execute(update(Calendar).where(Calendar.id == calendar_id).values(**days))


def change_week(
    api: ContractClient, stage: Scene, realm: TestRealm, calendar_id: UUID, hours: tuple[int, ...]
) -> None:
    """Change the hours of a calendar through the API, as a manager of the reference does."""
    changing = holding(stage.database, realm, "resource_settings.write")
    listed = api.get(f"{CALENDARS}?sort_by=is_default", headers=changing).json()["items"]
    calendar = next(each for each in listed if each["calendar_id"] == str(calendar_id))
    sent = {
        "label": calendar["label"],
        "weekly_hours": dict(zip(DAYS, (str(each) for each in hours), strict=True)),
        "lock_version": calendar["lock_version"],
    }
    changed = api.patch(f"{CALENDARS}/{calendar_id}", headers=changing, json=sent)
    assert changed.status_code == 200, changed.text


def calendar_of_role(database: Database, role_id: UUID) -> UUID:
    """Read the calendar of a role."""
    with database.transaction() as session:
        return session.scalars(
            select(ResourceRole.calendar_id).where(ResourceRole.id == role_id)
        ).one()


def default_calendar_id(database: Database) -> UUID:
    """Read the default calendar."""
    with database.transaction() as session:
        return session.scalars(select(Calendar.id).where(Calendar.is_default)).one()


def revisions(stage: Scene) -> int:
    """Count the revisions of the project of the stage."""
    with stage.database.transaction() as session:
        return (
            session.scalar(
                select(func.count())
                .select_from(Revision)
                .where(Revision.project_id == UUID(stage.project["project_id"]))
            )
            or 0
        )


def open_revision(api: ContractClient, stage: Scene) -> Any:
    """Ask to open the current revision of the project, as its manager does; give the answer."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    return api.post(path, headers=stage.manager.headers, json={})


@pytest.mark.requirement("WF-PLA-0010-A")
@pytest.mark.usefixtures("costs")
def test_the_opening_of_a_revision_refuses_a_task_left_without_an_hour_naming_it_and_its_roles(
    api: ContractClient, stage: Scene, tree: Tree, realm: TestRealm
) -> None:
    # [US-3330] The project at rest — its last revision marked, none current — keeps a task with
    # the lines of two roles; the calendar of one changes through the API (the guard lets the
    # project at rest through), the two share no day: the opening is refused naming the task of
    # the copy and the roles, and creates nothing; the calendar corrected, it succeeds.
    first = add_role(stage.database, "AA", WEEKDAYS)
    second = add_role(stage.database, "BB", WEEKDAYS)
    lines = Lines(tree)
    task = tree.made("Câblage")
    lines.made(task, **worked(first))
    lines.made(task, **worked(second, label="Second"))
    mark(stage, tree.revision)
    before = revisions(stage)
    calendar = calendar_of_role(stage.database, second)
    change_week(api, stage, realm, calendar, WEEKEND)
    refused = open_revision(api, stage)
    status, code, params = refusal(refused)
    assert (status, code) == (422, "TASK_WITHOUT_WORKING_HOURS")
    assert params["resource_roles"] == [
        {"resource_role_id": str(first), "code": "AA", "label": "Rôle AA"},
        {"resource_role_id": str(second), "code": "BB", "label": "Rôle BB"},
    ]
    [named] = params["tasks"]
    assert (named["project_id"], named["label"]) == (stage.project["project_id"], "Câblage")
    UUID(named["node_id"])
    assert revisions(stage) == before
    change_week(api, stage, realm, calendar, WEEKDAYS)
    assert open_revision(api, stage).status_code == 201
    assert revisions(stage) == before + 1


@pytest.mark.requirement("WF-PLA-0010-A")
def test_the_opening_names_no_role_for_a_task_without_a_line_on_a_default_calendar_without_hours(
    api: ContractClient, stage: Scene, tree: Tree
) -> None:
    # [US-3330] A task without a labour line falls on the default calendar: the roles are empty.
    tree.made("Études")
    mark(stage, tree.revision)
    set_week(stage.database, default_calendar_id(stage.database), (0,) * 7)
    status, code, params = refusal(open_revision(api, stage))
    assert (status, code) == (422, "TASK_WITHOUT_WORKING_HOURS")
    assert params["resource_roles"] == []
    [named] = params["tasks"]
    assert (named["project_id"], named["label"]) == (stage.project["project_id"], "Études")


@pytest.mark.requirement("WF-PLA-0010-A")
def test_the_first_task_created_on_a_default_calendar_without_hours_is_refused_not_a_500(
    api: ContractClient, stage: Scene, tree: Tree, realm: TestRealm
) -> None:
    # [US-3330] The default calendar passes to zero hours while no current revision has a task
    # (the guard of the change lets it through): the first automatic task created answers the same
    # 422, and nothing is written.
    changing = holding(stage.database, realm, "resource_settings.write")
    listed = api.get(f"{CALENDARS}?sort_by=is_default", headers=changing).json()["items"]
    calendar = next(each for each in listed if each["is_default"])
    sent = {
        "label": calendar["label"],
        "weekly_hours": dict.fromkeys(DAYS, "0"),
        "lock_version": calendar["lock_version"],
    }
    changed = api.patch(f"{CALENDARS}/{calendar['calendar_id']}", headers=changing, json=sent)
    assert changed.status_code == 200, changed.text
    refused = tree.create("Études")
    status, code, params = refusal(refused)
    assert (status, code) == (422, "TASK_WITHOUT_WORKING_HOURS")
    assert params["resource_roles"] == []
    [named] = params["tasks"]
    assert (named["project_id"], named["label"]) == (stage.project["project_id"], "Études")
    assert tree.items() == []


@pytest.mark.requirement("WF-PLA-0010-A")
@pytest.mark.usefixtures("costs")
def test_every_write_that_replays_the_engine_translates_the_refusal_where_it_is_called(
    stage: Scene, tree: Tree
) -> None:
    # [US-3330] The refusal is translated by ``dated``, the one call of the engine: a creation, a
    # change of a task and a change of a line all answer 422, none 500, and the task
    # stays as it was.
    role = add_role(stage.database, "AA", WEEKDAYS)
    other = add_role(stage.database, "BB", WEEKDAYS)
    task = tree.made("Câblage")
    lines = Lines(tree)
    first = lines.made(task, **worked(role))["nodes"][0]
    lines.made(task, **worked(other, label="Second"))
    before = tree.node(task["node_id"])
    set_week(stage.database, calendar_of_role(stage.database, other), WEEKEND)
    answers = [
        tree.create("Autre"),
        tree.change(before, duration={"value": "3", "unit": "d"}),
        lines.change(first, quantity="2"),
    ]
    refused = [refusal(each) for each in answers]
    assert [each[:2] for each in refused] == [(422, "TASK_WITHOUT_WORKING_HOURS")] * 3
    for _, _, params in refused:
        assert [(each["project_id"], each["label"]) for each in params["tasks"]] == [
            (stage.project["project_id"], "Câblage")
        ]
        assert [(each["resource_role_id"], each["code"]) for each in params["resource_roles"]] == [
            (str(role), "AA"),
            (str(other), "BB"),
        ]
    after = tree.node(task["node_id"])
    kept = ("duration", "start", "finish", "scheduling_mode")
    assert [after["task"][name] for name in kept] == [before["task"][name] for name in kept]
    assert after["lock_version"] == before["lock_version"]
    assert [each["task"]["label"] for each in tree.items() if each["task"]] == ["Câblage"]
