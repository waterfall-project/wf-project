# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API process: it states its version, refuses to start without its secrets, and serves.

It serves on the number of processes its setting says (US-2230), each building its application by
the factory, which opens the services of the process and closes them when it stops.
"""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import waterfall
from waterfall import bootstrap
from waterfall.api import main as api_main
from waterfall.platform.cache import PREFIX, IndicatorsCache
from waterfall.platform.database import Database
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.metrics import MULTIPROCESS, Capacities
from waterfall.platform.queue import TaskQueue
from waterfall.platform.storage import Bucket

if TYPE_CHECKING:
    from collections.abc import Callable

    from waterfall.api.authentication import Services
    from waterfall.api.system import Observed
    from waterfall.platform.settings import ServiceSettings


def test_the_version_is_stated_without_starting_anything(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert api_main.main(["--version"]) == 0
    assert capsys.readouterr().out == f"waterfall-api {waterfall.__version__}\n"


def test_without_its_secrets_the_process_returns_failure_and_names_them(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WATERFALL_DATABASE_URL", raising=False)
    monkeypatch.delenv("WATERFALL_REDIS_URL", raising=False)
    assert api_main.main([]) == 2
    assert "WATERFALL_DATABASE_URL" in capsys.readouterr().err


def served_by(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Keep what the process asks uvicorn to serve, instead of serving it."""
    served: dict[str, Any] = {}

    def serve(app: str, **options: Any) -> None:
        served.update(app=app, **options)

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    return served


