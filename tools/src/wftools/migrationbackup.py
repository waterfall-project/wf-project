# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A backup taken by the production platform of the last published version (US-2850).

Usage: ``python -m wftools.migrationbackup <archive>``.

WF-DAT-0140-A: after a suite of migrations, the amounts and the indicators a marked revision of an
earlier version kept are unchanged, and an installation of the version N passes to N+1 without
losing anything. N is the last published version (``wftools.migrationtests``): its Compose of
production, ``deploy/compose/compose.prod.yaml`` of its tag, is started from its published images
(``ghcr.io/waterfall-project/<image>:X.Y.Z``) under a project of its own, with values drawn for the
run for each setting it requires; its database and its identity provider are bootstrapped by its
own command (``install``), then its witness is loaded by its own (``load-witness``, the
``fixtures/api`` of its tag) — projects, and revisions marked with their lines and their amounts.
Then its worker takes a backup, as a task of the kind ``backup`` deposited by its own code, in its
container, and the archive it stored is copied out to ``<archive>``. The platform is removed, its
volumes with it, whatever the outcome; what its services said is printed first when it fails.

The branch reads that archive, restores it and migrates it:
``backend/tests/test_earlier_backup.py``, which ``make migrations-backup`` runs next. Without a
published version, nothing is taken, and the tool says it is not executed.

The front, Caddy and the supervision are not started: the backup reads the databases alone. The
deposit of the task is the code of N, not its operation ``startBackup``, which would ask for a
session of its first administrator through its front; a version that renames what it calls fails
here, naming what it lacks.
"""

import base64
import io
import json
import os
import re
import secrets
import string
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from wftools import REPOSITORY
from wftools.migrationtests import REQUIREMENT, MigrationTrialError, Version, last_published

TOOL = "wftools.migrationbackup"
PROJECT = "waterfall-migrations"
EXTRACTED = ("deploy/compose", "fixtures/api")
COMPOSE = Path("deploy/compose")
PRODUCTION = "compose.prod.yaml"
OVERRIDE = "compose.migrations.json"
"""The service of the witness the tool adds, written beside the files of N: JSON is YAML too."""
WITNESS = Path("fixtures/api")
STARTED = ("worker", "keycloak-realm")
"""What the bootstrap and the backup need: the databases, Redis, the storage, the worker, Keycloak
and its realm, which the bootstrap writes the first administrator into."""
REQUIRED = re.compile(r"\$\{(WATERFALL_[A-Z0-9_]+):\?")
SETTINGS = {
    "WATERFALL_DOMAIN": "waterfall.localhost",
    "WATERFALL_ACME_EMAIL": "exploitation@waterfall.test",
    "WATERFALL_ADMIN_EMAIL": "administrateur@waterfall.test",
    "WATERFALL_CURRENCY": "EUR",
    "WATERFALL_COMPANY_NAME": "Delmas Automatismes",
}
"""The settings of the run that are no secret: those of the witness (EP-05)."""
BACKUP = """
import pathlib, sys, tempfile, time
from sqlalchemy import text
from waterfall import schema
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.logs import PLATFORM, logging_context
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.settings import load_worker_settings
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import submit
schema.declared()
settings = load_worker_settings()
database = Database(create_database_engine(settings.database_url.get_secret_value()))
queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=DEPOSIT_TIMEOUT)
with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
    with database.transaction() as session:
        task = submit(session, queue, "backup", None)
asked = text("SELECT status FROM background_task WHERE id = :task")
for _ in range(300):
    with database.transaction() as session:
        status = session.execute(asked, {"task": task}).scalar_one()
    if status in ("succeeded", "failed"):
        break
    time.sleep(2)
if status != "succeeded":
    sys.exit(f"the backup {task} ended {status}")
