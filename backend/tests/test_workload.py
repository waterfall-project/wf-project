# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of a project by role and by month, and the planned value of its reference (US-1520).

``getProjectWorkload`` on the three bases, on the main structure of the revisions of a project its
manager made (``nodes_support``), its labour category rated and its roles on calendars of eight
hours from Monday to Friday (``estimate_support``); ``planned_value`` of the interface of the
estimate. Every answer is checked against the contract. In November and December 2026 the
calendars work 21 and 23 days, 168 and 184 hours; in March and April 2026, 22 days each. The clock
is set: the day of the service, and the day the worker marks on.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import Costing, Lines, add_role, costing
from nodes_support import Tree, faults, mark, opened, refusal, set_progress
from project_rows import STAMP
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import insert, select, update

from waterfall.core.estimate.interface import planned_value
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.resource_settings.tables import OrgNode, ResourceRole

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

STATE_FORBIDS = "STATE_FORBIDS_OPERATION"
VALIDATION_FAILED = "VALIDATION_FAILED"
# A task from the first Monday of November to the last day of December 2026.
NOV_DEC = ("2026-11-02", "2026-12-31")
NOVEMBER = ("2026-11-02", "2026-11-30")
WORKED_DAYS = (8, 8, 8, 8, 8, 0, 0)
CENT = Decimal("0.01")
type Clock = Callable[[date], None]


@dataclass
class Site:
    """The project of a scene, its revision opened, a role that works eight hours a weekday."""

    api: ContractClient
    stage: Scene
    tree: Tree
    lines: Lines
    costs: Costing
    worker: UUID

    @property
    def path(self) -> str:
        """Give the path of the project."""
        return f"{PROJECTS}/{self.stage.project['project_id']}"

    def task(self, label: str, dates: tuple[str, str] = NOV_DEC) -> dict[str, Any]:
        """Create a task that a manual scheduling places between two days."""
        start, finish = dates
        manual = {"scheduling_mode": "manual", "start": {"date": start}, "finish": {"date": finish}}
        return self.tree.made(label, task=manual)

    def labour(
        self, task: dict[str, Any], hours: str, role: UUID | None = None, **line: Any
    ) -> str:
        """Give a task a labour line of a role, one person for some hours; give its node."""
        held = {"quantity": "1", "resource_role_id": str(role or self.worker), "hours": hours}
        return self.lines.made(task, **{**held, **line})["nodes"][0]["node_id"]

    def material(self, task: dict[str, Any], amount: str) -> str:
        """Give a task a line of material for an amount; give its node."""
        held = {"quantity": "1", "cost_category_id": str(self.costs.material)}
        return self.lines.made(task, **held, unit_disbursement=amount)["nodes"][0]["node_id"]

    def referenced(self) -> Tree:
        """Mark the revision, designate it the reference; give the revision opened after."""
        mark(self.stage, self.tree.revision)
        headers = self.stage.manager.headers
        counter = self.api.get(self.path, headers=headers).json()["lock_version"]
        sent = {
            "revision_id": self.tree.revision["revision_id"],
            "confirmed": True,
            "lock_version": counter,
        }
        answer = self.api.put(f"{self.path}/reference-revision", headers=headers, json=sent)
        assert answer.status_code == 200, answer.text
        return Tree(self.api, self.stage, opened(self.api, self.stage))

    def asked(self, basis: str, **query: Any) -> Any:
        """Ask for the workload on a basis; give the answer."""
        text = "&".join(f"{name}={value}" for name, value in {"basis": basis, **query}.items())
        return self.api.get(f"{self.path}/workload?{text}", headers=self.stage.manager.headers)

    def plan(self, basis: str, **query: Any) -> dict[str, Any]:
        """Ask for a workload that must be given; give it."""
        answer = self.asked(basis, **query)
        assert answer.status_code == 200, answer.text
        return answer.json()

    def value(self, at: date) -> Decimal:
        """Give the planned value, at a day, of the reference of the project."""
        project = UUID(self.stage.project["project_id"])
        with self.stage.database.transaction() as session:
            return planned_value(session, project, UUID(self.tree.revision["revision_id"]), at)


