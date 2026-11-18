# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of a project on the current day, served (``getProjectIndicators``; US-1660/L3).

The context of the computation, the revision it reads — the current one, or the last marked one
without it —, the refusals in the order of the contract, and the sentences of the document on the
service: the progress, the indices and their zone on the thresholds of the day, the variances, the
projections, a review that adds a task then its cost. The projects are the one under way of
``indicators_support`` and references priced task by task (``day_indicators_support``). Every
answer is checked against the contract.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from costs_support import cost, load_import
from day_indicators_support import (
    Planned,
    completed,
    dated,
    indicators,
    indicators_answer,
    material,
    priced,
    reestimated,
    subproject,
)
from estimate_support import Lines
from indicators_support import COMPLETED_ON, TODAY, clock_setter, marked, thresholds, under_way
from nodes_support import Tree, faults, opened, refusal
from planning_support import DAY
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene

from waterfall.core.projects.interface import current_day
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from day_indicators_support import Priced
    from indicators_support import Clock, UnderWay
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

D = Decimal
ONE_DAY = timedelta(days=1)
FORBIDDEN = (409, "STATE_FORBIDS_OPERATION")


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the indicators are computed on."""
    return clock_setter(monkeypatch)


@pytest.fixture
def project(api: ContractClient, stage: Scene, clock: Clock) -> UnderWay:
    """Give the project under way, the clock on ``TODAY``."""
    return under_way(api, stage, clock)


@pytest.fixture
def thousand(api: ContractClient, stage: Scene, clock: Clock) -> Priced:
    """Give a project of budget 1 000, of earned value 400, of actual cost 500, of remaining 550.

    The studies, 400, completed on Monday; the wiring, 600, re-estimated to 550; the clock on the
    Tuesday, every task of the reference behind it.
    """
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600")])
    completed(found.tree, "Études", DAY)
    reestimated(found.tree, "Câblage", "550")
    load_import(stage, UUID(stage.project["project_id"]), [cost("FA-1", None, "500.00")])
    clock(DAY + ONE_DAY)
    return found


@pytest.fixture
def earned_900(api: ContractClient, stage: Scene, clock: Clock) -> Priced:
    """Give a project whose studies, 900, are completed on Monday, and no cost yet; the Tuesday."""
    found = priced(api, stage, [Planned("Études", "900"), Planned("Câblage", "100")])
    completed(found.tree, "Études", DAY)
    clock(DAY + ONE_DAY)
    return found


def computable(value: str | None, reason: str | None = None) -> dict[str, Any]:
    """Give a figure in the envelope of the contract."""
    return {"is_computable": value is not None, "value": value, "reason": reason}


def charged(stage: Scene, number: str, amount: str, day: date = DAY) -> None:
    """Import a line of cost of the project alone, of the amount said, dated Monday unless said."""
    load_import(stage, UUID(stage.project["project_id"]), [dated(number, None, amount, day)])


@pytest.mark.requirement("WF-IND-0010-A")
def test_the_indicators_of_the_day_are_those_of_the_current_revision_with_their_context(
    api: ContractClient, stage: Scene, project: UnderWay
) -> None:
    # no revision named, or the current one, the indicators of the current day on
    # the current revision, ``computed_at`` the instant of the computation, not kept; the amounts
    # to the cent, the ratios and the indices to four decimals, the zones of the thresholds of the
    # installation, 0.9 and 0.8.
    revision_id = project.tree.revision["revision_id"]
    body = indicators(api, stage)
    assert body == {
        "context": {
            "revision_id": revision_id,
            "revision_status": "draft",
            "computed_at": "2026-11-13T09:00:00Z",
            "scope": "project",
            "is_stored": False,
        },
        "reference_budget": "4000.00",
        "planned_value": "4000.00",
        "earned_value": "1000.00",
        "actual_cost": "1250.00",
        "remaining": "3000.00",
        "financial_progress": computable("0.2941"),
        "budget_consumption": computable("0.3125"),
        "physical_progress": computable("0.25"),
        "cost_index": {"value": computable("0.8"), "zone": "watch"},
        "schedule_index": {"value": computable("0.25"), "zone": "alert"},
        "cost_variance": "-250.00",
        "schedule_variance": "-3000.00",
        "projections": {
            "at_budget": "4250.00",
            "project_manager": "4250.00",
            "at_observed_rate": computable("5000.00"),
            "variance_at_budget": "250.00",
            "variance_project_manager": "250.00",
            "variance_at_observed_rate": "1000.00",
        },
    }
    assert project.now.date() == TODAY
    assert indicators(api, stage, f"?revision_id={revision_id}") == body
    assert indicators(api, stage, "?scope=project") == body


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_project_before_in_progress_has_no_project_indicator_and_its_state_is_named(
    api: ContractClient, stage: Scene
) -> None:
    # « Sur un projet à l'état Chiffrage, aucun indicateur projet n'est proposé. » Created, then
    # in pricing once its first revision is opened: 409, the state named with its enumeration —
    # before the parameters, which a scope unknown would refuse otherwise.
    assert refusal(indicators_answer(api, stage)) == (
        *FORBIDDEN,
        {"state": "created", "state_enum": "ProjectState"},
    )
    Tree(api, stage, opened(api, stage))
    for query in ("", "?scope=câblage&as_of=2026-11-02&revision_id=" + str(UUID(int=1))):
        assert refusal(indicators_answer(api, stage, query)) == (
            *FORBIDDEN,
            {"state": "pricing", "state_enum": "ProjectState"},
        )


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_revision_named_with_a_date_is_refused_with_an_unknown_scope_at_once(
    api: ContractClient, stage: Scene, project: UnderWay
) -> None:
    # ``revision_id`` and ``as_of`` both choose the revision, 422 on
    # ``/query/revision_id``; with an unknown scope, both refusals at once, the scope first.
    revision_id = project.tree.revision["revision_id"]
    both = f"?revision_id={revision_id}&as_of={TODAY.isoformat()}"
    assert faults(indicators_answer(api, stage, both)) == [
        ("/query/revision_id", "VALIDATION_FAILED", {}),
    ]
    assert faults(indicators_answer(api, stage, f"{both}&scope=SP-1")) == [
        ("/query/scope", "UNKNOWN_SUBPROJECT", {}),
        ("/query/revision_id", "VALIDATION_FAILED", {}),
    ]


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_revision_that_is_not_one_of_the_project_is_refused_as_not_found(
    api: ContractClient, stage: Scene, project: UnderWay
) -> None:
    # The contract refuses with 404 an object the project does not have: a revision unknown, or
    # another project's, never an error outside the envelope; the dates and the marked revisions
    # of the project wait for US-1670/L2.
    elsewhere = create(api, stage.manager, label="Extension de la ligne d'essais")
    opened_there = api.post(
        f"{PROJECTS}/{elsewhere['project_id']}/revisions", headers=stage.manager.headers, json={}
    )
    assert opened_there.status_code == 201, opened_there.text
    for revision_id in (uuid4(), opened_there.json()["revision_id"]):
        answer = indicators_answer(api, stage, f"?revision_id={revision_id}")
        assert answer.status_code == 404, answer.text
    own = project.tree.revision["revision_id"]
    assert indicators_answer(api, stage, f"?revision_id={own}").status_code == 200


@pytest.mark.requirement("WF-IND-0010-A")
def test_without_a_current_revision_the_last_marked_one_is_computed_with_the_cost_of_the_day(
    api: ContractClient, stage: Scene, clock: Clock, project: UnderWay
) -> None:
    # « Sur un projet sans révision en cours, un import de coûts réels change les indicateurs au
    # jour courant et laisse inchangés ceux conservés de la dernière révision marquée. » The
    # revision of the review marked, none is current: the day reads it, not kept, and an
    # extraction applied changes it. The review is marked after the reference, which the service
    # marked at the instant it was written: the clock is set after it.
    revision_id = project.tree.revision["revision_id"]
    at = clock(utc_now().date() + ONE_DAY)
    marked(stage, project.tree.revision, "Revue de novembre")
    body = indicators(api, stage)
    assert body["context"] == {
        "revision_id": revision_id,
        "revision_status": "marked",
        "computed_at": at.isoformat().replace("+00:00", "Z"),
        "scope": "project",
        "is_stored": False,
    }
    assert (body["earned_value"], body["actual_cost"]) == ("1000.00", "1250.00")
    load_import(stage, project.project_id, [dated("FA-4001", None, "750.00", COMPLETED_ON)])
    again = indicators(api, stage)
    assert (again["actual_cost"], again["cost_index"]["value"]["value"]) == ("2000.00", "0.5")
    assert again["context"] == body["context"]


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_kept_reading_of_a_subproject_created_after_the_marking_is_refused_without_a_state(
    api: ContractClient, stage: Scene, clock: Clock, project: UnderWay
) -> None:
    # Décision de l'auteur du 2026-11-16 (#3604) : a subproject created after the marking, which
    # the project has today — no 422 —, has no document in the revision, named or designated by
    # its date: 409 ``STATE_FORBIDS_OPERATION`` without ``params``, as a revision marked before
    # In progress; nothing is computed in its place. The scope the marking kept is read as kept,
    # and the day knows the subproject.
    revision_id = project.tree.revision["revision_id"]
    at = clock(utc_now().date() + ONE_DAY)
    marked(stage, project.tree.revision, "Revue de novembre")
    since = subproject(api, stage, "SP-9", "Essais")
    as_of = current_day(at).isoformat()
    for query in (f"?revision_id={revision_id}", f"?as_of={as_of}"):
        assert indicators(api, stage, query)["context"]["is_stored"] is True, query
        refused = indicators_answer(api, stage, f"{query}&scope={since}")
        assert refusal(refused) == (*FORBIDDEN, {}), query
    day = indicators(api, stage, f"?scope={since}")
    assert (day["context"]["scope"], day["context"]["is_stored"]) == (since, False)


@pytest.mark.requirement("WF-IND-0010-A")
@pytest.mark.requirement("WF-IND-0070-A")
@pytest.mark.requirement("WF-IND-0050-A")
@pytest.mark.usefixtures("earned_900")
def test_before_any_actual_cost_the_cost_index_and_the_observed_rate_are_not_computable(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « Un indice de coût sans coût réel est affiché non calculable. » « Avant le premier import
    # de coûts réels, il est affiché non calculable. » « Avant tout coût réel, la projection au
    # rythme constaté est non calculable et les deux autres sont affichées. » Then, a cost and no
    # value earned yet — the day before the studies complete —, ``no_earned_value``.
    body = indicators(api, stage)
    assert body["cost_index"] == {"value": computable(None, "no_actual_cost"), "zone": None}
    assert body["projections"] == {
        "at_budget": "100.00",
        "project_manager": "100.00",
        "at_observed_rate": computable(None, "no_actual_cost"),
        "variance_at_budget": "-900.00",
        "variance_project_manager": "-900.00",
        "variance_at_observed_rate": None,
    }
    charged(stage, "FA-1", "50.00", DAY - timedelta(days=7))
    clock(DAY - ONE_DAY)
    body = indicators(api, stage)
    assert body["earned_value"] == "0.00"
    assert body["projections"]["at_observed_rate"] == computable(None, "no_earned_value")
    assert body["cost_index"]["value"]["value"] == "0"


@pytest.mark.requirement("WF-IND-0050-A")
@pytest.mark.usefixtures("thousand")
def test_a_project_of_budget_1000_earned_400_cost_500_remaining_550_projects_1100_1050_1250(
    api: ContractClient, stage: Scene
) -> None:
    # « Sur un projet de budget 1 000, de valeur acquise 400, de coût réel 500 et de reste à
    # engager 550, les projections valent 1 100 au budget, 1 050 pour le chef de projet et 1 250 au
    # rythme constaté. » On the service, with their variances to the budget.
    body = indicators(api, stage)
    assert (body["reference_budget"], body["earned_value"]) == ("1000.00", "400.00")
    assert (body["actual_cost"], body["remaining"]) == ("500.00", "550.00")
    assert body["projections"] == {
        "at_budget": "1100.00",
        "project_manager": "1050.00",
        "at_observed_rate": computable("1250.00"),
        "variance_at_budget": "100.00",
        "variance_project_manager": "50.00",
        "variance_at_observed_rate": "250.00",
    }


@pytest.mark.requirement("WF-IND-0060-A")
@pytest.mark.usefixtures("thousand")
def test_a_budget_of_1000_of_which_400_are_borne_by_completed_tasks_is_40_percent_done(
    api: ContractClient, stage: Scene
) -> None:
    # « Sur un budget de 1 000 dont 400 sont portés par des tâches terminées, l'avancement physique
    # vaut 40 %. » On the service.
    assert indicators(api, stage)["physical_progress"] == computable("0.4")


@pytest.mark.requirement("WF-IND-0070-A")
@pytest.mark.requirement("WF-REF-0170-A")
@pytest.mark.usefixtures("thousand")
def test_an_earned_value_of_400_for_a_cost_of_500_gives_0_8_in_watch_and_minus_100(
    api: ContractClient, stage: Scene
) -> None:
    # « Une valeur acquise de 400 pour un coût réel de 500 donne 0,8. » « Une valeur acquise de
    # 400 pour un coût réel de 500 donne un écart de coût de -100. » « Avec des seuils à 0,9 et
    # 0,8, un indice de 0,9 est nominal et un indice de 0,8 en vigilance. »
    body = indicators(api, stage)
    assert body["cost_index"] == {"value": computable("0.8"), "zone": "watch"}
    assert body["cost_variance"] == "-100.00"


@pytest.mark.requirement("WF-REF-0170-A")
@pytest.mark.requirement("WF-IND-0070-A")
@pytest.mark.usefixtures("earned_900")
def test_the_cost_index_crosses_the_three_zones_as_the_actual_cost_grows(
    api: ContractClient, stage: Scene
) -> None:
    # « Un indice traverse les trois zones lorsque sa valeur décroît de 1 à 0,5, avec des seuils
    # fixés à 0,9 et 0,8. » « L'indice change de zone quand il franchit un seuil, dans un sens
    # comme dans l'autre. » The earned value, 900, over an actual cost that grows: the index shown,
    # to four decimals, is the one classified.
    steps = [
        ("900.00", "1", "nominal"),
        ("47.37", "0.95", "nominal"),
        ("52.63", "0.9", "nominal"),
        ("58.82", "0.85", "watch"),
        ("66.18", "0.8", "watch"),
        ("75.00", "0.75", "alert"),
        ("600.00", "0.5", "alert"),
    ]
    for number, (amount, index, zone) in enumerate(steps):
        charged(stage, f"FA-{number}", amount)
        assert indicators(api, stage)["cost_index"] == {"value": computable(index), "zone": zone}


@pytest.mark.requirement("WF-IND-0070-A")
@pytest.mark.usefixtures("earned_900")
def test_the_zone_of_an_index_is_classified_on_the_thresholds_of_each_reading(
    api: ContractClient, stage: Scene
) -> None:
    # « L'indice change de zone quand il franchit un seuil, dans un sens comme dans l'autre. »
    # An index of 0.85 is in watch at 0.9 and 0.8, nominal at 0.85 and 0.7, in alert at 0.95 and
    # 0.9: its value does not move, its zone follows the thresholds.
    charged(stage, "FA-1", "1058.82")
    found: dict[str, dict[str, Any]] = {}
    for watch, alert in (("0.9", "0.8"), ("0.85", "0.7"), ("0.95", "0.9")):
        thresholds(stage, watch, alert)
        found[watch] = indicators(api, stage)["cost_index"]
    assert {each: index["zone"] for each, index in found.items()} == {
        "0.9": "watch",
        "0.85": "nominal",
        "0.95": "alert",
    }
    assert {index["value"]["value"] for index in found.values()} == {"0.85"}


@pytest.mark.requirement("WF-RAE-0050-A")
def test_a_task_added_in_review_then_charged_moves_the_remaining_then_the_cost_index(
    api: ContractClient, stage: Scene, thousand: Priced
) -> None:
    # « Après ajout d'une tâche chiffrée en revue périodique, le reste à engager et la projection
    # du chef de projet augmentent de son montant ; le budget de référence, la projection au
    # budget, la projection au rythme constaté et l'indice de coût sont inchangés. » « Lorsque la
    # dépense de cette tâche est importée au coût réel, la valeur acquise ne change pas et
    # l'indice de coût baisse. »
    before = indicators(api, stage)
    tree = thousand.tree
    task = tree.made("Extension")
    Lines(tree).made(task, **material(thousand.costs, "Matériel Extension", "200", None))
    added = indicators(api, stage)
    assert (added["remaining"], added["projections"]["project_manager"]) == ("750.00", "1250.00")
    unchanged = ("reference_budget", "earned_value", "actual_cost", "cost_index")
    assert {name: added[name] for name in unchanged} == {name: before[name] for name in unchanged}
    for name in ("at_budget", "at_observed_rate"):
        assert added["projections"][name] == before["projections"][name]
    charged(stage, "FA-2", "150.00")
    paid = indicators(api, stage)
    assert (paid["earned_value"], paid["actual_cost"]) == ("400.00", "650.00")
    assert D(paid["cost_index"]["value"]["value"]) < D(added["cost_index"]["value"]["value"])
    assert paid["cost_index"]["value"]["value"] == "0.6154"
