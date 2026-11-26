# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hook of the chart issues the certificates of the data components only when due (US-2850).

``waterfall-authority secrets`` writes the Secret of a data component when it is missing, cannot be
read, was issued by another authority, holds another root or expires within six months, and leaves
it, and the pods that mount it, untouched otherwise: an upgrade does not restart PostgreSQL, Redis,
the storage or the supervision (the author's decision of 2026-11-26, #4089). A certificate renewed
restarts its workload, once, even when the hook is stopped before it could. The API of Kubernetes
is answered here by the test, as the cluster would.
"""

import base64
import copy
import json
import os
import threading
from argparse import ArgumentTypeError
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, ClassVar, override

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from waterfall.platform import authority_secrets
from waterfall.platform.authority import LEAF_LIFETIME, ROOT_LIFETIME, Authority, issued, made
from waterfall.platform.authority_secrets import (
    OWED,
    RESTARTED,
    Cluster,
    ClusterError,
    Workload,
    certify,
    due,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

pytestmark = [pytest.mark.story("US-2850"), pytest.mark.requirement("WF-EXP-0030-A")]

NOW = datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
POSTGRES = Workload("statefulsets", "waterfall-postgres")
SECRETS = "/api/v1/namespaces/waterfall/secrets"
POSTGRES_SECRET = f"{SECRETS}/waterfall-postgres-tls"
POSTGRES_WORKLOAD = "/apis/apps/v1/namespaces/waterfall/statefulsets/waterfall-postgres"


class Api:
    """The API of Kubernetes in the namespace ``waterfall``: Secrets kept, every request noted."""

    def __init__(self, workloads: set[str] | None = None) -> None:
        self.secrets: dict[str, dict[str, Any]] = {}
        self.workloads = {"/apis/apps/v1/namespaces/waterfall/statefulsets/waterfall-postgres"}
        if workloads is not None:
            self.workloads = workloads
        self.requests: list[tuple[str, str, Any]] = []
        self.refused: int | None = None
        # What a proxy in front of the API answers instead of it, as is, when given.
        self.page: bytes | None = None

    def send(self, method: str, path: str, body: Mapping[str, Any] | None) -> tuple[int, Any]:
        self.requests.append((method, path, copy.deepcopy(body)))
        if self.refused is not None:
            return self.refused, {}
        name = path.rsplit("/", 1)[-1]
        if method == "GET":
            found = self.secrets.get(name)
            return (200, copy.deepcopy(found)) if found else (404, {})
        if method == "POST" and body is not None:
            written = {**body, "metadata": {**body["metadata"], "resourceVersion": "1"}}
            self.secrets[body["metadata"]["name"]] = written
            return 201, written
        if method == "PUT" and body is not None:
            version = str(int(self.secrets[name]["metadata"]["resourceVersion"]) + 1)
            self.secrets[name] = {
                **body,
                "metadata": {**body["metadata"], "resourceVersion": version},
            }
            return 200, self.secrets[name]
        return (200, {}) if path in self.workloads else (404, {})

    def writes(self) -> list[tuple[str, str]]:
        return [(method, path) for method, path, _ in self.requests if method != "GET"]

    def cluster(self) -> Cluster:
        return Cluster("waterfall", self.send)


def leaf(data: Mapping[str, str]) -> x509.Certificate:
    return x509.load_pem_x509_certificates(base64.b64decode(data["tls.crt"]))[0]


def encoded(key: bytes, chain: bytes, root: bytes) -> dict[str, str]:
    def b64(content: bytes) -> str:
        return base64.b64encode(content).decode()

    return {"tls.key": b64(key), "tls.crt": b64(chain), "ca.crt": b64(root)}


def held_by(api: Api, authority: Authority, issued_at: datetime) -> None:
    """Give the API a Secret of PostgreSQL that the authority issued at a date."""
    key, chain = issued(authority, POSTGRES.name, issued_at)
    data = encoded(key, chain, authority.pem())
    metadata = {"name": POSTGRES.kept_in, "resourceVersion": "7"}
    api.secrets[POSTGRES.kept_in] = {"kind": "Secret", "metadata": metadata, "data": data}


@pytest.fixture(scope="module")
def authority() -> Authority:
    return made(NOW - timedelta(days=1000))


def test_a_missing_certificate_is_issued_into_the_secret_its_pods_mount(
    authority: Authority,
) -> None:
    api = Api()
    assert certify(api.cluster(), authority, POSTGRES, NOW) == "issued (missing)"
    assert api.writes() == [("POST", SECRETS)]
    secret = api.secrets["waterfall-postgres-tls"]
    assert secret["type"] == "kubernetes.io/tls"
    data = secret["data"]
    certificate = leaf(data)
    certificate.verify_directly_issued_by(authority.issuer)
    names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "waterfall-postgres" in names.get_values_for_type(x509.DNSName)
    key = serialization.load_pem_private_key(base64.b64decode(data["tls.key"]), password=None)
    assert key.public_key() == certificate.public_key()
    assert base64.b64decode(data["ca.crt"]) == authority.pem()


def test_an_upgrade_that_finds_the_certificate_valid_writes_nothing_and_restarts_nothing(
    authority: Authority,
) -> None:
    # « Une mise à jour […] sans qu'aucun utilisateur ne soit déconnecté » : the Secret stays as it
    # is, and so do the pods of Redis, which hold the sessions.
    api = Api()
    certify(api.cluster(), authority, POSTGRES, NOW)
    before = copy.deepcopy(api.secrets)
    api.requests.clear()
    later = NOW + LEAF_LIFETIME - authority_secrets.RENEW_BEFORE - timedelta(days=1)
    assert certify(api.cluster(), authority, POSTGRES, later) is None
    assert api.writes() == []
    assert api.secrets == before


def test_a_certificate_close_to_its_end_is_renewed_and_its_workload_restarted_once(
    authority: Authority,
) -> None:
    api = Api()
    held_by(
        api, authority, NOW - LEAF_LIFETIME + authority_secrets.RENEW_BEFORE - timedelta(days=1)
    )
    assert certify(api.cluster(), authority, POSTGRES, NOW) == "issued (expiring)"
    assert api.writes() == [
        ("PUT", POSTGRES_SECRET),
        ("PATCH", POSTGRES_WORKLOAD),
        ("PUT", POSTGRES_SECRET),
    ]
    put, patch, paid = (body for method, _, body in api.requests if method in {"PUT", "PATCH"})
    # Written over the version read, which a writer in between would have changed, with the restart
    # it owes; that restart cleared over the version written.
    assert put["metadata"]["resourceVersion"] == "7"
    assert put["metadata"]["annotations"] == {OWED: NOW.isoformat()}
    assert paid["metadata"]["resourceVersion"] == "8"
    assert OWED not in api.secrets["waterfall-postgres-tls"]["metadata"]["annotations"]
    assert leaf(api.secrets["waterfall-postgres-tls"]["data"]).not_valid_after_utc > NOW + (
        LEAF_LIFETIME - timedelta(days=1)
    )
    annotations = patch["spec"]["template"]["metadata"]["annotations"]
    assert annotations == {RESTARTED: NOW.isoformat()}
    api.requests.clear()
    assert certify(api.cluster(), authority, POSTGRES, NOW) is None
    assert api.writes() == []


def test_a_certificate_of_another_authority_or_unreadable_is_issued_again(
    authority: Authority,
) -> None:
    other = made(NOW)
    api = Api()
    held_by(api, other, NOW)
    said = certify(api.cluster(), authority, POSTGRES, NOW)
    assert said == "issued (issued by another authority)"
    leaf(api.secrets["waterfall-postgres-tls"]["data"]).verify_directly_issued_by(authority.issuer)
    key, chain = issued(authority, POSTGRES.name, NOW)
    _, mismatched = issued(authority, POSTGRES.name, NOW)
    assert due(None, authority, NOW) == "missing"
    assert due({"tls.crt": "not base 64!"}, authority, NOW) == "unreadable"
    assert due(encoded(key, mismatched, authority.pem()), authority, NOW) == "unreadable"
    assert due(encoded(key, chain, authority.pem()), authority, NOW) is None


def test_a_secret_whose_root_is_not_that_of_the_authority_is_issued_again(
    authority: Authority,
) -> None:
    # Its clients would trust another root than the one the platform signs with.
    key, chain = issued(authority, POSTGRES.name, NOW)
    assert due(encoded(key, chain, made(NOW).pem()), authority, NOW) == "another root"
    assert due(encoded(key, chain, b""), authority, NOW) == "another root"
    without = encoded(key, chain, authority.pem())
    del without["ca.crt"]
    assert due(without, authority, NOW) == "another root"


def test_a_certificate_that_ends_with_its_authority_is_not_issued_again_at_each_upgrade() -> None:
    # An authority with 90 days left signs certificates of 90 days (authority.issued): each would be
    # « expiring » from its issue, and every upgrade would restart the six components.
    ending = made(NOW - ROOT_LIFETIME + timedelta(days=90))
    api = Api()
    assert certify(api.cluster(), ending, POSTGRES, NOW) == "issued (missing)"
    end = leaf(api.secrets["waterfall-postgres-tls"]["data"]).not_valid_after_utc
    assert end == ending.issuer.not_valid_after_utc
    api.requests.clear()
    assert certify(api.cluster(), ending, POSTGRES, NOW + timedelta(days=30)) is None
    assert api.writes() == []


def test_a_renewal_before_its_workload_exists_restarts_nothing(authority: Authority) -> None:
    api = Api(workloads=set())
    held_by(api, made(NOW), NOW)
    said = certify(api.cluster(), authority, POSTGRES, NOW)
    assert said == "issued (issued by another authority)"
    assert [method for method, _ in api.writes()] == ["PUT", "PATCH", "PUT"]
    assert OWED not in api.secrets[POSTGRES.kept_in]["metadata"]["annotations"]


def test_a_restart_that_failed_is_sent_at_the_next_run_without_issuing_again(
    authority: Authority,
) -> None:
    # The Secret renewed, the restart refused once: the pods would serve the old certificate until
    # its end, the new one being valid and kept by every later run.
    api = Api()
    held_by(api, made(NOW), NOW)
    failures = [503]

    def failing_once(method: str, path: str, body: Mapping[str, Any] | None) -> tuple[int, Any]:
        if method == "PATCH" and failures:
            api.requests.append((method, path, copy.deepcopy(body)))
            return failures.pop(), {}
        return api.send(method, path, body)

    cluster = Cluster("waterfall", failing_once)
    with pytest.raises(ClusterError, match="answered 503 to PATCH"):
        certify(cluster, authority, POSTGRES, NOW)
    renewed = copy.deepcopy(api.secrets[POSTGRES.kept_in]["data"])
    assert api.secrets[POSTGRES.kept_in]["metadata"]["annotations"] == {OWED: NOW.isoformat()}
    api.requests.clear()
    later = NOW + timedelta(minutes=1)
    said = certify(cluster, authority, POSTGRES, later)
    assert said == f"restarted (owed since {NOW.isoformat()})"
    assert api.writes() == [("PATCH", POSTGRES_WORKLOAD), ("PUT", POSTGRES_SECRET)]
    patch = api.requests[1][2]
    # The time of the renewal, not of the run: a restart sent twice changes the template once.
    assert patch["spec"]["template"]["metadata"]["annotations"] == {RESTARTED: NOW.isoformat()}
    assert api.secrets[POSTGRES.kept_in]["data"] == renewed
    assert api.secrets[POSTGRES.kept_in]["metadata"]["annotations"] == {}
    api.requests.clear()
    assert certify(cluster, authority, POSTGRES, later) is None
    assert api.writes() == []


@pytest.mark.parametrize("status", [403, 500])
def test_a_refusal_of_the_api_stops_the_hook_saying_so(authority: Authority, status: int) -> None:
    api = Api()
    api.refused = status
    with pytest.raises(ClusterError, match=rf"answered {status}"):
        certify(api.cluster(), authority, POSTGRES, NOW)
    api = Api()
    held_by(api, made(NOW), NOW)
    cluster = api.cluster()

    def refusing(method: str, path: str, body: Mapping[str, Any] | None) -> tuple[int, Any]:
        return (status, {}) if method == "PUT" else api.send(method, path, body)

    with pytest.raises(ClusterError, match=rf"answered {status} to PUT"):
        certify(Cluster(cluster.namespace, refusing), authority, POSTGRES, NOW)
    assert api.secrets[POSTGRES.kept_in]["metadata"]["resourceVersion"] == "7"


def test_a_workload_is_named_by_its_resource_and_its_name() -> None:
    assert Workload.parse("deployments/waterfall-redis").kept_in == "waterfall-redis-tls"
    for wrong in ("pods/waterfall-redis", "deployments/", "waterfall-redis"):
        with pytest.raises(ArgumentTypeError, match="is not statefulsets"):
            Workload.parse(wrong)


class Served(BaseHTTPRequestHandler):
    """The API of Kubernetes over HTTP, answered by an ``Api``."""

    api: ClassVar[Api]

    def answer(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length)) if length else None
        status, answered = self.api.send(self.command, self.path, body)
        self.api.requests[-1] = (
            self.command,
            self.path,
            (self.headers["Authorization"], self.headers["Content-Type"]),
        )
        content = json.dumps(answered).encode() if self.api.page is None else self.api.page
        self.send_response(status)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        self.answer()

    def do_POST(self) -> None:
        self.answer()

    def do_PUT(self) -> None:
        self.answer()

    @override
    def log_message(self, format: str, *args: Any) -> None:
        """Write nothing."""


@pytest.fixture
def address() -> Iterator[str]:
    Served.api = Api()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Served)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def account_in(folder: Path) -> Path:
    """Write what Kubernetes mounts of a service account: its token, its namespace, its roots."""
    folder.mkdir()
    (folder / "token").write_text("token\n", encoding="utf-8")
    (folder / "namespace").write_text("waterfall\n", encoding="utf-8")
    (folder / "ca.crt").write_bytes(made(NOW).pem())
    return folder


def test_the_hook_issues_then_keeps_as_the_service_account_of_its_pod(
    tmp_path: Path, address: str, authority: Authority, capsys: pytest.CaptureFixture[str]
) -> None:
    provided = tmp_path / "authority"
    provided.mkdir()
    (provided / "ca.crt").write_bytes(authority.pem())
    (provided / "ca.key").write_bytes(
        authority.key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    account = account_in(tmp_path / "account")
    command = ["secrets", f"--provided={provided}", "statefulsets/waterfall-postgres"]
    assert authority_secrets.main(command, account, address) == 0
    assert authority_secrets.main(command, account, address) == 0
    said = capsys.readouterr().out.splitlines()
    assert said == [
        "waterfall-authority secrets: waterfall-postgres-tls: issued (missing)",
        "waterfall-authority secrets: waterfall-postgres-tls: kept",
    ]
    get, post, _ = Served.api.requests
    assert get == ("GET", f"{SECRETS}/waterfall-postgres-tls", ("Bearer token", "application/json"))
    assert post[:2] == ("POST", SECRETS)
    Served.api.refused = 403
    assert authority_secrets.main(command, account, address) == 1
    assert "answered 403" in capsys.readouterr().err
    # A proxy that answers a page of its own instead of the API: the refusal is said, as such.
    Served.api.refused = 502
    Served.api.page = b"<html><body>Bad Gateway</body></html>"
    assert authority_secrets.main(command, account, address) == 1
    assert capsys.readouterr().err == (
        "waterfall-authority secrets: the API of Kubernetes answered 502 to GET "
        f"{SECRETS}/waterfall-postgres-tls\n"
    )
    Served.api.refused = 200
    assert authority_secrets.main(command, account, address) == 1
    assert capsys.readouterr().err.endswith("waterfall-postgres-tls, not JSON\n")
    Served.api.page = None
    missing = ["secrets", f"--provided={tmp_path / 'none'}", "deployments/waterfall-redis"]
    assert authority_secrets.main(missing, account, address) == 1
    assert "the authority cannot be read" in capsys.readouterr().err


def test_without_secrets_the_command_is_that_of_the_compose(tmp_path: Path) -> None:
    (tmp_path / "provided").mkdir()
    folders = [f"--{name}={tmp_path / name}" for name in ("provided", "kept", "trust")]
    served = f"waterfall-postgres:{os.getuid()}:{os.getgid()}"
    command = [*folders, f"--certificates={tmp_path / 'certificates'}", served]
    assert authority_secrets.main(command) == 0
    root = (tmp_path / "trust" / "root.crt").read_bytes()
    assert (tmp_path / "certificates" / "waterfall-postgres" / "ca.crt").read_bytes() == root
