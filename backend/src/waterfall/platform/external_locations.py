# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The external locations of the backups, reached by the server alone (WF-ADM-0170, TFX-16).

Two natures, one interface (``ExternalStore``): a bucket of an S3 storage on another site, reached
by the standard operations of S3 alone, and a network share mounted on the server, a folder of its
file system. A file is written under a key — a folder of the location and a name —, read back, its
size and its digest, listed among those of its folder, and removed. What the location refuses is
said by its reason (``ExternalBackupFailure``): unreachable, access denied, writing or erasing
refused, space exhausted, time exceeded; never by its message, which may name an address. The
secrets of a location are the settings' (``waterfall.platform.settings.ExternalLocations``): no
reason, no log of this module carries one.

On a share, nothing is written outside the folder mounted: a key is made of the segments of a
relative path (``ExternalBackupPath``), and its folder, once resolved — a link followed —, must lie
under the folder mounted, or the access is denied. A file is written under a name of its own, then
renamed: a reader never sees a copy half written.
"""

import errno
import hashlib
import os
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as Late
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

import boto3
from boto3.exceptions import S3UploadFailedError
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
)

from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import get_logger
from waterfall.platform.settings import MountedShare, S3Location

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from mypy_boto3_s3.client import S3Client

    from waterfall.platform.settings import DeclaredLocation

logger = get_logger(__name__)

# Why a location refused, as the contract names it (``ExternalBackupFailure``).
type Failure = Literal[
    "location_unreachable",
    "access_denied",
    "write_failed",
    "delete_failed",
    "storage_full",
    "timed_out",
]
# What was being done when the location refused: the reason of a fault that says no other.
type Doing = Literal["write", "delete"]
CHUNK = 1 << 20
# The longest a copy to a location may take, as the operating parameter says it, and the bounds of
# the connections of an S3 client, in seconds (#4656).
COPY_TIMEOUT = 3600.0
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
# The longest a test of a location waits for it (``testExternalBackupLocation``), and its witness.
TEST_TIMEOUT = 30.0
WITNESS = b"Waterfall: a witness of the test of an external location, erased once read back.\n"
# The reasons this module gives of itself: a share or a location out of reach, a file that does not
# read back as written, a folder that leaves its share.
UNREACHABLE: Failure = "location_unreachable"
WRITE_FAILED: Failure = "write_failed"
TIMED_OUT: Failure = "timed_out"
DENIED: Failure = "access_denied"
# What an S3 storage says by the code of its refusal: the key refused, the bucket missing, the space
# spent. Another code is what was being done that failed.
BY_CODE: dict[str, Failure] = {
    **dict.fromkeys(
        ("AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch", "403", "Forbidden"), DENIED
    ),
    "NoSuchBucket": UNREACHABLE,
    **dict.fromkeys(
        ("QuotaExceeded", "InsufficientStorage", "EntityTooLarge", "507"), "storage_full"
    ),
}
# The errors of the file system that say the space is spent.
SPENT = {errno.ENOSPC, errno.EDQUOT}


class LocationRefusedError(Exception):
    """An external location refused what was asked of it, for a reason the contract names."""

    def __init__(self, failure: Failure) -> None:
        super().__init__(failure)
        self.failure: Failure = failure


class ExternalStore(Protocol):
    """What the server does in an external location, whatever its nature.

    A key is a relative path: the folder, empty for the root, then a name, separated by ``/``.
    """

    def put(self, key: str, path: Path) -> None:
        """Write a file under a key; a file there is replaced."""
        ...

    def read_back(self, key: str) -> tuple[int, str]:
        """Read a file back whole: its size and its SHA-256."""
        ...

    def names(self, folder: str) -> list[str]:
        """List the names of the files directly in a folder; none in a folder that is not there."""
        ...

    def remove(self, key: str) -> None:
        """Remove the file of a key."""
        ...

    def tidy(self) -> None:
        """Remove the empty folders this store created by writing: a test leaves nothing."""
        ...

    def close(self) -> None:
        """Let go of what reaches the location."""
        ...


def key_of(folder: str, name: str) -> str:
    """Give the key of a name in a folder, the root when the folder is empty."""
    return f"{folder}/{name}" if folder else name


def _s3_failure(error: BaseException, doing: Doing) -> Failure:
    """Name what an S3 storage refused, by its code; what it does not say, by what was done."""
    if isinstance(error, ConnectTimeoutError | ReadTimeoutError):
        return "timed_out"
    if not isinstance(error, ClientError):
        return UNREACHABLE
    code = str(error.response.get("Error", {}).get("Code", ""))
    return BY_CODE.get(code, WRITE_FAILED if doing == "write" else "delete_failed")


@contextmanager
def _s3_refusals(doing: Doing) -> Generator[None]:
    """Say what an S3 storage refused by its reason; a refused upload by the refusal it wraps.

    boto3 wraps the refusal of an upload (``S3UploadFailedError``), raised while it handles it.
    """
    try:
        yield
    except (BotoCoreError, ClientError) as error:
        raise LocationRefusedError(_s3_failure(error, doing)) from None
    except S3UploadFailedError as error:
        wrapped = error.__context__
        failure = WRITE_FAILED if wrapped is None else _s3_failure(wrapped, doing)
        raise LocationRefusedError(failure) from None


class S3Store:
    """A bucket of an S3 storage, on another site, as an external location."""

    def __init__(self, client: S3Client, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    @classmethod
    def of(cls, location: S3Location) -> S3Store:
        """Reach the bucket a location names, signing with its key; its certificate checked.

        By the path, which every storage serves; a checksum where S3 requires one. A storage that
        does not answer is let go after a bounded wait, retried once.
        """
        config = Config(
            s3={"addressing_style": "path"},
            connect_timeout=CONNECT_TIMEOUT,
            read_timeout=READ_TIMEOUT,
            retries={"mode": "standard", "max_attempts": 2},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
        client = boto3.client(
            "s3",
            endpoint_url=location.address,
            region_name=location.region,
            aws_access_key_id=location.access_key.get_secret_value(),
            aws_secret_access_key=location.secret_key.get_secret_value(),
            config=config,
            verify=True if location.authority is None else location.authority,
        )
        return cls(client, location.bucket)

    def put(self, key: str, path: Path) -> None:
        """Write a file under a key, in parts if it is large."""
        with _s3_refusals("write"):
            self.client.upload_file(str(path), self.bucket, key)

    def read_back(self, key: str) -> tuple[int, str]:
        """Read the object of a key whole: its size and its SHA-256."""
        hashed = hashlib.sha256()
        size = 0
        with _s3_refusals("write"):
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
            for chunk in body.iter_chunks(CHUNK):
                hashed.update(chunk)
                size += len(chunk)
        return size, hashed.hexdigest()

    def names(self, folder: str) -> list[str]:
        """List the names of the objects directly under a folder."""
        prefix = f"{folder}/" if folder else ""
        found: list[str] = []
        with _s3_refusals("delete"):
            pages = self.client.get_paginator("list_objects_v2").paginate(
                Bucket=self.bucket, Prefix=prefix, Delimiter="/"
            )
            for page in pages:
                found += [
                    listed.get("Key", "").removeprefix(prefix)
                    for listed in page.get("Contents", [])
                ]
        return found

    def remove(self, key: str) -> None:
        """Remove the object of a key."""
        with _s3_refusals("delete"):
            self.client.delete_object(Bucket=self.bucket, Key=key)

    def tidy(self) -> None:
        """Remove nothing: a bucket has no folders, only keys."""

    def close(self) -> None:
        """Close the client."""
        self.client.close()


def _share_failure(error: OSError, doing: Doing) -> Failure:
    """Name what a share refused, by the error of the file system; else by what was done."""
    if isinstance(error, PermissionError):
        return "access_denied"
    if error.errno in SPENT:
        return "storage_full"
    if isinstance(error, TimeoutError):
        return "timed_out"
    return WRITE_FAILED if doing == "write" else "delete_failed"


@contextmanager
def _share_refusals(doing: Doing) -> Generator[None]:
    try:
        yield
    except OSError as error:
        raise LocationRefusedError(_share_failure(error, doing)) from None


class ShareStore:
    """A network share mounted on the server, as an external location: a folder and its files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.created: list[Path] = []

    @classmethod
    def of(cls, location: MountedShare) -> ShareStore:
        """Reach the folder a location says the share is mounted on."""
        return cls(Path(location.directory))

    def _inside(self, folder: str) -> Path:
        """Give a folder of the share, resolved; refuse one that is not under its root.

        A share not mounted, or not a folder, is unreachable; a folder whose resolution leaves the
        root — a link that points elsewhere — is refused as an access denied.
        """
        with _share_refusals("write"):
            if not self.root.is_dir():
                raise LocationRefusedError(UNREACHABLE)
            root = self.root.resolve(strict=True)
            resolved = (root / folder).resolve()
        if resolved != root and not resolved.is_relative_to(root):
            raise LocationRefusedError(DENIED)
        return resolved

    def _file(self, key: str) -> Path:
        folder, _, name = key.rpartition("/")
        return self._inside(folder) / name

    def put(self, key: str, path: Path) -> None:
        """Write a file under a key: under a name of its own, flushed, then renamed."""
        target = self._file(key)
        partial = target.with_name(f".{target.name}.{new_id().hex}.partial")
        with _share_refusals("write"):
            above = (target.parent, *target.parent.parents)
            self.created += [each for each in above if not each.exists()]
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("rb") as read, partial.open("wb") as written:
                    shutil.copyfileobj(read, written, CHUNK)
                    written.flush()
                    os.fsync(written.fileno())
                partial.replace(target)
            finally:
                partial.unlink(missing_ok=True)

    def read_back(self, key: str) -> tuple[int, str]:
        """Read the file of a key whole: its size and its SHA-256."""
        hashed = hashlib.sha256()
        size = 0
        with _share_refusals("write"), self._file(key).open("rb") as read:
            while chunk := read.read(CHUNK):
                hashed.update(chunk)
                size += len(chunk)
        return size, hashed.hexdigest()

    def names(self, folder: str) -> list[str]:
        """List the names of the files directly in a folder; none if it is not there."""
        inside = self._inside(folder)
        with _share_refusals("delete"):
            if not inside.is_dir():
                return []
            return [each.name for each in inside.iterdir() if each.is_file()]

    def remove(self, key: str) -> None:
        """Remove the file of a key."""
        with _share_refusals("delete"):
            self._file(key).unlink(missing_ok=True)

    def tidy(self) -> None:
        """Remove the folders created by ``put``, the deepest first, those left empty only."""
        with _share_refusals("delete"):
            for each in sorted(self.created, key=lambda made: len(made.parts), reverse=True):
                with suppress(OSError):
                    each.rmdir()
            self.created.clear()

    def close(self) -> None:
        """Let go of nothing: the share stays mounted."""


