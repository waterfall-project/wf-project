# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of a project that carries a risk, identified or occurred (US-2630/L1).

The project of ``occurrence_support``: costed at 1 000 — ``Étude`` 600, ``Réalisation`` 400 —, a
risk of severity 200 at 30 % whose provision, 60, is borne by ``Étude``, the first revision marked
and designated the reference, the second opened; the project moved In progress, the studies
completed and paid, 400. The provision is counted in the remaining to commit and in the cash-out,
at its date and without a payment delay; the tasks an occurrence creates earn nothing; the own
estimate of a risk identified moves its provision, the remaining and the projection, and nothing of
the reference. Every answer is checked against the contract (``ContractClient``).
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import pairwise
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
from costs_support import load_import
from curves_support import COST_CURVE, curve
from day_indicators_support import dated, indicators
from estimate_support import Costing, costing
from fastapi.testclient import TestClient
from indicators_support import clock_setter, marked, progressed, zeroed
from nodes_support import Tree
from occurrence_support import (
    DIAGNOSTIC,
    REWIRING,
    SEARCH,
    TESTS,
    WIRES,
    Occurring,
    occurring,
    start_own_estimate,
)
from planning_support import DAY
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from remaining_support import line_named, task_named
from risks_support import costed
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.interface import PROJECT, UNASSIGNED
from waterfall.core.estimate.interface import IndicatorLine, Placement
from waterfall.core.indicators.caching import day_key
from waterfall.core.indicators.computing import LinesRead, amounts_from
from waterfall.core.indicators.curving import CurveSources, curves_of_scope
from waterfall.core.indicators.interface import IndicatorsReading, day_reading, offer_curves
from waterfall.core.planning.interface import WorkInstant, weekly_calendar
from waterfall.core.projects.interface import subproject_ids
from waterfall.platform.cache import PREFIX, IndicatorsCache
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.occurrence import occur
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from indicators_support import Clock
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

type Serve = Callable[[TaskQueue, IndicatorsCache], ContractClient]

TASKS = "/api/v1/tasks"
# The validity of an entry of the cache in these tests, in seconds: longer than any of them.
TTL = 300
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
# The Thursday the indicators are read on: after the studies, in the middle of the own estimate.
TODAY = date(2026, 11, 12)
D = Decimal
EIGHT = D(8)
# The week of the task of the lines built by hand: eight hours from Monday to Friday.
WEEK = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, D(0), D(0)))


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[IndicatorsCache]:
    """Give the cache of the indicators beside the queue of the test; its entries deleted after."""
    opened = IndicatorsCache.of(queue, TTL)
    yield opened
    held = cast("Any", queue.client)
    for key in held.scan_iter(match=f"{PREFIX}*"):
        held.delete(key)
    opened.close()


@pytest.fixture
def serve(
    contract: OpenAPI, database: Database, keycloak: Keycloak, realm_settings: ServiceSettings
) -> Serve:
    """Give the means to serve the API on the database of the test, a queue and a cache."""

    def served(queue: TaskQueue, cache: IndicatorsCache) -> ContractClient:
        administration = KeycloakAdmin(keycloak, realm_settings)
        services = Services(database, keycloak, administration, queue, nowhere()[1], None, cache)
        app = create_app(services)
        return ContractClient(TestClient(app, raise_server_exceptions=False), contract)

    return served


@pytest.fixture
def api(serve: Serve, queue: TaskQueue, cache: IndicatorsCache) -> ContractClient:
    """Give a client of the application that serves the indicators of the day from the cache.

    It deposits its tasks in the queue of the test; every reading below goes through the cache, so
    that an entry the writes did not leave would be served stale.
    """
    return serve(queue, cache)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the occurrences."""
    queue.prepare()
    return Worker(database, queue, {"risk_occurrence": occur}, "worker", AT_ONCE)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the indicators are computed on."""
    return clock_setter(monkeypatch)


@pytest.fixture
def ready(api: ContractClient, stage: Scene, clock: Clock) -> Occurring:
    """Give the risk identified in the second revision of the project, moved In progress.

    The making completed and paid, 400; the clock at ``TODAY``. The studies bear the provision, and
    become a summary task when the risk occurs: the making is the task that stays as it is.
    """
    costs: Costing = costing(stage.database)
    ready = occurring(api, costed(api, stage, costs))
    path = f"{PROJECTS}/{ready.project.project_id}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    coded = api.patch(
        path, headers=stage.manager.headers, json={"code": "PRJ-2630", "lock_version": counter}
    )
    assert (coded.status_code, coded.json()["state"]) == (200, "in_progress"), coded.text
    clock(TODAY)
    load_import(stage, ready.project.project_id, [dated("FA-1", None, "400.00", DAY)])
    finish(main_tree(ready), "Réalisation", "Fabrication")
    return ready


