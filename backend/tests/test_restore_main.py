# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The command of the service of the restoration: it refuses to start without its secrets, runs."""

import json
import os
from typing import TYPE_CHECKING

import pytest

import waterfall
from waterfall.platform.database import Database
from waterfall.platform.queue import RESTORES, STREAM
from waterfall.platform.settings import (
    KeycloakSettings,
    RealmSettings,
    RestoreTestSettings,
    load_restore_test_settings,
    load_worker_settings,
)
from waterfall.restore import main as restore_main
from waterfall.restore.provider import Keycloak
from waterfall.restore.task import RestoreTask
from waterfall.restore.trial import Readiness, RestoreTrial
from waterfall.worker.backup import DATABASES, REALM, BackupTask

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from waterfall.restore.runner import Restorer


def test_the_version_is_stated_without_starting_anything(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert restore_main.main(["--version"]) == 0
    assert capsys.readouterr().out == f"waterfall-restore {waterfall.__version__}\n"


def test_any_argument_but_the_version_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert restore_main.main(["restore"]) == 2
    assert capsys.readouterr().err.startswith("usage: waterfall-restore [--version | test]\n")


@pytest.mark.requirement("WF-SEC-0010-A")
def test_without_its_secrets_the_service_returns_failure_and_names_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # « Le démarrage d'un service sans les secrets attendus échoue en le disant, plutôt que de
    # démarrer sans. » : the owners of both databases, the client of the bootstrap, the folder of
    # the requests of the realm.
    with pytest.MonkeyPatch.context() as patch:
        for name in [name for name in os.environ if name.startswith("WATERFALL_")]:
            patch.delenv(name)
        assert restore_main.main([]) == 2
    said = capsys.readouterr().err
    for secret in (
        "DATABASE_URL",
        "KEYCLOAK_DATABASE_URL",
        "INSTALLATION_CLIENT_SECRET",
        "SERVICE_CLIENT_SECRET",
        "REALM_REQUESTS",
    ):
        assert f"WATERFALL_{secret}: is missing" in said


@pytest.mark.usefixtures("platform_environment", "logs")
def test_with_its_secrets_the_service_runs_the_restorations_of_their_stream(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The service reads the stream of the restorations, beside the worker's, as the owners of both
    # databases, and asks Keycloak as its service account and as the client of the bootstrap.
    monkeypatch.setenv("WATERFALL_INSTALLATION_CLIENT_SECRET", "installation-secret")
    monkeypatch.setenv("WATERFALL_REALM_REQUESTS", str(tmp_path))
    served: list[Restorer] = []

    def serve(restorer: Restorer) -> int:
        served.append(restorer)
        return 0

    monkeypatch.setattr(restore_main, "serve", serve)
    assert restore_main.main([]) == 0
    (restorer,) = served
    assert restorer.queue.stream == STREAM + RESTORES
    task = restorer.handlers["restore"]
    assert isinstance(task, RestoreTask)
    assert set(task.databases) == set(DATABASES)
    assert task.databases["identity_provider"] == os.environ["WATERFALL_KEYCLOAK_DATABASE_URL"]
    provider = task.provider
    assert isinstance(provider, Keycloak)
    assert provider.installation is not provider.service
    assert provider.realm.folder == tmp_path


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.usefixtures("platform_environment", "logs")
def test_a_check_of_the_database_that_fails_releases_it_and_the_error_comes_out(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Not an unreachable server (judged by database_accepted itself) but a fault of the check: the
    # service releases its connections before the exception leaves, as it does when it refuses.
    monkeypatch.setenv("WATERFALL_INSTALLATION_CLIENT_SECRET", "installation-secret")
    monkeypatch.setenv("WATERFALL_REALM_REQUESTS", str(tmp_path))
    released: list[Database] = []

    def broken(database: Database, name: str) -> bool:
        del database, name
        message = "the check broke"
        raise RuntimeError(message)

    def dispose(database: Database) -> None:
        released.append(database)

    def keep_logs(*arguments: object, **keywords: object) -> None:
        del arguments, keywords

    # The logs stay those of the fixture: main would point them at the error output of the test.
    monkeypatch.setattr(restore_main, "configure_logging", keep_logs)
    monkeypatch.setattr(restore_main, "database_accepted", broken)
    monkeypatch.setattr(Database, "dispose", dispose)
    with pytest.raises(RuntimeError, match="the check broke"):
        restore_main.main([])
    assert len(released) == 1


# The ephemeral platform of a test of a restoration, its databases and its API, as Compose has them.
EPHEMERAL = {
    "WATERFALL_RESTORE_TEST_DATABASE_URL": "postgresql://waterfall:ephemeral-secret@restore-test-postgres/waterfall",
    "WATERFALL_RESTORE_TEST_KEYCLOAK_DATABASE_URL": (
        "postgresql://keycloak:ephemeral-secret@restore-test-postgres/keycloak"
    ),
    "WATERFALL_RESTORE_TEST_API_ADDRESS": "https://restore-test-api:8443",
}


@pytest.mark.story("US-2930")
@pytest.mark.requirement("WF-SEC-0010-A")
def test_without_its_settings_the_test_of_a_restoration_returns_failure_and_names_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.MonkeyPatch.context() as patch:
        for name in [name for name in os.environ if name.startswith("WATERFALL_")]:
            patch.delenv(name)
        assert restore_main.main(["test"]) == 2
    said = capsys.readouterr().err
    for setting in (
        "DATABASE_URL",
        "STORAGE_SECRET",
        "RESTORE_TEST_DATABASE_URL",
        "RESTORE_TEST_KEYCLOAK_DATABASE_URL",
        "RESTORE_TEST_API_ADDRESS",
        "RESTORE_TEST_RESTORED_FILE",
    ):
        assert f"WATERFALL_{setting}: is missing" in said


@pytest.mark.story("US-2930")
@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_test_of_a_restoration_restores_the_production_into_the_ephemeral_platform(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The production read as the role of the service, the ephemeral databases as their owners, its
    # API at its address; the file the platform waits for is written once restored. 0 if the test
    # succeeded, 1 if it failed.
    for name, value in EPHEMERAL.items():
        monkeypatch.setenv(name, value)
    restored = tmp_path / "restored"
    monkeypatch.setenv("WATERFALL_RESTORE_TEST_RESTORED_FILE", str(restored))
    monkeypatch.setenv("WATERFALL_RESTORE_TEST_PATIENCE", "60")
    built: list[RestoreTrial] = []
    outcomes = [True, False]
    trial = restore_main.trial

    def tried(settings: RestoreTestSettings, production: Database) -> Callable[[], bool]:
        built.append(trial(settings, production))
        return lambda: outcomes.pop(0)

    monkeypatch.setattr(restore_main, "trial", tried)
    assert restore_main.main(["test"]) == 0
    assert restore_main.main(["test"]) == 1
    restoring = built[0]
    assert restoring.databases == {
        "waterfall": EPHEMERAL["WATERFALL_RESTORE_TEST_DATABASE_URL"],
        "identity_provider": EPHEMERAL["WATERFALL_RESTORE_TEST_KEYCLOAK_DATABASE_URL"],
    }
    assert restoring.realm == "waterfall"
    started = restoring.ephemeral.started
    assert isinstance(started, Readiness)
    assert started.patience == 60
    restoring.ephemeral.restored()
    assert restored.exists()


@pytest.mark.story("US-2930")
@pytest.mark.usefixtures("platform_environment")
def test_a_test_of_a_restoration_that_cannot_run_returns_failure_and_says_why(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name, value in EPHEMERAL.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("WATERFALL_RESTORE_TEST_RESTORED_FILE", str(tmp_path / "restored"))

    def unreached(_settings: RestoreTestSettings, _production: Database) -> Callable[[], bool]:
        def run() -> bool:
            message = "the production does not answer"
            raise ConnectionError(message)

        return run

    monkeypatch.setattr(restore_main, "trial", unreached)
    assert restore_main.main(["test"]) == 1
    said = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    (failed,) = [record for record in said if record["event"] == "restore_test.not_run"]
    assert (failed["level"], failed["actor"]) == ("error", "platform")
    assert "ConnectionError" in str(failed["exception"])


@pytest.mark.story("US-2940")
@pytest.mark.usefixtures("platform_environment")
def test_the_backup_and_the_test_of_a_restoration_read_the_same_realm_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # [US-2940] #4662: the default realm has one source, ``RealmSettings``: the realm the backup
    # counts the accounts of is the one the test of a restoration counts again, and neither
    # redeclares it.
    for name, value in EPHEMERAL.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("WATERFALL_RESTORE_TEST_RESTORED_FILE", str(tmp_path / "restored"))
    monkeypatch.delenv("WATERFALL_KEYCLOAK_REALM", raising=False)
    assert BackupTask.of(load_worker_settings()).realm == REALM
    assert load_restore_test_settings().keycloak_realm == REALM
    assert "keycloak_realm" in RealmSettings.__annotations__
    for settings in (KeycloakSettings, RestoreTestSettings):
        assert "keycloak_realm" not in settings.__annotations__
    monkeypatch.setenv("WATERFALL_KEYCLOAK_REALM", "other")
    assert BackupTask.of(load_worker_settings()).realm == "other"
    assert load_restore_test_settings().keycloak_realm == "other"
