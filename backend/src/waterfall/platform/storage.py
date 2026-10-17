# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The object storage, reached by the standard operations of S3 alone (PBS-3.3, WF-ARC-0050).

Writing, reading and the multipart upload that boto3 makes of a large file — or that a deposit by
parts makes, a part at a time (#350): no extension of one product, so that an operator plugs in the
storage they already run — Garage on the platforms of Waterfall. The buckets are settings. A storage
that cannot be reached refuses as a component that is unavailable (503), never as a failure of the
service; an object that is missing is said apart.
"""

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from waterfall.platform.errors import UnavailableError
from waterfall.platform.settings import ServiceSettings

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_s3.type_defs import CompletedPartTypeDef

COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
OBJECT_STORAGE = "object_storage"
# What a stream of an object reads at a time.
CHUNK = 1 << 20
# The codes by which S3 says an object, or a deposit in parts, is not there.
MISSING = {"NoSuchKey", "NoSuchUpload", "404"}
# How many parts S3 lists at a time.
PARTS_PAGE = 1000


class MissingObjectError(Exception):
    """The bucket holds no object under the key."""


def unavailable() -> UnavailableError:
    """Refuse as the contract does when the object storage does not answer (503)."""
    return UnavailableError(COMPONENT_UNAVAILABLE, {"component": OBJECT_STORAGE})


@contextmanager
def reached() -> Generator[None]:
    """Say a storage that does not answer, or refuses, as unavailable; a missing object apart."""
    try:
        yield
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in MISSING:
            raise MissingObjectError from error
        raise unavailable() from error
    except BotoCoreError as error:
        raise unavailable() from error


class Bucket:
    """A bucket of the object storage, and what Waterfall does with its objects."""

    def __init__(self, client: "S3Client", name: str) -> None:
        self.client = client
        self.name = name

    @classmethod
    def connect(
        cls, name: str, address: str, region: str, access_key: str, secret_key: str
    ) -> "Bucket":
        """Open a bucket of the storage at an address, signing with a key and its secret.

        The addresses are by path, which every storage serves; a checksum is sent and checked only
        where S3 requires one, as every storage accepts.
        """
        config = Config(
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=60,
            retries={"mode": "standard", "max_attempts": 3},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
        client: S3Client = boto3.client(
            "s3",
            endpoint_url=address,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config,
        )
        return cls(client, name)

    @classmethod
    def of_backups(cls, settings: ServiceSettings) -> "Bucket":
        """Open the bucket of the backups the settings name."""
        return cls.connect(
            settings.backups_bucket,
            settings.storage_address,
            settings.storage_region,
            settings.storage_access_key,
            settings.storage_secret.get_secret_value(),
        )

    def upload(self, key: str, path: Path) -> None:
        """Write a file under a key, in parts if it is large; an object there is replaced."""
        with reached():
            self.client.upload_file(str(path), self.name, key)

    def download(self, key: str, path: Path) -> None:
        """Read the object of a key into a file."""
        with reached():
            self.client.download_file(self.name, key, str(path))

    def stream(self, key: str) -> Iterator[bytes]:
        """Open the object of a key, to be read as a stream of chunks.

        Refused before the first chunk if the object is missing or the storage does not answer.
        """
        with reached():
            body = self.client.get_object(Bucket=self.name, Key=key)["Body"]
        return body.iter_chunks(CHUNK)

    def open_parts(self, key: str) -> str:
        """Open the deposit in parts of an object under a key; give the identifier S3 gives it."""
        with reached():
            return self.client.create_multipart_upload(Bucket=self.name, Key=key)["UploadId"]

    def put_part(self, key: str, deposit: str, number: int, content: bytes) -> None:
        """Write a part of a deposit, by its number; a part written again is replaced."""
        with reached():
            self.client.upload_part(
                Bucket=self.name, Key=key, UploadId=deposit, PartNumber=number, Body=content
            )

    def parts(self, key: str, deposit: str) -> dict[int, str]:
        """Give the parts a deposit has received, by their number, with the tag S3 gave each."""
        received: dict[int, str] = {}
        marker = 0
        with reached():
            while True:
                page = self.client.list_parts(
                    Bucket=self.name,
                    Key=key,
                    UploadId=deposit,
                    PartNumberMarker=marker,
                    MaxParts=PARTS_PAGE,
                )
                for part in page.get("Parts", []):
                    received[part.get("PartNumber", 0)] = part.get("ETag", "")
                if not page.get("IsTruncated"):
                    return received
                marker = page.get("NextPartNumberMarker", 0)

    def assemble(self, key: str, deposit: str, parts: dict[int, str]) -> None:
        """Make the object of a deposit of its parts, in the order of their numbers."""
        listed: list[CompletedPartTypeDef] = [
            {"PartNumber": number, "ETag": tag} for number, tag in sorted(parts.items())
        ]
        with reached():
            self.client.complete_multipart_upload(
                Bucket=self.name, Key=key, UploadId=deposit, MultipartUpload={"Parts": listed}
            )

    def size(self, key: str) -> int | None:
        """Give the size of the object of a key; ``None`` if there is none."""
        try:
            with reached():
                return self.client.head_object(Bucket=self.name, Key=key)["ContentLength"]
        except MissingObjectError:
            return None

    def head(self, key: str, length: int) -> bytes:
        """Read the first bytes of an object, ``length`` at most."""
        with reached():
            body = self.client.get_object(Bucket=self.name, Key=key, Range=f"bytes=0-{length - 1}")
            return body["Body"].read()
