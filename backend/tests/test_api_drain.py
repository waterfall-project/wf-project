# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The drain of an instance of the API being stopped: each answer closes its connection (US-2850).

Once the file the settings name exists — the chart writes it when the pod is ending —, the server
of the front drops each connection it kept to the instance once answered, and none is left open
when the server stops (#5020). That no request fails during an upgrade is tried on a cluster, by
``make chart-upgrade``.
"""

from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from waterfall.api import main as api_main
from waterfall.api.drain import IDLE_SECONDS, DrainMiddleware

if TYPE_CHECKING:
    from pathlib import Path

    from starlette.requests import Request

pytestmark = [pytest.mark.requirement("WF-EXP-0030-A"), pytest.mark.story("US-2850")]

DRAIN = 10
"""The seconds the chart waits once the pod is ending (``waterfall.drainSeconds``, tried by
``tools/tests/test_chartdrain.py``)."""


def served(flag: Path) -> TestClient:
    def answer(_: Request) -> PlainTextResponse:
        return PlainTextResponse("ok", headers={"X-Served": "yes"})

    app = Starlette(routes=[Route("/", answer)])
    return TestClient(DrainMiddleware(app, flag))


def test_before_the_drain_an_answer_keeps_its_connection(tmp_path: Path) -> None:
    answer = served(tmp_path / "draining").get("/")
    assert answer.status_code == 200
    assert "connection" not in answer.headers


def test_once_the_drain_has_begun_each_answer_closes_its_connection(tmp_path: Path) -> None:
    flag = tmp_path / "draining"
    client = served(flag)
    flag.touch()
    for _ in range(2):
        answer = client.get("/")
        assert answer.status_code == 200
        assert answer.headers["connection"] == "close"
        assert answer.headers["x-served"] == "yes"
        assert answer.text == "ok"


@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_api_closes_its_connections_once_the_file_its_settings_name_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flag = tmp_path / "draining"
    monkeypatch.setenv("WATERFALL_DRAIN_FILE", str(flag))
    with TestClient(api_main.application()) as client:
        assert "connection" not in client.get("/api/v1/health").headers
        flag.touch()
        assert client.get("/api/v1/health").headers["connection"] == "close"


@pytest.mark.usefixtures("platform_environment", "logs")
def test_without_the_setting_the_api_has_no_drain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WATERFALL_DRAIN_FILE", raising=False)
    app = api_main.application()
    assert all(middleware.cls is not DrainMiddleware for middleware in app.user_middleware)
    with TestClient(app) as client:
        assert "connection" not in client.get("/api/v1/health").headers


@pytest.mark.usefixtures("platform_environment", "logs")
def test_a_connection_idle_through_the_drain_is_closed_before_the_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # One that serves nothing once the drain has begun carries no answer to close it: the server
    # closes it idle, and must before the end of the wait, when the stop would close it at once.
    served: dict[str, Any] = {}

    def serve(app: str, **options: Any) -> None:
        served.update(app=app, **options)

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    assert api_main.main([]) == 0
    assert served["timeout_keep_alive"] == IDLE_SECONDS
    assert IDLE_SECONDS < DRAIN
