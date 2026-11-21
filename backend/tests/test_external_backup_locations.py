# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The external locations of the backups: declared by a file, listed without secrets, tested.

``listExternalBackupLocations`` and ``testExternalBackupLocation`` (US-2910/L3) on the database of
the test and the realm of test, every answer checked against the contract; the locations are a
folder of the test, standing for a mounted share, and a bucket of its own on the object storage of
the tests, standing for the bucket of another site (``external_support``). The file that declares
them is read as the settings read it, its secrets masked in the logs and never served.
"""

import json
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from access_rows import account, role
from external_support import (
    BUCKET,
    SHARE,
    bucket_elsewhere,
    declaration,
    declared,
    objects,
    storage,
    unvalidated,
)
from fastapi.testclient import TestClient
from realm import KEY, TestRealm
from support import PLATFORM_SECRETS, ContractClient, bearer, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform import authority
from waterfall.platform.external_locations import (
    ExternalStore,
    LocationRefusedError,
    ShareStore,
    try_location,
)
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.settings import (
    ExternalLocations,
    MountedShare,
    SettingsError,
    load_service_settings,
)

if TYPE_CHECKING:
    from openapi_core import OpenAPI

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.settings import DeclaredLocation, ServiceSettings
    from waterfall.platform.storage import Bucket

pytestmark = pytest.mark.story("US-2910")

LOCATIONS = "/api/v1/external-backup-locations"
READ = "backups.read"
WRITE = "backups.write"
EXAMPLES = Path(__file__).resolve().parents[2] / "fixtures" / "api"

type Person = Callable[..., dict[str, str]]
type ApiOn = Callable[[ExternalLocations], ContractClient]


def example(name: str) -> Any:
    """Read the value of an example of the contract."""
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))["value"]


@pytest.fixture
def elsewhere() -> Iterator[Bucket]:
    with bucket_elsewhere() as bucket:
        yield bucket


@pytest.fixture
def share(tmp_path: Path) -> Path:
    folder = tmp_path / "share"
    folder.mkdir()
    return folder


@pytest.fixture
def api_on(
    contract: OpenAPI, database: Database, keycloak: Keycloak, realm_settings: ServiceSettings
) -> ApiOn:
    """Give a maker of clients of the API on an installation that declares locations."""

    def client(locations: ExternalLocations) -> ContractClient:
        administration = KeycloakAdmin(keycloak, realm_settings)
        services = Services(
            database, keycloak, administration, *nowhere(), external_locations=locations
        )
        return ContractClient(
            TestClient(create_app(services), raise_server_exceptions=False), contract
        )

    return client


@pytest.fixture
def located(api_on: ApiOn, tmp_path: Path, share: Path, elsewhere: Bucket) -> ContractClient:
    """Give a client of the API on an installation that declares the share and the bucket."""
    return api_on(declared(tmp_path, declaration(share, elsewhere)))


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts, each holding a role of the permissions given: its header."""

    def make(*permissions: str) -> dict[str, str]:
        subject = f"subject-{uuid4()}"
        held = role(database, f"Rôle {uuid4().hex[:8]}", permissions=permissions)
        account(database, "Martin", uuid4().hex[:8], roles=(held,), idp_subject=subject)
        return bearer(realm.token(subject, KEY))

    return make


def test_the_locations_the_file_declares_are_served_by_their_names_without_any_secret(
    located: ContractClient, person: Person
) -> None:
    # Proper to US-2910: « les emplacements sont ceux que la configuration de déploiement déclare,
    # lus sans aucun de leurs secrets » — the name, the nature, the description, in the order of
    # the names, as the example of the contract says them; neither the address, nor the bucket, nor
    # the folder mounted, nor the key, nor its secret.
    answer = located.get(LOCATIONS, headers=person(READ))
    assert answer.status_code == 200
    assert answer.json() == example("external_backup_locations")
    endpoint, key, secret = storage()
    for hidden in (endpoint, key, secret, "waterfall-elsewhere-", "/share"):
        assert hidden not in answer.text


def test_an_installation_that_declares_no_location_lists_none(
    api_on: ApiOn, person: Person
) -> None:
    answer = api_on(ExternalLocations()).get(LOCATIONS, headers=person(READ))
    assert answer.status_code == 200
    assert answer.json() == example("external_backup_locations_none")


