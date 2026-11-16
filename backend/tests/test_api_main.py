# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API process: it states its version, refuses to start without its secrets, and serves."""

import json
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import pytest
from fastapi import FastAPI

import waterfall
from waterfall import bootstrap
from waterfall.api import main as api_main
from waterfall.platform.cache import PREFIX, IndicatorsCache

if TYPE_CHECKING:
    from waterfall.api.authentication import Services


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


@pytest.mark.usefixtures("platform_environment", "logs")
def test_with_its_secrets_the_process_serves_the_application_on_its_address(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_PORT", "8123")
    served: dict[str, Any] = {}

    def serve(app: FastAPI, **options: Any) -> None:
        served.update(app=app, **options)

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    assert api_main.main([]) == 0
    assert isinstance(served["app"], FastAPI)
    assert (served["host"], served["port"]) == ("127.0.0.1", 8123)
    (line,) = capsys.readouterr().err.splitlines()
    record = json.loads(line)
    assert record["event"] == "service.starting"
    assert (record["version"], record["port"]) == (waterfall.__version__, 8123)


@pytest.mark.parametrize("arguments", [["--versoin"], ["--version", "--extra"], ["serve"]])
def test_any_argument_but_version_is_refused_with_a_usage(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert api_main.main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("usage: waterfall-api [--version | install | load-witness]\n")
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
    # writes; its pool, its own, is released when the service stops (#3547).
    monkeypatch.setenv("WATERFALL_REDIS_URL", redis_url)
    monkeypatch.setenv("WATERFALL_INDICATORS_CACHE_TTL", "137")
    key = f"{uuid4()}:{uuid4().hex}"
    validity: list[int] = []
    closed: list[IndicatorsCache] = []
    close = IndicatorsCache.close

    def closing(cache: IndicatorsCache) -> None:
        closed.append(cache)
        close(cache)

    def serve(app: FastAPI, **_: Any) -> None:
        cache = cast("Services", app.state.services).indicators_cache
        assert cache is not None
        cache.write(key, "{}")
        validity.append(int(str(cache.client.ttl(PREFIX + key))))
        cache.client.delete(PREFIX + key)

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    monkeypatch.setattr(IndicatorsCache, "close", closing)
    assert api_main.main([]) == 0
    (seconds,) = validity
    assert 130 < seconds <= 137
    assert len(closed) == 1


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