@pytest.mark.usefixtures("platform_environment", "logs")
def test_with_its_secrets_the_process_serves_the_application_on_its_address(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_PORT", "8123")
    served = served_by(monkeypatch)
    assert api_main.main([]) == 0
    # Built by its factory, once per process: one by default, the workstation and the tests' own.
    assert (served["app"], served["factory"]) == ("waterfall.api.main:application", True)
    assert (served["host"], served["port"], served["workers"]) == ("127.0.0.1", 8123, 1)
    (line,) = capsys.readouterr().err.splitlines()
    record = json.loads(line)
    assert record["event"] == "service.starting"
    assert (record["version"], record["port"], record["processes"]) == (
        waterfall.__version__,
        8123,
        1,
    )


@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_number_of_processes_is_a_setting_of_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    # Proper to US-2230: « un réglage de l'API dit le nombre de ses processus ».
    monkeypatch.setenv("WATERFALL_API_PROCESSES", "4")
    served = served_by(monkeypatch)
    assert api_main.main([]) == 0
    assert served["workers"] == 4


@pytest.mark.usefixtures("platform_environment")
@pytest.mark.parametrize("processes", ["0", "-1", "two"])
def test_a_number_of_processes_that_is_no_whole_number_above_zero_stops_the_service(
    processes: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WATERFALL_API_PROCESSES", processes)
    served = served_by(monkeypatch)
    assert api_main.main([]) == 2
    assert "WATERFALL_API_PROCESSES" in capsys.readouterr().err
    assert served == {}


def closings(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record the closing of each service a process opens, instead of closing it."""
    closed: list[str] = []

    def closing(name: str) -> Callable[[object], None]:
        def close(_: object) -> None:
            closed.append(name)

        return close

    monkeypatch.setattr(Database, "dispose", closing("database"))
    monkeypatch.setattr(Keycloak, "close", closing("keycloak"))
    monkeypatch.setattr(TaskQueue, "close", closing("redis"))
    monkeypatch.setattr(IndicatorsCache, "close", closing("cache"))
    of_backups = Bucket.of_backups

    def backups(settings: ServiceSettings) -> Bucket:
        bucket = of_backups(settings)
        monkeypatch.setattr(bucket.client, "close", lambda: closed.append("storage"))
        return bucket

    monkeypatch.setattr(api_main.Bucket, "of_backups", staticmethod(backups))
    return closed


@pytest.mark.usefixtures("platform_environment", "logs")
def test_each_process_closes_the_services_it_opened_when_it_stops(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    closed = closings(monkeypatch)
    app = api_main.application()
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert closed == []
    # The last opened first: nothing closed is still used by what was opened after it. The
    # connections of the observation, opened by the application, close before all.
    assert closed == ["database", "cache", "storage", "redis", "keycloak", "database"]
    events = [json.loads(line)["event"] for line in capsys.readouterr().err.splitlines()]
    assert events[-1] == "service.stopped"


@pytest.mark.usefixtures("platform_environment")
def test_a_service_that_cannot_be_opened_closes_those_opened_before_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = closings(monkeypatch)

    def unreachable(*_: object, **__: object) -> TaskQueue:
        message = "Redis is no address"
        raise ValueError(message)

    monkeypatch.setattr(api_main.TaskQueue, "connect", unreachable)
    with pytest.raises(ValueError, match="Redis is no address"):
        api_main.application()
    assert closed == ["keycloak", "database"]


@pytest.mark.parametrize("arguments", [["--versoin"], ["--version", "--extra"], ["serve"]])
def test_any_argument_but_version_is_refused_with_a_usage(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert api_main.main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(
        "usage: waterfall-api [--version | install | load-witness"
        " | load-reference [--projects N]]\n"
    )
    assert arguments[0] in captured.err


def test_the_command_of_the_api_serves_it_or_bootstraps_the_installation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # ``waterfall-api`` starts in the bootstrap, which passes anything but ``install`` on.
    assert bootstrap.main(["--version"]) == 0
    assert capsys.readouterr().out == f"waterfall-api {waterfall.__version__}\n"


@pytest.mark.usefixtures("platform_environment")
def test_the_bootstrap_without_its_settings_returns_failure_and_names_them(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The settings of the API do not suffice: the bootstrap needs the client of the installation,
    # the address of its administrator and its language (US-0420).
    missing = (
        "WATERFALL_INSTALLATION_CLIENT_SECRET",
        "WATERFALL_ADMIN_EMAIL",
        "WATERFALL_DEFAULT_LANGUAGE",
    )
    for variable in missing:
        monkeypatch.delenv(variable, raising=False)
    assert bootstrap.main(["install"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    for variable in missing:
        assert f"{variable}: is missing" in captured.err


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_validity_the_environment_sets_is_that_of_an_entry_and_the_cache_closes_at_the_end(
    monkeypatch: pytest.MonkeyPatch, redis_url: str
) -> None:
    # Propre à l'US : la durée de validité est `WATERFALL_INDICATORS_CACHE_TTL`, lue par les
    # réglages de l'API : from the variable to the `ex` of the entry the cache of the process
    # writes; its pool, its own, is released when the process stops (#3547).
    monkeypatch.setenv("WATERFALL_REDIS_URL", redis_url)
    monkeypatch.setenv("WATERFALL_INDICATORS_CACHE_TTL", "137")
    key = f"{uuid4()}:{uuid4().hex}"
    closed: list[IndicatorsCache] = []
    close = IndicatorsCache.close

    def closing(cache: IndicatorsCache) -> None:
        closed.append(cache)
        close(cache)

    monkeypatch.setattr(IndicatorsCache, "close", closing)
    app = api_main.application()
    with TestClient(app):
        cache = cast("Services", app.state.services).indicators_cache
        assert cache is not None
        cache.write(key, "{}")
        seconds = int(str(cache.client.ttl(PREFIX + key)))
        cache.client.delete(PREFIX + key)
        assert closed == []
    assert 130 < seconds <= 137
    assert closed == [cache]


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.usefixtures("platform_environment")
@pytest.mark.parametrize("value", ["0", "-5", "dix"])
def test_a_validity_that_is_not_a_whole_number_above_zero_stops_the_start(
    value: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The validity of an entry is a whole number of seconds above zero: anything else is refused
    # at the start, the variable named, before anything is reached (#3547).
    monkeypatch.setenv("WATERFALL_INDICATORS_CACHE_TTL", value)

    def serve(*_: Any, **__: Any) -> None:
        pytest.fail("the service started")

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    assert api_main.main([]) == 2
    assert "WATERFALL_INDICATORS_CACHE_TTL" in capsys.readouterr().err


@pytest.mark.usefixtures("platform_environment", "logs")
@pytest.mark.parametrize(("processes", "shared"), [("1", False), ("3", True)])
def test_several_processes_share_their_counters_in_a_folder_removed_after_them(
    processes: str, shared: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proper to US-2870: the metrics of the API are aggregated between its processes, which write
    # their counters in a folder they share while they serve; one process keeps them.
    monkeypatch.setenv("WATERFALL_API_PROCESSES", processes)
    monkeypatch.delenv(MULTIPROCESS, raising=False)
    folders: list[str | None] = []

    def serve(*_: Any, **__: Any) -> None:
        folder = os.environ.get(MULTIPROCESS)
        assert folder is None or Path(folder).is_dir()
        folders.append(folder)

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    assert api_main.main([]) == 0
    (folder,) = folders
    assert (folder is not None) == shared
    assert MULTIPROCESS not in os.environ
    assert folder is None or not Path(folder).exists()


@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_capacities_the_deployment_declares_are_those_the_metrics_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2870: the space available is the capacity the deployment declares less the
    # space used (EP-13, "La supervision"), a setting of the API in bytes.
    monkeypatch.setenv("WATERFALL_DATABASE_CAPACITY_BYTES", "5000000000")
    monkeypatch.setenv("WATERFALL_STORAGE_CAPACITY_BYTES", "7000000000")
    app = api_main.application()
    with TestClient(app):
        capacities = cast("Observed", app.state.observed).state.capacities
    assert capacities == Capacities(database=5_000_000_000, object_storage=7_000_000_000)


@pytest.mark.usefixtures("platform_environment")
@pytest.mark.parametrize("variable", ["DATABASE_CAPACITY_BYTES", "STORAGE_CAPACITY_BYTES"])
def test_a_capacity_that_is_no_whole_number_above_zero_stops_the_start(
    variable: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proper to US-2870: a capacity is a whole number of bytes above zero; anything else stops the
    # start, the variable named.
    monkeypatch.setenv(f"WATERFALL_{variable}", "0")

    def serve(*_: Any, **__: Any) -> None:
        pytest.fail("the service started")

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    assert api_main.main([]) == 2
    assert f"WATERFALL_{variable}" in capsys.readouterr().err