def test_the_locations_are_read_and_tested_only_under_the_permissions_of_the_backups(
    located: ContractClient, person: Person
) -> None:
    # Listed under the permission to read the backups (404 without it), tested under the one to
    # change them besides (403 without it), as the contract says (WF-ADM-0100).
    nothing, reader = person(), person(READ)
    assert located.get(LOCATIONS, headers=nothing).status_code == 404
    assert located.post(f"{LOCATIONS}/{SHARE}/test", headers=nothing).status_code == 404
    refused = located.post(f"{LOCATIONS}/{SHARE}/test", headers=reader)
    assert (refused.status_code, refused.json()["params"]) == (403, {"missing_permission": WRITE})


@pytest.mark.parametrize("name", [BUCKET, SHARE])
def test_a_location_tested_takes_a_witness_file_and_keeps_nothing(
    located: ContractClient, person: Person, share: Path, elsewhere: Bucket, name: str
) -> None:
    # A test writes a witness file in the folder given, reads it back, erases it: succeeded, the
    # failure null, nothing left in the location; at its root, the same.
    tester = person(READ, WRITE)
    path = "waterfall/sauvegardes"
    answer = located.post(f"{LOCATIONS}/{name}/test", headers=tester, json={"path": path})
    assert answer.status_code == 200, answer.text
    tested = answer.json()
    assert (tested["location"], tested["path"], tested["failure"]) == (name, path, None)
    rooted = located.post(f"{LOCATIONS}/{name}/test", headers=tester)
    assert rooted.status_code == 200
    assert (rooted.json()["path"], rooted.json()["failure"]) == (None, None)
    assert objects(elsewhere) == []
    assert list(share.rglob("*")) == []


def test_a_location_that_refuses_its_key_or_does_not_answer_says_why_as_a_code(
    api_on: ApiOn, person: Person, tmp_path: Path, share: Path, elsewhere: Bucket
) -> None:
    # « le motif de l'échec en code » (WF-ARC-0110): a key refused is an access denied; a storage
    # that does not answer, a share not mounted, are unreachable. The test answers 200 all the same.
    gone = tmp_path / "not-mounted"
    refusing = declaration(
        share,
        elsewhere,
        **{BUCKET: {"secret_key": "not-the-secret"}, SHARE: {"directory": str(gone)}},
    )
    unreachable = declaration(share, elsewhere, **{BUCKET: {"address": "http://127.0.0.1:9"}})
    tester = person(READ, WRITE)
    for locations, name, failure in (
        (declared(tmp_path, refusing), BUCKET, "access_denied"),
        (declared(tmp_path, refusing), SHARE, "location_unreachable"),
        (declared(tmp_path, unreachable), BUCKET, "location_unreachable"),
    ):
        answer = api_on(locations).post(f"{LOCATIONS}/{name}/test", headers=tester)
        assert answer.status_code == 200, answer.text
        assert answer.json()["failure"] == failure, name
    assert not gone.exists()


def test_a_location_not_declared_is_not_found_and_a_folder_that_leaves_it_is_refused(
    located: ContractClient, person: Person, share: Path
) -> None:
    # 404 for a name the installation does not declare, well formed or not; 422 ``PATH_INVALID`` on
    # ``/path`` for a folder absolute or that climbs, as the example says, before anything is
    # written; a folder sent null is refused too.
    tester = person(READ, WRITE)
    for unknown in ("secours-paris", "Secours"):
        assert located.post(f"{LOCATIONS}/{unknown}/test", headers=tester).status_code == 404
    expected = example("external_backup_location_test_path_invalid")
    for path in ("/sauvegardes", "../ailleurs", "a/./b"):
        refused = located.post(f"{LOCATIONS}/{BUCKET}/test", headers=tester, json={"path": path})
        assert refused.status_code == 422
        assert refused.json()["fields"] == expected["fields"]
    sent_null = located.post(f"{LOCATIONS}/{SHARE}/test", headers=tester, json={"path": None})
    assert (sent_null.status_code, sent_null.json()["fields"][0]["pointer"]) == (422, "/path")
    assert list(share.iterdir()) == []