def main_tree(ready: Occurring) -> Tree:
    """Give the main structure of the current revision of the project, read afresh."""
    return Tree(ready.api, ready.project.stage, ready.revision)


def finish(tree: Tree, task: str, line: str, on: date = DAY) -> None:
    """Start a task of the current revision, then complete it by setting its line to nought."""
    progressed(tree, task_named(tree, task), "started", on)
    zeroed(tree, line_named(tree, line), on)


def occurred(ready: Occurring, worker: Worker) -> None:
    """Confirm the occurrence of the risk and have the worker run it."""
    report = ready.reported()
    sent = {
        "confirmed": True,
        "main_structure_lock_version": report["main_structure_lock_version"],
        "risk_lock_version": report["risk_lock_version"],
        "creates_current_revision": report["creates_current_revision"],
    }
    answer = ready.api.post(f"{ready.path}/occurrence", headers=ready.risks.headers, json=sent)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    task = ready.api.get(f"{TASKS}/{answer.json()['task_id']}", headers=ready.risks.headers)
    assert task.json()["status"] == "succeeded", task.text


def read(ready: Occurring) -> dict[str, Any]:
    """Read the indicators of the project, as the manager does."""
    return indicators(ready.api, ready.project.stage)


def estimate(ready: Occurring) -> dict[str, Any]:
    """Read the indicators of the estimate of the current revision, as the manager does."""
    answer = ready.api.get(
        f"{PROJECTS}/{ready.project.project_id}/estimate-indicators", headers=ready.risks.headers
    )
    assert answer.status_code == 200, answer.text
    return answer.json()


def cash_out(ready: Occurring) -> list[dict[str, Any]]:
    """Read the cash-out by month of the cost curve with the payment delays."""
    body = curve(ready.api, ready.project.stage, COST_CURVE, "?payment_delays=true")
    return body["cash_out_by_month"]


def forecast(ready: Occurring) -> Decimal:
    """Give the sum of the cash-out to come, by month, of the cost curve with the delays."""
    body = curve(ready.api, ready.project.stage, COST_CURVE, "?payment_delays=true")
    return sum((D(each["forecast"]) for each in body["cash_out_by_month"]), D(0))


def own_line(ready: Occurring, label: str) -> dict[str, Any]:
    """Read a line of the own estimate of the risk, in the current revision."""
    return next(
        each
        for each in ready.own()
        if each["kind"] == "estimate_line" and each["estimate_line"]["label"] == label
    )


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_remaining_counts_the_provision_and_the_cash_out_to_come_adds_up_to_it(
    ready: Occurring,
) -> None:
    # « La somme des décaissements à venir égale le reste à engager, provisions des risques
    # identifiés comprises. » The studies, 600, bear the provision, 60: the making being completed,
    # the remaining is 660 and the 660 of the forecast are in the month of the studies (9 to 16
    # November), the provision at its date, none of it delayed; the 400 paid are the past.
    found = read(ready)
    assert (found["remaining"], found["projections"]["project_manager"]) == ("660.00", "1060.00")
    assert cash_out(ready) == [{"month": "2026-11", "past": "400.00", "forecast": "660.00"}]
    assert forecast(ready) == D(found["remaining"])


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_provision_is_counted_whatever_the_state_of_its_task_and_leaves_the_budget_alone(
    ready: Occurring,
) -> None:
    # « Le reste à engager égale la somme des montants réestimés courants des lignes des tâches non
    # terminées, hors lignes de provision, plus les provisions des risques identifiés, quel que soit
    # l'état de la tâche qui les porte » (WF-RAE-0010), and the reference budget is without
    # provisions (WF-IND-0020): the studies completed, the line of the studies set to nought, the
    # provision of 60 stays in the remaining and out of the budget and of the planned value.
    finish(main_tree(ready), "Étude", "Plans")
    found = read(ready)
    assert found["remaining"] == "60.00"
    assert (found["reference_budget"], found["earned_value"]) == ("1000.00", "1000.00")
    assert forecast(ready) == D("60.00")


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_provisions_identified_of_the_estimate_are_the_provision_lines_of_the_scope(
    ready: Occurring, worker: Worker
) -> None:
    # #4223 : `provisions_identified` n'est plus nul en dur : la provision du risque identifié,
    # 60, que le total compte (660 : le réestimé de la réalisation terminée est nul), puis rien une
    # fois le risque survenu, sa ligne retirée.
    before = estimate(ready)
    assert (before["provisions_identified"], before["total"]["value"]) == ("60.00", "660.00")
    occurred(ready, worker)
    after = estimate(ready)
    assert after["provisions_identified"] == "0.00"
    assert after["total"]["value"] == "800.00"


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_own_estimate_of_a_risk_moves_the_provision_the_remaining_and_the_projection_only(
    ready: Occurring,
) -> None:
    # Propre à l'US (WF-RIS-0030, US-2570) : saisir 220 au lieu de 120 dans le devis propre du
    # risque identifié porte son coût à 300 et sa provision de 60 à 90 : le reste à engager, la
    # projection du chef de projet et l'avancement financier changent ; le budget de référence, la
    # valeur planifiée, la valeur acquise et les indices de coût et de délai restent ce qu'ils sont.
    before = read(ready)
    line = own_line(ready, SEARCH)
    revision_id = ready.revision["revision_id"]
    ready.risks.repriced(ready.read(), revision_id, line, "220.00")
    after = read(ready)
    held = ("reference_budget", "planned_value", "earned_value", "cost_index", "schedule_index")
    assert {name: after[name] for name in held} == {name: before[name] for name in held}
    assert (after["remaining"], after["projections"]["project_manager"]) == ("690.00", "1090.00")
    assert after["financial_progress"] != before["financial_progress"]
    assert estimate(ready)["provisions_identified"] == "90.00"
    assert forecast(ready) == D("690.00")


