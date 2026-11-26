# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The components Waterfall requires: the check of a deployment, and the refusal at the start.

The command ``waterfall-check-components`` refuses a PostgreSQL, a Redis or a Keycloak that does not
fit, before the migrations; the API, the worker and the service of the restoration refuse to start
on a PostgreSQL of another major version than 18, or set for fewer than 1 024 locks per
transaction (WF-CMP-0020-A, #3964, #4963).
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, Any, ClassVar, override

import pytest
from test_api_main import served_by
from test_api_processes import free_port

import waterfall
from waterfall.api import main as api_main
from waterfall.platform import components, components_check
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.settings import ComponentsSettings, load_components_settings
from waterfall.restore import main as restore_main
from waterfall.worker import main as worker_main

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping
    from pathlib import Path

NAME = "waterfall-check-components"
EIGHTEEN = 180_001
LOCKS = components.POSTGRESQL_LOCKS
CHECKED = ("DATABASE_URL", "REDIS_URL", "KEYCLOAK_ADDRESS", "SERVICE_CLIENT_SECRET")


def server_state(version_number: int, locks: int) -> Callable[[Database], tuple[int, int]]:
    """Give a PostgreSQL that announces what is given, in place of the one the test reads."""

    def state(database: Database) -> tuple[int, int]:
        del database
        return version_number, locks

    return state


# --- The rules -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.parametrize(
    ("version_number", "locks", "said"),
    [
        (170_009, LOCKS, "PostgreSQL 17 is not the major version 18"),
        (190_000, LOCKS, "PostgreSQL 19 is not the major version 18"),
        (EIGHTEEN, 64, "set for 64 locks per transaction"),
        (EIGHTEEN, LOCKS - 1, "set for 1023 locks per transaction"),
    ],
)
def test_a_postgresql_of_another_major_version_or_set_for_fewer_locks_is_refused_naming_why(
    version_number: int, locks: int, said: str
) -> None:
    # « Le démarrage échoue en le disant si le serveur PostgreSQL est d'une autre version majeure
    # que la 18, ou réglé pour moins de 1 024 verrous par transaction. »
    (fault,) = components.database_faults(version_number, locks)
    assert said in fault


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.parametrize(("version_number", "locks"), [(EIGHTEEN, LOCKS), (180_005, 4096)])
def test_a_postgresql_18_set_for_at_least_1024_locks_fits(version_number: int, locks: int) -> None:
    assert components.database_faults(version_number, locks) == []


@pytest.mark.requirement("WF-CMP-0020-A")
def test_both_faults_of_a_postgresql_are_said_together() -> None:
    assert len(components.database_faults(170_000, 64)) == 2


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.parametrize(
    ("information", "said"),
    [
        ({"redis_version": "7.4.2"}, "Redis 7.4.2 is older than the version 8"),
        ({"redis_version": "6.0.0", "cluster_enabled": 0}, "Redis 6.0.0 is older"),
        ({}, "not announced"),
        ({"redis_version": "unstable"}, "cannot be read"),
    ],
)
def test_a_redis_older_than_8_or_that_says_nothing_readable_is_refused(
    information: dict[str, Any], said: str
) -> None:
    # « Le déploiement échoue en le disant si un composant est d'une version antérieure à celle
    # exigée. »
    (fault,) = components.redis_faults(information)
    assert said in fault


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.parametrize(
    "information",
    [{"redis_version": "8.0.1", "cluster_enabled": 0}, {"redis_version": "9.1.0"}],
)
def test_a_standalone_redis_from_8_on_fits(information: dict[str, Any]) -> None:
    assert components.redis_faults(information) == []


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.parametrize("enabled", [1, "1"])
def test_a_redis_in_cluster_mode_is_refused_though_its_version_fits(enabled: object) -> None:
    # #4963: Redis Cluster is not supported, the clients of Waterfall do not speak it.
    (fault,) = components.redis_faults({"redis_version": "8.2.0", "cluster_enabled": enabled})
    assert "cluster mode (cluster_enabled:1)" in fault
    assert "does not support" in fault


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.parametrize(
    ("version", "fits"),
    [("25.0.6", False), ("26.0.0", True), ("26.4.2", True), ("27.1.0", True), (None, False)],
)
def test_a_keycloak_older_than_26_or_that_announces_no_version_is_refused(
    version: str | None, fits: bool
) -> None:
    assert (components.keycloak_faults(version) == []) is fits


