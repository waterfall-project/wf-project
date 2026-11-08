# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structures redated when the reference changes, and the idle tasks (US-1390/L2).

``setDurationUnits``, ``updateCalendar`` and ``setDefaultCalendar`` redate, in their transaction,
the structures of the current revisions — a marked revision keeps the dates it computed —, and
refuse a default calendar that would leave a task of a current revision without an hour, naming
its projects by their label and their code, the author consulting none of them. The recalculation
waits for the write of the planning that holds a structure, and a structure carried beyond fifteen
years refuses the change. Every answer of the service is checked against the contract. The
structures start their planning on Monday the 2nd of November 2026, on the default calendar of
eight hours from Monday to Friday.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from installed_reference import holding
from nodes_support import Tree, instant, mark, opened, refusal, scheduled_at
from planning_support import DAY
from projects_support import Scene, create
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import wait_for_a_lock

from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.interface import (
    Units,
    get_duration_units,
    set_duration_units,
)
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

CALENDARS = "/api/v1/reference/calendars"
UNITS = "/api/v1/reference/duration-units"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
TUESDAY = DAY + timedelta(days=1)
THURSDAY = DAY + timedelta(days=3)
TWO_DAYS = {"duration": {"value": "2", "unit": "d"}}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def changing(stage: Scene, realm: TestRealm) -> dict[str, str]:
    """Give the session of who changes the resource settings, a contributor of no project."""
    return holding(stage.database, realm, "resource_settings.write")


def week(*hours: str) -> dict[str, str]:
    """Name the hours of a week by day, Monday first."""
    return dict(zip(DAYS, hours, strict=True))


def units(api: ContractClient, headers: dict[str, str], per_day: str) -> Any:
    """Set the hours per day, those per week at five days of them; give the answer."""
    read = api.get(UNITS, headers=headers).json()
    sent = {
        "hours_per_day": per_day,
        "hours_per_week": str(Decimal(per_day) * 5),
        "days_per_month": "20",
        "lock_version": read["lock_version"],
    }
    return api.put(UNITS, headers=headers, json=sent)


def default_calendar(api: ContractClient, headers: dict[str, str]) -> dict[str, Any]:
    """Read the default calendar."""
    listed = api.get(f"{CALENDARS}?sort_by=is_default", headers=headers).json()["items"]
    return next(each for each in listed if each["is_default"])


def stage_of(stage: Scene, project: dict[str, Any]) -> Scene:
    """Give the stage of another project of the same manager."""
    return replace(stage, project=project)


def finish(tree: Tree, node: dict[str, Any]) -> dict[str, str]:
    """Read the finish of a task of a structure."""
    return tree.node(node["node_id"])["task"]["finish"]


@pytest.mark.requirement("WF-PLA-0160-A")
def test_seven_hours_a_day_redate_the_current_revision_and_leave_the_marked_one(
    api: ContractClient, tree: Tree, stage: Scene, changing: dict[str, str]
) -> None:
    # « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j » dans une révision en
    # cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision marquée, elle
    # vaut toujours seize heures. »
    marked_task = tree.made("Études", task=TWO_DAYS)
    assert finish(tree, marked_task) == instant(TUESDAY, "8")
    mark(stage, tree.revision)
    current = Tree(api, stage, opened(api, stage))
    [current_task] = current.items()
    marked_at, current_at = scheduled_at(tree), scheduled_at(current)
    answer = units(api, changing, "7")
    assert answer.status_code == 200, answer.text
    # Fourteen hours on a calendar of eight: the Monday, then six hours of the Tuesday.
    assert current_task["task"]["duration"] == {"value": "2", "unit": "d"}
    assert finish(current, current_task) == instant(TUESDAY, "6")
    assert scheduled_at(current) > current_at
    # The marked revision keeps the sixteen hours it computed.
    assert finish(tree, marked_task) == instant(TUESDAY, "8")
    assert scheduled_at(tree) == marked_at


@pytest.mark.requirement("WF-PLA-0010-A")
def test_the_hours_of_the_default_calendar_changed_redate_the_current_tasks(
    api: ContractClient, tree: Tree, changing: dict[str, str]
) -> None:
    task = tree.made("Études", task=TWO_DAYS)
    calendar = default_calendar(api, changing)
    sent = {
        "label": calendar["label"],
        "weekly_hours": week("4", "4", "4", "4", "4", "0", "0"),
        "lock_version": calendar["lock_version"],
    }
    answer = api.patch(f"{CALENDARS}/{calendar['calendar_id']}", headers=changing, json=sent)
    assert answer.status_code == 200, answer.text
    # Sixteen hours of four a day: Monday to Thursday.
    read = tree.node(task["node_id"])["task"]
    assert read["finish"] == instant(THURSDAY, "4")
    assert read["calendar_hours"]["monday"] == "4"