@pytest.mark.requirement("WF-IND-0100-A")
def test_after_an_occurrence_the_projection_carries_the_cost_of_the_risk_and_the_index_drifts(
    ready: Occurring, worker: Worker
) -> None:
    # Propre à l'US (WF-RIS-0050, US-2610) : la survenance retire la provision, 60, et verse le coût
    # du risque, 200, au reste à engager : la projection passe de 1 060 à 1 200, 200 au-dessus du
    # budget. Le diagnostic fait et payé, 120, sans valeur acquise (les tâches de la survenance n'en
    # portent pas), l'indice de coût, 400 acquis pour 520 payés, dérive : 0,7692, la projection
    # restant à 1 200.
    before = read(ready)
    assert before["cost_index"]["value"]["value"] == "1"
    occurred(ready, worker)
    drifting = read(ready)
    assert (drifting["remaining"], drifting["projections"]["project_manager"]) == (
        "800.00",
        "1200.00",
    )
    assert drifting["projections"]["variance_project_manager"] == "200.00"
    assert forecast(ready) == D("800.00")
    load_import(ready.project.stage, ready.project.project_id, [dated("FA-2", None, "120.00", DAY)])
    finish(main_tree(ready), DIAGNOSTIC, SEARCH)
    spent = read(ready)
    assert (spent["actual_cost"], spent["earned_value"]) == ("520.00", "400.00")
    assert spent["cost_index"]["value"]["value"] == "0.7692"
    assert spent["projections"]["project_manager"] == "1200.00"


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_documents_a_marking_keeps_count_the_provisions(ready: Occurring) -> None:
    # Propre à l'US : les documents conservés au marquage comptent les provisions, comme la lecture
    # du jour : the revision marked keeps a remaining of 660 and a cash-out to come of 660, which
    # the revision read by name serves as it kept them, whatever the risk becomes after.
    revision_id = ready.revision["revision_id"]
    marked(ready.project.stage, ready.revision, "v2")
    query = f"?revision_id={revision_id}"
    kept = indicators(ready.api, ready.project.stage, query)
    assert (kept["context"]["is_stored"], kept["remaining"]) == (True, "660.00")
    body = curve(ready.api, ready.project.stage, COST_CURVE, f"{query}&payment_delays=true")
    assert sum((D(each["forecast"]) for each in body["cash_out_by_month"]), D(0)) == D("660.00")


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_curves_of_an_offer_read_the_provision_lines_as_the_curves_of_a_project(
    ready: Occurring,
) -> None:
    # [US-2680] « les courbes d'une offre » (US-2680/L1b): the estimate of the revision read as an
    # offer's, by ``offer_curves``: one rule of the provisions in the curves, that of a project. The
    # budget is that of the lines without the provision, 1 000; the projection, from nought, the
    # remaining, provision of 60 included, 660, as the cash-out to come of the project.
    revision_id = UUID(ready.revision["revision_id"])
    with ready.project.stage.database.transaction() as session:
        document = offer_curves(session, revision_id, datetime(2026, 11, 12, 9, tzinfo=UTC))
    with_delays = document["cost_curve_payment_delays"]
    delayed = {each["name"]: each["points"] for each in with_delays["series"]}
    plain = {each["name"]: each["points"] for each in document["cost_curve"]["series"]}
    assert plain["reference_budget"][-1]["amount"] == "1000.00"
    assert plain["project_manager_projection"][-1]["amount"] == "660.00"
    assert plain["actual_cost"] == delayed["actual_cost"] == []
    forecast_of_offer = sum(
        (D(each["forecast"]) for each in with_delays["cash_out_by_month"]), D(0)
    )
    assert forecast_of_offer == forecast(ready) == D("660.00")


