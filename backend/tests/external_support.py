# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the external locations share: a share, a bucket elsewhere, and their file.

The share is a folder of the test, standing for a network share mounted on the server; the bucket
elsewhere, a bucket of its own on the object storage of the tests, with the key of the tests,
standing for the bucket of another site. They are declared under the names and the descriptions of
the examples of the contract (``external_backup_locations``), as a deployment declares them: in a
file, read as the settings read it.
"""

import json
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit
from uuid import uuid4

from waterfall.platform.settings import ExternalLocations, read_external_locations
from waterfall.platform.storage import Bucket

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

STORAGE_VARIABLE = "WATERFALL_TEST_STORAGE_URL"
SHARE = "nas-siege"
BUCKET = "secours-lyon"
DESCRIPTIONS = {
    SHARE: "Partage du NAS du siège, monté sur le serveur de la plateforme.",
    BUCKET: (
        "Compartiment S3 du site de secours de Lyon, hors du centre de données de la plateforme."
    ),
}


def storage() -> tuple[str, str, str]:
    """Give the object storage of the tests: its address, its key and the secret of the key."""
    address = os.environ.get(STORAGE_VARIABLE, "")
    assert address, f"{STORAGE_VARIABLE} is not set"
    parts = urlsplit(address)
    return (
        f"{parts.scheme}://{parts.hostname}:{parts.port}",
        parts.username or "",
        parts.password or "",
    )


@contextmanager
def bucket_elsewhere() -> Generator[Bucket]:
    """Give a bucket of its own on the storage of the tests, emptied and deleted after."""
    endpoint, key, secret = storage()
    name = f"waterfall-elsewhere-{uuid4().hex}"
    bucket = Bucket.connect(name, endpoint, "us-east-1", key, secret)
    bucket.client.create_bucket(Bucket=name)
    try:
        yield bucket
    finally:
        for listed in bucket.client.list_objects_v2(Bucket=name).get("Contents", []):
            bucket.client.delete_object(Bucket=name, Key=listed.get("Key", ""))
        bucket.client.delete_bucket(Bucket=name)
        bucket.client.close()


def declaration(share: Path, bucket: Bucket, **changes: dict[str, Any]) -> dict[str, Any]:
    """Declare the share and the bucket as a deployment does; ``changes`` change a location."""
    endpoint, key, secret = storage()
    declared: dict[str, dict[str, Any]] = {
        SHARE: {
            "kind": "mounted_share",
            "description": DESCRIPTIONS[SHARE],
            "directory": str(share),
        },
        BUCKET: {
            "kind": "s3",
            "description": DESCRIPTIONS[BUCKET],
            "address": endpoint,
            "bucket": bucket.name,
            "access_key": key,
            "secret_key": secret,
        },
    }
    for name, changed in changes.items():
        declared[name] = declared[name] | changed
    return declared


def declared(folder: Path, declaration: dict[str, Any]) -> ExternalLocations:
    """Write a declaration in a file, and read it back as the settings do."""
    path = folder / "external-locations.json"
    path.write_text(json.dumps(declaration), encoding="utf-8")
    return read_external_locations(path)


def objects(bucket: Bucket, prefix: str = "") -> list[str]:
    """List the keys of the objects of a bucket under a prefix."""
    listed = bucket.client.list_objects_v2(Bucket=bucket.name, Prefix=prefix)
    return sorted(each.get("Key", "") for each in listed.get("Contents", []))