@pytest.fixture
def site(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Site:
    """Give a platform, a project its manager made, its revision opened, and a role to load."""
    stage = make_scene(api, owner, database, realm)
    tree = Tree(api, stage, opened(api, stage))
    worker = add_role(database, "WRK", WORKED_DAYS)
    return Site(api, stage, tree, Lines(tree), costing(database), worker)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the service reads as today, and the worker marks on."""

    def set_day(day: date) -> None:
        now = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
        monkeypatch.setattr("waterfall.api.workload.utc_now", lambda: now)
        monkeypatch.setattr("nodes_support.utc_now", lambda: now)

    return set_day


def role_of(read: dict[str, Any], role_id: UUID) -> dict[str, Any]:
    """Give the role of a plan."""
    return next(each for each in read["roles"] if each["resource_role_id"] == str(role_id))


def months_of(role: dict[str, Any]) -> list[tuple[str, str]]:
    """Give the months of a role with their hours."""
    return [(each["month"], each["hours"]) for each in role["months"]]


def totals_of(read: dict[str, Any]) -> list[tuple[str, str]]:
    """Give the monthly totals of a plan."""
    return [(each["month"], each["hours"]) for each in read["monthly_totals"]]


def hours_of(read: dict[str, Any]) -> Decimal:
    """Give the hours of all the months of a plan."""
    return sum((Decimal(hours) for _, hours in totals_of(read)), Decimal(0))


# --- The load of a line --------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_line_of_a_task_over_two_civil_months_loads_both_in_proportion_to_the_hours_worked(
    site: Site, clock: Clock
) -> None:
    # « La charge d’une ligne portée par une tâche qui couvre exactement deux mois civils apparaît
    # sur ces deux mois, au prorata des heures travaillées de la tâche dans chacun. »
    clock(date(2026, 10, 15))
    site.labour(site.task("Câblage"), "352")
    current = site.referenced()
    for basis in ("reference_budget", "current_remaining"):
        read = site.plan(basis)
        assert months_of(role_of(read, site.worker)) == [
            ("2026-11", "168.00"),
            ("2026-12", "184.00"),
        ]
        assert totals_of(read) == [("2026-11", "168.00"), ("2026-12", "184.00")]
    assert (
        site.plan("current_remaining")["context"]["revision_id"]
        == (current.revision["revision_id"])
    )
    assert (
        site.plan("reference_budget")["context"]["revision_id"]
        == (site.tree.revision["revision_id"])
    )


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_load_is_the_quantity_times_the_hours_and_a_line_that_is_not_labour_has_none(
    site: Site, clock: Clock
) -> None:
    # The load of a labour line is its quantity times its hours (WF-DEV-0020); a line of material
    # carries no hour of work (body of the requirement: "les lignes de main-d'œuvre").
    clock(date(2026, 10, 15))
    task = site.task("Câblage")
    site.labour(task, "88", quantity="4")
    site.material(task, "350.00")
    site.referenced()
    read = site.plan("reference_budget")
    assert hours_of(read) == Decimal(352)
    assert [each["resource_role_id"] for each in read["roles"] if each["months"]] == [
        str(site.worker)
    ]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_monthly_totals_run_from_the_first_to_the_last_month_loaded_without_a_gap(
    site: Site,
) -> None:
    # Propre à l'US: « monthly_totals du premier au dernier mois chargé, sans trou », a month
    # without load included at zero, while the months of a role are those it is loaded in.
    site.labour(site.task("Études", NOVEMBER), "168")
    site.labour(site.task("Essais", ("2027-01-04", "2027-01-29")), "80")
    site.referenced()
    read = site.plan("reference_budget")
    assert totals_of(read) == [("2026-11", "168.00"), ("2026-12", "0"), ("2027-01", "80.00")]
    assert months_of(role_of(read, site.worker)) == [("2026-11", "168.00"), ("2027-01", "80.00")]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_plan_without_a_labour_line_has_no_total(site: Site) -> None:
    # Propre à l'US: monthly_totals « vide quand aucun rôle n'a de charge ».
    site.material(site.task("Câblage"), "350.00")
    site.referenced()
    read = site.plan("reference_budget")
    assert read["monthly_totals"] == []
    assert all(each["months"] == [] for each in read["roles"])


# --- The capacity and the zone ------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0070-A")
def test_each_role_shows_its_capacity_and_a_month_over_it_is_in_alert(site: Site) -> None:
    # « La capacité de chaque rôle est affichée. » : the capacity of the reference, for the roles
    # the lines employ and for the active roles they do not; a month is in alert past it.
    site.labour(site.task("Câblage"), "352")
    with site.stage.owner.begin() as connection:
        connection.execute(
            update(ResourceRole)
            .where(ResourceRole.id == site.worker)
            .values(monthly_hours=Decimal(175))
        )
    site.referenced()
    read = site.plan("reference_budget")
    role = role_of(read, site.worker)
    assert Decimal(role["capacity_monthly_hours"]) == Decimal(175)
    assert [(each["month"], each["zone"]) for each in role["months"]] == [
        ("2026-11", "nominal"),
        ("2026-12", "alert"),
    ]
    idle = next(each for each in read["roles"] if each["label"] == "Ingénieur")
    assert (Decimal(idle["capacity_monthly_hours"]), idle["months"]) == (Decimal(140), [])


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_role_deactivated_appears_only_if_the_lines_employ_it(site: Site) -> None:
    # « La capacité de chaque rôle est affichée. » : « pour chaque rôle employé » — a deactivated
    # role the lines employ keeps its capacity; one they do not employ is not listed.
    unused = add_role(site.stage.database, "OLD", WORKED_DAYS)
    site.labour(site.task("Câblage"), "352")
    with site.stage.owner.begin() as connection:
        connection.execute(
            update(ResourceRole)
            .where(ResourceRole.id.in_([site.worker, unused]))
            .values(is_active=False)
        )
    site.referenced()
    read = site.plan("reference_budget")
    listed = {each["resource_role_id"] for each in read["roles"]}
    assert str(site.worker) in listed
    assert str(unused) not in listed
    assert Decimal(role_of(read, site.worker)["capacity_monthly_hours"]) == Decimal(140)


# --- The filter by organisation node -------------------------------------------------------------


@dataclass(frozen=True)
class Below:
    """The node of the roles of the scene, a node under it, and a role attached to that one."""

    parent: UUID
    child: UUID
    fitter: UUID


@pytest.fixture
def below(site: Site) -> Below:
    """Give a node under the one the roles of the scene belong to, and a role that belongs to it."""
    child, fitter = uuid4(), uuid4()
    with site.stage.owner.begin() as connection:
        held = connection.execute(
            select(
                ResourceRole.org_node_id, ResourceRole.cost_category_id, ResourceRole.calendar_id
            ).where(ResourceRole.code == "ING")
        ).one()
        connection.execute(
            insert(OrgNode).values(
                id=child, code="SUB", label="Atelier", parent_id=held[0], is_active=True, **STAMP
            )
        )
        connection.execute(
            insert(ResourceRole).values(
                id=fitter,
                code="SUB",
                label="Monteur",
                org_node_id=child,
                cost_category_id=held[1],
                calendar_id=held[2],
                monthly_hours=Decimal(100),
                headcount=Decimal(1),
                is_active=True,
                **STAMP,
            )
        )
        connection.execute(
            update(ResourceRole).where(ResourceRole.id == site.worker).values(org_node_id=held[0])
        )
    return Below(held[0], child, fitter)


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_filter_by_node_keeps_the_roles_of_the_node_and_of_its_descendants(
    site: Site, below: Below
) -> None:
    # « Le filtre par nœud d’organisation ne laisse voir que les rôles qui en relèvent. »
    task = site.task("Câblage")
    site.labour(task, "168")
    site.labour(task, "184", role=below.fitter)
    site.referenced()
    both = {str(site.worker), str(below.fitter)}
    whole = site.plan("reference_budget")
    assert (whole["org_node_id"], whole["org_node_label"]) == (None, None)
    assert both <= {each["resource_role_id"] for each in whole["roles"]}
    # The node and its descendants: both roles, the total of both.
    from_parent = site.plan("reference_budget", org_node_id=below.parent)
    assert (from_parent["org_node_id"], from_parent["org_node_label"]) == (
        str(below.parent),
        "Direction",
    )
    assert both <= {each["resource_role_id"] for each in from_parent["roles"]}
    assert hours_of(from_parent) == Decimal(352)
    # The descendant alone: its role, and nothing of the others, in its total as in its list.
    from_child = site.plan("reference_budget", org_node_id=below.child)
    assert from_child["org_node_label"] == "Atelier"
    assert [each["resource_role_id"] for each in from_child["roles"]] == [str(below.fitter)]
    assert hours_of(from_child) == Decimal(184)
    assert Decimal(role_of(from_child, below.fitter)["capacity_monthly_hours"]) == Decimal(100)


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_node_the_reference_does_not_hold_is_refused_and_a_deactivated_one_is_named(
    site: Site, below: Below
) -> None:
    # « org_node_label résolu, UNKNOWN_ORG_NODE sinon » : 422 on ``/query/org_node_id``; the label
    # of a node deactivated is resolved all the same (WF-REF-0150).
    site.labour(site.task("Câblage"), "168")
    site.referenced()
    unknown = site.asked("reference_budget", org_node_id=uuid4())
    assert refusal(unknown)[:2] == (422, VALIDATION_FAILED)
    assert faults(unknown) == [("/query/org_node_id", "UNKNOWN_ORG_NODE", {})]
    with site.stage.owner.begin() as connection:
        connection.execute(update(OrgNode).where(OrgNode.id == below.child).values(is_active=False))
    named = site.plan("reference_budget", org_node_id=below.child)
    assert named["org_node_label"] == "Atelier"


# --- The completed tasks -------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_remaining_ignores_the_lines_of_the_tasks_completed_and_the_reference_does_not(
    site: Site, clock: Clock
) -> None:
    # « Le plan de charge calculé sur le reste à engager ignore les lignes des tâches terminées. »
    clock(date(2026, 10, 15))
    site.labour(site.task("Câblage"), "352")
    done = site.task("Repérage", NOVEMBER)
    site.labour(done, "168")
    set_progress(site.stage, done["node_id"], "completed", date(2026, 11, 20))
    current = site.referenced()
    marked = site.tree.revision["revision_id"]
    finished = next(
        each
        for each in current.items()
        if each["kind"] == "task" and each["task"]["label"] == "Repérage"
    )
    set_progress(site.stage, finished["node_id"], "completed", date(2026, 11, 20))
    assert hours_of(site.plan("reference_budget")) == Decimal(520)
    kept = [("2026-11", "168.00"), ("2026-12", "184.00")]
    for read in (
        site.plan("current_remaining"),
        site.plan("marked_remaining", revision_id=marked),
    ):
        assert months_of(role_of(read, site.worker)) == kept
        assert totals_of(read) == kept


# --- The three bases -----------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0070-A")
def test_without_a_reference_the_basis_of_the_reference_is_refused_and_the_current_one_is_offered(
    site: Site, clock: Clock
) -> None:
    # « Les trois bases sont proposées ; sur un projet sans révision de référence, la base de la
    # référence est absente, et sur un projet sans aucune révision marquée, seule la révision en
    # cours est proposée. »
    clock(date(2026, 10, 15))
    site.labour(site.task("Câblage"), "352")
    state = site.api.get(site.path, headers=site.stage.manager.headers).json()["state"]
    status, code, params = refusal(site.asked("reference_budget"))
    assert (status, code, params) == (
        409,
        STATE_FORBIDS,
        {"state": state, "state_enum": "ProjectState"},
    )
    current = site.plan("current_remaining")
    assert current["context"]["revision_id"] == site.tree.revision["revision_id"]
    assert (current["context"]["revision_status"], current["context"]["is_stored"]) == (
        "draft",
        False,
    )
    # No marked revision: ``marked_remaining`` names none, or the current revision, or nothing.
    for query in ({}, {"revision_id": site.tree.revision["revision_id"]}, {"revision_id": uuid4()}):
        refused = site.asked("marked_remaining", **query)
        assert refusal(refused)[:2] == (422, VALIDATION_FAILED)
        assert faults(refused) == [("/query/revision_id", VALIDATION_FAILED, {})]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_without_a_current_revision_its_basis_is_refused_and_a_marked_one_remains_a_basis(
    site: Site, clock: Clock
) -> None:
    # « Les trois bases sont proposées […] » : ``current_remaining`` refused by 409 without a
    # current revision, ``marked_remaining`` a basis of a marked revision, reference or not.
    clock(date(2026, 10, 15))
    site.labour(site.task("Câblage"), "352")
    mark(site.stage, site.tree.revision)
    status, code, params = refusal(site.asked("current_remaining"))
    assert (status, code, params["state_enum"]) == (409, STATE_FORBIDS, "ProjectState")
    read = site.plan("marked_remaining", revision_id=site.tree.revision["revision_id"])
    assert read["basis"] == "marked_remaining"
    assert read["context"]["revision_id"] == site.tree.revision["revision_id"]
    assert (read["context"]["revision_status"], read["context"]["is_stored"]) == ("marked", True)
    assert totals_of(read) == [("2026-11", "168.00"), ("2026-12", "184.00")]


# --- The date of calculation ---------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_not_started_carries_its_whole_load_on_the_months_that_follow_the_day(
    site: Site, clock: Clock
) -> None:
    # « Une tâche non démarrée dont la date de début est antérieure à la date de calcul ne présente
    # aucune charge sur les mois écoulés ; sa charge est la même avant et après son démarrage. »
    site.labour(site.task("Câblage"), "352")
    site.referenced()
    clock(date(2026, 11, 16))
    read = site.plan("current_remaining")
    assert read["context"]["computed_at"] == "2026-11-16T09:00:00Z"
    # 88 and 184 hours remain to work: the 352 hours of the line are shared between them.
    november = (Decimal(352) * 88 / 272).quantize(CENT)
    assert months_of(role_of(read, site.worker)) == [
        ("2026-11", str(november)),
        ("2026-12", str(352 - november)),
    ]
    clock(date(2026, 12, 1))
    started = site.plan("current_remaining")
    assert months_of(role_of(started, site.worker)) == [("2026-12", "352.00")]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_whose_end_is_past_carries_its_load_on_the_month_of_the_day(
    site: Site, clock: Clock
) -> None:
    # « […] sa charge est la même avant et après son démarrage. » : la charge portée au mois de la
    # date de calcul quand la fin est dépassée.
    site.labour(site.task("Câblage"), "352")
    site.referenced()
    clock(date(2027, 2, 17))
    read = site.plan("current_remaining")
    assert months_of(role_of(read, site.worker)) == [("2027-02", "352.00")]
    assert totals_of(read) == [("2027-02", "352.00")]
    # The reference is read whole, whatever the day.
    whole = site.plan("reference_budget")
    assert months_of(role_of(whole, site.worker)) == [("2026-11", "168.00"), ("2026-12", "184.00")]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_on_a_marked_revision_the_date_of_calculation_is_its_marking_date(
    site: Site, clock: Clock
) -> None:
    # « […] sur une révision marquée, la date de calcul est sa date de marquage. » (écart d'EP-09
    # pour le reste de 80 heures : ici, la charge courante de la ligne.) The plan holds no month
    # before the day of the marking, and does not move with the clock afterwards.
    site.labour(site.task("Câblage"), "352")
    clock(date(2026, 11, 16))
    mark(site.stage, site.tree.revision)
    clock(date(2031, 6, 1))
    read = site.plan("marked_remaining", revision_id=site.tree.revision["revision_id"])
    assert read["context"]["computed_at"] == "2026-11-16T09:00:00Z"
    november = (Decimal(352) * 88 / 272).quantize(CENT)
    assert totals_of(read) == [("2026-11", str(november)), ("2026-12", str(352 - november))]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_plan_of_the_reference_does_not_follow_the_delay_of_the_current_revision(
    site: Site, clock: Clock
) -> None:
    # The reference basis is read on the reference revision, the remaining on the current one:
    # a delay in the current revision moves the second, not the first.
    clock(date(2026, 10, 15))
    site.labour(site.task("Câblage"), "352")
    current = site.referenced()
    task = next(each for each in current.items() if each["kind"] == "task")
    delay = {"start": {"date": "2027-01-04"}, "finish": {"date": "2027-01-29"}}
    current.changed(task, scheduling_mode="manual", **delay)
    reference = site.plan("reference_budget")
    assert totals_of(reference) == [("2026-11", "168.00"), ("2026-12", "184.00")]
    assert totals_of(site.plan("current_remaining")) == [("2027-01", "352.00")]


# --- The planned value ---------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_of_a_budget_of_1000_is_nought_before_and_1000_at_the_end(
    site: Site,
) -> None:
    # « Sur un projet dont le budget de référence est de 1 000, la valeur planifiée vaut 1 000 à la
    # date de fin de la dernière tâche de la référence, et 0 avant le début de la première. »
    site.material(site.task("Câblage", NOVEMBER), "600")
    site.material(site.task("Essais", ("2026-12-01", "2026-12-31")), "400")
    site.referenced()
    assert site.value(date(2026, 11, 1)) == Decimal(0)
    assert site.value(date(2026, 12, 31)) == Decimal(1000)
    assert site.value(date(2031, 1, 1)) == Decimal(1000)
    assert site.value(date(2026, 11, 30)) == Decimal(600)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_line_of_a_task_of_two_months_worth_as_much_counts_for_half_at_the_end_of_the_first(
    site: Site,
) -> None:
    # « Une ligne portée par une tâche de deux mois comptant autant d’heures travaillées
    # contribue pour moitié à la fin du premier mois. » (March and April 2026: 22 days each.)
    site.material(site.task("Câblage", ("2026-03-02", "2026-04-30")), "1000")
    site.referenced()
    assert site.value(date(2026, 3, 31)) == Decimal(500)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_provision_is_not_part_of_the_planned_value(site: Site) -> None:
    # « calculée sur les lignes de la révision de référence hors provision » (corps du critère).
    task = site.task("Câblage", NOVEMBER)
    site.material(task, "600")
    provision = site.material(task, "250")
    with site.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(provision))
            .values(cost_category_id=site.costs.provision)
        )
    site.referenced()
    assert site.value(date(2026, 11, 30)) == Decimal(600)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_delaying_a_task_of_the_current_revision_leaves_the_planned_value_of_the_reference(
    site: Site,
) -> None:
    # « Retarder une tâche dans la révision courante ne change pas la valeur planifiée. »
    site.material(site.task("Câblage", NOVEMBER), "800")
    current = site.referenced()
    days = (date(2026, 11, 6), date(2026, 11, 20), date(2026, 11, 30))
    before = [site.value(day) for day in days]
    task = next(each for each in current.items() if each["kind"] == "task")
    delay = {"start": {"date": "2027-03-01"}, "finish": {"date": "2027-03-31"}}
    current.changed(task, scheduling_mode="manual", **delay)
    moved = next(each for each in current.items() if each["kind"] == "task")
    assert moved["task"]["start"]["date"] == "2027-03-01"
    assert [site.value(day) for day in days] == before
    assert before[-1] == Decimal(800)