def line_of(budgeted: str, origin: UUID | None) -> IndicatorLine:
    """Give a line of the reference on a task of one day, the risk its task comes from if any."""
    task = uuid4()
    held = Placement(WEEK, WorkInstant(DAY), WorkInstant(DAY, EIGHT))
    amount = D(budgeted)
    return IndicatorLine(uuid4(), task, task, origin, None, amount, amount, 0, held)


@pytest.mark.requirement("WF-IND-0030-A")
def test_a_completed_task_issued_from_a_risk_adds_nothing_to_the_earned_value(
    database: Database,
) -> None:
    # « les tâches issues d'un risque survenu n'y contribuent pas » : the reference holds a task of
    # 1 000 and a task of 200 that a risk created (``origin_risk_id``), both completed on the day:
    # the budget is 1 200, the earned value 1 000, in the amounts and in the curve of the month.
    plain, issued = line_of("1000.00", None), line_of("200.00", uuid4())
    done = {plain.task_lineage_id: DAY, issued.task_lineage_id: DAY}
    read_lines = LinesRead((plain, issued), (plain, issued), {}, done)
    project_id = uuid4()
    with database.transaction() as session:
        found = amounts_from(session, project_id, read_lines, TODAY, [PROJECT])[PROJECT]
        sources = CurveSources((plain, issued), (plain, issued), {}, done)
        reading = curves_of_scope(session, project_id, sources, TODAY, PROJECT)
    assert (found.reference_budget, found.earned_value) == (D("1200.00"), D("1000.00"))
    assert sum((amount for _, amount in reading.earned), D(0)) == D("1000.00")


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_curves_of_a_subproject_read_the_provisions_attached_to_it_only(
    database: Database,
) -> None:
    # Propre à l'US (US-2630/L1) : les provisions entrent dans les lignes lues par les courbes ; le
    # périmètre d'un sous-projet garde celle qui lui est rattachée, et celle sans sous-projet tombe
    # hors de lui (elle reste dans le projet et dans « non affecté »).
    sub = uuid4()
    plain = line_of("100.00", None)
    attached = replace(line_of("60.00", None), subproject_id=sub, is_provision=True)
    loose = replace(line_of("30.00", None), is_provision=True)
    remaining = {attached.node_id: D("60.00"), loose.node_id: D("30.00")}
    sources = CurveSources((plain,), (plain, attached, loose), remaining, {})
    with database.transaction() as session:
        read_of = {
            scope: curves_of_scope(session, uuid4(), sources, TODAY, scope)
            for scope in (sub, PROJECT, UNASSIGNED)
        }
    assert [line for line, _ in read_of[sub].lines] == [attached]
    assert [line for line, _ in read_of[PROJECT].lines] == [plain, attached, loose]
    assert [line for line, _ in read_of[UNASSIGNED].lines] == [plain, loose]
    assert sum((rest for _, rest in read_of[sub].lines), D(0)) == D("60.00")


@pytest.mark.requirement("WF-IND-0030-A")
def test_the_earned_value_of_the_project_all_completed_is_the_reference_budget(
    ready: Occurring, worker: Worker
) -> None:
    # « La valeur acquise d'un projet dont toutes les tâches sont terminées égale son budget de
    # référence ; les tâches issues d'un risque survenu n'y contribuent pas. » Every task of the
    # project completed, those the occurrence created included: 1 000, the budget of the reference.
    occurred(ready, worker)
    tree = main_tree(ready)
    finish(tree, DIAGNOSTIC, SEARCH)
    finish(tree, REWIRING, WIRES)
    progressed(tree, task_named(tree, TESTS), "started", DAY)
    progressed(tree, task_named(tree, TESTS), "completed", DAY)
    zeroed(tree, line_named(tree, "Plans"), DAY)
    found = read(ready)
    assert (found["earned_value"], found["reference_budget"]) == ("1000.00", "1000.00")
    assert found["remaining"] == "0.00"


