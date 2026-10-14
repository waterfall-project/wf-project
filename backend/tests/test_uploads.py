# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The deposit by parts of a backup copied out of a platform, and its restoration (#350).

The deposits are made through the API of an installation of the tests (``installations``), on the
object storage of the tests; a backup taken on one installation, copied out, deposited on another
and restored there by the service of the restoration makes it a copy of the first.
"""

import hashlib
import io
import json
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from fastapi.testclient import TestClient
from httpx2 import Response
from installations import Installation, Provider, Take, installed, restorer_headers
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import insert, select
from support import ContractClient, bearer

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.backups.interface import MANIFEST, archive_taken_at
from waterfall.core.backups.tables import Backup
from waterfall.core.users.tables import UserAccount
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.installation import THE_ROW
from waterfall.platform.installation import Installation as InstallationRow
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.maintenance import SUFFIX, Maintenance
from waterfall.platform.queue import RESTORES as RESTORES_SUFFIX
from waterfall.platform.queue import TaskQueue
from waterfall.platform.settings import ServiceSettings
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import LARGEST_PART, MOST_PARTS, SMALLEST_PART, FileUpload, cut
from waterfall.restore.runner import Restorer
from waterfall.restore.task import RestoreTask
from waterfall.worker.runner import Timing

DEPOSITS = "/api/v1/chunked-uploads"
RESTORES = "/api/v1/restores"
GIBIBYTE = 1024**3
TAKEN_AT = datetime(2026, 6, 2, 1, tzinfo=UTC)


def settled(installation: Installation, language: str = "fr", bound: int = 20 * GIBIBYTE) -> None:
    """Write the row of the installation, as its bootstrap does, as the owner of the tables."""
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        connection.execute(
            insert(InstallationRow).values(
                id=THE_ROW,
                default_language=language,
                avatar_max_bytes=2 * 1024**2,
                external_backup_max_bytes=bound,
                installed_at=utc_now(),
            )
        )
    owner.dispose()


def iso(at: datetime) -> str:
    """Write an instant as the API does."""
    return at.isoformat().replace("+00:00", "Z")


def manifest_of(taken_at: str, **more: object) -> dict[str, object]:
    """Write the manifest of a backup of this version taken at ``taken_at``, saying ``more``."""
    return {"application_version": __version__, "taken_at": taken_at, "databases": [], **more}


def backup_archive(manifest: dict[str, object], *, first: bool = True) -> bytes:
    """Write an archive whose manifest says ``manifest``: its first member, or its second."""
    members = [(MANIFEST, json.dumps(manifest).encode()), ("waterfall.dump", b"not a dump")]
    written = io.BytesIO()
    with tarfile.open(fileobj=written, mode="w") as tar:
        for name, content in members if first else reversed(members):
            member = tarfile.TarInfo(name)
            member.size = len(content)
            tar.addfile(member, io.BytesIO(content))
    return written.getvalue()


def redated(archive: bytes, taken_at: str) -> bytes:
    """Write an archive again, each member as it was but the manifest, which says ``taken_at``."""
    written = io.BytesIO()
    with (
        tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as read,
        tarfile.open(fileobj=written, mode="w") as tar,
    ):
        for member in read.getmembers():
            content = read.extractfile(member)
            assert content is not None
            said = content.read()
            if member.name == MANIFEST:
                said = json.dumps({**json.loads(said), "taken_at": taken_at}).encode()
                member.size = len(said)
            tar.addfile(member, io.BytesIO(said))
    return written.getvalue()


def completion(
    api: ContractClient, headers: dict[str, str], content: bytes
) -> tuple[str, Response]:
    """Deposit a file by parts, as the front does, and ask for its completion; give its answer."""
    opened = api.post(
        DEPOSITS, json={"filename": "copie.tar", "size_bytes": len(content)}, headers=headers
    )
    assert opened.status_code == 201
    deposit = opened.json()
    size = deposit["part_size_bytes"]
    for number in range(1, deposit["part_count"] + 1):
        part = content[(number - 1) * size : number * size]
        sent = api.request(
            "PUT",
            f"{DEPOSITS}/{deposit['chunked_upload_id']}/parts/{number}",
            content=part,
            headers={**headers, "Content-Type": "application/octet-stream"},
        )
        assert sent.status_code == 200
    upload_id = deposit["chunked_upload_id"]
    return upload_id, api.post(f"{DEPOSITS}/{upload_id}/completion", headers=headers)


def deposited(api: ContractClient, headers: dict[str, str], content: bytes) -> dict[str, object]:
    """Deposit a file by parts, as the front does, and complete it; give the deposit completed."""
    _, completed = completion(api, headers, content)
    assert completed.status_code == 201
    return completed.json()


def test_a_file_is_cut_into_the_fewest_parts_the_bounds_let() -> None:
    # 5 MiB at least but the last, 10 MiB at most, 10 000 parts at most.
    one = cut(1)
    assert one is not None
    assert (one.part_size_bytes, one.part_count) == (SMALLEST_PART, 1)
    held = cut(MOST_PARTS * SMALLEST_PART + 1)
    assert held is not None
    assert held.part_size_bytes > SMALLEST_PART
    assert held.part_count <= MOST_PARTS
    assert cut(MOST_PARTS * LARGEST_PART) is not None
    assert cut(MOST_PARTS * LARGEST_PART + 1) is None


def test_a_deposit_beyond_the_bound_of_the_installation_is_refused_before_any_part(
    installation: Installation, installation_api: ContractClient, realm: TestRealm
) -> None:
    settled(installation, bound=GIBIBYTE)
    headers = restorer_headers(installation, realm)
    for size in (GIBIBYTE + 1, MOST_PARTS * LARGEST_PART + 1):
        refused = installation_api.post(
            DEPOSITS, json={"filename": "copie.tar", "size_bytes": size}, headers=headers
        )
        assert (refused.status_code, refused.json()["code"]) == (413, "FILE_TOO_LARGE")
    with installation.database.transaction() as session:
        assert session.scalars(select(FileUpload)).all() == []


def test_parts_received_in_any_order_are_assembled_into_the_file_deposited(
    installation: Installation, installation_api: ContractClient, realm: TestRealm
) -> None:
    # Two parts, the last first; a part of the wrong size is refused, naming the size expected,
    # and a number the deposit does not count is not found; a part sent again replaces it. A part
    # lacking refuses the completion, naming it; completed, the deposit receives nothing more.
    settled(installation)
    headers = restorer_headers(installation, realm)
    head = backup_archive(manifest_of(iso(TAKEN_AT)))
    content = head + bytes(range(256)) * ((SMALLEST_PART - len(head)) // 256) + b"the rest"
    opened = installation_api.post(
        DEPOSITS, json={"filename": "copie.tar", "size_bytes": len(content)}, headers=headers
    ).json()
    assert (opened["part_size_bytes"], opened["part_count"], opened["received_parts"]) == (
        SMALLEST_PART,
        2,
        [],
    )
    deposit = f"{DEPOSITS}/{opened['chunked_upload_id']}"
    octets = {**headers, "Content-Type": "application/octet-stream"}
    wrong = installation_api.request("PUT", f"{deposit}/parts/2", content=b"short", headers=octets)
    assert wrong.status_code == 422
    assert wrong.json()["fields"][0]["params"] == {"minimum": 8, "maximum": 8}
    beyond = installation_api.request(
        "PUT", f"{deposit}/parts/3", content=b"the rest", headers=octets
    )
    assert beyond.status_code == 404
    last = installation_api.request(
        "PUT", f"{deposit}/parts/2", content=b"the rest", headers=octets
    )
    assert last.json()["received_parts"] == [2]
    lacking = installation_api.post(f"{deposit}/completion", headers=headers)
    assert (lacking.status_code, lacking.json()["params"]) == (409, {"missing_parts": [1]})
    for _ in range(2):
        first = installation_api.request(
            "PUT", f"{deposit}/parts/1", content=content[:SMALLEST_PART], headers=octets
        )
        assert first.json()["received_parts"] == [1, 2]
    completed = installation_api.post(f"{deposit}/completion", headers=headers)
    assert completed.status_code == 201
    assert completed.json()["purpose"] == "external_backup"
    # The date the manifest says, at the head of the archive (#1006).
    assert completed.json()["backup_taken_at"] == iso(TAKEN_AT)
    assert installation_api.post(f"{deposit}/completion", headers=headers).status_code == 404
    gone = installation_api.request(
        "PUT", f"{deposit}/parts/1", content=b"the rest", headers=octets
    )
    assert gone.status_code == 404
    with installation.database.transaction() as session:
        key = session.get_one(FileUpload, UUID(opened["chunked_upload_id"])).object_key
    stored = installation.bucket.client.get_object(Bucket=installation.bucket.name, Key=key)
    assert hashlib.sha256(stored["Body"].read()).digest() == hashlib.sha256(content).digest()


@pytest.mark.requirement("WF-ADM-0160-A")
@pytest.mark.parametrize(
    "content",
    [
        backup_archive(manifest_of(iso(TAKEN_AT)), first=False),
        backup_archive(manifest_of("2026-06-02T01:00:00")),
        backup_archive(manifest_of(iso(TAKEN_AT), padding="x" * (64 * 1024))),
    ],
    ids=["second", "without-time-zone", "beyond-the-head"],
)
def test_a_deposit_whose_date_does_not_read_is_refused_and_never_restored(
    content: bytes, installation: Installation, installation_api: ContractClient, realm: TestRealm
) -> None:
    # « La confirmation nomme la date de la sauvegarde. » of WF-ADM-0160-A: an archive whose
    # manifest is not its first member, whose head does not hold it whole, or whose date says no
    # time zone has no date a confirmation could name. Its completion is refused (422), the deposit
    # left uncompleted, which no restoration names: nothing is queued.
    settled(installation)
    headers = restorer_headers(installation, realm)
    upload_id, refused = completion(installation_api, headers, content)
    assert (refused.status_code, refused.json()["code"]) == (422, "FILE_FORMAT_UNREADABLE")
    asked = {
        "external_backup_upload_id": upload_id,
        "confirmed": True,
        "acknowledged_backup_taken_at": iso(TAKEN_AT),
    }
    assert installation_api.post(RESTORES, json=asked, headers=headers).status_code == 404
    with installation.database.transaction() as session:
        assert session.get_one(FileUpload, UUID(upload_id)).completed_at is None
        assert (
            session.scalars(select(BackgroundTask).where(BackgroundTask.kind == "restore")).all()
            == []
        )


@dataclass(frozen=True, slots=True)
class Target:
    """Another installation, its API, and the queue its API and its restorations share."""

    installation: Installation
    api: ContractClient
    queue: TaskQueue

    def restorer(self) -> Restorer:
        """Give the service of the restoration of this installation; Keycloak stands aside."""
        owner = Database(create_database_engine(self.installation.owner["waterfall"]))
        maintenance = Maintenance.of(self.queue)
        task = RestoreTask(
            self.installation.owner, self.installation.bucket, maintenance, Provider([]), upgrade
        )
        restorer = Restorer(owner, self.queue, task, "restorer-target", Timing(0, 0.1))
        restorer.queue.prepare()
        return restorer


@pytest.fixture
def target_installation(
    database_url: str, backup_role: tuple[str, str], installation: Installation
) -> Iterator[Installation]:
    """Give another installation, on the same server and the same bucket."""
    yield from installed(database_url, backup_role, installation.bucket)


@pytest.fixture
def target(
    target_installation: Installation,
    queue: TaskQueue,
    contract: OpenAPI,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
) -> Iterator[Target]:
    """Serve the API on another installation, on a queue of its own, deleted after."""
    own = TaskQueue(queue.client, f"{queue.stream}:target")
    services = Services(
        target_installation.database,
        keycloak,
        KeycloakAdmin(keycloak, realm_settings),
        own,
        target_installation.bucket,
        Maintenance.of(own),
    )
    client = TestClient(create_app(services), raise_server_exceptions=False)
    yield Target(target_installation, ContractClient(client, contract), own)
    own.client.delete(own.stream, own.stream + RESTORES_SUFFIX, own.stream + SUFFIX)


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_backup_copied_deposited_and_restored_on_another_installation_makes_it_a_copy(
    installation: Installation,
    target: Target,
    take: Take,
    realm: TestRealm,
    installation_api: ContractClient,
) -> None:
    # Proper to US-0440: « une sauvegarde prise sur une installation, téléchargée, puis déposée
    # sur une autre installation de même version ou plus récente et restaurée, y rend les
    # comptes, les rôles et les réglages de la première, et l'administrateur de la première s'y
    # connecte ». « La confirmation nomme la date de la sauvegarde. » of WF-ADM-0160-A: the
    # deposit completed gives the date its manifest says (#1006), the one the confirmation names.
    # The restorer of the target may not read the backups: a deposit is none of the list.
    settled(installation, language="en")
    source = f"subject-{uuid4()}"
    administration = role(installation.database, "Administration de la source")
    account(installation.database, "Source", "Alix", roles=(administration,), idp_subject=source)
    take()
    with installation.database.transaction() as session:
        backup = session.scalars(select(Backup)).one()
    copied = installation_api.get(
        f"/api/v1/backups/{backup.id}/content", headers=restorer_headers(installation, realm)
    )
    assert copied.status_code == 200
    settled(target.installation)
    headers = restorer_headers(target.installation, realm, ("platform_restore",), "Dominique")
    completed = deposited(target.api, headers, copied.content)
    assert completed["backup_taken_at"] == iso(backup.taken_at)
    upload_id = str(completed["upload_id"])
    asked = {"external_backup_upload_id": upload_id, "confirmed": True}
    late = {**asked, "acknowledged_backup_taken_at": iso(backup.taken_at + timedelta(seconds=1))}
    refused = target.api.post(RESTORES, json=late, headers=headers)
    assert (refused.status_code, refused.json()["code"]) == (400, "CONFIRMATION_REQUIRED")
    confirmed = {**asked, "acknowledged_backup_taken_at": iso(backup.taken_at)}
    assert target.api.post(RESTORES, json=confirmed, headers=headers).status_code == 202
    restorer = target.restorer()
    try:
        assert restorer.step()
    finally:
        restorer.database.dispose()
    with target.installation.database.transaction() as session:
        accounts = set(session.scalars(select(UserAccount.idp_subject)))
        roles = set(session.scalars(select(AccessRole.label)))
        language = session.get_one(InstallationRow, THE_ROW).default_language
        last = session.scalars(
            select(AuditEntry).order_by(AuditEntry.occurred_at.desc(), AuditEntry.id.desc())
        ).first()
    assert source in accounts
    assert "Administration de la source" in roles
    assert language == "en"
    assert last is not None
    assert (last.action, last.object_kind, str(last.object_id)) == (
        "restore",
        "external_backup_upload",
        upload_id,
    )
    signed_in = target.api.get("/api/v1/me", headers=bearer(realm.token(source, KEY)))
    assert signed_in.status_code == 200


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_restoration_whose_whole_manifest_says_another_date_fails_before_the_maintenance(
    installation: Installation,
    target: Target,
    take: Take,
    realm: TestRealm,
    installation_api: ContractClient,
) -> None:
    # « La confirmation nomme la date de la sauvegarde. » of WF-ADM-0160-A: the task reads the
    # manifest whole, and refuses an archive whose date is not the one confirmed — replaced on the
    # storage since its completion — before the maintenance, nothing replaced.
    settled(installation)
    source = f"subject-{uuid4()}"
    account(installation.database, "Source", "Alix", idp_subject=source)
    take()
    with installation.database.transaction() as session:
        backup = session.scalars(select(Backup)).one()
    copied = installation_api.get(
        f"/api/v1/backups/{backup.id}/content", headers=restorer_headers(installation, realm)
    ).content
    settled(target.installation)
    headers = restorer_headers(target.installation, realm, ("platform_restore",), "Dominique")
    upload_id = str(deposited(target.api, headers, copied)["upload_id"])
    with target.installation.database.transaction() as session:
        key = session.get_one(FileUpload, UUID(upload_id)).object_key
    later = redated(copied, iso(backup.taken_at + timedelta(seconds=1)))
    bucket = target.installation.bucket
    bucket.client.put_object(Bucket=bucket.name, Key=key, Body=later)
    asked = {
        "external_backup_upload_id": upload_id,
        "confirmed": True,
        "acknowledged_backup_taken_at": iso(backup.taken_at),
    }
    assert target.api.post(RESTORES, json=asked, headers=headers).status_code == 202
    restorer = target.restorer()
    try:
        assert restorer.step()
    finally:
        restorer.database.dispose()
    with target.installation.database.transaction() as session:
        task = session.scalars(select(BackgroundTask).where(BackgroundTask.kind == "restore")).one()
        accounts = set(session.scalars(select(UserAccount.idp_subject)))
    assert (task.status, (task.problem or {}).get("code")) == ("failed", "FILE_FORMAT_UNREADABLE")
    assert source not in accounts
    assert Maintenance.of(target.queue).current() is None


def test_a_restoration_refuses_a_deposit_unknown_without_date_or_made_for_an_import(
    installation: Installation, installation_api: ContractClient, realm: TestRealm
) -> None:
    # A deposit unknown, or not completed, is not found (404); one made for an import is refused
    # (422, UPLOAD_PURPOSE_MISMATCH), the field that names it in fault. A deposit completed whose
    # date is not known — which its completion refuses — is one no confirmation names (400).
    headers = restorer_headers(installation, realm)
    with installation.database.transaction() as session:
        held_by = session.scalars(select(UserAccount.id)).one()
    imported, undated = uuid4(), uuid4()
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        for upload_id, purpose in ((imported, "import"), (undated, "external_backup")):
            connection.execute(
                insert(FileUpload).values(
                    id=upload_id,
                    purpose=purpose,
                    filename="planning.xml",
                    size_bytes=1,
                    part_size_bytes=SMALLEST_PART,
                    part_count=1,
                    object_key=f"uploads/{upload_id}",
                    uploaded_by=held_by,
                    created_at=utc_now(),
                    expires_at=utc_now() + timedelta(hours=1),
                    completed_at=utc_now(),
                )
            )
    owner.dispose()
    asked = {"confirmed": True, "acknowledged_backup_taken_at": iso(utc_now())}
    unknown = {**asked, "external_backup_upload_id": str(uuid4())}
    assert installation_api.post(RESTORES, json=unknown, headers=headers).status_code == 404
    mismatch = {**asked, "external_backup_upload_id": str(imported)}
    refused = installation_api.post(RESTORES, json=mismatch, headers=headers)
    assert refused.status_code == 422
    assert refused.json()["fields"] == [
        {"pointer": "/external_backup_upload_id", "code": "UPLOAD_PURPOSE_MISMATCH"}
    ]
    without = {**asked, "external_backup_upload_id": str(undated)}
    unnamed = installation_api.post(RESTORES, json=without, headers=headers)
    assert (unnamed.status_code, unnamed.json()["code"]) == (400, "CONFIRMATION_REQUIRED")


def test_the_head_of_a_file_that_is_no_archive_says_no_date() -> None:
    # The date a deposit is confirmed by is read from its manifest; a file without one says none,
    # and its completion is refused.
    assert archive_taken_at(b"not an archive") is None
    assert archive_taken_at(b"") is None