class Silent:
    """A location that never answers a writing, until the test lets it go."""

    def __init__(self, released: threading.Event) -> None:
        self.released = released

    def put(self, key: str, path: Path) -> None:
        del key, path
        self.released.wait(10)

    def read_back(self, key: str) -> tuple[int, str]:
        del key
        return 0, ""

    def names(self, folder: str) -> list[str]:
        del folder
        return []

    def remove(self, key: str) -> None:
        del key

    def tidy(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_a_location_that_does_not_answer_within_the_bound_is_said_timed_out(share: Path) -> None:
    # The test waits thirty seconds at most (`testExternalBackupLocation`): past its bound, a
    # location that does not answer is ``timed_out``, and the answer does not wait for it.
    released = threading.Event()

    def opened(_location: DeclaredLocation) -> ExternalStore:
        return Silent(released)

    location = MountedShare(kind="mounted_share", directory=str(share))
    try:
        assert try_location(location, "", opened, timeout=0.2) == "timed_out"
    finally:
        released.set()


def test_a_share_writes_nothing_outside_the_folder_mounted(share: Path, tmp_path: Path) -> None:
    # A folder of the share that is a link to elsewhere is refused as an access denied: nothing is
    # written outside the folder mounted, whatever the share holds.
    outside = tmp_path / "outside"
    outside.mkdir()
    (share / "escape").symlink_to(outside)
    store = ShareStore(share)
    witness = tmp_path / "witness.txt"
    witness.write_text("témoin", encoding="utf-8")
    with pytest.raises(LocationRefusedError) as refused:
        store.put("escape/copy.tar", witness)
    assert refused.value.failure == "access_denied"
    assert list(outside.iterdir()) == []


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch, platform_environment: dict[str, str]) -> None:
    """Give the settings of a service the environment of the test platform."""
    for name, value in platform_environment.items():
        monkeypatch.setenv(name, value)


@pytest.mark.usefixtures("environment")
def test_the_settings_read_the_locations_of_their_file_and_mask_their_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, share: Path, elsewhere: Bucket
) -> None:
    # The file the deployment mounts, named by WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE, is read at
    # start; the key and the secret of a bucket are secrets of the process, which its logs mask
    # (WF-OBS-0020), and none is in the text of the settings.
    path = tmp_path / "locations.json"
    path.write_text(json.dumps(declaration(share, elsewhere)), encoding="utf-8")
    monkeypatch.setenv("WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE", str(path))
    settings = load_service_settings()
    assert settings.external_locations.names() == {SHARE, BUCKET}
    _, key, secret = storage()
    assert {key, secret} <= set(settings.secret_values())
    assert secret not in repr(settings.external_locations)
    monkeypatch.setenv("WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE", "")
    assert load_service_settings().external_locations.names() == frozenset()


@pytest.mark.usefixtures("environment")
def test_a_file_of_locations_in_default_stops_the_start_naming_it_without_its_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A file that cannot be read, that is not JSON, or that declares a location badly stops the
    # process, the variable and the place of the fault named; no value of the file is repeated.
    path = tmp_path / "locations.json"
    monkeypatch.setenv("WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE", str(path))
    with pytest.raises(SettingsError, match="cannot be read"):
        load_service_settings()
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SettingsError, match="is not JSON"):
        load_service_settings()
    secret = uuid4().hex
    bad = {"Lyon": {"kind": "s3", "address": "ftp://elsewhere", "secret_key": secret, "x": 1}}
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SettingsError) as refused:
        load_service_settings()
    said = str(refused.value)
    assert "WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE" in said
    assert "Lyon.[key]" in said
    assert "Lyon.s3.address" in said
    assert secret not in said
    assert "ftp://elsewhere" not in said
    carried = {
        "lyon": {
            "kind": "s3",
            "address": f"https://key:{secret}@elsewhere.example",
            "bucket": "copies",
            "access_key": "key",
            "secret_key": secret,
        }
    }
    path.write_text(json.dumps(carried), encoding="utf-8")
    with pytest.raises(SettingsError, match="must not carry credentials") as carrying:
        load_service_settings()
    assert secret not in str(carrying.value)


# The addresses of the platform in TLS, as a process given the root of the platform reads them.
VERIFIED = "sslmode=verify-full&sslrootcert=/trust/root.crt"
ENCRYPTED = {
    "WATERFALL_DATABASE_URL": f"{PLATFORM_SECRETS['WATERFALL_DATABASE_URL']}?{VERIFIED}",
    "WATERFALL_REDIS_URL": PLATFORM_SECRETS["WATERFALL_REDIS_URL"].replace("redis:", "rediss:", 1),
    "WATERFALL_KEYCLOAK_ADDRESS": "https://keycloak:8443/auth",
    "WATERFALL_STORAGE_ADDRESS": "https://storage:3900",
}


