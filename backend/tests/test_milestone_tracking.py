# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time/time diagram of a project, served (``getMilestoneTracking``; US-1710).

A project In progress whose current revision is marked review after review, a milestone dated at
each: the points by marking, the horizontal and the slope, the completion and the reopening, the
renaming, the inscriptions of the milestones alone — one left on a task that ceased to be a
milestone is not rendered and not purged (#2498) —, the point of the day of the last marked
revision, and the refusals. The helpers are in ``milestone_tracking_support``; every answer is
checked against the contract by the client of the tests.
"""

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from indicators_support import clock_setter, marked
from milestone_tracking_support import (
    DELIVERY,
    JULY_31,
    JUNE_30,
    START,
    STUDIES,
    TIME_TIME,
    Project,
    at_nine,
    milestone,
    months,
    points,
)
from nodes_support import refusal
from projects_support import PROJECTS
from projects_support import scene as make_scene
from sqlalchemy import func, select

from waterfall.core.planning.interface import milestone_forecasts, tracked_milestones
from waterfall.core.planning.tables import TrackingEntry

if TYPE_CHECKING:
    from indicators_support import Clock
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the diagram is computed on."""
    return clock_setter(monkeypatch)


def labelled(body: dict[str, Any]) -> list[str]:
    """Give the labels of the milestones of a diagram."""
    return [each["label"] for each in body["milestones"]]


@pytest.fixture
def project(api: ContractClient, stage: Scene, clock: Clock) -> Project:
    """Give a project In progress, its two milestones inscribed in the time/time tracking."""
    found = Project(api, stage, clock)
    found.track(STUDIES, TIME_TIME)
    found.track(DELIVERY, TIME_TIME)
    return found


def review_at(project: Project, day: date, forecast: date, version_name: str) -> None:
    """Forecast the studies at a date, then mark the current revision at a day."""
    project.date(STUDIES, forecast)
    project.review(day, version_name)


def three_reviews(project: Project, forecasts: tuple[date, date, date]) -> tuple[date, ...]:
    """Mark three reviews a month apart, the studies forecast at the dates given; give the days."""
    days = tuple(months(START, each) for each in range(3))
    for rank, (day, forecast) in enumerate(zip(days, forecasts, strict=True)):
        review_at(project, day, forecast, f"v{rank + 1}")
    return days


@pytest.mark.requirement("WF-IND-0090-A")
def test_a_milestone_forecast_on_the_same_day_in_three_reviews_draws_a_horizontal_then_the_day(
    project: Project,
) -> None:
    # « Un jalon prévu au 30 juin dans trois revues successives trace une horizontale. » The
    # reference, marked before In progress, gives no point; the point of the day is that of the
    # current revision, at the instant of the computation, its date the finish of the revision.
    days = three_reviews(project, (JUNE_30, JUNE_30, JUNE_30))
    project.date(STUDIES, JUNE_30)
    today = days[-1] + timedelta(days=5)
    body = project.diagram(today)
    found = milestone(body, STUDIES)
    assert points(found) == [
        *((at_nine(each), "2027-06-30") for each in days),
        (at_nine(today), "2027-06-30"),
    ]
    assert found["completed_on"] is None
    context = body["context"]
    assert (context["revision_status"], context["scope"], context["is_stored"]) == (
        "draft",
        "project",
        False,
    )
    assert context["revision_id"] == project.tree.revision["revision_id"]
    assert context["computed_at"] == at_nine(today)


@pytest.mark.requirement("WF-IND-0090-A")
def test_a_milestone_pushed_back_a_month_at_each_of_three_monthly_reviews_draws_a_slope_of_one(
    project: Project,
) -> None:
    # « Un jalon repoussé d’un mois à chacune de trois revues mensuelles trace une droite de pente
    # 1. » The forecast moves a month as the marking does: 15 April, 15 May, 15 June.
    forecasts = tuple(months(JUNE_30.replace(day=15), each - 2) for each in range(3))
    days = three_reviews(project, (forecasts[0], forecasts[1], forecasts[2]))
    project.date(STUDIES, forecasts[2])
    found = milestone(project.diagram(days[-1] + timedelta(days=1)), STUDIES)
    assert [each[1] for each in points(found)[:3]] == ["2027-04-15", "2027-05-15", "2027-06-15"]
    assert [each[0] for each in points(found)[:3]] == [at_nine(each) for each in days]
    shifts = [(forecasts[rank + 1] - forecasts[rank]).days for rank in range(2)]
    assert shifts == [30, 31]


@pytest.mark.requirement("WF-IND-0090-A")
def test_a_milestone_completed_has_no_point_after_its_completion_and_ends_on_the_diagonal(
    project: Project,
) -> None:
    # « Un jalon terminé n’a plus de point après sa terminaison, et son dernier point est sur la
    # diagonale. » Completed between the second review and the third: the third adds no point, the
    # last is the completion at midnight, and the point of the day is not drawn.
    first, second = months(START, 0), months(START, 1)
    review_at(project, first, JUNE_30, "v1")
    review_at(project, second, JUNE_30, "v2")
    done = second + timedelta(days=10)
    project.progress(STUDIES, "completed", done)
    review_at(project, months(START, 2), JUNE_30, "v3")
    body = project.diagram(months(START, 3))
    found = milestone(body, STUDIES)
    assert points(found) == [
        (at_nine(first), "2027-06-30"),
        (at_nine(second), "2027-06-30"),
        (f"{done.isoformat()}T00:00:00Z", done.isoformat()),
    ]
    assert found["completed_on"] == done.isoformat()
    # The other milestone, not completed, ends on the day.
    other = milestone(body, DELIVERY)
    assert other["completed_on"] is None
    assert points(other)[-1][0] == at_nine(months(START, 3))


@pytest.mark.requirement("WF-IND-0090-A")
def test_a_review_marked_the_eve_of_the_completion_gives_a_point_and_the_day_itself_none(
    project: Project,
) -> None:
    # « Un jalon terminé n’a plus de point après sa terminaison » : the boundary is the completion
    # at midnight, universal time. A marking of the eve (clock at nine) is before it and is drawn;
    # one of the very day of the completion (nine, after midnight) is after it and is not, the
    # last point being the completion on the diagonal.
    eve = START
    done = eve + timedelta(days=1)
    review_at(project, eve, JUNE_30, "v1")
    project.clock(done)
    project.progress(STUDIES, "completed", done)
    review_at(project, done, JUNE_30, "v2")
    found = milestone(project.diagram(done + timedelta(days=3)), STUDIES)
    assert points(found) == [
        (at_nine(eve), "2027-06-30"),
        (f"{done.isoformat()}T00:00:00Z", done.isoformat()),
    ]


@pytest.mark.requirement("WF-IND-0090-A")
def test_a_review_marked_at_midnight_sharp_of_the_completion_gives_no_point(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Un jalon terminé n’a plus de point après sa terminaison » : the boundary is the completion
    # at midnight, universal time, and it belongs to the completion. A marking at 00:00:00 of the
    # very day is not before it: it is not drawn, only the completion on the diagonal ends the
    # line, which tells ``marked_at >= completed_on`` from ``marked_at > completed_on``.
    eve = START
    done = eve + timedelta(days=1)
    review_at(project, eve, JUNE_30, "v1")
    project.clock(done)
    project.progress(STUDIES, "completed", done)
    project.date(STUDIES, JUNE_30)
    midnight = datetime(done.year, done.month, done.day, tzinfo=UTC)
    monkeypatch.setattr("indicators_support.now", lambda: midnight)
    # The instant of the marking is asserted: were the patch not applied, it would be nine o’clock.
    assert marked(project.stage, project.tree.revision, "v2") == midnight
    found = milestone(project.diagram(done + timedelta(days=3)), STUDIES)
    assert points(found) == [
        (at_nine(eve), "2027-06-30"),
        (f"{done.isoformat()}T00:00:00Z", done.isoformat()),
    ]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_milestone_reopened_receives_the_point_of_the_day_again_and_has_no_completion(
    project: Project,
) -> None:
    # « Un jalon terminé que l’on rouvre est non démarré et ne contribue plus à la valeur acquise. »
    # Completed, it ends on the diagonal; reopened, its suivi temps/temps receives the point of the
    # day again, ``completed_on`` null, and its marks all count.
    review_at(project, START, JUNE_30, "v1")
    done = START + timedelta(days=3)
    project.progress(STUDIES, "completed", done)
    assert milestone(project.diagram(START + timedelta(days=4)), STUDIES)["completed_on"] == (
        done.isoformat()
    )
    project.progress(STUDIES, "not_started", START + timedelta(days=5))
    project.date(STUDIES, JUNE_30)
    today = START + timedelta(days=6)
    found = milestone(project.diagram(today), STUDIES)
    assert found["completed_on"] is None
    assert points(found) == [(at_nine(START), "2027-06-30"), (at_nine(today), "2027-06-30")]


@pytest.mark.requirement("WF-IND-0090-A")
def test_only_the_markings_that_kept_the_indicators_of_the_project_give_a_point(
    project: Project,
) -> None:
    # A project In progress keeps its indicators at each marking: the reference, marked before, is
    # not one of the points, and a lineage a marked revision does not hold has no point there — the
    # milestone made in the second revision only has the points that follow.
    review_at(project, START, JUNE_30, "v1")
    project.tree.made("Mise en service", task={"duration": {"value": "0", "unit": "d"}})
    project.date("Mise en service", JUNE_30)
    project.track("Mise en service", TIME_TIME)
    project.review(months(START, 1), "v2")
    body = project.diagram(months(START, 2))
    assert len(milestone(body, STUDIES)["points"]) == 3
    assert [each[0] for each in points(milestone(body, "Mise en service"))] == [
        at_nine(months(START, 1)),
        at_nine(months(START, 2)),
    ]


@pytest.mark.requirement("WF-DAT-0030-A")
def test_a_milestone_renamed_keeps_its_curve_and_is_labelled_as_the_revision_of_the_day(
    project: Project,
) -> None:
    # « Un jalon renommé conserve sa courbe sur le diagramme temps/temps. » The points are read by
    # lineage in each marked revision; the label is the current revision's.
    review_at(project, START, JUNE_30, "v1")
    project.tree.changed(project.node(STUDIES), label="Réception provisoire des études")
    body = project.diagram(START + timedelta(days=2))
    found = milestone(body, "Réception provisoire des études")
    assert points(found)[0] == (at_nine(START), "2027-06-30")
    assert all(each["label"] != STUDIES for each in body["milestones"])


@pytest.mark.requirement("WF-PLA-0060-A")
def test_the_diagram_follows_the_milestones_inscribed_and_a_milestone_removed_disappears(
    project: Project,
) -> None:
    # « Le diagramme temps/temps ne suit que les jalons inscrits. » The task that is no milestone
    # and the milestone that is not inscribed are not drawn; a milestone removed by
    # ``setNodeTracking`` is gone at the next reading.
    project.track(DELIVERY)
    review_at(project, START, JUNE_30, "v1")
    body = project.diagram(START + timedelta(days=1))
    assert [each["label"] for each in body["milestones"]] == [STUDIES]
    project.track(STUDIES)
    assert project.diagram()["milestones"] == []


@pytest.mark.requirement("WF-PLA-0060-A")
def test_an_inscription_left_on_a_task_that_ceased_to_be_a_milestone_is_not_rendered_nor_purged(
    project: Project,
) -> None:
    # #2498: ``setNodeTracking`` refuses an inscription on a task that is no milestone at its entry
    # alone. The milestone given a duration of five days — dated manually from Monday to Friday —
    # is no longer one: it is not rendered, its inscription stays in the base, and the milestone
    # beside it is.
    review_at(project, START, JUNE_30, "v1")
    assert labelled(project.diagram(START + timedelta(days=1))) == [STUDIES, DELIVERY]
    project.tree.changed(
        project.node(STUDIES),
        scheduling_mode="manual",
        start={"date": "2027-01-11"},
        finish={"date": "2027-01-15"},
    )
    assert project.node(STUDIES)["task"]["duration"] == {"value": "5", "unit": "d"}
    assert labelled(project.diagram(START + timedelta(days=2))) == [DELIVERY]
    with project.stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(TrackingEntry)) == 2
        assert len(tracked_milestones(session, project.project_id)) == 2


@pytest.mark.requirement("WF-IND-0090-A")
def test_without_a_current_revision_the_point_of_the_day_is_the_last_marked_revisions(
    project: Project,
) -> None:
    # « le point du jour courant vient de la révision en cours ou, sans elle, de la dernière
    # révision marquée » : the current revision marked and none opened, the context names it
    # marked, and its date is the finish of the milestone there.
    project.date(STUDIES, JUNE_30)
    revision_id = project.tree.revision["revision_id"]
    project.review(START, "v1", reopen=False)
    today = START + timedelta(days=9)
    body = project.diagram(today)
    assert (body["context"]["revision_id"], body["context"]["revision_status"]) == (
        revision_id,
        "marked",
    )
    assert points(milestone(body, STUDIES)) == [
        (at_nine(START), "2027-06-30"),
        (at_nine(today), "2027-06-30"),
    ]


@pytest.mark.requirement("WF-IND-0090-A")
def test_the_forecasts_read_the_finish_of_each_lineage_in_each_revision_that_holds_it(
    project: Project,
) -> None:
    # What ``milestone_forecasts`` reads: by revision, the finish of the lineages named that it
    # holds; none for a lineage it does not hold, nor for no lineage.
    project.date(STUDIES, JUNE_30)
    project.date(DELIVERY, JULY_31)
    lineages = {each: UUID(project.node(each)["lineage_id"]) for each in (STUDIES, DELIVERY)}
    revision_id = UUID(project.tree.revision["revision_id"])
    project.review(START, "v1")
    with project.stage.database.transaction() as session:
        assert set(tracked_milestones(session, project.project_id)) == set(lineages.values())
        asked = [*lineages.values()]
        found = milestone_forecasts(session, project.project_id, asked, [revision_id])
        assert dict(found[revision_id]) == {
            lineages[STUDIES]: JUNE_30,
            lineages[DELIVERY]: JULY_31,
        }
        unknown = milestone_forecasts(session, project.project_id, [uuid4()], [revision_id])
        assert dict(unknown.get(revision_id, {})) == {}
        assert not milestone_forecasts(session, project.project_id, [], [revision_id])


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_project_before_in_progress_is_refused_with_its_state_named(
    api: ContractClient, stage: Scene
) -> None:
    # #1778: 409 ``STATE_FORBIDS_OPERATION``, ``params.state`` and ``params.state_enum``.
    answer = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/indicators/milestone-tracking",
        headers=stage.manager.headers,
    )
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"state": "created", "state_enum": "ProjectState"},
    )
