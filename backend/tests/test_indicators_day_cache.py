# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the current day served from the cache, under a versioned key (US-1720/L2).

Against the Redis of the tests, as the guide asks ("Un test contre Redis"): the entry served for
the four readings of the day, then left for good by a line re-estimated, a line of cost excluded, a
revision abandoned; the same answers after the base of the test is emptied (``FLUSHDB``); a Redis
that answers nowhere, which neither a reading nor an entry notices. The key read at each reading
changes with every write the indicators of the day depend on, and with the day; a marked revision is
never read in the cache. The project is the one of ``test_indicators_marked_read``.
"""

import inspect
import json
import time
from annotationlib import Format
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol, cast
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import pytest
from costs_support import load_import
from day_indicators_support import (
    Planned,
    completed,
    dated,
    indicators,
    priced,
    reestimated,
    subproject,
)
from fastapi.testclient import TestClient
from indicators_support import marked, progressed
from planning_support import DAY
from project_rows import AT
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from remaining_support import task_named
from structlog.testing import capture_logs
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.interface import PROJECT, costs_stamp
from waterfall.core.estimate.interface import lines_stamp
from waterfall.core.indicators import caching
from waterfall.core.indicators.caching import day_key
from waterfall.core.indicators.interface import IndicatorsReading, day_reading
from waterfall.core.planning.interface import revision_content_stamp
from waterfall.core.projects.interface import current_day, subproject_ids
from waterfall.platform.cache import PREFIX, IndicatorsCache, forget_reports
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.queue import DEPOSIT_TIMEOUT, WORKER_TIMEOUT, TaskQueue

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from day_indicators_support import Priced
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.settings import ServiceSettings

# The validity of an entry in these tests, in seconds; the default is ten minutes.
TTL = 300
# The day the readings are made on, the Friday of the week after the studies were completed; the
# instants of that day the clock is set at.
TODAY = DAY + timedelta(days=11)
MORNING = datetime(TODAY.year, TODAY.month, TODAY.day, 9, 0, tzinfo=UTC)
NOON = MORNING.replace(hour=12)
# The routes of the readings the cache serves, which read the instant of their computation.
ROUTES = (
    "waterfall.api.project_indicators",
    "waterfall.api.indicator_curves",
    "waterfall.api.index_history",
)
# The readings of the day, by their path below the project.
READINGS = (
    "indicators",
    "indicators/cost-curve",
    "indicators/cost-curve?payment_delays=true",
    "indicators/earned-value-curves",
    "indicators/index-history",
)
# A Redis no one listens on, and how many Redis databases the tests' workers may take at most.
CLOSED_PORT = "redis://127.0.0.1:1/0"
WORKERS = 8
REDIS_DATABASES = 16

type Clock = Callable[[datetime], None]


class Keyed(Protocol):
    """What these tests ask of the client of Redis of a queue, typed: its keys, and ``FLUSHDB``."""

    def scan_iter(self, *, match: str) -> Iterator[str]: ...

    def delete(self, *names: str) -> int: ...

    def flushdb(self) -> bool: ...

    def set(self, name: str, value: str, *, ex: int) -> object: ...


def keyed(queue: TaskQueue) -> Keyed:
    """Give the client of Redis of a queue, which decodes its answers, as these tests use it."""
    return cast("Keyed", queue.client)


type Serve = Callable[[TaskQueue, IndicatorsCache], ContractClient]


@pytest.fixture(autouse=True)
def fresh_reports() -> None:
    """Forget the causes the process has logged: each test sees the first of them."""
    forget_reports()


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[IndicatorsCache]:
    """Give the cache of the indicators beside the queue of the test; its entries deleted after."""
    opened = IndicatorsCache.of(queue, TTL)
    yield opened
    held = keyed(queue)
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
    """Give a client of the service whose readings of the day are served from the cache."""
    return serve(queue, cache)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions and a project."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the instant the readings of the day are computed at."""

    def set_instant(instant: datetime) -> None:
        for route in ROUTES:
            monkeypatch.setattr(f"{route}.utc_now", lambda: instant)

    set_instant(MORNING)
    return set_instant


