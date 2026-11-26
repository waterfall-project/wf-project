# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A backup taken by the production platform of the last published version (US-2850).

``make migrations-backup`` takes it in the full tier of the chain (``make check-migrations``), then
the tests of the back of the branch restore and migrate it (``test_earlier_backup.py``); these tests
hold what the tool decides by itself — the settings it gives the Compose of N, the service that
loads its witness, the order of its steps — on a Compose played by a fake. They cite WF-DAT-0140-A
(its third sentence): the backup is that of a version before, its marked revisions among it.
"""

import base64
import string
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from wftools import migrationbackup
from wftools.migrationbackup import (
    BACKUP,
    STARTED,
    environment_of,
    required,
    take,
    witness_service,
)
from wftools.migrationtests import MigrationTrialError, Version

if TYPE_CHECKING:
    from collections.abc import Mapping

pytestmark = pytest.mark.story("US-2850")

COMPOSE = ["docker", "compose", "-p", "trial", "-f", "prod.yaml"]
STORED = "/scratch/backup/earlier-backup.tar"
DRAWN = "drawn-for-the-run"


def test_the_settings_a_compose_stops_without_are_found_once() -> None:
    text = (
        "image: x:${WATERFALL_IMAGE_TAG:?set it}\n"
        "tag: ${WATERFALL_IMAGE_TAG:?set it}\n"
        "password: ${WATERFALL_REDIS_PASSWORD:?set it}\n"
        "port: ${WATERFALL_HTTPS_PORT:-443}\n"
    )
    assert required(text) == ["WATERFALL_IMAGE_TAG", "WATERFALL_REDIS_PASSWORD"]


@pytest.mark.requirement("WF-DAT-0140-A")
def test_the_platform_of_n_runs_its_published_images_with_secrets_drawn_for_the_run() -> None:
    names = [
        "WATERFALL_IMAGE_TAG",
        "WATERFALL_CURRENCY",
        "WATERFALL_STORAGE_RPC_SECRET",
        "WATERFALL_SERVER_ACTIONS_KEY",
        "WATERFALL_REDIS_PASSWORD",
    ]
    values = environment_of(names, Version("v0.3.0"), lambda: DRAWN)
    assert values["WATERFALL_IMAGE_TAG"] == "0.3.0"
    assert values["WATERFALL_CURRENCY"] == "EUR"
    assert len(values["WATERFALL_STORAGE_RPC_SECRET"]) == 64
    assert set(values["WATERFALL_STORAGE_RPC_SECRET"]) <= set(string.hexdigits)
    assert len(base64.b64decode(values["WATERFALL_SERVER_ACTIONS_KEY"])) == 32
    assert values["WATERFALL_REDIS_PASSWORD"] == DRAWN


def test_a_secret_drawn_holds_letters_and_digits_alone() -> None:
    drawn = migrationbackup.drawn()
    assert len(drawn) == 32
    assert drawn.isalnum()


@pytest.mark.requirement("WF-DAT-0140-A")
def test_the_witness_of_n_is_loaded_by_its_own_image_as_its_api_reaches_the_database() -> None:
    config = {
        "services": {
            "api": {
                "image": "ghcr.io/waterfall-project/waterfall:0.3.0",
                "environment": {"WATERFALL_DATABASE_URL": "postgresql://service@postgres/w"},
                "volumes": [{"type": "bind", "source": "/a", "target": "/b"}],
            }
        }
    }
    service = witness_service(config, Path("/n/fixtures/api"))["services"]["witness"]
    assert service["image"] == "ghcr.io/waterfall-project/waterfall:0.3.0"
    assert service["command"] == ["waterfall-api", "load-witness"]
    assert service["environment"] == {
        "WATERFALL_DATABASE_URL": "postgresql://service@postgres/w",
        "WATERFALL_WITNESS_PATH": "/witness",
    }
    assert service["volumes"][-1] == "/n/fixtures/api:/witness:ro"
    assert service["profiles"] == ["witness"]


class Compose:
    """A Compose that records the commands, fails the one asked, and says the backup taken."""

    def __init__(
        self, failing: str = "", backup: tuple[int, str] = (0, f"log\n{STORED}\n")
    ) -> None:
        self.commands: list[list[str]] = []
        self.failing = failing
        self.backup = backup

    def run(self, command: list[str], environment: Mapping[str, str]) -> int:
        assert environment == {"WATERFALL_IMAGE_TAG": "0.3.0"}
        self.commands.append(command)
        return 1 if self.failing and self.failing in command else 0

    def read(self, command: list[str], environment: Mapping[str, str]) -> tuple[int, str]:
        assert environment == {"WATERFALL_IMAGE_TAG": "0.3.0"}
        self.commands.append(command)
        return self.backup


@pytest.mark.requirement("WF-DAT-0140-A")
def test_n_is_bootstrapped_its_witness_loaded_then_backed_up_and_its_archive_copied_out(
    tmp_path: Path,
) -> None:
    compose = Compose()
    take(compose.run, compose.read, COMPOSE, tmp_path / "a.tar", {"WATERFALL_IMAGE_TAG": "0.3.0"})
    assert [command[len(COMPOSE) :] for command in compose.commands] == [
        ["up", "--detach", "--wait", *STARTED],
        ["run", "--rm", "--no-TTY", "install"],
        ["run", "--rm", "--no-TTY", "witness"],
        ["exec", "--no-TTY", "worker", "python", "-c", BACKUP],
        ["cp", f"worker:{STORED}", str(tmp_path / "a.tar")],
    ]


@pytest.mark.parametrize(("failing", "said"), [("install", "bootstrap"), ("witness", "witness")])
def test_a_step_that_fails_stops_the_others_and_is_named(failing: str, said: str) -> None:
    compose = Compose(failing)
    with pytest.raises(MigrationTrialError, match=said):
        take(compose.run, compose.read, COMPOSE, Path("a.tar"), {"WATERFALL_IMAGE_TAG": "0.3.0"})
    assert compose.commands[-1][-1] == failing


def test_a_backup_that_fails_says_what_the_worker_said() -> None:
    compose = Compose(backup=(1, "the backup 01 ended failed"))
    with pytest.raises(MigrationTrialError, match="ended failed"):
        take(compose.run, compose.read, COMPOSE, Path("a.tar"), {"WATERFALL_IMAGE_TAG": "0.3.0"})
    assert "cp" not in compose.commands[-1]


def test_a_compose_that_does_not_read_is_named() -> None:
    def refused(command: list[str], environment: Mapping[str, str]) -> tuple[int, str]:
        del command, environment
        return 1, "required variable WATERFALL_DOMAIN is missing"

    with pytest.raises(MigrationTrialError, match="WATERFALL_DOMAIN is missing"):
        migrationbackup.configured(refused, COMPOSE, {})


def test_the_tool_asks_for_its_archive(capsys: pytest.CaptureFixture[str]) -> None:
    assert migrationbackup.main([], {}) == 2
    assert "usage" in capsys.readouterr().err


def no_tags(command: list[str], environment: Mapping[str, str] | None = None) -> tuple[int, str]:
    """Return a git that knows no tag."""
    del command, environment
    return 0, ""


def test_without_a_published_version_nothing_is_taken_and_no_archive_is_left(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stale = tmp_path / "earlier.tar"
    stale.write_bytes(b"an archive of a run before")
    monkeypatch.setattr(migrationbackup, "_read", no_tags)
    assert migrationbackup.main([str(stale)], {}) == 0
    assert not stale.exists()
    assert "not executed: no published version" in capsys.readouterr().out
