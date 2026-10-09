# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API process: it states its version, refuses to start without its secrets, and serves."""

import json
from typing import Any

import pytest
from fastapi import FastAPI

import waterfall
from waterfall.api import main as api_main


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
    assert captured.err.startswith("usage: waterfall-api [--version]\n")
    assert arguments[0] in captured.err