def store_of(location: DeclaredLocation) -> ExternalStore:
    """Reach a location by its nature."""
    if isinstance(location, S3Location):
        return S3Store.of(location)
    return ShareStore.of(location)


@contextmanager
def reached(
    location: DeclaredLocation, opened: Callable[[DeclaredLocation], ExternalStore] = store_of
) -> Generator[ExternalStore]:
    """Open a location for the time of a use, and let go of it after.

    A location that cannot be opened — a region or an address the client refuses — is unreachable.
    """
    try:
        store = opened(location)
    except (BotoCoreError, ValueError, OSError) as error:
        # Its class alone, never its message: the client may repeat the address it refused.
        logger.warning("location.open_refused", error=type(error).__name__)
        raise LocationRefusedError(UNREACHABLE) from None
    try:
        yield store
    finally:
        store.close()


def witness_test(store: ExternalStore, folder: str) -> None:
    """Write a witness file in a folder of a location, read it back, then erase it.

    Refused as the location refuses: a witness that does not read back whole is a writing refused.
    """
    key = key_of(folder, f"waterfall-test-{new_id().hex}.txt")
    try:
        with tempfile.TemporaryDirectory(prefix="waterfall-location-test-") as work:
            witness = Path(work) / "witness.txt"
            witness.write_bytes(WITNESS)
            store.put(key, witness)
        try:
            if store.read_back(key) != (len(WITNESS), hashlib.sha256(WITNESS).hexdigest()):
                raise LocationRefusedError(WRITE_FAILED)
        finally:
            # The witness leaves the location whatever the reading says: a test leaves nothing.
            store.remove(key)
    finally:
        store.tidy()


