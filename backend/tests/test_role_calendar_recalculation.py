# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The current revisions redated and priced again when the calendar of a role changes (US-3320).

``updateCalendar`` on any calendar whose hours change, and ``updateResourceRole`` giving a role
another calendar, redate in their transaction the structures of the current revisions and price
again every line of them, moved or not (#4411: BRC-01, BCH-07); a marked revision keeps its dates
and its amounts (WF-REF-0130). A label alone, or a role that keeps its calendar, redate nothing; a
change carried beyond fifteen years, or that prices a line past its column, is refused, nothing
written. The role is changed under the lock of the reference, taken before its own and before any
structure (EP-06). The structures start their planning on Monday the 2nd of November 2026; the
role R, of the category of labour of the scene, works on a calendar of its own, not the default,
of eight hours from Monday to Friday. Every answer of the service is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, add_role, costing
from installed_reference import holding
from nodes_support import Tree, faults, instant, mark, opened, refusal
from planning_support import DAY
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.cost_settings.interface import set_hourly_rate
from waterfall.core.resource_settings.interface import (
    CategoryAdmission,
    RoleChange,
    lock_reference,
    update_role,
)
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

CALENDARS = "/api/v1/reference/calendars"
ROLES = "/api/v1/reference/resource-roles"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
TUESDAY = DAY + timedelta(days=1)
WEDNESDAY = DAY + timedelta(days=2)
THURSDAY = DAY + timedelta(days=3)
SIXTEEN_HOURS = {"duration": {"value": "16", "unit": "h"}}
EIGHT_HOURS = (8, 8, 8, 8, 8, 0, 0)
FOUR_HOURS = ("4", "4", "4", "4", "4", "0", "0")
THREE_DAYS = ("8", "8", "8", "0", "0", "0", "0")
PRECISION = "VALIDATION_FAILED"
PROJECT = {"project_label": "Modernisation du poste de commande", "project_code": None}


@dataclass(frozen=True)
class Setting:
    """The main structure of the current revision, its lines, the role R, and who changes it."""

    tree: Tree
    lines: Lines
    role: UUID
    changing: dict[str, str]

    @property
    def api(self) -> ContractClient:
        """Give the client of the service."""
        return self.tree.api

    @property
    def stage(self) -> Scene:
        """Give the stage of the tree."""
        return self.tree.stage


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def setting(api: ContractClient, stage: Scene, realm: TestRealm) -> Setting:
    """Give the revision the manager opened, the role R, and who changes the resource settings.

    The one who changes them is a contributor of no project.
    """
    tree = Tree(api, stage, opened(api, stage))
    changing = holding(stage.database, realm, "resource_settings.read", "resource_settings.write")
    return Setting(tree, Lines(tree), add_role(stage.database, "R", EIGHT_HOURS), changing)


def week(*hours: str) -> dict[str, str]:
    """Name the hours of a week by day, Monday first."""
    return dict(zip(DAYS, hours, strict=True))


def worked(role: UUID) -> dict[str, Any]:
    """Give a labour line of a role: one person for ten hours."""
    return {"quantity": "1", "resource_role_id": str(role), "hours": "10"}


def task_of_r(setting: Setting, label: str, task: dict[str, Any]) -> dict[str, Any]:
    """Make a task that bears a labour line of R; give the task as created."""
    made = setting.tree.made(label, task=task)
    setting.lines.made(made, **worked(setting.role))
    return made


def read_role(setting: Setting) -> dict[str, Any]:
    """Read R as the list gives it."""
    answer = setting.api.get(f"{ROLES}?include_inactive=true", headers=setting.changing)
    role = str(setting.role)
    return next(each for each in answer.json()["items"] if each["resource_role_id"] == role)


def calendar_of_r(setting: Setting) -> str:
    """Give the calendar of R."""
    return str(read_role(setting)["calendar_id"])


def read_calendar(setting: Setting, calendar: str) -> dict[str, Any]:
    """Read a calendar as the list gives it."""
    answer = setting.api.get(f"{CALENDARS}?include_inactive=true", headers=setting.changing)
    return next(each for each in answer.json()["items"] if each["calendar_id"] == calendar)


def change_calendar(setting: Setting, *hours: str, label: str = "") -> Any:
    """Change the hours of the calendar of R, its label kept unless one is given; give the reply."""
    calendar = calendar_of_r(setting)
    read = read_calendar(setting, calendar)
    sent = {
        "label": label or read["label"],
        "weekly_hours": week(*hours) if hours else read["weekly_hours"],
        "lock_version": read["lock_version"],
    }
    return setting.api.patch(f"{CALENDARS}/{calendar}", headers=setting.changing, json=sent)


def new_calendar(setting: Setting, label: str, *hours: str) -> str:
    """Create a calendar of these hours; give its identifier."""
    sent = {"label": label, "weekly_hours": week(*hours)}
    created = setting.api.post(CALENDARS, headers=setting.changing, json=sent)
    assert created.status_code == 201, created.text
    return str(created.json()["calendar_id"])


def change_role(setting: Setting, **changed: str) -> Any:
    """Change R as read, with what is given; give the answer."""
    read = read_role(setting)
    kept = ("code", "label", "cost_category_id", "calendar_id")
    sent = {
        **{name: read[name] for name in kept},
        "capacity": {"headcount": read["capacity"]["headcount"]},
        "lock_version": read["lock_version"],
        **changed,
    }
    return setting.api.patch(f"{ROLES}/{setting.role}", headers=setting.changing, json=sent)


def finish(tree: Tree, node: dict[str, Any]) -> dict[str, str]:
    """Read the finish of a task of a structure."""
    return tree.node(node["node_id"])["task"]["finish"]


def counted(tree: Tree) -> tuple[Any, int]:
    """Read the instant the dates of the structure were computed, and its counter."""
    with tree.stage.owner.connect() as connection:
        row = connection.execute(
            select(CostStructure.scheduled_at, CostStructure.lock_version).where(
                CostStructure.id == UUID(tree.structure_id)
            )
        ).one()
    return row.scheduled_at, row.lock_version


def dates_and_amounts(tree: Tree) -> list[tuple[Any, ...]]:
    """Read the dates and amounts of each task and the amounts of each line of a structure."""
    read: list[tuple[Any, ...]] = []
    for item in tree.items():
        if item["kind"] == "task":
            task = item["task"]
            names = ("start", "finish", "base_amount", "reestimated_amount")
            read.append((item["node_id"], *(task[name] for name in names)))
        else:
            line = item["estimate_line"]
            names = ("base_amount", "budgeted_amount", "reestimated_amount", "consumption_year")
            read.append((item["node_id"], *(line[name] for name in names)))
    return read


def inflated(setting: Setting, rate: str) -> None:
    """Change the rate of inflation of the project at the counter read."""
    stage = setting.stage
    path = f"{PROJECTS}/{stage.project['project_id']}"
    held = setting.api.get(path, headers=stage.manager.headers).json()["lock_version"]
    sent = {"inflation_rate": rate, "lock_version": held}
    answer = setting.api.patch(path, headers=stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


# --- The dates follow the calendar of the role -------------------------------------------------


@pytest.mark.requirement("WF-PLA-0010-A")
@pytest.mark.usefixtures("costs")
def test_the_hours_of_a_role_calendar_changed_redate_its_tasks_at_the_next_reading(
    setting: Setting,
) -> None:
    # « Une tâche de seize heures en mode automatique, commencée un lundi matin sur un calendrier
    # de huit heures du lundi au vendredi, finit le mardi ; sur un calendrier de quatre heures,
    # elle finit le jeudi. » The calendar of the role R, not the default, passed to four hours by
    # ``updateCalendar``: the task finishes on Thursday at the next reading, without another write.
    task = task_of_r(setting, "Études", SIXTEEN_HOURS)
    assert finish(setting.tree, task) == instant(TUESDAY, "8")
    changed = change_calendar(setting, *FOUR_HOURS)
    assert changed.status_code == 200, changed.text
    read = setting.tree.node(task["node_id"])["task"]
    assert (read["finish"], read["calendar_hours"]["monday"]) == (instant(THURSDAY, "4"), "4")


@pytest.mark.requirement("WF-PLA-0010-A")
@pytest.mark.usefixtures("costs")
def test_a_role_given_another_calendar_redates_its_tasks_at_the_next_reading(
    setting: Setting,
) -> None:
    # « Une tâche de seize heures en mode automatique, commencée un lundi matin sur un calendrier
    # de huit heures du lundi au vendredi, finit le mardi ; sur un calendrier de quatre heures,
    # elle finit le jeudi. » R given by ``updateResourceRole`` another calendar, of four hours.
    task = task_of_r(setting, "Études", SIXTEEN_HOURS)
    assert finish(setting.tree, task) == instant(TUESDAY, "8")
    half = new_calendar(setting, "Mi-temps", *FOUR_HOURS)
    changed = change_role(setting, calendar_id=half)
    assert changed.status_code == 200, changed.text
    read = setting.tree.node(task["node_id"])["task"]
    assert (read["finish"], read["calendar_id"]) == (instant(THURSDAY, "4"), half)


# --- The amounts follow it too, for a task that does not move -----------------------------------


def priced_at_2026(setting: Setting) -> None:
    """Price the revision at 2026, its labour at 100.00 an hour, the project inflating at 3 %."""
    stage = setting.stage
    with stage.owner.begin() as connection:
        connection.execute(
            update(Revision)
            .where(Revision.id == UUID(setting.tree.revision["revision_id"]))
            .values(reference_year=2026)
        )
    with stage.database.transaction() as session:
        labour = session.scalar(
            select(ResourceRole.cost_category_id).where(ResourceRole.id == setting.role)
        )
        assert labour is not None
        set_hourly_rate(session, (labour, 2026), Decimal("100.00"), None, Act(None, utc_now()))
    inflated(setting, "0.03")


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_line_of_a_task_the_change_does_not_move_is_priced_again_on_the_new_calendar(
    setting: Setting,
) -> None:
    # « La répartition mensuelle de la charge d'une ligne suit les heures du calendrier de son
    # rôle. » For a task the change does not move (BCH-07): a manual task from the 28th of
    # December to the 8th of January bears a line of 1 000 at 3 % of inflation; its role passes
    # from five days of 8 h to four days of 10 h: the share between the two years passes from
    # 40/60 to 50/50, and the re-estimated amount from 1 018.00 to 1 015.00, in the transaction of
    # the change. The revision is priced at 2026, the year of those dates, ten hours at 100.00.
    priced_at_2026(setting)
    manual = {
        "scheduling_mode": "manual",
        "start": {"date": date(2026, 12, 28).isoformat()},
        "finish": {"date": date(2027, 1, 8).isoformat()},
    }
    task = setting.tree.made("Mise en service", task=manual)
    line = setting.lines.made(task, **worked(setting.role))["nodes"][0]["estimate_line"]
    assert (line["base_amount"], line["reestimated_amount"]) == ("1000.00", "1018.00")
    assert line["consumption_year"] == 2027
    before = setting.tree.node(task["node_id"])["task"]
    changed = change_calendar(setting, "10", "10", "10", "10", "0", "0", "0")
    assert changed.status_code == 200, changed.text
    [after] = [each["estimate_line"] for each in setting.tree.items("?kinds=estimate_line")]
    assert (after["base_amount"], after["reestimated_amount"]) == ("1000.00", "1015.00")
    assert after["consumption_year"] == 2026
    read = setting.tree.node(task["node_id"])["task"]
    assert (read["start"], read["finish"]) == (before["start"], before["finish"])
    assert read["reestimated_amount"] == "1015.00"


# --- A marked revision keeps what it computed ---------------------------------------------------


@pytest.mark.requirement("WF-REF-0130-A")
@pytest.mark.usefixtures("costs")
def test_a_marked_revision_keeps_its_dates_and_amounts_when_the_calendar_of_its_role_changes(
    setting: Setting,
) -> None:
    # « Après correction d'un taux horaire et changement de la catégorie d'un rôle, les montants
    # d'une révision marquée qui les employait sont identiques à ceux relevés avant la
    # modification. » Its form for the calendar: the hours of the calendar of R changed, then R
    # given another calendar, the marked revision that employed it keeps its dates and its
    # amounts; the current one opened from it follows each change.
    marked = setting.tree
    task_of_r(setting, "Études", SIXTEEN_HOURS)
    mark(setting.stage, marked.revision)
    current = Tree(setting.api, setting.stage, opened(setting.api, setting.stage))
    [current_task] = [each for each in current.items() if each["kind"] == "task"]
    kept = dates_and_amounts(marked)
    assert change_calendar(setting, *FOUR_HOURS).status_code == 200
    assert finish(current, current_task) == instant(THURSDAY, "4")
    assert dates_and_amounts(marked) == kept
    six = new_calendar(setting, "Six heures", "6", "6", "6", "6", "6", "0", "0")
    assert change_role(setting, calendar_id=six).status_code == 200
    # Sixteen hours of six a day: the Monday, the Tuesday, then four hours of the Wednesday.
    assert finish(current, current_task) == instant(WEDNESDAY, "4")
    assert dates_and_amounts(marked) == kept


# --- What redates nothing ----------------------------------------------------------------------


@pytest.mark.story("US-3320")
@pytest.mark.usefixtures("costs")
def test_a_label_alone_or_a_role_that_keeps_its_calendar_redate_and_price_nothing(
    setting: Setting,
) -> None:
    # A change that touches the label of a calendar alone, or a role whose calendar does not
    # change, neither redates nor prices anything: the instant and the counter of the structure
    # stay as they were, and so do the dates and the amounts.
    task_of_r(setting, "Études", SIXTEEN_HOURS)
    before = (counted(setting.tree), dates_and_amounts(setting.tree))
    renamed = change_calendar(setting, label="Semaine de l'atelier")
    assert renamed.status_code == 200, renamed.text
    relabelled = change_role(setting, label="Rôle renommé")
    assert relabelled.status_code == 200, relabelled.text
    assert (counted(setting.tree), dates_and_amounts(setting.tree)) == before


# --- What is refused, nothing written -----------------------------------------------------------


@pytest.mark.story("US-3320")
@pytest.mark.usefixtures("costs")
def test_a_role_change_carrying_a_project_beyond_fifteen_years_is_refused_naming_it(
    setting: Setting,
) -> None:
    # The change that would carry a project beyond fifteen years is refused, the projects named by
    # their label and their code (422 ``PROJECT_HORIZON_EXCEEDED``), as for the default calendar;
    # nothing is written. Three thousand days of eight hours lie within fifteen years; of four,
    # beyond: by the hours of the calendar of R as by R given another calendar.
    task_of_r(setting, "Exploitation", {"duration": {"value": "3000", "unit": "d"}})
    before = dates_and_amounts(setting.tree)
    calendar = calendar_of_r(setting)
    named = (422, "PROJECT_HORIZON_EXCEEDED", {"projects": [PROJECT]})
    assert refusal(change_calendar(setting, *FOUR_HOURS)) == named
    assert read_calendar(setting, calendar)["weekly_hours"]["monday"] == "8"
    half = new_calendar(setting, "Mi-temps", *FOUR_HOURS)
    assert refusal(change_role(setting, calendar_id=half)) == named
    assert calendar_of_r(setting) == calendar
    assert dates_and_amounts(setting.tree) == before


@pytest.mark.story("US-3320")
def test_a_role_change_that_prices_a_line_past_its_column_is_refused_at_the_field(
    setting: Setting, costs: Costing
) -> None:
    # The change that would price a line past its column is refused at the field entered (#3401),
    # as for the default calendar; nothing is written. A task of thirty days on the calendar of R
    # bears a line of material at its most: three days a week carry it past the year, its share
    # of the next one projected at 3 %. Each day changed is named for the calendar, its
    # ``/calendar_id`` for the role.
    inflated(setting, "0.03")
    task = task_of_r(setting, "Câblage", {"duration": {"value": "30", "unit": "d"}})
    most = {"cost_category_id": str(costs.material), "unit_disbursement": "999999999999.99"}
    setting.lines.made(task, quantity="1", **most)
    before = dates_and_amounts(setting.tree)
    calendar = calendar_of_r(setting)
    assert faults(change_calendar(setting, *THREE_DAYS)) == [
        ("/weekly_hours/thursday", PRECISION, {}),
        ("/weekly_hours/friday", PRECISION, {}),
    ]
    assert read_calendar(setting, calendar)["weekly_hours"]["thursday"] == "8"
    shorter = new_calendar(setting, "Trois jours", *THREE_DAYS)
    refused = change_role(setting, calendar_id=shorter)
    assert faults(refused) == [("/calendar_id", PRECISION, {})]
    assert calendar_of_r(setting) == calendar
    assert dates_and_amounts(setting.tree) == before


# --- The order of the locks ----------------------------------------------------------------------


def changed_role(database: Database, role: UUID, calendar: UUID, code: str | None = None) -> None:
    """Give a role another calendar, and a code if given, by the module, in a transaction."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        held = session.get_one(ResourceRole, role)
        change = RoleChange(
            held.code if code is None else code,
            held.label,
            None,
            held.cost_category_id,
            CategoryAdmission(is_labour=True, is_active=True),
            calendar,
            held.headcount,
        )
        update_role(session, role, change, held.lock_version, act)


@pytest.mark.story("US-3320")
@pytest.mark.usefixtures("costs")
def test_a_role_changed_takes_the_reference_before_the_role_and_any_structure(
    setting: Setting,
) -> None:
    # The order of EP-06: the reference, the role, then the structures. Waiting for the reference,
    # the change holds neither the role nor a structure.
    task = task_of_r(setting, "Études", SIXTEEN_HOURS)
    half = UUID(new_calendar(setting, "Mi-temps", *FOUR_HOURS))
    owner, database = setting.stage.owner, setting.stage.database
    with Session(owner) as holder, holder.begin(), ThreadPoolExecutor(max_workers=1) as pool:
        lock_reference(holder)
        changed = pool.submit(changed_role, database, setting.role, half)
        wait_for_a_lock(database)
        with owner.connect() as other:
            role = ResourceRole.id == setting.role
            other.execute(select(ResourceRole.id).where(role).with_for_update(nowait=True))
            other.execute(select(CostStructure.id).with_for_update(nowait=True))
            other.rollback()
        assert not changed.done()
        holder.commit()
        changed.result(timeout=10)
    assert finish(setting.tree, task) == instant(THURSDAY, "4")


@pytest.mark.story("US-3320")
@pytest.mark.usefixtures("costs")
def test_a_role_changed_waiting_for_a_structure_leaves_a_line_free_to_name_the_role(
    setting: Setting,
) -> None:
    # The change holds the role while it waits for a structure a write of the planning holds: it
    # holds it ``FOR NO KEY UPDATE``, so that the foreign key of a line the write adds, which
    # shares the key of the role, is not waited for — the two would wait for each other.
    task = task_of_r(setting, "Études", SIXTEEN_HOURS)
    half = UUID(new_calendar(setting, "Mi-temps", *FOUR_HOURS))
    owner, database = setting.stage.owner, setting.stage.database
    structure = CostStructure.id == UUID(setting.tree.structure_id)
    with owner.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute(select(CostStructure.id).where(structure).with_for_update())
        changed = pool.submit(changed_role, database, setting.role, half)
        wait_for_a_lock(database)
        role = ResourceRole.id == setting.role
        shared = select(ResourceRole.id).where(role)
        holder.execute(shared.with_for_update(read=True, key_share=True, nowait=True))
        assert not changed.done()
        holder.commit()
        changed.result(timeout=10)
    assert finish(setting.tree, task) == instant(THURSDAY, "4")


@pytest.mark.story("US-3320")
@pytest.mark.usefixtures("costs")
def test_a_role_changed_of_code_and_calendar_waiting_for_a_structure_leaves_a_line_free(
    setting: Setting,
) -> None:
    # The code, unique, takes the role ``FOR UPDATE`` when it is written: written last, after the
    # structures, the change waiting for one does not hold the role strongly, and a line naming it
    # is not waited for.
    task = task_of_r(setting, "Études", SIXTEEN_HOURS)
    half = UUID(new_calendar(setting, "Mi-temps", *FOUR_HOURS))
    owner, database = setting.stage.owner, setting.stage.database
    structure = CostStructure.id == UUID(setting.tree.structure_id)
    with owner.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute(select(CostStructure.id).where(structure).with_for_update())
        changed = pool.submit(changed_role, database, setting.role, half, "RENAMED")
        wait_for_a_lock(database)
        role = ResourceRole.id == setting.role
        shared = select(ResourceRole.id).where(role)
        holder.execute(shared.with_for_update(read=True, key_share=True, nowait=True))
        assert not changed.done()
        holder.commit()
        changed.result(timeout=10)
    assert finish(setting.tree, task) == instant(THURSDAY, "4")
    with owner.connect() as check:
        assert check.scalar(select(ResourceRole.code).where(role)) == "RENAMED"
