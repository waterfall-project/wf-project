# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The earned value, the planned value and the actual cost of a project at a day (US-1660/L3).

On the project under way of ``indicators_support`` — the studies, 1 000, completed on
``COMPLETED_ON``, the wiring, 3 000, started, 1 250 of actual cost —, and on references priced task
by task (``day_indicators_support``): the earned value from the day of the completion, never from
the start nor from the cost; the planned value of the reference at the end of the day, the one
``planned_value`` of EP-07 gives; the actual cost of the lines dated on or before the day. Every
answer is checked against the contract.
"""

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from costs_support import load_import
from day_indicators_support import Planned, completed, dated, indicators, priced
from estimate_support import Lines, costing
from indicators_support import COMPLETED_ON, TODAY, clock_setter, under_way
from planning_support import DAY
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_support import in_progress
from sqlalchemy import select, update

from waterfall.core.estimate.interface import planned_value
from waterfall.core.resource_settings.tables import Calendar, ResourceRole

if TYPE_CHECKING:
    from datetime import date

    from day_indicators_support import Priced
    from indicators_support import Clock, UnderWay
    from nodes_support import Tree
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

D = Decimal
ONE_DAY = timedelta(days=1)


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
def behind(api: ContractClient, stage: Scene) -> Priced:
    """Give a reference of 600: the studies, 400 on Monday, completed then; the wiring, 200.

    The wiring runs on Monday and Tuesday: at the end of Monday, half its hours are behind it, 500
    planned and 400 earned.
    """
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "200", days="2")])
    completed(found.tree, "Études", DAY)
    return found


def oracle(stage: Scene, reference: UUID, at: date) -> Decimal:
    """Give the planned value of the reference at a day, as EP-07 computes it."""
    with stage.database.transaction() as session:
        return planned_value(session, UUID(stage.project["project_id"]), reference, at)


@pytest.mark.requirement("WF-IND-0030-A")
def test_a_task_completed_on_a_day_earns_from_that_day_and_not_the_day_before(
    api: ContractClient, stage: Scene, clock: Clock, project: UnderWay
) -> None:
    # « Une tâche terminée le 12 du mois contribue à la valeur acquise dès cette date, non à la
    # revue suivante. » The studies, completed on ``COMPLETED_ON``, earn their 1 000 that day.
    clock(COMPLETED_ON - ONE_DAY)
    assert indicators(api, stage)["earned_value"] == "0.00"
    clock(COMPLETED_ON)
    assert indicators(api, stage)["earned_value"] == "1000.00"
    clock(TODAY)
    body = indicators(api, stage)
    assert (body["reference_budget"], body["earned_value"]) == ("4000.00", "1000.00")
    assert body["context"]["revision_id"] == project.tree.revision["revision_id"]


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_task_started_contributes_nothing_to_the_earned_value(
    api: ContractClient, stage: Scene, project: UnderWay
) -> None:
    # « Une tâche démarrée à 90 % de son temps ne contribue pas. » The wiring, started, its dates
    # all behind the day, earns nothing: only the completion earns.
    assert project.wiring["task"]["progress"] == "started"
    body = indicators(api, stage)
    assert (body["planned_value"], body["earned_value"]) == ("4000.00", "1000.00")
    assert body["physical_progress"]["value"] == "0.25"


@pytest.mark.requirement("WF-IND-0030-A")
def test_a_task_whose_actual_cost_exceeds_its_budget_earns_its_budgeted_amount(
    api: ContractClient, stage: Scene, project: UnderWay
) -> None:
    # « Une tâche dont le coût réel dépasse le montant budgété contribue pour le montant
    # budgété. » The earned value reads no line of cost: 2 000 more of actual cost leave it.
    load_import(stage, project.project_id, [dated("FA-2001", None, "2000.00", COMPLETED_ON)])
    body = indicators(api, stage)
    assert (body["earned_value"], body["actual_cost"]) == ("1000.00", "3250.00")


@pytest.mark.requirement("WF-IND-0010-A")
def test_the_actual_cost_of_the_day_counts_the_lines_dated_on_or_before_it_known_now(
    api: ContractClient, stage: Scene, project: UnderWay
) -> None:
    # « Une ligne de coût datée après la date de marquage n'entre pas dans le coût réel de cette
    # révision. » On the current day, the lines dated on or before it, known at the computation —
    # one imported now, dated long before, included —; one dated the day after, not.
    lines = [
        dated("FA-3001", None, "100.00", TODAY),
        dated("FA-3002", None, "200.00", TODAY + ONE_DAY),
        dated("FA-3003", None, "50.00", DAY - timedelta(days=200)),
    ]
    load_import(stage, project.project_id, lines)
    assert indicators(api, stage)["actual_cost"] == "1400.00"


@pytest.mark.requirement("WF-IND-0080-A")
def test_an_earned_value_of_400_for_a_planned_value_of_500_gives_0_8_and_minus_100(
    api: ContractClient, stage: Scene, clock: Clock, behind: Priced
) -> None:
    # « Une valeur acquise de 400 pour une valeur planifiée de 500 donne 0,8. » « Une valeur
    # acquise de 400 pour une valeur planifiée de 500 donne un écart de délai de -100. » The
    # planned value is the one of EP-07 at the end of the day, on the reference.
    clock(DAY)
    body = indicators(api, stage)
    assert (body["planned_value"], body["earned_value"]) == ("500.00", "400.00")
    assert body["planned_value"] == str(oracle(stage, behind.reference_id, DAY))
    assert body["schedule_index"] == {
        "value": {"is_computable": True, "value": "0.8", "reason": None},
        "zone": "watch",
    }
    assert body["schedule_variance"] == "-100.00"


@pytest.mark.requirement("WF-IND-0080-A")
def test_before_the_first_task_of_the_reference_starts_the_schedule_index_is_not_computable(
    api: ContractClient, stage: Scene, clock: Clock, behind: Priced
) -> None:
    # « Avant la date de début de la première tâche de la référence, l'indice est non
    # calculable. » The day before the Monday, nothing is planned yet.
    clock(DAY - ONE_DAY)
    body = indicators(api, stage)
    assert body["planned_value"] == "0.00"
    assert body["schedule_index"] == {
        "value": {"is_computable": False, "value": None, "reason": "no_planned_value"},
        "zone": None,
    }
    assert str(oracle(stage, behind.reference_id, DAY - ONE_DAY)) == "0.00"


@pytest.mark.requirement("WF-IND-0080-A")
@pytest.mark.requirement("WF-IND-0030-A")
def test_every_task_completed_at_the_finish_of_the_reference_earns_its_budget_and_shows_1(
    api: ContractClient, stage: Scene, clock: Clock, behind: Priced
) -> None:
    # « Un projet dont toutes les tâches sont terminées à la date de fin prévue par la référence
    # affiche 1. » « La valeur acquise d'un projet dont toutes les tâches sont terminées égale son
    # budget de référence ; … » The wiring completed on Tuesday, its last day.
    completed(behind.tree, "Câblage", DAY + ONE_DAY)
    clock(DAY + ONE_DAY)
    body = indicators(api, stage)
    assert body["reference_budget"] == body["planned_value"] == body["earned_value"] == "600.00"
    assert body["schedule_index"] == {
        "value": {"is_computable": True, "value": "1", "reason": None},
        "zone": "nominal",
    }
    assert body["physical_progress"]["value"] == "1"


def test_the_planned_value_is_the_one_ep07_gives_of_the_reference_at_the_project_scope(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # The oracle of the design (EP-10, "Ce que le cadrage décide"): a line of labour on the
    # calendar of its role and a line of material on that of its task, over three days, and a line
    # of a milestone, whole at its date; read each day, the planned value is ``planned_value`` of
    # EP-07.
    # The equality may differ by a cent: EP-07 rounds the share of each line, EP-10 the share of
    # each line over a common spreading, and the two roundings may fall differently (#3566).
    costs = costing(stage.database)

    def build(tree: Tree, lines: Lines) -> None:
        studies = tree.made("Études", task={"duration": {"value": "3", "unit": "d"}})
        lines.made(
            studies,
            label="Ingénierie",
            quantity="1",
            resource_role_id=str(costs.role),
            hours="10",
        )
        lines.made(
            studies,
            label="Câbles",
            quantity="1",
            cost_category_id=str(costs.material),
            unit_disbursement="333.33",
        )
        milestone = tree.made("Réception", task={"duration": {"value": "0", "unit": "d"}})
        lines.made(
            milestone,
            label="Procès-verbal",
            quantity="1",
            cost_category_id=str(costs.material),
            unit_disbursement="100",
        )

    review = in_progress(api, stage, build)
    reference = UUID(review.reference["revision_id"])
    for day in (DAY - ONE_DAY, DAY, DAY + ONE_DAY, DAY + 2 * ONE_DAY, DAY + 3 * ONE_DAY):
        clock(day)
        body = indicators(api, stage)
        assert body["planned_value"] == str(oracle(stage, reference, day)), day
    assert body["planned_value"] == body["reference_budget"] == "1083.33"


@pytest.mark.requirement("WF-IND-0020-A")
def test_the_planned_value_of_ep07_is_the_sum_of_the_shares_of_the_lines_as_ep10_s(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « La somme des valeurs […] des sous-projets […] égale celle du projet, de même pour […] la
    # valeur planifiée » holds because each line counts its share rounded to the cent; EP-07 counts
    # it so too (#3566). Two lines of 100.00 on tasks of 3 days: at the end of the first day, 33.33
    # each, 66.66 by both, not the 66.67 of one rounding of the exact sum.
    tasks = [Planned("Câblage", "100", days="3"), Planned("Essais", "100", days="3")]
    found = priced(api, stage, tasks)
    clock(DAY)
    assert indicators(api, stage)["planned_value"] == "66.66"
    assert oracle(stage, found.reference_id, DAY) == D("66.66")


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_of_ep07_reads_the_calendar_of_a_role_as_the_reference_kept_it(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « étalé sur la durée de leur tâche au prorata des heures travaillées — sur le calendrier de
    # son rôle […] — telle que la révision de référence la date » : the calendar its marking kept,
    # as the indicators read it (#3566). 10 hours at 65.00 over three days of eight hours: a third
    # at the end of the Monday, 216.67, still once the calendar of the role works two hours on
    # Monday, which would make it 650.00 x 2/18, 72.22.
    costs = costing(stage.database)

    def build(tree: Tree, lines: Lines) -> None:
        studies = tree.made("Études", task={"duration": {"value": "3", "unit": "d"}})
        lines.made(
            studies, label="Ingénierie", quantity="1", resource_role_id=str(costs.role), hours="10"
        )

    reference = UUID(in_progress(api, stage, build).reference["revision_id"])
    clock(DAY)
    assert DAY.weekday() == 0
    assert oracle(stage, reference, DAY) == D("216.67")
    with stage.owner.begin() as connection:
        calendar = connection.scalar(
            select(ResourceRole.calendar_id).where(ResourceRole.id == costs.role)
        )
        connection.execute(update(Calendar).where(Calendar.id == calendar).values(monday=D(2)))
    assert oracle(stage, reference, DAY) == D("216.67")
    assert indicators(api, stage)["planned_value"] == "216.67"
