# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload computed on the remaining to commit (US-1580/L3).

``getProjectWorkload`` on ``current_remaining`` and ``marked_remaining`` after a re-estimate: the
project In progress, its reference and its tasks written through the service
(``remaining_support``), a role on a calendar of eight hours from Monday to Friday; a line
reestimated by ``setLineRemaining``, a task completed by the remaining set to nought, a task not
started then started. In March and April 2026 the calendar works 22 days each, 176 hours. The
clock is set: the day of the service, and the day the markings are made on. Every answer is
checked against the contract.
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Lines, add_role, costing
from nodes_support import Tree, set_progress
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, review_marked, task_named

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# Eight hours from Monday to Friday.
WORKED_DAYS = (8, 8, 8, 8, 8, 0, 0)
# A task over exactly four civil months, January to April 2026, scheduled by hand.
FOUR_MONTHS = {
    "scheduling_mode": "manual",
    "start": {"date": "2026-01-05"},
    "finish": {"date": "2026-04-30"},
}
STARTED_ON = date(2026, 1, 5)
CALCULATION_DAY = date(2026, 3, 1)
HALF = [("2026-03", "40.00"), ("2026-04", "40.00")]
type Build = Callable[[Tree, Lines, UUID], None]


class Plant:
    """A project In progress, the role that works eight hours a weekday, and the clock."""

    def __init__(
        self, api: ContractClient, stage: Scene, worker: UUID, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.api = api
        self.stage = stage
        self.worker = worker
        self.monkeypatch = monkeypatch
        self.review: Review

    def clock(self, day: date) -> None:
        """Set the day the service reads as today, and the day the markings are made on."""
        now = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
        self.monkeypatch.setattr("waterfall.api.workload.utc_now", lambda: now)
        self.monkeypatch.setattr("nodes_support.utc_now", lambda: now)
        self.monkeypatch.setattr("remaining_support.utc_now", lambda: now)

    def open(self, build: Build) -> Review:
        """Write the reference through the service, move the project In progress."""
        self.review = in_progress(
            self.api, self.stage, lambda tree, lines: build(tree, lines, self.worker)
        )
        return self.review

    @property
    def path(self) -> str:
        """Give the path of the project."""
        return f"{PROJECTS}/{self.stage.project['project_id']}"

    def plan(self, basis: str, **query: Any) -> dict[str, Any]:
        """Ask for the workload on a basis, which must be given; give it."""
        text = "&".join(f"{name}={value}" for name, value in {"basis": basis, **query}.items())
        answer = self.api.get(f"{self.path}/workload?{text}", headers=self.stage.manager.headers)
        assert answer.status_code == 200, answer.text
        return answer.json()

    def reestimate(self, label: str, body: dict[str, Any], **more: Any) -> None:
        """Set the remaining of the line of a label, at the counter read."""
        tree = self.review.tree
        line = line_named(tree, label)
        sent = {"lock_version": line["lock_version"], "reestimated_amount_basis": body, **more}
        answer = self.api.put(
            f"{tree.path}/nodes/{line['node_id']}/remaining",
            headers=self.stage.manager.headers,
            json=sent,
        )
        assert answer.status_code == 200, answer.text

    def months(self, read: dict[str, Any]) -> list[tuple[str, str]]:
        """Give the months of the worker in a plan, with their hours."""
        role = next(each for each in read["roles"] if each["resource_role_id"] == str(self.worker))
        return [(each["month"], each["hours"]) for each in role["months"]]


def totals_of(read: dict[str, Any]) -> list[tuple[str, str]]:
    """Give the monthly totals of a plan."""
    return [(each["month"], each["hours"]) for each in read["monthly_totals"]]


def labour(worker: UUID, label: str, hours: str) -> dict[str, Any]:
    """Give a labour line of the worker: one person for the hours said."""
    return {"label": label, "quantity": "1", "resource_role_id": str(worker), "hours": hours}


@pytest.fixture
def plant(
    api: ContractClient,
    owner: Engine,
    database: Database,
    realm: TestRealm,
    monkeypatch: pytest.MonkeyPatch,
) -> Plant:
    """Give a platform, the project its manager made, a role to load, the clock at January."""
    stage = make_scene(api, owner, database, realm)
    costing(database)
    made = Plant(api, stage, add_role(database, "WRK", WORKED_DAYS), monkeypatch)
    made.clock(date(2026, 1, 2))
    return made


def one_task(label: str, hours: str) -> Build:
    """Give the build of a project of one task over four months, one labour line of some hours."""

    def build(tree: Tree, lines: Lines, worker: UUID) -> None:
        lines.made(tree.made(label, task=FOUR_MONTHS), **labour(worker, "Montage", hours))

    return build


def start(plant: Plant, label: str) -> None:
    """Start a task of the current revision, on the day its schedule begins."""
    node = task_named(plant.review.tree, label)["node_id"]
    set_progress(plant.stage, node, "started", STARTED_ON)


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_started_task_reestimated_at_80_hours_spreads_them_over_the_two_months_left(
    plant: Plant,
) -> None:
    # « Une tâche démarrée qui couvre exactement quatre mois civils, à mi-parcours à la date de
    # calcul — le premier jour du troisième mois —, dont une ligne porte un reste de 80 heures,
    # présente ces 80 heures sur les deux mois restants au prorata de leurs heures travaillées —
    # 40 et 40 s'ils en comptent autant — et rien sur les mois écoulés ; sur une révision
    # marquée, la date de calcul est sa date de marquage. »
    plant.open(one_task("Câblage", "200"))
    start(plant, "Câblage")
    plant.reestimate("Montage", {"hours": "80"})
    plant.clock(CALCULATION_DAY)
    read = plant.plan("current_remaining")
    assert read["context"]["computed_at"] == "2026-03-01T09:00:00Z"
    assert plant.months(read) == HALF
    assert totals_of(read) == HALF
    # Marked, the revision is read at its marking date, whatever the clock says afterwards.
    marked = plant.review.tree.revision
    review_marked(plant.stage, marked, "v2.0")
    plant.clock(date(2026, 4, 15))
    kept = plant.plan("marked_remaining", revision_id=marked["revision_id"])
    assert kept["context"]["computed_at"] == "2026-03-01T09:00:00Z"
    assert plant.months(kept) == HALF
    assert totals_of(kept) == HALF


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_completed_by_setting_its_remaining_to_nought_counts_nothing_on_the_current_plan(
    plant: Plant,
) -> None:
    # « Le plan de charge calculé sur le reste à engager ignore les lignes des tâches
    # terminées. » The task completed by the last open line set to nought, with its date; the
    # other task, reestimated at 80 hours, is the only one the plan holds then.
    def build(tree: Tree, lines: Lines, worker: UUID) -> None:
        lines.made(tree.made("Câblage", task=FOUR_MONTHS), **labour(worker, "Montage", "200"))
        lines.made(tree.made("Essais", task=FOUR_MONTHS), **labour(worker, "Banc", "160"))

    plant.open(build)
    start(plant, "Câblage")
    start(plant, "Essais")
    plant.reestimate("Montage", {"hours": "80"})
    plant.clock(CALCULATION_DAY)
    both = [("2026-03", "120.00"), ("2026-04", "120.00")]
    assert totals_of(plant.plan("current_remaining")) == both
    plant.reestimate("Banc", {"quantity": "0"}, completed_on="2026-03-01")
    assert task_named(plant.review.tree, "Essais")["task"]["progress"] == "completed"
    read = plant.plan("current_remaining")
    assert plant.months(read) == HALF
    assert totals_of(read) == HALF


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_not_started_whose_start_is_past_carries_the_same_load_once_it_is_started(
    plant: Plant,
) -> None:
    # « Une tâche non démarrée dont la date de début est antérieure à la date de calcul ne
    # présente aucune charge sur les mois écoulés ; sa charge est la même avant et après son
    # démarrage. » The same task, started by the progress, carries the same load.
    plant.open(one_task("Câblage", "160"))
    plant.clock(CALCULATION_DAY)
    before = plant.plan("current_remaining")
    assert plant.months(before) == [("2026-03", "80.00"), ("2026-04", "80.00")]
    assert totals_of(before) == plant.months(before)
    start(plant, "Câblage")
    after = plant.plan("current_remaining")
    assert plant.months(after) == plant.months(before)
    assert totals_of(after) == totals_of(before)