# --- The key of the cache ------------------------------------------------------------------------


def key_of(ready: Occurring) -> str:
    """Give the key of the entry of the day of the project, as a reading reads it."""
    project_id = ready.project.project_id
    at = datetime(TODAY.year, TODAY.month, TODAY.day, 9, 0, tzinfo=UTC)
    with ready.project.stage.database.transaction() as session:
        reading = day_reading(session, project_id, IndicatorsReading(PROJECT, at))
        assert reading is not None
        subprojects = subproject_ids(session, project_id)
        return day_key(session, reading.basis, reading.context, subprojects)


def counter_of(ready: Occurring, structure_id: str) -> int:
    """Read the counter of a structure of the current revision, as the list gives it."""
    answer = ready.api.get(structures_path(ready), headers=ready.risks.headers)
    assert answer.status_code == 200, answer.text
    return next(each for each in answer.json() if each["structure_id"] == structure_id)[
        "lock_version"
    ]


def structures_path(ready: Occurring) -> str:
    """Give the path of the structures of the current revision."""
    revision = f"{PROJECTS}/{ready.project.project_id}/revisions/{ready.revision['revision_id']}"
    return f"{revision}/structures"


@pytest.mark.requirement("WF-DAT-0130-A")
def test_every_write_of_a_risk_or_of_a_structure_changes_the_key_even_when_no_line_does(
    ready: Occurring,
) -> None:
    # Propre à l'US (#3629) : l'empreinte lit le compteur de toutes les structures de la révision,
    # le nombre des risques du projet et la somme de leurs compteurs. Ce qui ne touche aucune ligne
    # la change tout de même : la confirmation d'un risque (son compteur), le début du planning de
    # son devis propre (celui de sa structure), l'ouverture d'un différentiel, une saisie dans le
    # différentiel (celui de sa structure), son abandon, la déclaration d'un autre risque.
    keys = [key_of(ready)]
    ready.risks.reviewed(ready.read())
    keys.append(key_of(ready))
    start_own_estimate(ready, date(2026, 11, 10))
    keys.append(key_of(ready))
    path = structures_path(ready)
    opened = ready.api.post(
        path, headers=ready.risks.headers, json={"kind": "amendment", "label": "Avenant 1"}
    )
    assert opened.status_code == 201, opened.text
    held = opened.json()["structure_id"]
    keys.append(key_of(ready))
    changed = ready.api.patch(
        f"{path}/{held}",
        headers=ready.risks.headers,
        json={"planning_start_on": "2026-11-16", "lock_version": counter_of(ready, held)},
    )
    assert changed.status_code == 200, changed.text
    keys.append(key_of(ready))
    abandoned = ready.api.delete(
        f"{path}/{held}?lock_version={counter_of(ready, held)}", headers=ready.risks.headers
    )
    assert abandoned.status_code == 204, abandoned.text
    keys.append(key_of(ready))
    ready.risks.declared("0.1", "Un autre risque")
    keys.append(key_of(ready))
    assert all(before != after for before, after in pairwise(keys))
    # The differential abandoned leaves nothing behind: the project is what it was before it was
    # opened, and the entry of that state, which no write has outdated, is the right one again.
    assert keys[5] == keys[2]
    assert len(set(keys)) == len(keys) - 1
    assert key_of(ready) == keys[-1]


@pytest.mark.requirement("WF-DAT-0130-A")
def test_no_entry_is_served_stale_after_an_entry_a_reexamination_or_an_occurrence(
    ready: Occurring, worker: Worker
) -> None:
    # Propre à l'US (#3629) : lu une fois — l'entrée est écrite —, le reste à engager se relit juste
    # après une saisie dans le devis propre (la provision passe de 60 à 90), un réexamen (la
    # probabilité à 50 % la porte à 150) et la survenance (le coût, 300, remplace la provision).
    assert read(ready)["remaining"] == "660.00"
    line = own_line(ready, SEARCH)
    ready.risks.repriced(ready.read(), ready.revision["revision_id"], line, "220.00")
    assert read(ready)["remaining"] == "690.00"
    ready.risks.reviewed(ready.read(), probability="0.5")
    assert read(ready)["remaining"] == "750.00"
    occurred(ready, worker)
    assert read(ready)["remaining"] == "900.00"