# --- The refusal at the start of each process ----------------------------------------------------


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_postgresql_of_the_tests_is_accepted_by_the_start_of_a_process(
    database: Database,
) -> None:
    # The server of the repository is a PostgreSQL 18 set for the locks Waterfall requires.
    assert components.database_accepted(database, "waterfall-test")


@pytest.mark.requirement("WF-CMP-0020-A")
def test_a_server_out_of_reach_is_not_judged_and_the_process_goes_on(
    capsys: pytest.CaptureFixture[str],
) -> None:
    nowhere = Database(create_database_engine("postgresql://nobody:secret@127.0.0.1:9/none"))
    try:
        assert components.database_accepted(nowhere, "waterfall-test")
    finally:
        nowhere.dispose()
    assert capsys.readouterr().err == ""


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("platform_environment", "logs")
@pytest.mark.parametrize(
    ("version_number", "locks", "said"),
    [(170_000, LOCKS, "PostgreSQL 17"), (EIGHTEEN, 256, "256 locks per transaction")],
)
def test_the_api_refuses_to_start_on_a_postgresql_that_does_not_fit_and_says_why(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    version_number: int,
    locks: int,
    said: str,
) -> None:
    monkeypatch.setattr(components, "database_state", server_state(version_number, locks))
    served = served_by(monkeypatch)
    assert api_main.main([]) == 1
    assert served == {}
    error = capsys.readouterr().err
    assert error.splitlines()[-1].startswith("waterfall-api: ")
    assert said in error


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("platform_environment", "logs")
@pytest.mark.parametrize(
    ("version_number", "locks", "said"),
    [(190_000, LOCKS, "PostgreSQL 19"), (EIGHTEEN, 64, "64 locks per transaction")],
)
def test_the_worker_refuses_to_start_on_a_postgresql_that_does_not_fit_and_says_why(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    version_number: int,
    locks: int,
    said: str,
) -> None:
    monkeypatch.setenv("WATERFALL_METRICS_PORT", str(free_port()))
    monkeypatch.setattr(components, "database_state", server_state(version_number, locks))
    served: list[object] = []
    monkeypatch.setattr(worker_main, "serve", served.append)
    assert worker_main.main([]) == 1
    assert served == []
    error = capsys.readouterr().err
    assert error.splitlines()[-1].startswith("waterfall-worker: ")
    assert said in error


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("platform_environment", "logs")
@pytest.mark.parametrize(
    ("server", "said"),
    [((170_000, LOCKS), "PostgreSQL 17"), ((EIGHTEEN, 100), "100 locks per transaction")],
)
def test_the_service_of_the_restoration_refuses_to_start_on_a_postgresql_that_does_not_fit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    server: tuple[int, int],
    said: str,
) -> None:
    monkeypatch.setenv("WATERFALL_INSTALLATION_CLIENT_SECRET", "installation-secret")
    monkeypatch.setenv("WATERFALL_REALM_REQUESTS", str(tmp_path))
    monkeypatch.setattr(components, "database_state", server_state(*server))
    served: list[object] = []
    monkeypatch.setattr(restore_main, "serve", served.append)
    assert restore_main.main([]) == 1
    assert served == []
    error = capsys.readouterr().err
    assert error.splitlines()[-1].startswith("waterfall-restore: ")
    assert said in error


# --- The command that checks a deployment -----------------------------------------------------