stored = pathlib.Path(tempfile.mkdtemp()) / "earlier-backup.tar"
Bucket.of_backups(settings).download(f"backup-{task}.tar", stored)
print(stored)
"""
"""What the worker of N runs to take a backup, wait for it, and read its archive from the bucket
into a file of its container, whose path it says last: the task deposited as its own command
deposits one, under a correlation of its own, as the platform."""

Run = Callable[[list[str], Mapping[str, str]], int]
Ask = Callable[[list[str], Mapping[str, str]], tuple[int, str]]


def required(compose: str) -> list[str]:
    """Return the settings a Compose file stops without, ``${NAME:?…}``, each once."""
    return sorted(set(REQUIRED.findall(compose)))


def drawn(length: int = 32) -> str:
    """Draw a secret of letters and digits, which a URL holds as it is."""
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def environment_of(
    names: list[str], version: Version, draw: Callable[[], str] = drawn
) -> dict[str, str]:
    """Give a value to each setting N requires: its tag, the settings above, else a secret drawn.

    Garage wants the secret of its RPC in 64 hexadecimal digits, and the server of Next a key of 32
    bytes in base64.
    """
    values: dict[str, str] = {}
    for name in names:
        if name == "WATERFALL_IMAGE_TAG":
            values[name] = version.tag
        elif name in SETTINGS:
            values[name] = SETTINGS[name]
        elif name == "WATERFALL_STORAGE_RPC_SECRET":
            values[name] = secrets.token_hex(32)
        elif name == "WATERFALL_SERVER_ACTIONS_KEY":
            values[name] = base64.b64encode(secrets.token_bytes(32)).decode()
        else:
            values[name] = draw()
    return values


def witness_service(config: Mapping[str, Any], witness: Path) -> dict[str, Any]:
    """Return the service that loads the witness of N: the image and the environment of its API.

    As the role of the service, as the API writes; the description read-only from the tag of N.
    """
    api = config["services"]["api"]
    service: dict[str, Any] = {
        "image": api["image"],
        "environment": {**api.get("environment", {}), "WATERFALL_WITNESS_PATH": "/witness"},
        "command": ["waterfall-api", "load-witness"],
        "profiles": ["witness"],
        "restart": "no",
        "volumes": [*api.get("volumes", []), f"{witness}:/witness:ro"],
    }
    return {"services": {"witness": service}}


def extract(archive: bytes, folder: Path) -> Path:
    """Write the Compose files and the witness of N under ``folder``; give its Compose folder."""
    with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
        tree.extractall(folder, filter="data")
    found = folder / COMPOSE
    if not (found / PRODUCTION).is_file():
        message = f"the version gives no {COMPOSE / PRODUCTION}"
        raise MigrationTrialError(message)
    return found


def configured(read: Ask, compose: list[str], given: Mapping[str, str]) -> dict[str, Any]:
    """Return the Compose of N as Compose reads it, its settings given."""
    code, said = read([*compose, "config", "--format", "json"], given)
    if code:
        message = f"the Compose does not read: {said.strip()}"
        raise MigrationTrialError(message)
    return json.loads(said)


def take(run: Run, read: Ask, compose: list[str], target: Path, given: Mapping[str, str]) -> None:
    """Start the platform of N, bootstrap it, load its witness, back it up, copy the archive out."""
    steps = (
        ("start", [*compose, "up", "--detach", "--wait", *STARTED]),
        ("bootstrap", [*compose, "run", "--rm", "--no-TTY", "install"]),
        ("load the witness", [*compose, "run", "--rm", "--no-TTY", "witness"]),
    )
    for what, command in steps:
        print(f"  {what}", flush=True)
        if code := run(command, given):
            message = f"{what} failed ({code})"
            raise MigrationTrialError(message)
    print("  back up", flush=True)
    code, said = read([*compose, "exec", "--no-TTY", "worker", "python", "-c", BACKUP], given)
    lines = said.strip().splitlines()
    if code or not lines:
        message = f"the backup failed ({code}): {said.strip()[-2000:]}"
        raise MigrationTrialError(message)
    print("  copy the archive out", flush=True)
    if code := run([*compose, "cp", f"worker:{lines[-1]}", str(target)], given):
        message = f"the archive {lines[-1]} cannot be copied out ({code})"
        raise MigrationTrialError(message)


def main(arguments: list[str] | None = None, environment: Mapping[str, str] | None = None) -> int:
    """Find N, take a backup of its witness on its platform, and leave nothing of it behind."""
    words = sys.argv[1:] if arguments is None else arguments
    given = dict(os.environ if environment is None else environment)
    if len(words) != 1:
        print(f"usage: python -m {TOOL} <archive>", file=sys.stderr)
        return 2
    target = Path(words[0]).resolve()
    target.unlink(missing_ok=True)
    try:
        version = last_published(_read)
    except MigrationTrialError as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 1
    if version is None:
        notice = "::notice::" if given.get("GITHUB_ACTIONS") == "true" else ""
        print(f"{notice}{TOOL}: not executed: no published version; {REQUIREMENT} is not held")
        return 0
    project = given.get("WATERFALL_MIGRATIONS_PROJECT") or PROJECT
    scratch = REPOSITORY / ".waterfall"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="migration-backup-", dir=scratch) as folder:
        try:
            found = extract(_archive(version.name), Path(folder))
            production = found / PRODUCTION
            values = environment_of(required(production.read_text(encoding="utf-8")), version)
            running = {**given, **values}
            compose = ["docker", "compose", "-p", project, "-f", str(production)]
            witness = witness_service(configured(_read, compose, running), Path(folder) / WITNESS)
            (found / OVERRIDE).write_text(json.dumps(witness), encoding="utf-8")
        except (
            MigrationTrialError,
            subprocess.CalledProcessError,
            OSError,
            KeyError,
            ValueError,
        ) as error:
            print(f"{TOOL}: {error}", file=sys.stderr)
            return 1
        compose += ["-f", str(found / OVERRIDE)]
        print(f"  {version.name}, its images {version.tag}, as the project {project}", flush=True)
        failed = True
        try:
            take(_run, _read, compose, target, running)
            failed = False
        except MigrationTrialError as error:
            print(f"{TOOL}: {version.name}: {error}", file=sys.stderr)
        finally:
            if failed:
                _run([*compose, "logs", "--no-color", "--tail", "60"], running)
            _run([*compose, "down", "--volumes", "--remove-orphans"], running)
    return 1 if failed else 0


def _archive(name: str) -> bytes:
    return subprocess.run(
        ["git", "archive", "--format=tar", name, *EXTRACTED],
        cwd=REPOSITORY,
        capture_output=True,
        check=True,
    ).stdout


def _run(command: list[str], environment: Mapping[str, str]) -> int:
    return subprocess.run(command, cwd=REPOSITORY, env=dict(environment), check=False).returncode


def _read(command: list[str], environment: Mapping[str, str] | None = None) -> tuple[int, str]:
    done = subprocess.run(
        command,
        cwd=REPOSITORY,
        env=None if environment is None else dict(environment),
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode, done.stdout + done.stderr if done.returncode else done.stdout


if __name__ == "__main__":
    sys.exit(main())