@pytest.mark.usefixtures("environment")
def test_a_bucket_reached_in_the_clear_is_refused_when_the_platform_has_its_authority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, share: Path, elsewhere: Bucket
) -> None:
    # US-2840: with the root of the platform given, every address is reached in TLS, a location's
    # too; in https://, it is read.
    provided = tmp_path / "provided"
    provided.mkdir()
    authority.run(provided, tmp_path / "kept", tmp_path / "trust", tmp_path / "certificates", [])
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(tmp_path / "trust" / "root.crt"))
    for name, value in ENCRYPTED.items():
        monkeypatch.setenv(name, value)
    path = tmp_path / "locations.json"
    path.write_text(json.dumps(declaration(share, elsewhere)), encoding="utf-8")
    monkeypatch.setenv("WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE", str(path))
    with pytest.raises(SettingsError, match=f"the address of {BUCKET} must be in https://"):
        load_service_settings()
    encrypted = {BUCKET: {"address": "https://elsewhere.example:3900"}}
    path.write_text(json.dumps(declaration(share, elsewhere, **encrypted)), encoding="utf-8")
    assert load_service_settings().external_locations.names() == {SHARE, BUCKET}


def test_a_test_removes_only_the_folders_it_created_on_a_share(
    located: ContractClient, person: Person, share: Path
) -> None:
    # « Rien n'est laissé » (testExternalBackupLocation): a folder that was there stays, those the
    # test created under it go, a deeper path included.
    (share / "waterfall").mkdir()
    tester = person(READ, WRITE)
    answer = located.post(
        f"{LOCATIONS}/{SHARE}/test", headers=tester, json={"path": "waterfall/a/b/c"}
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["failure"] is None
    assert [each.relative_to(share).as_posix() for each in share.rglob("*")] == ["waterfall"]


def test_a_share_file_already_removed_is_not_a_failure_to_remove(share: Path) -> None:
    # Two copies that turn the same folder both remove the oldest: the second finds it gone.
    store = ShareStore(share)
    (share / "old.tar").write_bytes(b"x")
    store.remove("old.tar")
    store.remove("old.tar")
    assert list(share.iterdir()) == []


@pytest.mark.parametrize("changes", [{"region": "us east"}, {"address": "http://"}])
def test_a_location_the_client_cannot_open_is_unreachable_not_a_server_error(
    api_on: ApiOn,
    person: Person,
    share: Path,
    elsewhere: Bucket,
    changes: dict[str, str],
) -> None:
    # A region or an address the S3 client refuses to open (a file read before the settings bounded
    # them) is diagnosed as the location out of reach: 200 and the reason, never a 500.
    declared_now = declared(share.parent, declaration(share, elsewhere))
    locations = unvalidated(declared_now, BUCKET, **changes)
    answer = api_on(locations).post(f"{LOCATIONS}/{BUCKET}/test", headers=person(READ, WRITE))
    assert answer.status_code == 200, answer.text
    assert answer.json()["failure"] == "location_unreachable"


@pytest.mark.usefixtures("environment")
@pytest.mark.parametrize(
    ("changes", "rule"),
    [
        ({"region": "us east"}, "region"),
        ({"region": "-us"}, "region"),
        ({"address": "http://"}, "must name a host"),
        ({"address": "https://elsewhere.example/?token=SECRET-TOKEN"}, "no query nor fragment"),
        ({"address": "https://elsewhere.example/#SECRET-TOKEN"}, "no query nor fragment"),
    ],
)
def test_a_location_with_an_unusable_region_or_address_stops_the_start_without_its_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, changes: dict[str, str], rule: str
) -> None:
    # A region botocore refuses, an address with no host, one that carries a token in its query or
    # its fragment, are refused when the file is read; the value is never repeated.
    base = {
        "kind": "s3",
        "address": "https://elsewhere.example",
        "bucket": "copies",
        "access_key": "key",
        "secret_key": "secret-of-the-key",
    }
    path = tmp_path / "locations.json"
    path.write_text(json.dumps({"lyon": base | changes}), encoding="utf-8")
    monkeypatch.setenv("WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE", str(path))
    with pytest.raises(SettingsError, match=rule) as refused:
        load_service_settings()
    said = str(refused.value)
    assert "SECRET-TOKEN" not in said
    assert "us east" not in said