class Keycloak(BaseHTTPRequestHandler):
    """A Keycloak that gives a token to the service account of its realm, and its version."""

    version: str | None = "26.4.2"
    document: Any = None
    phrase = "service-phrase"
    asked: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        self.asked.append(f"POST {self.path} {body}")
        granted = f"client_secret={self.phrase}" in body
        token = {"access_token": "token", "expires_in": 300}
        self._answer(200 if granted else 401, token if granted else {})

    def do_GET(self) -> None:
        self.asked.append(f"GET {self.path} {self.headers.get('Authorization')}")
        if self.headers.get("Authorization") != "Bearer token":
            self._answer(401, {})
            return
        if self.document is not None:
            self._answer(200, self.document)
            return
        self._answer(200, {} if self.version is None else {"version": self.version})

    def _answer(self, status: int, document: Any) -> None:
        body = json.dumps(document).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @override
    def log_message(self, format: str, *args: object) -> None:
        """Say nothing."""


@pytest.fixture
def keycloak() -> Iterator[str]:
    """Serve the Keycloak above on a loopback port; give its address."""
    Keycloak.version, Keycloak.asked, Keycloak.document = "26.4.2", [], None
    server = HTTPServer(("127.0.0.1", 0), Keycloak)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/auth"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def check_settings(
    monkeypatch: pytest.MonkeyPatch, process_database_url: str, redis_url: str, keycloak: str
) -> ComponentsSettings:
    """Give the command the PostgreSQL and the Redis of the tests, and the Keycloak above."""
    monkeypatch.setenv("WATERFALL_DATABASE_URL", process_database_url)
    monkeypatch.setenv("WATERFALL_REDIS_URL", redis_url)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_ADDRESS", keycloak)
    monkeypatch.setenv("WATERFALL_SERVICE_CLIENT_SECRET", Keycloak.phrase)
    return load_components_settings()


def test_the_command_states_its_version_without_checking_anything(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert components_check.main(["--version"]) == 0
    assert capsys.readouterr().out == f"{NAME} {waterfall.__version__}\n"


@pytest.mark.parametrize(
    "arguments",
    [["--now"], ["--component"], ["--component", "storage"], ["redis"], ["--component=redis"]],
)
def test_any_argument_but_the_version_and_the_components_is_refused(
    capsys: pytest.CaptureFixture[str], arguments: list[str]
) -> None:
    assert components_check.main(arguments) == 2
    assert capsys.readouterr().err.startswith(f"usage: {NAME} [--version | [--component ")


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_components_named_are_the_only_ones_checked_and_none_named_checks_every_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], process_database_url: str
) -> None:
    # At an installation the chart reaches PostgreSQL alone: its Redis and its Keycloak are not
    # there yet, and a check that went to them would fail an installation that is sound.
    monkeypatch.setenv("WATERFALL_DATABASE_URL", process_database_url)
    monkeypatch.setenv("WATERFALL_REDIS_URL", "redis://:secret-redis@127.0.0.1:9/0")
    monkeypatch.setenv("WATERFALL_KEYCLOAK_ADDRESS", "http://127.0.0.1:9/auth")
    monkeypatch.setenv("WATERFALL_SERVICE_CLIENT_SECRET", Keycloak.phrase)
    assert components_check.main(["--component", "postgresql"]) == 0
    said = capsys.readouterr()
    assert said.out.startswith(f"{NAME}: PostgreSQL 18 ")
    assert "Redis" not in said.out + said.err
    assert components_check.main(["--component", "redis", "--component", "keycloak"]) == 1
    error = capsys.readouterr().err
    assert "Redis does not answer" in error
    assert "Keycloak does not answer" in error
    assert "PostgreSQL" not in error
    assert components_check.main([]) == 1
    assert "PostgreSQL" not in capsys.readouterr().err