@pytest.mark.requirement("WF-PLA-0010-A")
def test_another_calendar_designated_the_default_redates_the_current_tasks(
    api: ContractClient, tree: Tree, changing: dict[str, str]
) -> None:
    # « Une tâche sans ligne de main-d'œuvre est planifiée sur le calendrier par défaut. »
    task = tree.made("Études", task=TWO_DAYS)
    sent = {"label": "Mi-temps", "weekly_hours": week("4", "4", "4", "4", "4", "0", "0")}
    created = api.post(CALENDARS, headers=changing, json=sent)
    assert created.status_code == 201, created.text
    half = created.json()
    designated = api.put(
        f"{CALENDARS}/{half['calendar_id']}/default",
        headers=changing,
        json={"lock_version": half["lock_version"]},
    )
    assert designated.status_code == 200, designated.text
    read = tree.node(task["node_id"])["task"]
    assert (read["calendar_id"], read["finish"]) == (half["calendar_id"], instant(THURSDAY, "4"))


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_default_left_without_hours_is_refused_naming_each_project_by_label_and_code(
    api: ContractClient, tree: Tree, stage: Scene, changing: dict[str, str]
) -> None:
    # « La modification d'un calendrier qui laisserait une tâche sans heure dans un projet que le
    # manager ne peut pas consulter est refusée en nommant ce projet par son libellé et son code ;
    # un projet en chiffrage sans code est nommé par son seul libellé. »
    tree.made("Études")
    other = create(api, stage.manager, label="Ligne de convoyage")
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project).where(Project.id == UUID(other["project_id"])).values(code="PRJ-002")
        )
    second = Tree(api, stage_of(stage, other), opened(api, stage_of(stage, other)))
    second.made("Convoyeur")
    # A third project holds its task in a marked revision alone: no task of it is current.
    third = create(api, stage.manager, label="Atelier de peinture")
    marked = Tree(api, stage_of(stage, third), opened(api, stage_of(stage, third)))
    marked.made("Cabine")
    mark(stage_of(stage, third), marked.revision)
    calendar = default_calendar(api, changing)
    idle = week("0", "0", "0", "0", "0", "0", "0")
    sent = {"label": calendar["label"], "weekly_hours": idle, "lock_version": 1}
    named = {
        "resource_roles": [],
        "projects": [
            {"project_label": "Ligne de convoyage", "project_code": "PRJ-002"},
            {"project_label": "Modernisation du poste de commande", "project_code": None},
        ],
    }
    answer = api.patch(
        f"{CALENDARS}/{calendar['calendar_id']}",
        headers=changing,
        json={**sent, "lock_version": calendar["lock_version"]},
    )
    assert refusal(answer) == (422, "TASK_WITHOUT_WORKING_HOURS", named)
    created = api.post(CALENDARS, headers=changing, json={"label": "Fermé", "weekly_hours": idle})
    closed = created.json()
    designated = api.put(
        f"{CALENDARS}/{closed['calendar_id']}/default",
        headers=changing,
        json={"lock_version": closed["lock_version"]},
    )
    assert refusal(designated) == (422, "TASK_WITHOUT_WORKING_HOURS", named)
    assert default_calendar(api, changing)["weekly_hours"]["monday"] == "8"


@pytest.mark.requirement("WF-PLA-0160-A")
def test_the_recalculation_waits_for_the_write_that_holds_a_structure(
    tree: Tree, stage: Scene, database: Database
) -> None:
    # The reference first, then each structure in the order of (project, identifier): the change
    # waits for the write of the planning that holds the structure, which never waits for the
    # reference (EP-06, « Ce que le cadrage décide »).
    task = tree.made("Études", task=TWO_DAYS)
    act = Act(None, utc_now())

    def change() -> None:
        with database.transaction() as session:
            held = get_duration_units(session).lock_version
            set_duration_units(session, Units(Decimal(7), Decimal(35), Decimal(20)), held, act)

    with stage.owner.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute(
            select(CostStructure.id)
            .where(CostStructure.id == UUID(tree.structure_id))
            .with_for_update()
        )
        changed = pool.submit(change)
        wait_for_a_lock(database)
        assert not changed.done()
        holder.commit()
        changed.result(timeout=10)
    assert finish(tree, task) == instant(TUESDAY, "6")


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_change_carrying_a_current_structure_beyond_fifteen_years_writes_nothing(
    tree: Tree, database: Database
) -> None:
    # Three thousand days of eight hours lie within fifteen years; of twenty-four, beyond.
    task = tree.made("Exploitation", task={"duration": {"value": "3000", "unit": "d"}})
    before = finish(tree, task)
    act = Act(None, utc_now())
    with database.transaction() as session:
        held = get_duration_units(session).lock_version
    longer = Units(Decimal(24), Decimal(120), Decimal(20))
    with pytest.raises(UnprocessableError) as refused, database.transaction() as session:
        set_duration_units(session, longer, held, act)
    assert (refused.value.code, refused.value.params) == (
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": task["node_id"], "label": "Exploitation"}},
    )
    with database.transaction() as session:
        assert get_duration_units(session).units.hours_per_day == Decimal(8)
    assert finish(tree, task) == before