@pytest.fixture
def lot(api: ContractClient, stage: Scene) -> str:
    """Give a subproject of the project, which the line of the wiring bears."""
    return subproject(api, stage, "10001", "Lot 10001")


@pytest.fixture
def project(api: ContractClient, stage: Scene, lot: str) -> Priced:
    """Give a project In progress of budget 1 000, the studies, 400, completed, 500 spent."""
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600", lot)])
    completed(found.tree, "Études", DAY)
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    return found


def project_path(stage: Scene) -> str:
    """Give the address of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def read(api: ContractClient, stage: Scene, path: str) -> dict[str, Any]:
    """Read a reading of the indicators of the project of the stage, which must be served."""
    answer = api.get(f"{project_path(stage)}/{path}", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def entries(queue: TaskQueue, stage: Scene) -> list[str]:
    """Give the keys of the entries of the project of the stage in the cache."""
    match = f"{PREFIX}{stage.project['project_id']}:*"
    return list(keyed(queue).scan_iter(match=match))


def entry(queue: TaskQueue, stage: Scene) -> dict[str, Any]:
    """Give the only entry of the project of the stage, as the cache keeps it."""
    (key,) = entries(queue, stage)
    return json.loads(str(queue.client.get(key)))


def without_instants(found: Any) -> Any:
    """Give a document without its instants of computation: ``computed_at``, and the point of day.

    The point of the day of the evolution of the indices is at the instant of its computation; the
    points a marking kept are at theirs, which do not change.
    """
    if isinstance(found, list):
        return [without_instants(each) for each in cast("list[Any]", found)]
    if not isinstance(found, dict):
        return found
    held = cast("dict[str, Any]", found)
    kept = {name: without_instants(value) for name, value in held.items() if name != "computed_at"}
    if "version_name" in kept and kept["version_name"] is None:
        kept.pop("at", None)
    return kept


def exclude(api: ContractClient, stage: Scene, number: str) -> None:
    """Exclude the line of cost of a document from the scope tracked, as the manager does."""
    lines = read(api, stage, "actual-costs")["items"]
    (line,) = [each for each in lines if each["document_number"] == number]
    path = f"{project_path(stage)}/actual-costs/{line['cost_line_id']}/tracked-scope"
    answer = api.put(path, headers=stage.manager.headers, json={"is_in_tracked_scope": False})
    assert answer.status_code == 200, answer.text


def remaining_sent(api: ContractClient, project: Priced, amount: str) -> Any:
    """Re-estimate the line of the wiring through a client given; give the answer."""
    line = next(
        item
        for item in project.tree.items()
        if item["kind"] == "estimate_line" and item["estimate_line"]["label"] == "Matériel Câblage"
    )
    sent = {
        "reestimated_amount_basis": {"unit_disbursement": amount},
        "lock_version": line["lock_version"],
    }
    path = f"{project.tree.path}/nodes/{line['node_id']}/remaining"
    return api.put(path, headers=project.tree.stage.manager.headers, json=sent)


# --- The entry served, and left at the next reading -------------------------------------------


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("project")
def test_an_entry_serves_the_four_readings_of_the_day_until_its_validity_ends(
    api: ContractClient, stage: Scene, queue: TaskQueue, clock: Clock
) -> None:
    # Propre à l'US : une entrée par projet, écrite au premier calcul, sert les quatre lectures du
    # jour tant que rien de ce dont elles dépendent ne change ; sa durée de validité est le réglage.
    # Read at nine, read again at noon: the same answers, computed at nine.
    first = {path: read(api, stage, path) for path in READINGS}
    (key,) = entries(queue, stage)
    assert 0 < int(str(queue.client.ttl(key))) <= TTL
    clock(NOON)
    again = {path: read(api, stage, path) for path in READINGS}
    assert again == first
    assert {each["context"]["computed_at"] for each in again.values()} == {"2026-11-13T09:00:00Z"}
    assert entries(queue, stage) == [key]


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock", "project")
def test_the_entry_holds_the_indicators_and_the_curves_of_every_scope_and_no_zone(
    api: ContractClient, stage: Scene, queue: TaskQueue, lot: str
) -> None:
    # Propre à l'US : l'entrée porte, pour chaque maille, les indicateurs et les deux courbes du
    # jour, valeurs des indices comprises mais jamais leur zone, classée à la lecture.
    answered = indicators(api, stage)
    kept = entry(queue, stage)["scopes"]
    assert set(kept) == {PROJECT, lot, "unassigned"}
    kinds = {"project", "cost_curve", "cost_curve_payment_delays", "earned_value_curves"}
    for scope, documents in kept.items():
        assert set(documents) == kinds
        assert {each["context"]["scope"] for each in documents.values()} == {scope}
        assert documents["project"]["cost_index"]["zone"] is None
        assert documents["project"]["schedule_index"]["zone"] is None
    index = kept[PROJECT]["project"]["cost_index"]
    assert (
        index["value"]
        == answered["cost_index"]["value"]
        == {
            "is_computable": True,
            "value": "0.8",
            "reason": None,
        }
    )
    assert answered["cost_index"]["zone"] is not None
    assert read(api, stage, f"indicators/cost-curve?scope={lot}") == kept[lot]["cost_curve"]


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_line_re_estimated_changes_the_indicators_at_the_next_reading(
    api: ContractClient, stage: Scene, queue: TaskQueue, clock: Clock, project: Priced
) -> None:
    # « La modification d'une ligne de devis change les indicateurs de la révision en cours à la
    # lecture suivante. » After `setLineRemaining` on the current revision, `getProjectIndicators`
    # read at once answers the remaining to commit and the projections changed.
    before = indicators(api, stage)
    reestimated(project.tree, "Câblage", "900")
    clock(NOON)
    after = indicators(api, stage)
    assert (before["remaining"], after["remaining"]) == ("600.00", "900.00")
    assert before["projections"]["project_manager"] == "1100.00"
    assert after["projections"]["project_manager"] == "1400.00"
    assert after["context"]["computed_at"] == "2026-11-13T12:00:00Z"
    assert len(entries(queue, stage)) == 2


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock", "project")
def test_a_line_of_cost_excluded_changes_the_cost_index_at_the_next_reading(
    api: ContractClient, stage: Scene
) -> None:
    # « L'exclusion d'une ligne de coût change l'indice de coût au jour courant à la lecture
    # suivante […] » After `setActualCostTrackedScope`, `cost_index` is computed again: without
    # an actual cost, it is not computable.
    assert indicators(api, stage)["cost_index"]["value"]["value"] == "0.8"
    exclude(api, stage, "FA-1")
    after = indicators(api, stage)
    assert after["actual_cost"] == "0.00"
    assert after["cost_index"]["value"] == {
        "is_computable": False,
        "value": None,
        "reason": "no_actual_cost",
    }


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock")
def test_the_abandonment_presents_the_last_marked_revision_at_the_next_reading(
    api: ContractClient, stage: Scene, project: Priced
) -> None:
    # « […] l'abandon de la révision en cours présente à la lecture suivante les indicateurs de
    # la dernière révision marquée au jour courant. » After `abandonRevision`, the indicators
    # without `revision_id` are computed on the last marked revision, with the actual cost of the
    # day, `context.revision_id` naming it.
    current = project.tree.revision["revision_id"]
    assert indicators(api, stage)["context"]["revision_id"] == current
    path = f"{project_path(stage)}/revisions/{current}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    abandoned = api.delete(f"{path}?lock_version={counter}", headers=stage.manager.headers)
    assert abandoned.status_code == 204, abandoned.text
    after = indicators(api, stage)
    assert after["context"]["revision_id"] == str(project.reference_id)
    assert (after["context"]["revision_status"], after["context"]["is_stored"]) == ("marked", False)
    assert after["actual_cost"] == "500.00"


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock", "project")
def test_two_readings_of_an_entry_absent_compute_it_both_and_answer_the_same(
    api: ContractClient, stage: Scene, queue: TaskQueue
) -> None:
    # Propre à l'US : deux lectures parallèles d'une entrée absente calculent toutes deux et
    # écrivent la même valeur, sans verrou (EP-10, « Le cache ») : the same answers, one entry.
    def reading(_: int) -> dict[str, Any]:
        return indicators(api, stage)

    with ThreadPoolExecutor(max_workers=2) as pool:
        both = list(pool.map(reading, range(2)))
    assert both[0] == both[1]
    assert len(entries(queue, stage)) == 1


# --- The cache emptied, the cache out of reach ------------------------------------------------


@pytest.fixture
def emptied_queue(redis_url: str, worker_id: str) -> Iterator[TaskQueue]:
    """Give a queue on a database of the Redis of the tests that no worker takes, emptied after.

    The workers take the databases that follow the one given, eight at most: the eighth after
    the worker's own is the test's, whichever worker it runs on, and ``FLUSHDB`` empties nothing
    another test reads. That holds for eight processes at most, as the ``Makefile`` runs them
    (``--maxprocesses``): beyond, the database emptied could be a worker's own, so the test fails
    rather than empty it.
    """
    rank = int(worker_id.removeprefix("gw")) if worker_id != "master" else 0
    if rank >= WORKERS:
        pytest.fail(
            f"worker {worker_id} would empty the database of another worker: this test is for "
            f"{WORKERS} processes at most (-n {WORKERS} or fewer)",
            pytrace=False,
        )
    parts = urlsplit(redis_url)
    index = (int(parts.path.strip("/") or 0) + WORKERS) % REDIS_DATABASES
    opened = TaskQueue.connect(urlunsplit(parts._replace(path=f"/{index}")), timeout=WORKER_TIMEOUT)
    yield opened
    flush(opened)
    opened.close()


def flush(queue: TaskQueue) -> None:
    """Empty the database of Redis of a queue, as ``FLUSHDB`` does."""
    keyed(queue).flushdb()


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("project")
def test_after_the_cache_is_emptied_every_value_is_computed_again_and_the_same(
    serve: Serve, emptied_queue: TaskQueue, stage: Scene, clock: Clock, lot: str
) -> None:
    # « Après vidage complet du cache, toutes les valeurs sont recalculées et identiques à celles
    # qu'il portait. » The four readings, read, the cache emptied by `FLUSHDB` of the base of the
    # test, read again: the same answers, `computed_at` aside.
    emptied = IndicatorsCache.of(emptied_queue, TTL)
    served = serve(emptied_queue, emptied)
    paths = [*READINGS, f"indicators?scope={lot}", "indicators/index-history?scope=unassigned"]
    try:
        first = {path: read(served, stage, path) for path in paths}
        assert entries(emptied_queue, stage) != []
        flush(emptied_queue)
        assert entries(emptied_queue, stage) == []
        clock(NOON)
        again = {path: read(served, stage, path) for path in paths}
        assert entries(emptied_queue, stage) != []
    finally:
        emptied.close()
    assert {each["context"]["computed_at"] for each in again.values()} == {"2026-11-13T12:00:00Z"}
    assert without_instants(again) == without_instants(first)


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock")
def test_a_redis_out_of_reach_lets_every_reading_and_an_entry_through(
    serve: Serve, api: ContractClient, stage: Scene, project: Priced
) -> None:
    # « L'indisponibilité du cache des indicateurs n'empêche aucune lecture ni aucune saisie faite
    # par l'API […] » Redis pointed at an address that does not answer: `getProjectIndicators`
    # answers 200 with the computation, within the delay of a request, logged once; and an entry
    # of a line answers 200. The session of the front is EP-03's (US-0340).
    computed = {path: read(api, stage, path) for path in READINGS}
    closed = TaskQueue.connect(CLOSED_PORT, timeout=WORKER_TIMEOUT)
    unreachable = IndicatorsCache.of(closed, TTL)
    cut_off = serve(closed, unreachable)
    try:
        with capture_logs() as records:
            started = time.monotonic()
            found = {path: read(cut_off, stage, path) for path in READINGS}
            elapsed = time.monotonic() - started
            entered = remaining_sent(cut_off, project, "900")
            after = indicators(cut_off, stage)
    finally:
        unreachable.close()
        closed.close()
    assert found == computed
    assert elapsed < len(READINGS) * 2 * DEPOSIT_TIMEOUT
    assert entered.status_code == 200, entered.text
    assert after["remaining"] == "900.00"
    unavailable = [r for r in records if r["event"] == "indicators.cache_unavailable"]
    assert [r["cause"] for r in unavailable] == ["ConnectionError"]


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock", "project")
def test_a_reading_with_a_redis_out_of_reach_computes_the_scope_asked_alone(
    serve: Serve,
    stage: Scene,
    lot: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Propre à l'US : un Redis en panne n'est pas un manque — l'entrée ne s'écrira pas —, la lecture
    # ne calcule que la maille demandée, non toutes celles du projet et leurs trois courbes.
    computed: list[int] = []
    day_entry = caching.day_entry

    scopes_of = inspect.signature(day_entry, annotation_format=Format.FORWARDREF)

    def counting(*args: Any, **named: Any) -> Any:
        computed.append(len(scopes_of.bind(*args, **named).arguments["scopes"]))
        return day_entry(*args, **named)

    monkeypatch.setattr(caching, "day_entry", counting)
    closed = TaskQueue.connect(CLOSED_PORT, timeout=WORKER_TIMEOUT)
    unreachable = IndicatorsCache.of(closed, TTL)
    try:
        cut_off = serve(closed, unreachable)
        for path in ("indicators", f"indicators?scope={lot}", "indicators/cost-curve"):
            computed.clear()
            assert read(cut_off, stage, path)
            assert computed == [1], path
    finally:
        unreachable.close()
        closed.close()


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock", "project")
@pytest.mark.parametrize("damage", ["scope_without_project", "scope_not_a_document"])
def test_an_entry_readable_but_incomplete_is_a_miss_computed_and_written_again(
    api: ContractClient, stage: Scene, queue: TaskQueue, damage: str
) -> None:
    # Propre à l'US : une entrée lisible mais mal formée (une maille sans `project`, ou qui n'est
    # pas un document) se traite comme un manque : 200, valeur recalculée, entrée réécrite.
    first = indicators(api, stage)
    (key,) = entries(queue, stage)
    kept = entry(queue, stage)
    scope = next(iter(kept["scopes"]))
    kept["scopes"][scope] = {} if damage == "scope_without_project" else "broken"
    keyed(queue).set(key, json.dumps(kept), ex=TTL)
    assert indicators(api, stage) == first
    assert entry(queue, stage) != kept
    assert "project" in entry(queue, stage)["scopes"][scope]


# --- The key ------------------------------------------------------------------------------------


def key_of(stage: Scene, at: datetime = MORNING) -> str:
    """Give the key of the entry of the day of the project of the stage, as a reading reads it."""
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        reading = day_reading(session, project_id, IndicatorsReading(PROJECT, at))
        assert reading is not None
        subprojects = subproject_ids(session, project_id)
        return day_key(session, reading.basis, reading.context, subprojects)


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("project")
def test_the_key_is_read_again_the_same_while_nothing_changes(stage: Scene) -> None:
    # Propre à l'US : l'empreinte est lue à chaque consultation ; deux lectures sans écriture entre
    # elles désignent la même entrée, à toute heure du jour, et elle porte l'identifiant du projet.
    key = key_of(stage)
    assert key == key_of(stage, NOON)
    project_id, fingerprint = key.split(":")
    assert project_id == stage.project["project_id"]
    assert len(fingerprint) == 32


@pytest.mark.requirement("WF-DAT-0130-A")
def test_every_write_the_indicators_of_the_day_depend_on_changes_the_key(
    api: ContractClient, stage: Scene, project: Priced
) -> None:
    # Propre à l'US : toute écriture dont une entrée dépend change sa clé — une saisie de ligne, de
    # tâche, l'application d'un import, l'exclusion, la création d'un sous-projet, le jour suivant,
    # le marquage, le compteur du projet — sans qu'aucun de leurs chemins n'appelle le cache.
    project_id = UUID(stage.project["project_id"])
    seen = [key_of(stage)]

    def changed() -> None:
        key = key_of(stage)
        assert key not in seen
        seen.append(key)

    reestimated(project.tree, "Câblage", "50")
    changed()
    completed(project.tree, "Câblage", DAY)
    changed()
    load_import(stage, project_id, [dated("FA-2", None, "70.00", DAY)], at=MORNING)
    changed()
    exclude(api, stage, "FA-2")
    changed()
    subproject(api, stage, "10002", "Lot 10002")
    changed()
    assert key_of(stage, MORNING + timedelta(days=1)) not in seen
    marked(stage, project.tree.revision, "Revue")
    changed()
    # A designation writes the reference and the counter of the project; In progress, the counter
    # alone moves here, by a change of the project. The designation of the reference itself is
    # refused in the course of a project (409 `reference_correctable`) and advances this same
    # counter: it is by the counter that « la désignation change la clé » is held.
    path = project_path(stage)
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    sent = {"code": "PRJ-1720", "lock_version": counter}
    renamed = api.patch(path, headers=stage.manager.headers, json=sent)
    assert renamed.status_code == 200, renamed.text
    changed()


class Instants(NamedTuple):
    """The counts and the last instants of the stamps of a project, the imports apart."""

    content: tuple[object, ...]
    lines: tuple[object, ...]
    costs: tuple[object, ...]
    imports: int


def instants(stage: Scene) -> Instants:
    """Give the counts and the last instants of the stamps of the project of the stage.

    The number of the imports comes last, apart: it is the one an import changes.
    """
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        reading = day_reading(session, project_id, IndicatorsReading(PROJECT, MORNING))
        assert reading is not None
        revision_id = reading.basis.revision_id
        content = revision_content_stamp(session, project_id, revision_id)
        lines = lines_stamp(session, project_id, revision_id)
        costs = costs_stamp(session, project_id)
        return Instants(
            (content.nodes, content.tasks, content.links, content.updated_at),
            (lines.count, lines.updated_at),
            (costs.imported_at, costs.lines, costs.updated_at, costs.versions),
            costs.imports,
        )


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_write_that_started_before_the_last_one_committed_still_changes_the_key(
    stage: Scene, project: Priced, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Propre à l'US : une écriture A commencée (t0) avant qu'une écriture B d'un autre nœud
    # (t1 > t0) ne valide porte l'instant t0 ; le maximum des instants reste t1 et les comptes ne
    # bougent pas, mais la clé lue après A n'est plus celle sous laquelle un lecteur a écrit
    # l'entrée entre B et A : le compteur de la structure principale, que chaque écriture de
    # l'arbre avance sous son verrou, et le nombre des imports avancent dans l'ordre des
    # validations.
    project_id = UUID(stage.project["project_id"])
    started = utc_now() - timedelta(minutes=10)
    project.tree.changed(task_named(project.tree, "Études"), label="Études préalables")
    read_between = key_of(stage)
    held = instants(stage)
    monkeypatch.setattr("waterfall.api.nodes.utc_now", lambda: started)
    reestimated(project.tree, "Câblage", "60")
    assert instants(stage) == held
    after_line = key_of(stage)
    assert after_line != read_between
    progressed(project.tree, task_named(project.tree, "Câblage"), "started", DAY)
    assert instants(stage) == held
    after_state = key_of(stage)
    assert after_state not in {read_between, after_line}
    load_import(stage, project_id, [], at=AT - timedelta(days=1))
    after_import = instants(stage)
    assert after_import[:3] == held[:3]
    assert after_import.imports == held.imports + 1
    assert key_of(stage) not in {read_between, after_line, after_state}


def line_id(api: ContractClient, stage: Scene, number: str) -> str:
    """Give the identifier of the line of cost of a document of the project of the stage."""
    (line,) = [
        each
        for each in read(api, stage, "actual-costs")["items"]
        if each["document_number"] == number
    ]
    return str(line["cost_line_id"])


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock", "project")
def test_two_exclusions_of_one_project_each_change_the_key_whatever_their_instants(
    api: ContractClient, stage: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Propre à l'US (#3629) : l'exclusion d'une ligne de coût avance le compteur de la ligne sous le
    # verrou du projet, que la clé lit. Deux exclusions commencées avant la dernière écriture
    # validée portent un instant plus ancien que le maximum, qui ne bouge pas : seul le compteur
    # change la clé, à chacune, et à la réintégration. « Concurrent » s'émule par une écriture dont
    # l'instant est plus ancien que le dernier `updated_at` validé (le verrou du projet sérialise
    # les transactions : deux écritures ne se chevauchent jamais). Après chacune, la lecture, dont
    # l'entrée est déjà dans Redis avant l'exclusion, rend les coûts recalculés, non l'entrée
    # précédente.
    project_id = UUID(stage.project["project_id"])
    # FA-3 stays tracked, at the last instant: the maximum is its, whatever the exclusions write.
    lines = [
        dated("FA-1", None, "10.00", DAY),
        dated("FA-2", None, "20.00", DAY),
        dated("FA-3", None, "30.00", DAY),
    ]
    load_import(stage, project_id, lines, at=MORNING)
    seen = [key_of(stage)]
    held = instants(stage)
    costs = [indicators(api, stage)["actual_cost"]]
    monkeypatch.setattr("waterfall.api.actual_costs.utc_now", lambda: MORNING - timedelta(hours=1))
    for number in ("FA-1", "FA-2"):
        exclude(api, stage, number)
        # The entry of the key before the exclusion is in Redis: it is not the one served.
        costs.append(indicators(api, stage)["actual_cost"])
        assert costs[-1] != costs[-2]
        key = key_of(stage)
        assert key not in seen
        seen.append(key)
        # Neither the counts nor the last instant moved: the counter alone did.
        now = instants(stage)
        assert now[:2] == held[:2]
        assert now.costs[:3] == held.costs[:3]
        assert now.costs[3] == cast("int", held.costs[3]) + len(seen) - 1
    path = f"{project_path(stage)}/actual-costs/{line_id(api, stage, 'FA-1')}/tracked-scope"
    answer = api.put(path, headers=stage.manager.headers, json={"is_in_tracked_scope": True})
    assert answer.status_code == 200, answer.text
    assert key_of(stage) not in seen
    assert indicators(api, stage)["actual_cost"] not in costs[1:]


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("project")
def test_the_write_of_a_held_line_and_an_imputation_advance_its_counter_a_new_line_starts_at_zero(
    api: ContractClient, stage: Scene
) -> None:
    # Propre à l'US (#3629) : une ligne neuve commence à 0 ; chaque écriture d'une ligne que
    # l'import détient déjà, puis l'imputation à un sous-projet créé, avancent son compteur.
    project_id = UUID(stage.project["project_id"])

    def versions() -> int:
        with stage.database.transaction() as session:
            return costs_stamp(session, project_id).versions

    before = versions()
    load_import(stage, project_id, [dated("LC-1", None, "10.00", DAY)], at=MORNING)
    assert versions() == before
    load_import(stage, project_id, [dated("LC-1", None, "11.00", DAY)], at=MORNING)
    assert versions() == before + 1
    load_import(stage, project_id, [dated("LC-3", "10077", "5.00", DAY)], at=MORNING)
    assert versions() == before + 1
    subproject(api, stage, "10077", "Lot 10077")
    assert versions() == before + 2


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("clock")
def test_a_marked_revision_is_never_read_in_the_cache(
    api: ContractClient, stage: Scene, queue: TaskQueue, project: Priced
) -> None:
    # Propre à l'US : aucune lecture d'une révision marquée ne passe par le cache — nommée ou à
    # une date, rien n'y est lu ni écrit pour elle.
    at = marked(stage, project.tree.revision, "Revue")
    revision = project.tree.revision["revision_id"]
    for query in (f"revision_id={revision}", f"as_of={current_day(at).isoformat()}"):
        for path in ("indicators", "indicators/cost-curve", "indicators/earned-value-curves"):
            found = read(api, stage, f"{path}?{query}")
            assert found["context"]["is_stored"] is True
    assert entries(queue, stage) == []