@pytest.mark.requirement("WF-SEC-0010-A")
def test_without_its_settings_the_command_returns_failure_and_names_them(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in CHECKED:
        monkeypatch.delenv(f"WATERFALL_{name}", raising=False)
    assert components_check.main([]) == 2
    said = capsys.readouterr().err
    for name in CHECKED:
        assert f"WATERFALL_{name}: is missing" in said


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_the_components_of_the_platform_of_the_tests_fit_and_the_command_says_what_it_read(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert components_check.main([]) == 0
    said = capsys.readouterr()
    assert said.err == ""
    assert "PostgreSQL 18" in said.out
    assert "Redis 8." in said.out
    assert "(standalone)" in said.out
    assert "Keycloak 26.4.2" in said.out
    assert Keycloak.phrase not in said.out


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_the_command_signs_in_as_the_service_account_to_read_the_version_from_the_extension() -> (
    None
):
    assert components_check.main([]) == 0
    token, version = Keycloak.asked
    assert token.startswith("POST /auth/realms/waterfall/protocol/openid-connect/token ")
    assert "grant_type=client_credentials" in token
    assert "client_id=waterfall-service" in token
    assert version == "GET /auth/realms/waterfall/server-version Bearer token"


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_deployment_on_a_keycloak_older_than_26_fails_saying_so(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # « Le déploiement échoue en le disant si un composant est d'une version antérieure à celle
    # exigée. »
    Keycloak.version = "25.0.6"
    assert components_check.main([]) == 1
    assert f"{NAME}: Keycloak 25.0.6 is older than the version 26" in capsys.readouterr().err


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_keycloak_that_announces_no_version_fails_saying_so(
    capsys: pytest.CaptureFixture[str],
) -> None:
    Keycloak.version = None
    assert components_check.main([]) == 1
    error = capsys.readouterr().err
    assert f"{NAME}: Keycloak does not answer as expected: IdentityProviderError" in error
    assert error.endswith("(WF-CMP-0020)\n")


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_keycloak_that_refuses_the_service_account_fails_saying_it_did_not_answer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WATERFALL_SERVICE_CLIENT_SECRET", "another-password")
    assert components_check.main([]) == 1
    error = capsys.readouterr().err
    assert "Keycloak does not answer as expected: IdentityProviderError" in error
    assert "another-password" not in error


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
@pytest.mark.parametrize("document", [["not", "an", "object"], {"version": 26}, 26])
def test_a_keycloak_whose_server_version_is_not_a_version_fails_saying_it_did_not_answer(
    capsys: pytest.CaptureFixture[str], document: object
) -> None:
    Keycloak.document = document
    assert components_check.main([]) == 1
    assert "Keycloak does not answer as expected" in capsys.readouterr().err


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_keycloak_out_of_reach_fails_saying_so_and_the_others_are_still_said(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WATERFALL_KEYCLOAK_ADDRESS", f"http://127.0.0.1:{free_port()}/auth")
    monkeypatch.setenv("WATERFALL_REDIS_URL", "gopher://nowhere:1")
    monkeypatch.setattr(components_check, "database_state", server_state(170_000, LOCKS))
    assert components_check.main([]) == 1
    error = capsys.readouterr().err
    assert "Keycloak does not answer as expected: UnavailableError (WF-CMP-0020)" in error
    assert "Redis does not answer" in error
    assert "PostgreSQL 17 is not" in error
    assert "Traceback" not in error


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_keycloak_that_fails_with_503_fails_saying_so_and_the_others_are_still_said(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unavailable_answer(self: Keycloak) -> None:
        self.send_response(503)
        self.send_header("Content-Length", "0")
        self.end_headers()

    monkeypatch.setattr(Keycloak, "do_POST", unavailable_answer)
    monkeypatch.setenv("WATERFALL_REDIS_URL", "gopher://nowhere:1")
    monkeypatch.setattr(components_check, "database_state", server_state(170_000, LOCKS))
    assert components_check.main([]) == 1
    error = capsys.readouterr().err
    assert "Keycloak does not answer as expected: UnavailableError (WF-CMP-0020)" in error
    assert "Redis does not answer" in error
    assert "PostgreSQL 17 is not" in error
    assert "Traceback" not in error


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_redis_address_of_an_unknown_scheme_fails_saying_so_not_by_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WATERFALL_REDIS_URL", "gopher://nowhere:1")
    assert components_check.main([]) == 1
    assert "Redis does not answer: ValueError (WF-CMP-0020)" in capsys.readouterr().err


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_database_address_that_cannot_be_read_fails_saying_so_not_by_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WATERFALL_DATABASE_URL", "not a url")
    assert components_check.main([]) == 1
    assert "PostgreSQL does not answer: ArgumentError (WF-CMP-0020)" in capsys.readouterr().err


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
@pytest.mark.parametrize(
    ("version_number", "locks", "said"),
    [(170_000, LOCKS, "PostgreSQL 17 is not"), (EIGHTEEN, 64, "64 locks per transaction")],
)
def test_a_deployment_on_a_postgresql_that_does_not_fit_fails_saying_so(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    version_number: int,
    locks: int,
    said: str,
) -> None:
    monkeypatch.setattr(components_check, "database_state", server_state(version_number, locks))
    assert components_check.main([]) == 1
    assert said in capsys.readouterr().err


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_a_deployment_on_a_redis_in_cluster_mode_fails_saying_so(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # #4963: the check refuses a Redis in cluster mode, even of a version that fits; it reads the
    # sections ``server`` and ``cluster`` of its ``INFO``.
    sections: dict[str, Mapping[str, object]] = {
        "server": {"redis_version": "8.2.0"},
        "cluster": {"cluster_enabled": 1},
    }

    class Cluster:
        def info(self, section: str) -> Mapping[str, object]:
            return sections[section]

        def close(self) -> None:
            return None

    def from_url(address: str, **options: object) -> Cluster:
        del address, options
        return Cluster()

    monkeypatch.setattr(components_check.redis, "from_url", from_url)
    assert components_check.main([]) == 1
    assert "cluster mode (cluster_enabled:1)" in capsys.readouterr().err


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("check_settings")
def test_every_component_that_does_not_fit_is_said_not_the_first_alone(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(components_check, "database_state", server_state(170_000, 64))
    Keycloak.version = "24.0.0"
    assert components_check.main([]) == 1
    said = capsys.readouterr().err.splitlines()
    assert len(said) == 3
    assert all(line.startswith(f"{NAME}: ") and line.endswith("(WF-CMP-0020)") for line in said)


@pytest.mark.requirement("WF-CMP-0020-A")
def test_a_redis_that_does_not_answer_fails_saying_so(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    process_database_url: str,
    keycloak: str,
) -> None:
    monkeypatch.setenv("WATERFALL_DATABASE_URL", process_database_url)
    monkeypatch.setenv("WATERFALL_REDIS_URL", "redis://:secret-redis@127.0.0.1:9/0")
    monkeypatch.setenv("WATERFALL_KEYCLOAK_ADDRESS", keycloak)
    monkeypatch.setenv("WATERFALL_SERVICE_CLIENT_SECRET", Keycloak.phrase)
    assert components_check.main([]) == 1
    error = capsys.readouterr().err
    assert f"{NAME}: Redis does not answer: ConnectionError" in error
    assert "secret-redis" not in error


@pytest.mark.requirement("WF-CMP-0020-A")
def test_a_postgresql_that_does_not_answer_fails_saying_so(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    redis_url: str,
    keycloak: str,
) -> None:
    monkeypatch.setenv("WATERFALL_DATABASE_URL", "postgresql://nobody:secret-pg@127.0.0.1:9/none")
    monkeypatch.setenv("WATERFALL_REDIS_URL", redis_url)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_ADDRESS", keycloak)
    monkeypatch.setenv("WATERFALL_SERVICE_CLIENT_SECRET", Keycloak.phrase)
    assert components_check.main([]) == 1
    error = capsys.readouterr().err
    assert f"{NAME}: PostgreSQL does not answer: OperationalError" in error
    assert "secret-pg" not in error
