# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The health of the control of the projects, served (``getPortfolioPilotHealth``; US-2750).

The four projects of the fabrics (``portfolio_support``): the project In progress was reviewed and
marked on 2 March 2026, after its offer on 12 January and its passage In progress on 19 January; it
is read at the date of the witness, 3 June 2026, thirteen weeks later, and the current day against
what the day computes. The documents ``portfolio_milestones`` a marking kept are set to the
milestones of the sentence under test, as a marking of EP-11 would have kept them; the imports are
written to the log the way the witness loads them. Every answer is validated against the contract
by the client of the tests. The risks, whose reviews carry the instant of their writing, are in
``test_portfolio_pilot_risks``.
"""

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import load_import
from portfolio_listing_support import EVERY, READ, kept_changed, read, revision_of, served
from portfolio_support import (
    REVIEW_MARKED,
    Portfolio,
    another_in_progress,
    at,
    current_of,
    portfolio,
)
from projects_support import MANAGING, Scene, contribute, person
from projects_support import scene as make_scene

from waterfall.core.cost_settings.interface import (
    SettingsChange,
    read_reference_settings,
    write_reference_settings,
)
from waterfall.core.costs.interface import last_imports
from waterfall.core.portfolio.interface import (
    PortfolioAsked,
    PortfolioReading,
    read_pilot_health,
)
from waterfall.core.projects.interface import Viewer
from waterfall.core.revisions.interface import (
    create_revision,
    mark_revision,
    marked_revisions_of,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

REQUIREMENT = "WF-PTF-0110-A"
# The current day of the tests of the day, after the whole chronology of the fabrics.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
# The date of the witness, thirteen weeks after the marking of the review of the running project.
WEEKS = 13
RUNNING_LABEL = "Rénovation de la ligne 3"
# The reference date of the milestones of the sentences under test.
PASSED, TODAY, NEXT = "2026-05-01", "2026-06-03", "2026-07-01"
LINEAGE = "01926f3a-7c00-7000-8000-000600000001"


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def health(api: ContractClient, fabrics: Portfolio, query: str = READ) -> dict[str, Any]:
    """Read the health as the manager that reads the portfolio does; the contract judges it."""
    return served(api, fabrics.stage.reader, "pilot-health", query)


def signals_of(body: dict[str, Any], code: str) -> list[dict[str, Any]]:
    """Give the signals of an answer that carry a code, in the order of the answer."""
    found: list[dict[str, Any]] = [each for each in body["signals"] if each["code"] == code]
    return found


def delay(fabrics: Portfolio, weeks: int) -> None:
    """Set the delay between two reviews, as ``updateReferenceSettings`` does."""
    with fabrics.stage.database.transaction() as session:
        counter = read_reference_settings(session).lock_version
        change = SettingsChange(max_weeks_between_reviews=weeks)
        write_reference_settings(session, change, counter, Act(None, utc_now()))


def remarked(fabrics: Portfolio, project_id: UUID, instant: datetime) -> None:
    """Open a revision of a project In progress and mark it at an instant, as its manager does."""
    viewer = Viewer(fabrics.stage.manager.user_id, MANAGING)
    act = Act(fabrics.stage.manager.user_id, instant)
    with logging_context(correlation_id="marking"), fabrics.stage.database.transaction() as session:
        create_revision(session, project_id, act, viewer)
        mark_revision(session, current_of(session, project_id), "Revue de mai", None, act)


def milestone(label: str, reference: str | None, completed: str | None = None) -> dict[str, Any]:
    """Write a milestone of the document ``portfolio_milestones``, its lineage after its label."""
    return {
        "lineage_id": str(UUID(int=int(LINEAGE.replace("-", ""), 16) + len(label))),
        "label": label,
        "reference_date": reference,
        "completed_on": completed,
    }


def keep_milestones(owner: Engine, fabrics: Portfolio, *milestones: dict[str, Any]) -> None:
    """Set the milestones the last marking of the running project kept."""
    kept_changed(
        owner,
        revision_of(fabrics, "running"),
        "portfolio_milestones",
        lambda _: {"milestones": list(milestones)},
    )


# --- The review overdue --------------------------------------------------------------------------


@pytest.mark.requirement(REQUIREMENT)
def test_a_project_in_progress_without_a_marking_for_longer_than_the_delay_appears_with_its_weeks(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Un projet en cours sans révision marquée depuis plus que le délai maximal apparaît dans la
    # vue » : the review of 2 March, thirteen weeks before the date, on the delay of six weeks the
    # reference is delivered with; the signal names its project, its zone, and whether it opens.
    body = health(api, fabrics)
    assert signals_of(body, "review_overdue") == [
        {
            "project_id": str(fabrics.in_progress.project_id),
            "project_label": RUNNING_LABEL,
            "can_open": True,
            "zone": "watch",
            "code": "review_overdue",
            "params": {"weeks_since_last_mark": WEEKS},
        }
    ]
    assert body["scope"] == {
        "states": ["in_progress"],
        "as_of": "2026-06-03",
        "from": None,
        "to": None,
        "org_node_id": None,
        "org_node_label": None,
        "project_count": 1,
    }
    # The offer, the project completed and the project lost are not examined, however old their
    # marking: the signals are those of the project In progress.
    assert {each["project_id"] for each in body["signals"]} == {str(fabrics.in_progress.project_id)}


@pytest.mark.requirement(REQUIREMENT)
def test_the_project_leaves_the_view_at_the_next_marking_and_a_past_date_reads_the_markings_then(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « …et en disparaît au marquage suivant » : a revision marked on 20 May leaves the project nine
    # days from the date, while the 1st of May, which that marking does not yet see, still has it
    # eight weeks after the one of 2 March.
    remarked(fabrics, fabrics.in_progress.project_id, at(5, 20))
    assert signals_of(health(api, fabrics), "review_overdue") == []
    earlier = health(api, fabrics, "as_of=2026-05-01")
    assert [each["params"] for each in signals_of(earlier, "review_overdue")] == [
        {"weeks_since_last_mark": 8}
    ]
    assert earlier["scope"]["as_of"] == "2026-05-01"


@pytest.mark.requirement("WF-REF-0180-A")
def test_the_delay_read_is_that_of_the_reference_at_the_reading_and_a_week_more_is_not_late(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Un projet dont la dernière révision marquée date de plus que ce délai est signalé » : 93
    # days since the review. At 13 weeks (91 days) it is late, at 14 (98) it is not; the delay
    # changed changes the signal at the next reading, none being kept.
    def weeks() -> list[dict[str, Any]]:
        return [each["params"] for each in signals_of(health(api, fabrics), "review_overdue")]

    assert weeks() == [{"weeks_since_last_mark": WEEKS}]
    delay(fabrics, 13)
    assert weeks() == [{"weeks_since_last_mark": WEEKS}]
    delay(fabrics, 14)
    assert weeks() == []
    delay(fabrics, 2)
    assert weeks() == [{"weeks_since_last_mark": WEEKS}]


@pytest.mark.requirement(REQUIREMENT)
def test_the_current_day_reads_the_weeks_from_the_marking_to_the_day_of_the_installation(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Au jour courant : the date of calculation is the current day, and the weeks run from the day
    # of the marking of 2 March to it.
    body = health(api, fabrics, "")
    day = date.fromisoformat(body["scope"]["as_of"])
    assert abs((day - utc_now().date()).days) <= 1
    expected = (day - REVIEW_MARKED.date()).days // 7
    assert [each["params"] for each in signals_of(body, "review_overdue")] == [
        {"weeks_since_last_mark": expected}
    ]


@pytest.mark.story("US-2750")
def test_a_state_other_than_in_progress_has_no_effect_the_completed_one_included(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US : « seuls les projets en cours du périmètre sont examinés ; un autre état que
    # ``states`` nomme — terminé compris — est sans effet, et la vue ne prend pas de période »
    # (#1714). The project completed in April has a review as old as the running one's: asked
    # alone it retains nobody, asked with the others it adds nothing, and the list of every state
    # answers as the default does.
    default = health(api, fabrics)
    completed = health(api, fabrics, f"{READ}&states=completed")
    assert completed["scope"]["states"] == ["completed"]
    assert completed["scope"]["project_count"] == 0
    assert completed["signals"] == []
    with_it = health(api, fabrics, f"{READ}&states=in_progress,completed")
    assert with_it["signals"] == default["signals"]
    assert with_it["scope"]["project_count"] == 1
    every = health(api, fabrics, f"{READ}&states={EVERY}")
    assert every["signals"] == default["signals"]
    assert every["scope"]["from"] is every["scope"]["to"] is None
    pricing = health(api, fabrics, f"{READ}&states=pricing")
    assert pricing["signals"] == []


@pytest.mark.story("US-2750")
def test_a_project_is_examined_while_it_is_in_progress_at_the_date_and_the_signals_follow_ids(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # À une date passée : on 14 April the project completed the next day is still In progress, and
    # as late as the other (43 days, six weeks and a day); the signals come by project, the
    # projects in the order of their identifier, then by code.
    body = health(api, fabrics, "as_of=2026-04-14")
    assert body["scope"]["project_count"] == 2
    reviews = signals_of(body, "review_overdue")
    assert {each["project_id"] for each in reviews} == {
        str(fabrics.in_progress.project_id),
        str(fabrics.completed.project_id),
    }
    assert {each["params"]["weeks_since_last_mark"] for each in reviews} == {6}
    keys = [(each["project_id"], each["code"]) for each in body["signals"]]
    projects = [project for project, _ in keys]
    assert projects == sorted(projects)
    assert [code for project, code in keys if project == projects[0]] == [
        "review_overdue",
        "no_actual_cost_since_last_review",
    ]
    assert health(api, fabrics, "as_of=2026-04-20")["scope"]["project_count"] == 1


# --- The costs not imported ----------------------------------------------------------------------


@pytest.mark.requirement(REQUIREMENT)
def test_a_project_whose_last_review_imported_no_cost_appears_and_one_that_imported_does_not(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « …un projet dont la dernière revue n'a importé aucun coût apparaît » : the interval is that
    # between the marking of 12 January, before the last, and that of 2 March. Without an import
    # the signal is there, in watch and without parameters; an import of 10 February, in the
    # interval, takes it away.
    project_id = fabrics.in_progress.project_id
    found = signals_of(health(api, fabrics), "no_actual_cost_since_last_review")
    assert found == [
        {
            "project_id": str(project_id),
            "project_label": RUNNING_LABEL,
            "can_open": True,
            "zone": "watch",
            "code": "no_actual_cost_since_last_review",
        }
    ]
    load_import(fabrics.stage, project_id, [], at=at(2, 10))
    assert signals_of(health(api, fabrics), "no_actual_cost_since_last_review") == []


@pytest.mark.requirement(REQUIREMENT)
def test_an_import_outside_the_interval_of_the_last_review_does_not_count_its_bounds_do_not_leave(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # The interval runs from the marking before the last, included, to the last marking, excluded:
    # an import the day before the first, and one after the last — a later review's —, leave the
    # signal; one at the very instant of the first marking takes it away, and so does the one of
    # the interval when a later import follows the marking (the last of all is not the last of the
    # interval).
    project_id = fabrics.in_progress.project_id
    code = "no_actual_cost_since_last_review"
    load_import(fabrics.stage, project_id, [], at=at(1, 12) - timedelta(seconds=1))
    load_import(fabrics.stage, project_id, [], at=at(4, 1))
    assert len(signals_of(health(api, fabrics), code)) == 1
    load_import(fabrics.stage, project_id, [], at=at(1, 12))
    assert signals_of(health(api, fabrics), code) == []
    assert signals_of(health(api, fabrics, "as_of=2026-02-01"), code) != []


@pytest.mark.requirement(REQUIREMENT)
def test_the_last_imports_are_read_for_every_project_in_a_fixed_number_of_statements(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Les lectures groupées (#4294 point 1) : the last import of each project before its own
    # instant, in one query whatever the number of projects; the marked revisions of all of them in
    # one more.
    second = another_in_progress(api, fabrics, "Second chantier", "PRJ-2750")
    first = fabrics.in_progress.project_id
    load_import(fabrics.stage, first, [], at=at(2, 10))
    load_import(fabrics.stage, first, [], at=at(2, 20))
    load_import(fabrics.stage, second, [], at=at(4, 1))
    with fabrics.stage.database.transaction() as session:
        found = last_imports(session, {first: at(3, 2), second: at(3, 2)})
        marked = marked_revisions_of(session, [first, second, fabrics.offer.project_id])
    assert found == {first: at(2, 20)}
    assert [instant for _, instant in marked[first]] == [at(1, 12), at(3, 2)]
    assert len(marked) == 3
    assert [instant for _, instant in marked[fabrics.offer.project_id]] == [at(2, 16)]
    with fabrics.stage.database.transaction() as session:
        assert last_imports(session, {}) == {}
        assert marked_revisions_of(session, []) == {}


# --- The milestones overdue ----------------------------------------------------------------------


@pytest.mark.requirement(REQUIREMENT)
def test_a_tracked_milestone_passed_and_not_completed_appears_in_alert_until_it_is_completed(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Un jalon contractuel dont la date de référence est passée et qui n'est pas terminé
    # apparaît, et disparaît à sa terminaison » : read at a past date, from what the marking kept.
    # The milestone dated 1 May and not completed is the one; one completed, one dated the day of
    # the reading or after, and one the reference does not date, are not.
    late = milestone("Réception usine", PASSED)
    keep_milestones(
        owner,
        fabrics,
        late,
        milestone("Essais", PASSED, "2026-04-20"),
        milestone("Livraison", TODAY),
        milestone("Mise en service", NEXT),
        milestone("Recette", None),
    )
    found = signals_of(health(api, fabrics), "contractual_milestone_overdue")
    assert found == [
        {
            "project_id": str(fabrics.in_progress.project_id),
            "project_label": RUNNING_LABEL,
            "can_open": True,
            "zone": "alert",
            "code": "contractual_milestone_overdue",
            "params": {
                "lineage_id": late["lineage_id"],
                "milestone_label": "Réception usine",
                "reference_date": PASSED,
            },
        }
    ]
    keep_milestones(owner, fabrics, {**late, "completed_on": "2026-05-15"})
    assert signals_of(health(api, fabrics), "contractual_milestone_overdue") == []


@pytest.mark.story("US-2750")
def test_the_overdue_milestones_of_a_project_come_in_the_order_of_the_plan_after_its_other_signals(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : the three signals of a project in watch come before its milestones, in alert,
    # which keep the order of the plan; the date of the reading is a past date when the markings
    # are, and the zone of each signal follows its code.
    keep_milestones(
        owner,
        fabrics,
        milestone("Second jalon", "2026-05-20"),
        milestone("Premier jalon", PASSED),
    )
    body = health(api, fabrics)
    assert [(each["code"], each["zone"]) for each in body["signals"]] == [
        ("review_overdue", "watch"),
        ("no_actual_cost_since_last_review", "watch"),
        ("contractual_milestone_overdue", "alert"),
        ("contractual_milestone_overdue", "alert"),
    ]
    labels = [
        each["params"]["milestone_label"]
        for each in signals_of(body, "contractual_milestone_overdue")
    ]
    assert labels == ["Second jalon", "Premier jalon"]


# --- Who opens ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0030-A")
def test_a_signal_says_whether_its_project_opens_for_the_caller_as_the_list_does(
    api: ContractClient, realm: TestRealm, database: Database, fabrics: Portfolio
) -> None:
    # « Chaque signal nomme son projet et dit s'il s'ouvre » : an account that holds the permission
    # of the view alone, contributor of no project, reads the signal under its label without a
    # link; once it contributes to the project it opens it, as the list's ``can_open`` does.
    reading = person(database, realm, "portfolio_pilot_health.read", name="Zoé")
    assert [each["can_open"] for each in served(api, reading, "pilot-health", READ)["signals"]] == [
        False,
        False,
    ]
    contribute(database, str(fabrics.in_progress.project_id), reading, "contributor")
    body = served(api, reading, "pilot-health", READ)
    assert [each["can_open"] for each in body["signals"]] == [True, True]
    assert {each["project_label"] for each in body["signals"]} == {RUNNING_LABEL}


@pytest.mark.requirement("WF-PTF-0030-A")
def test_the_view_is_read_under_its_own_permission_alone(
    api: ContractClient, realm: TestRealm, database: Database, fabrics: Portfolio
) -> None:
    # « Chaque vue est gardée par la permission de sa fonction au catalogue, et par elle seule » :
    # an account that holds the permission of another view has a 404, the manager of the project
    # that holds neither, and a reader of every project that holds this one has an answer.
    other = person(database, realm, "portfolio_projects.read", name="Alix")
    assert read(api, other, "pilot-health", READ).status_code == 404
    assert read(api, fabrics.stage.manager, "pilot-health", READ).status_code == 404
    assert read(api, fabrics.stage.reader, "pilot-health", READ).status_code == 200


@pytest.mark.story("US-2750")
def test_an_unknown_state_is_refused_in_the_envelope_of_the_contract(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Une erreur est un code : a state that is none of the six is refused, 422, on its pointer.
    answer = read(api, fabrics.stage.reader, "pilot-health", f"{READ}&states=sleeping")
    assert answer.status_code == 422
    assert [(each["pointer"], each["code"]) for each in answer.json()["fields"]] == [
        ("/query/states", "VALIDATION_FAILED")
    ]


@pytest.mark.story("US-2750")
def test_the_service_reads_the_current_day_by_the_reading_it_is_given(fabrics: Portfolio) -> None:
    # Toute vue lit par ``PortfolioReading(at, cache)`` (#4194) : the current day is that of the
    # instant of the reading, here 19 November, and the weeks run to it.
    viewer = Viewer(fabrics.stage.reader.user_id, MANAGING)
    with fabrics.stage.database.transaction() as session:
        body = read_pilot_health(session, PortfolioAsked(), PortfolioReading(NOW), viewer)
    assert body["scope"]["as_of"] == "2026-11-19"
    weeks = (NOW.date() - REVIEW_MARKED.date()).days // 7
    assert [each["params"] for each in signals_of(body, "review_overdue")] == [
        {"weeks_since_last_mark": weeks}
    ]
