# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The command of the service of the restoration: it refuses to start without its secrets, runs."""

import os
from pathlib import Path

import pytest

import waterfall
from waterfall.platform.queue import RESTORES, STREAM
from waterfall.restore import main as restore_main
from waterfall.restore.provider import Keycloak
from waterfall.restore.runner import Restorer
from waterfall.restore.task import RestoreTask
from waterfall.worker.backup import DATABASES


def test_the_version_is_stated_without_starting_anything(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert restore_main.main(["--version"]) == 0
    assert capsys.readouterr().out == f"waterfall-restore {waterfall.__version__}\n"


def test_any_argument_but_the_version_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert restore_main.main(["restore"]) == 2
    assert capsys.readouterr().err.startswith("usage: waterfall-restore [--version]\n")


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
