# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the task of the backup costs, and what it leaves behind when it fails (US-2940/L2).

The space its folder holds, the wait for a lock, the time of a dump and of a connection, an archive
no row names, a revision that cannot be read, an address a file of services cannot carry: each is
bounded or said, against the real databases and the real storage of the tests.
"""

import socket
import subprocess
import time
from contextlib import closing, contextmanager
from typing import TYPE_CHECKING, Any, cast

import pytest
from backup_support import Corrupting, Run, worker_of
from sqlalchemy import text
from support import captured_logs
from task_handlers import REQUEST, deposit, task

from waterfall.platform.errors import UnavailableError
from waterfall.platform.storage import Bucket
from waterfall.worker import backup as backup_module
from waterfall.worker.backup import (
    AddressError,
    BackupTask,
    DumpError,
    connect,
    connection,
    dump,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path
    from uuid import UUID

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

pytestmark = pytest.mark.story("US-2940")
CODE = "COMPONENT_UNAVAILABLE"


def keys_under(bucket: Bucket, prefix: str) -> list[str]:
    """List the keys of the bucket under a prefix."""
    pages = bucket.client.get_paginator("list_objects_v2").paginate(
        Bucket=bucket.name, Prefix=prefix
    )
    return [item.get("Key", "") for page in pages for item in page.get("Contents", [])]


def files_of(folder: Path) -> list[str]:
    """Name the dumps and the archives a folder holds, which are what takes its space."""
    return sorted(each.name for each in folder.iterdir() if each.suffix in {".dump", ".tar"})


class Watching(Bucket):
    """A bucket that notes what the folder of the task holds when the task reaches it."""

    seen: list[tuple[str, list[str]]]

    def upload(self, key: str, path: Path) -> None:
        self.seen.append(("upload", files_of(path.parent)))
        super().upload(key, path)

    def download(self, key: str, path: Path) -> None:
        self.seen.append(("download", files_of(path.parent)))
        super().download(key, path)


def watching(bucket: Bucket) -> Watching:
    """Give a bucket that notes the folder of the task."""
    watched = Watching(bucket.client, bucket.name)
    watched.seen = []
    return watched


def test_the_folder_of_the_task_holds_at_most_twice_the_dumps_and_one_copy_at_a_time(
    database: Database,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [US-2940] #896: the folder held about four times the databases — the dumps, the archive made
    # of them, the archive read back, the dumps read back. What a step is done with is removed
    # before the next: the archive is made of the dumps, which go; it is sent, and goes; the archive
    # is read back, and each dump of it, one at a time, goes once read.
    watched = watching(backups_bucket)
    listed_with: list[list[str]] = []
    pg_restore_list = backup_module.listed

    def spy(path: Path) -> bool:
        listed_with.append(files_of(path.parent))
        return pg_restore_list(path)

    monkeypatch.setattr(backup_module, "listed", spy)
    task_id = run(BackupTask(databases, watched))
    assert task(database, task_id).status == "succeeded"
    assert watched.seen == [("upload", ["backup.tar"]), ("download", [])]
    assert listed_with == [["stored.tar", "verified-0.dump"], ["stored.tar", "verified-1.dump"]]


@contextmanager
def holding_a_lock(address: str) -> Generator[None]:
    """Hold an exclusive lock on the table ``realm`` of a database, until the block ends."""
    with connect(address) as locker:
        locker.execute("LOCK TABLE realm IN ACCESS EXCLUSIVE MODE")
        yield
        locker.rollback()


def test_a_dump_that_waits_for_a_lock_fails_after_the_wait_it_is_given_and_says_why(
    databases: dict[str, str], provider_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [US-2940] #896: ``pg_dump`` takes a lock on every table it dumps and waited for it for ever;
    # it is given a minute, then fails, as an internal error that says why. The test shortens the
    # minute to a second, once it has seen the option given.
    run_pg_dump = subprocess.run
    given: list[str] = []

    def shortened(command: list[str], **options: Any) -> subprocess.CompletedProcess[bytes]:
        given.extend(each for each in command if each.startswith("--lock-wait-timeout"))
        shorter = [each.replace("=60s", "=1s") for each in command]
        return cast("subprocess.CompletedProcess[bytes]", run_pg_dump(shorter, **options))

    monkeypatch.setattr(subprocess, "run", shortened)
    started = time.monotonic()
    with captured_logs() as logs, holding_a_lock(provider_url), pytest.raises(DumpError):
        dump("identity_provider", databases["identity_provider"], tmp_path)
    assert given == ["--lock-wait-timeout=60s"]
    assert time.monotonic() - started < 30
    (failed,) = logs.named("backup.dump_failed")
    assert failed["database"] == "identity_provider"
    assert "LOCK TABLE public.realm" in failed["said"]


def test_a_dump_that_lasts_beyond_its_deadline_is_stopped_and_says_so(
    databases: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [US-2940] #896: the transaction of the worker stays open while the databases are dumped; a
    # dump that does not end within its deadline is stopped, and the task fails with it.
    monkeypatch.setattr(backup_module, "DUMP_DEADLINE", 0.001)
    with captured_logs() as logs, pytest.raises(DumpError):
        dump("waterfall", databases["waterfall"], tmp_path)
    (stopped,) = logs.named("backup.dump_timed_out")
    assert stopped["database"] == "waterfall"


def test_the_dump_of_a_database_that_a_role_cannot_read_says_why_in_the_journal(
    service_database_url: str, tmp_path: Path
) -> None:
    # [US-2940] #908: the cause pg_dump gives is written to the journal of the service.
    with captured_logs() as logs, pytest.raises(DumpError):
        dump("waterfall", service_database_url, tmp_path)
    (failed,) = logs.named("backup.dump_failed")
    assert "permission denied" in failed["said"]


@contextmanager
def silent_server() -> Generator[str]:
    """Listen on a port and never answer: a database that accepts a connection and says nothing."""
    with closing(socket.socket()) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        yield f"postgresql://backup:secret@127.0.0.1:{server.getsockname()[1]}/waterfall"


def test_a_database_that_answers_nothing_fails_the_connection_after_its_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [US-2940] #4191: no timeout was set, and a database that stops answering held the task.
    monkeypatch.setattr(backup_module, "CONNECT_TIMEOUT", 1)
    started = time.monotonic()
    with silent_server() as address, pytest.raises(UnavailableError) as raised:
        connect(address)
    assert time.monotonic() - started < 10
    assert dict(raised.value.params) == {"component": "database"}


def test_the_tools_of_postgresql_are_given_a_connection_timeout_and_honour_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [US-2940] #4191: ``PGCONNECT_TIMEOUT`` reaches pg_dump, which fails after it, and the dump
    # then finds the database does not answer: unavailable, not a dump that hangs.
    monkeypatch.setattr(backup_module, "CONNECT_TIMEOUT", 1)
    with silent_server() as address:
        environment = connection(address, tmp_path / "waterfall.service")
        assert environment["PGCONNECT_TIMEOUT"] == "1"
        started = time.monotonic()
        with pytest.raises(UnavailableError):
            dump("waterfall", address, tmp_path)
    assert time.monotonic() - started < 15


def test_a_revision_that_cannot_be_read_on_a_database_reached_is_an_error_that_says_why(
    database: Database,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
) -> None:
    # [US-2940] #908: the database answers and holds no revision of a schema: the task fails as an
    # internal error, writes why to the journal, and leaves no archive and no row.
    unmigrated = {**databases, "waterfall": databases["identity_provider"]}
    with captured_logs() as logs:
        task_id = run(BackupTask(unmigrated, backups_bucket))
    failed = task(database, task_id)
    assert (failed.status, failed.problem) == (
        "failed",
        {"code": "INTERNAL_ERROR", "status": 500, "correlation_id": REQUEST},
    )
    (said,) = logs.named("backup.revision_unreadable")
    assert "alembic_version" in said["said"]
    assert keys_under(backups_bucket, f"backup-{task_id}") == []
    with database.transaction() as session:
        assert session.execute(text("SELECT count(*) FROM backup")).scalar_one() == 0


@pytest.mark.parametrize(
    "query",
    [
        "application_name=a%0Ab",
        "application_name=a%0Db",
        "application_name=%20ab",
        "application_name=ab%20",
        "application_name=%09ab",
    ],
    ids=["line-feed", "carriage-return", "leading-space", "trailing-space", "leading-tab"],
)
def test_an_address_whose_value_a_line_of_the_file_of_services_cannot_carry_is_refused(
    tmp_path: Path, query: str
) -> None:
    # [US-2940] #908: a line break would add a line to the file, and libpq takes the spaces at the
    # edge off a value. Refused, naming the keyword and not the value, before anything is written.
    service = tmp_path / "waterfall.service"
    with pytest.raises(AddressError, match="application_name") as refused:
        connection(f"postgresql://owner:s3cret@db.example/waterfall?{query}", service)
    assert "s3cret" not in str(refused.value)
    assert not service.exists()


def test_an_address_with_a_database_name_that_libpq_would_trim_is_refused(tmp_path: Path) -> None:
    # [US-2940] #908: the keywords the address names itself are checked as those of its query.
    with pytest.raises(AddressError, match="dbname"):
        connection("postgresql://owner@db.example/waterfall%20", tmp_path / "waterfall.service")


def test_a_backup_whose_address_the_file_of_services_cannot_carry_fails_and_stores_nothing(
    database: Database,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
) -> None:
    # [US-2940] #908: the fault is the operator's configuration, an internal error of the task.
    unwritable = databases["identity_provider"] + "?application_name=%20x"
    refused = {**databases, "identity_provider": unwritable}
    task_id = run(BackupTask(refused, backups_bucket))
    assert task(database, task_id).status == "failed"
    assert keys_under(backups_bucket, f"backup-{task_id}") == []


class Lying(Bucket):
    """A bucket that keeps an archive and says it did not."""

    def upload(self, key: str, path: Path) -> None:
        super().upload(key, path)
        raise UnavailableError(CODE, {"component": "object_storage"})


def test_an_archive_stored_by_an_upload_that_fails_leaves_no_object_under_its_key(
    database: Database, run: Run, databases: dict[str, str], backups_bucket: Bucket
) -> None:
    # [US-2940] #896: the upload is inside the guarded block: what it left is removed.
    task_id = run(BackupTask(databases, Lying(backups_bucket.client, backups_bucket.name)))
    assert task(database, task_id).status == "failed"
    assert keys_under(backups_bucket, f"backup-{task_id}") == []


def test_an_archive_that_fails_its_verification_and_whose_row_cannot_be_written_is_not_left(
    database: Database,
    queue: TaskQueue,
    databases: dict[str, str],
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [US-2940] #4515: the archive is kept for the row that names it; when the row cannot be
    # written, the task is undone and nothing names the archive, which is removed. The fault goes
    # on, as it does when the row of a verified archive cannot be written.
    def refuse(*_: object) -> UUID:
        raise UnavailableError(CODE, {"component": "database"})

    monkeypatch.setattr(backup_module, "add_backup", refuse)
    corrupting = Corrupting(backups_bucket.client, backups_bucket.name)
    worker = worker_of(database, queue, BackupTask(databases, corrupting))
    task_id = deposit(database, queue, "backup")
    with pytest.raises(UnavailableError):
        worker.step()
    assert keys_under(backups_bucket, f"backup-{task_id}") == []