def bounded[T](seconds: float, work: Callable[[threading.Event], T]) -> T:
    """Run work for ``seconds`` at most; give its result, or raise what it raised.

    A location that does not answer — a share whose mount hangs, a storage that holds a connection —
    is said ``timed_out`` once the time is spent. The work runs in a thread of its own, a daemon: a
    call stuck in the file system cannot be interrupted, and is let go of rather than joined, so
    that it holds neither the task nor the stop of the worker.

    The work is given an event, set once the time is spent: a work let go of must not go on to do
    what the refusal said was not done — read back, or erase the older copies. A copy it wrote
    before may remain on the location.
    """
    outcome: list[T] = []
    failed: list[BaseException] = []
    abandoned = threading.Event()

    def run() -> None:
        try:
            outcome.append(work(abandoned))
        except LocationRefusedError as refused:
            failed.append(refused)
        except BaseException as error:
            # A fault of the program, handed to the caller as it is: the thread has no one to tell.
            logger.exception("location.copy_failed")
            failed.append(error)

    thread = threading.Thread(target=run, name="location-copy", daemon=True)
    thread.start()
    thread.join(seconds)
    if thread.is_alive():
        abandoned.set()
        raise LocationRefusedError(TIMED_OUT)
    if failed:
        raise failed[0]
    return outcome[0]


def try_location(
    location: DeclaredLocation,
    folder: str,
    opened: Callable[[DeclaredLocation], ExternalStore] = store_of,
    timeout: float = TEST_TIMEOUT,
) -> Failure | None:
    """Test a location: a witness written, then erased; give why it failed, ``None`` if it did not.

    The test waits ``timeout`` seconds at most: a location that does not answer by then is said
    ``timed_out``, and the test is left to end on its own, in its thread.
    """
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="location-test")

    def test() -> None:
        with reached(location, opened) as store:
            witness_test(store, folder)

    running = pool.submit(test)
    try:
        running.result(timeout=timeout)
    except Late:
        return "timed_out"
    except LocationRefusedError as refused:
        return refused.failure
    finally:
        pool.shutdown(wait=False)
    return None
