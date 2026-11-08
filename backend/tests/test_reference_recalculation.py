# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structures redated when the reference changes, and the idle tasks (US-1390/L2).

``setDurationUnits``, ``updateCalendar`` and ``setDefaultCalendar`` — and a calendar the bootstrap
or the witness creates the default (#2510) — redate, in their transaction,
the structures of the current revisions — a marked revision keeps the dates it computed —, and
refuse a default calendar that would leave a task of a current revision without an hour, naming
its projects by their label and their code, the author consulting none of them. The recalculation
takes the reference before any structure, waits for the write of the planning that holds a
structure and for an opening in flight, is waited for by a marking, and a structure carried beyond
fifteen years refuses the change naming its project alone. A revision opened from a marked one is
dated with the constants of its opening; a label, or the same constants sent again, redate
nothing. Every answer of the service is checked against the contract. The
structures start their planning on Monday the 2nd of November 2026, on the default calendar of
eight hours from Monday to Friday.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from installed_reference import holding
from nodes_support import Tree, instant, mark, opened, refusal, scheduled_at
from planning_support import DAY
from projects_support import Scene, create
from projects_support import scene as make_scene
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.projects.interface import Viewer
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.interface import (
    CalendarContent,
    Units,
    WeeklyHours,
    create_calendar,
    get_duration_units,
    lock_reference,
    set_duration_units,
)
from waterfall.core.resource_settings.tables import DurationUnit
from waterfall.core.revisions.interface import create_revision
from waterfall.core.revisions.tables import CostStructure, Revision
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
def test_a_calendar_created_the_default_is_judged_and_redates_as_a_designation(
    tree: Tree, database: Database
) -> None:
    # « Une tâche sans ligne de main-d'œuvre est planifiée sur le calendrier par défaut. » The
    # bootstrap and the loader of the witness create the default by the module, which judges and
    # redates it as ``setDefaultCalendar`` does (#2510).
    task = tree.made("Études", task=TWO_DAYS)
    act = Act(None, utc_now())
    closed = CalendarContent("Fermé", WeeklyHours(*[Decimal(0)] * 7))
    with pytest.raises(UnprocessableError) as refused, database.transaction() as session:
        create_calendar(session, closed, act, default=True)
    assert refused.value.code == "TASK_WITHOUT_WORKING_HOURS"
    four, none = Decimal(4), Decimal(0)
    half = CalendarContent("Mi-temps", WeeklyHours(four, four, four, four, four, none, none))
    with database.transaction() as session:
        created = create_calendar(session, half, act, default=True)
    read = tree.node(task["node_id"])["task"]
    assert (read["calendar_id"], read["finish"]) == (
        str(created.calendar_id),
        instant(THURSDAY, "4"),
    )


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
    sent = {
        "label": calendar["label"],
        "weekly_hours": idle,
        "lock_version": calendar["lock_version"],
    }
    named = {
        "resource_roles": [],
        "projects": [
            {"project_label": "Ligne de convoyage", "project_code": "PRJ-002"},
            {"project_label": "Modernisation du poste de commande", "project_code": None},
        ],
    }
    answer = api.patch(f"{CALENDARS}/{calendar['calendar_id']}", headers=changing, json=sent)
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
def test_a_change_carrying_a_structure_beyond_fifteen_years_names_its_project_alone(
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
    # The project named by its label and its code, without anything else: the author of the change
    # may consult none of them (WF-ADM-0110).
    named = {"project_label": "Modernisation du poste de commande", "project_code": None}
    assert (refused.value.code, refused.value.params) == (
        "PROJECT_HORIZON_EXCEEDED",
        {"projects": [named]},
    )
    assert task["node_id"] not in repr(refused.value.params)
    assert "Exploitation" not in repr(refused.value.params)
    with database.transaction() as session:
        assert get_duration_units(session).units.hours_per_day == Decimal(8)
    assert finish(tree, task) == before


def seven_hours(database: Database) -> None:
    """Set the hours per day at seven, those per week at thirty-five, in a transaction."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        held = get_duration_units(session).lock_version
        set_duration_units(session, Units(Decimal(7), Decimal(35), Decimal(20)), held, act)


def counted(tree: Tree) -> tuple[datetime, int]:
    """Read the instant the dates of the structure were computed, and its counter."""
    with tree.stage.owner.connect() as connection:
        row = connection.execute(
            select(CostStructure.scheduled_at, CostStructure.lock_version).where(
                CostStructure.id == UUID(tree.structure_id)
            )
        ).one()
    return row.scheduled_at, row.lock_version


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_revision_opened_after_the_change_is_dated_with_the_new_constants(
    api: ContractClient, tree: Tree, stage: Scene, changing: dict[str, str]
) -> None:
    # The marked revision keeps its sixteen hours; the current one opened from it after the change
    # counts fourteen, from its opening, before any write.
    marked_task = tree.made("Études", task=TWO_DAYS)
    mark(stage, tree.revision)
    answer = units(api, changing, "7")
    assert answer.status_code == 200, answer.text
    current = Tree(api, stage, opened(api, stage))
    [current_task] = current.items()
    assert finish(current, current_task) == instant(TUESDAY, "6")
    assert scheduled_at(current) > scheduled_at(tree)
    assert finish(tree, marked_task) == instant(TUESDAY, "8")


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_change_made_while_a_revision_opens_redates_it_once_opened(
    api: ContractClient, tree: Tree, stage: Scene, database: Database
) -> None:
    # The opening shares the lock of the reference the change takes: the change waits for the
    # opening, then sees the revision it opened, and redates it.
    tree.made("Études", task=TWO_DAYS)
    mark(stage, tree.revision)
    project_id = UUID(stage.project["project_id"])
    act = Act(None, utc_now())
    with ThreadPoolExecutor(max_workers=1) as pool:
        with database.transaction() as session:
            revision = create_revision(session, project_id, act, Viewer(uuid4(), ()))
            changed = pool.submit(seven_hours, database)
            wait_for_a_lock(database)
            assert not changed.done()
        changed.result(timeout=10)
    current = Tree(api, stage, {"revision_id": str(revision.revision_id)})
    [current_task] = current.items()
    assert finish(current, current_task) == instant(TUESDAY, "6")


@pytest.mark.requirement("WF-PLA-0160-A")
def test_the_change_takes_the_reference_before_its_constants_and_any_structure(
    tree: Tree, stage: Scene, database: Database
) -> None:
    # The order of the locks (EP-06, « Ce que le cadrage décide »): the reference first. Waiting
    # for it, the change holds neither its constants nor a structure.
    task = tree.made("Études", task=TWO_DAYS)
    with (
        Session(stage.owner) as holder,
        holder.begin(),
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        lock_reference(holder)
        changed = pool.submit(seven_hours, database)
        wait_for_a_lock(database)
        with stage.owner.connect() as other:
            other.execute(select(DurationUnit.id).with_for_update(nowait=True))
            other.execute(select(CostStructure.id).with_for_update(nowait=True))
            other.rollback()
        assert not changed.done()
        holder.commit()
        changed.result(timeout=10)
    assert finish(tree, task) == instant(TUESDAY, "6")


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_marking_asked_during_the_recalculation_marks_the_dates_it_computed(
    tree: Tree, stage: Scene, database: Database
) -> None:
    # The recalculation reads the current revisions FOR SHARE: the marking, which locks its
    # revision, waits for it, and the marked revision keeps the fourteen hours it computed.
    task = tree.made("Études", task=TWO_DAYS)
    with stage.owner.connect() as holder, ThreadPoolExecutor(max_workers=2) as pool:
        holder.execute(
            select(CostStructure.id)
            .where(CostStructure.id == UUID(tree.structure_id))
            .with_for_update()
        )
        changed = pool.submit(seven_hours, database)
        wait_for_a_lock(database)
        marking = pool.submit(mark, stage, tree.revision)
        wait_for_a_lock(database, 2)
        assert not changed.done()
        assert not marking.done()
        holder.commit()
        changed.result(timeout=10)
        marking.result(timeout=10)
    assert finish(tree, task) == instant(TUESDAY, "6")
    with stage.owner.connect() as connection:
        status = connection.scalar(
            select(Revision.status).where(Revision.id == UUID(tree.revision["revision_id"]))
        )
    assert status == "marked"


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_label_or_the_same_constants_written_redate_nothing(
    api: ContractClient, tree: Tree, changing: dict[str, str]
) -> None:
    # Only the constants, the hours of the default or its designation redate the plannings: a
    # label changed, or the constants sent again, leave the instant and the counter of each
    # structure as they were.
    tree.made("Études", task=TWO_DAYS)
    before = counted(tree)
    calendar = default_calendar(api, changing)
    sent = {
        "label": "Calendrier de l'atelier",
        "weekly_hours": calendar["weekly_hours"],
        "lock_version": calendar["lock_version"],
    }
    renamed = api.patch(f"{CALENDARS}/{calendar['calendar_id']}", headers=changing, json=sent)
    assert renamed.status_code == 200, renamed.text
    again = units(api, changing, "8")
    assert again.status_code == 200, again.text
    assert counted(tree) == before
