# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The detail of the plan of workload by role and by task (US-2040/L2, WF-DEV-0090).

``getProjectWorkload`` on the main structure of the revisions of a project its manager made
(``workload_support``): each role details the tasks that bear its labour lines, their hours and
their parts by month, rounded so that they sum to each line (``parting``). The roles work eight
hours from Monday to Friday; November and December 2026 hold 168 and 184 hours. Every answer is
checked against the contract.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import add_role
from nodes_support import set_progress
from workload_support import (
    NOVEMBER,
    WORKED_DAYS,
    Clock,
    Site,
    day_setter,
    make_below,
    make_site,
)

if TYPE_CHECKING:
    from uuid import UUID

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MARCH = ("2026-03-02", "2026-03-31")
APRIL = ("2026-04-01", "2026-04-30")


@pytest.fixture
def site(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Site:
    """Give a platform, a project its manager made, its revision opened, and a role to load."""
    return make_site(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the service reads as today, and the worker marks on."""
    return day_setter(monkeypatch)


def role_of(read: dict[str, Any], role_id: UUID) -> dict[str, Any]:
    """Give the role of a plan."""
    return next(each for each in read["roles"] if each["resource_role_id"] == str(role_id))


def tasks_of(read: dict[str, Any], role_id: UUID) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Give the tasks of a role: their label, their hours, their months with their hours."""
    return [
        (each["label"], each["hours"], [(m["month"], m["hours"]) for m in each["months"]])
        for each in role_of(read, role_id)["tasks"]
    ]


def summed(read: dict[str, Any], role_id: UUID) -> list[tuple[str, str]]:
    """Give the hours of the tasks of a role, summed month by month."""
    sums: dict[str, Decimal] = defaultdict(Decimal)
    for task in role_of(read, role_id)["tasks"]:
        for month in task["months"]:
            sums[month["month"]] += Decimal(month["hours"])
    return [(month, str(sums[month])) for month in sorted(sums)]


def months_of(read: dict[str, Any], role_id: UUID) -> list[tuple[str, str]]:
    """Give the months of a role with their hours."""
    return [(each["month"], each["hours"]) for each in role_of(read, role_id)["months"]]


@pytest.mark.requirement("WF-DEV-0090-A")
def test_for_each_role_and_month_the_tasks_of_the_detail_sum_to_the_load_of_the_plan(
    site: Site, clock: Clock
) -> None:
    # « Pour chaque rôle et chaque mois, la somme des charges des tâches du détail égale la charge
    # que le plan présente. » Three lines of 100 hours over November and December: 47.727… and
    # 52.272… hours each, 47.73 and 52.27 once rounded; the plan sums the parts so rounded, 143.19
    # in November where the exact sum would round to 143.18.
    clock(date(2026, 10, 15))
    for label in ("Câblage", "Repérage", "Essais"):
        site.labour(site.task(label), "100")
    site.referenced()
    for basis in ("reference_budget", "current_remaining"):
        read = site.plan(basis)
        assert months_of(read, site.worker) == [("2026-11", "143.19"), ("2026-12", "156.81")]
        assert summed(read, site.worker) == months_of(read, site.worker)
        assert [(each["month"], each["hours"]) for each in read["monthly_totals"]] == [
            ("2026-11", "143.19"),
            ("2026-12", "156.81"),
        ]
        assert {hours for _, hours, _ in tasks_of(read, site.worker)} == {"100.00"}


@pytest.mark.requirement("WF-DEV-0090-A")
def test_two_lines_of_a_role_under_a_task_make_one_task_of_their_summed_hours(
    site: Site, clock: Clock
) -> None:
    # « Deux lignes d’un même rôle sous une même tâche y comptent pour une seule ligne du détail,
    # de la somme de leurs charges. » A line of another role under the task is in its own role.
    clock(date(2026, 10, 15))
    other = add_role(site.stage.database, "TWO", WORKED_DAYS)
    task = site.task("Câblage")
    site.labour(task, "176")
    site.labour(task, "88", quantity="2")
    site.labour(task, "35.2", role=other)
    site.referenced()
    read = site.plan("reference_budget")
    assert tasks_of(read, site.worker) == [
        ("Câblage", "352.00", [("2026-11", "168.00"), ("2026-12", "184.00")])
    ]
    assert tasks_of(read, other) == [
        ("Câblage", "35.20", [("2026-11", "16.80"), ("2026-12", "18.40")])
    ]
    (detail,) = role_of(read, site.worker)["tasks"]
    assert detail["node_id"] == task["node_id"]
    assert detail["row_number"] == 1
    assert (detail["start"], detail["finish"]) == (
        {"date": "2026-11-02", "hours": "0"},
        {"date": "2026-12-31", "hours": "8"},
    )


@pytest.mark.requirement("WF-DEV-0090-A")
def test_on_the_remaining_a_completed_task_is_not_in_the_detail(site: Site, clock: Clock) -> None:
    # « Sur la base du reste à engager, une tâche terminée n’y figure pas. » The reference budget
    # keeps it.
    clock(date(2026, 10, 15))
    site.labour(site.task("Câblage"), "352")
    site.labour(site.task("Repérage", NOVEMBER), "168")
    current = site.referenced()
    done = next(
        each
        for each in current.items()
        if each["kind"] == "task" and each["task"]["label"] == "Repérage"
    )
    set_progress(site.stage, done["node_id"], "completed", date(2026, 11, 20))
    marked = site.tree.revision["revision_id"]
    assert [label for label, _, _ in tasks_of(site.plan("current_remaining"), site.worker)] == [
        "Câblage"
    ]
    assert [label for label, _, _ in tasks_of(site.plan("reference_budget"), site.worker)] == [
        "Câblage",
        "Repérage",
    ]
    # The marked revision: the task was not completed when it was marked.
    kept = site.plan("marked_remaining", revision_id=marked)
    assert len(tasks_of(kept, site.worker)) == 2


@pytest.mark.requirement("WF-DEV-0090-A")
def test_a_task_that_starts_in_march_comes_before_one_that_starts_in_april_whatever_their_place(
    site: Site, clock: Clock
) -> None:
    # « Sous un rôle, une tâche qui débute en mars précède une tâche qui débute en avril, quelle que
    # soit leur place dans l’arbre du planning ; […] » (the way to the grid is US-2040/L3's). Two
    # tasks that start the same day follow the order of the plan.
    clock(date(2026, 1, 15))
    for label, dates in (("Avril", APRIL), ("Mars B", MARCH), ("Mars A", MARCH)):
        site.labour(site.task(label, dates), "8")
    site.referenced()
    read = site.plan("reference_budget")
    assert [label for label, _, _ in tasks_of(read, site.worker)] == ["Mars B", "Mars A", "Avril"]
    rows = [each["row_number"] for each in role_of(read, site.worker)["tasks"]]
    assert rows[0] < rows[1]
    assert rows[2] < rows[0]


@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_detail_of_a_marked_revision_is_computed_when_read_on_its_own_tasks(
    site: Site, clock: Clock
) -> None:
    # Propre à l'US : « pour une révision marquée, le détail est calculé à la lecture, non conservé
    # au marquage ». The revision marked, its roles' load read again after the current revision
    # moved its task: the detail is the marked revision's, its nodes and its dates, and it follows
    # the date of calculation of the marking as the plan does.
    clock(date(2026, 10, 15))
    site.labour(site.task("Câblage"), "352")
    current = site.referenced()
    marked = site.tree.revision["revision_id"]
    moved = next(each for each in current.items() if each["kind"] == "task")
    delay = {"start": {"date": "2027-01-04"}, "finish": {"date": "2027-01-29"}}
    current.changed(moved, scheduling_mode="manual", **delay)
    clock(date(2031, 6, 1))
    read = site.plan("marked_remaining", revision_id=marked)
    (detail,) = role_of(read, site.worker)["tasks"]
    assert detail["node_id"] != moved["node_id"]
    assert detail["node_id"] in {each["node_id"] for each in site.tree.items()}
    assert (detail["start"]["date"], detail["finish"]["date"]) == ("2026-11-02", "2026-12-31")
    assert [(m["month"], m["hours"]) for m in detail["months"]] == months_of(read, site.worker)
    assert months_of(read, site.worker) == [("2026-11", "168.00"), ("2026-12", "184.00")]
    (now,) = role_of(site.plan("current_remaining"), site.worker)["tasks"]
    assert (now["node_id"], now["start"]["date"]) == (moved["node_id"], "2027-01-04")


@pytest.mark.requirement("WF-DEV-0090-A")
def test_a_task_of_no_hour_is_kept_in_the_detail_with_no_month_and_the_role_has_none_for_it(
    site: Site, clock: Clock
) -> None:
    # A line of no hour bears a task of the role, which the detail keeps, empty of months; a line of
    # half a thousandth of an hour bears one too, which the column of its hours (two decimals)
    # records as a hundredth, not the rounding of the parts, which would give it nought a half to
    # the even (``test_parting``): the months of a role are those of the tasks that load some.
    clock(date(2026, 10, 15))
    other = add_role(site.stage.database, "ZER", WORKED_DAYS)
    site.labour(site.task("Vide"), "0", role=other)
    site.labour(site.task("Infime"), "0.005")
    site.referenced()
    read = site.plan("reference_budget")
    assert tasks_of(read, other) == [("Vide", "0", [])]
    assert months_of(read, other) == []
    assert tasks_of(read, site.worker) == [("Infime", "0.01", [("2026-12", "0.01")])]
    assert months_of(read, site.worker) == [("2026-12", "0.01")]


@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_detail_follows_the_filter_by_organisation_node_of_the_plan(
    site: Site, clock: Clock
) -> None:
    # « sous les filtres du plan » : the roles the node leaves out have no detail, those it keeps
    # have theirs whole.
    clock(date(2026, 10, 15))
    below = make_below(site)
    task = site.task("Câblage")
    site.labour(task, "168")
    site.labour(task, "92", role=below.fitter)
    site.referenced()
    whole = site.plan("reference_budget")
    assert len(tasks_of(whole, site.worker)) == len(tasks_of(whole, below.fitter)) == 1
    kept = site.plan("reference_budget", org_node_id=below.child)
    assert [each["resource_role_id"] for each in kept["roles"]] == [str(below.fitter)]
    assert tasks_of(kept, below.fitter) == tasks_of(whole, below.fitter)
    assert tasks_of(kept, below.fitter) == [
        ("Câblage", "92.00", [("2026-11", "43.91"), ("2026-12", "48.09")])
    ]
    both = site.plan("reference_budget", org_node_id=below.parent)
    assert tasks_of(both, site.worker) == tasks_of(whole, site.worker)


@pytest.mark.requirement("WF-DEV-0090-A")
def test_on_the_remaining_a_task_whose_end_is_past_falls_on_the_month_of_the_day_in_the_detail(
    site: Site, clock: Clock
) -> None:
    # The load of a task whose finish is past falls on the month of the day (WF-DEV-0070): the
    # detail of the task, not only the role's months, is there, on the reference as it was.
    site.labour(site.task("Câblage"), "352")
    site.referenced()
    clock(date(2027, 2, 17))
    read = site.plan("current_remaining")
    assert tasks_of(read, site.worker) == [("Câblage", "352.00", [("2027-02", "352.00")])]
    assert summed(read, site.worker) == months_of(read, site.worker)
    whole = site.plan("reference_budget")
    assert tasks_of(whole, site.worker) == [
        ("Câblage", "352.00", [("2026-11", "168.00"), ("2026-12", "184.00")])
    ]
