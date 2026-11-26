# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The certificates of the data components under Kubernetes, kept in Secrets (US-2850, US-2840).

Under the chart, PostgreSQL, Redis, the object storage, Prometheus, Alertmanager and Grafana do not
issue their certificates at each start, as the Compose does: a container of initialisation that ran
the image of Waterfall changed their pods at each version, and an upgrade restarted them, every
session with Redis (decision of the author of 2026-11-26, #4089, option C). A hook of the chart runs
``waterfall-authority secrets`` before the installation and before each upgrade instead. For
each workload it names, it writes the Secret ``<name>-tls`` — the key, the certificate for the
name of its Service and the root of the platform, ``tls.key``, ``tls.crt`` and ``ca.crt`` —, which
the pods of that workload mount, and only when the Secret is missing, cannot be read, was not
issued by the authority of the platform, holds another root, or expires within ``RENEW_BEFORE`` —
unless it already ends with the authority, which no renewal would outlast: an ordinary upgrade
writes nothing, and restarts nothing.

A certificate renewed is read by its server at its next start: the hook restarts the workload
then, as ``kubectl rollout restart`` does, the only restart a renewal costs. That restart is owed
in the Secret itself, by ``OWED``, written with the certificate and cleared once the workload is
restarted: a hook stopped between the two — a refusal, a timeout — restarts it at its next run, or
at the next upgrade, though the certificate is then valid. A workload that does not exist yet — at
the installation — is left alone. The authority is the Secret the chart mounts as
``--provided``: the operator's, or the one the chart makes at the installation.
"""

import argparse
import base64
import binascii
import json
import ssl
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx2
from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization

from waterfall.platform import authority as authorities
from waterfall.platform.authority import Authority, AuthorityError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

COMMAND = "secrets"
# Where Kubernetes mounts the token, the authority and the namespace of the service account of a
# pod, and the address of its API inside the cluster.
SERVICE_ACCOUNT = Path("/var/run/secrets/kubernetes.io/serviceaccount")
API = "https://kubernetes.default.svc"
TIMEOUT = 10.0
OK, CREATED, MISSING = 200, 201, 404
# A certificate is issued for two years (authority.LEAF_LIFETIME): any upgrade in its last six
# months renews it, long before a client refuses it.
RENEW_BEFORE = timedelta(days=180)
# What kubectl rollout restart writes in the template of the pods: a new value restarts them.
RESTARTED = "kubectl.kubernetes.io/restartedAt"
# The annotation of a Secret renewed whose workload is not restarted yet: the time of the renewal,
# which the restart writes as RESTARTED — a restart sent twice changes the template once.
OWED = f"{authorities.NAME}/restart-owed"
# How a restart is sent: merged into the template, as kubectl does.
PATCH = "application/strategic-merge-patch+json"
WORKLOADS = ("statefulsets", "deployments")
LABELS = {"app.kubernetes.io/managed-by": authorities.NAME}

type Send = Callable[[str, str, Mapping[str, Any] | None], tuple[int, dict[str, Any]]]


class ClusterError(Exception):
    """The API of Kubernetes refused a step: nothing after it is written."""


@dataclass(frozen=True, slots=True)
class Workload:
    """A workload whose pods serve in TLS: its resource, and its name, that of its Service."""

    resource: str
    name: str

    @classmethod
    def parse(cls, given: str) -> Workload:
        """Read ``statefulsets/<name>`` or ``deployments/<name>``."""
        resource, _, name = given.partition("/")
        if resource not in WORKLOADS or not name:
            message = f"{given!r} is not statefulsets/<name> nor deployments/<name>"
            raise argparse.ArgumentTypeError(message)
        return cls(resource, name)

    @property
    def kept_in(self) -> str:
        """Give the name of the Secret its pods mount."""
        return f"{self.name}-tls"


@dataclass(frozen=True, slots=True)
class Cluster:
    """The API of Kubernetes in a namespace.

    ``send`` takes a method, a path and a body, and gives the status and the body answered.
    """

    namespace: str
    send: Send

    @classmethod
    def in_cluster(cls, account: Path = SERVICE_ACCOUNT, address: str = API) -> Cluster:
        """Reach the API of the cluster the pod runs in, as the service account it mounts.

        The token is read at each request: Kubernetes renews the file before the token expires.
        """
        namespace = (account / "namespace").read_text(encoding="utf-8").strip()
        roots = ssl.create_default_context(cafile=str(account / "ca.crt"))

        def send(
            method: str, path: str, body: Mapping[str, Any] | None
        ) -> tuple[int, dict[str, Any]]:
            token = (account / "token").read_text(encoding="utf-8").strip()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": PATCH if method == "PATCH" else "application/json",
            }
            content = None if body is None else json.dumps(body).encode()
            with httpx2.Client(base_url=address, verify=roots, timeout=TIMEOUT) as http:
                answer = http.request(method, path, content=content, headers=headers)
            return answer.status_code, _decoded(answer, method, path)

        return cls(namespace, send)

    def expect(
        self, method: str, path: str, body: Mapping[str, Any] | None, *ok: int
    ) -> tuple[int, dict[str, Any]]:
        """Send a request; give its answer if its status is one of ``ok``, else stop, saying so."""
        status, answered = self.send(method, path, body)
        if status not in ok:
            message = f"the API of Kubernetes answered {status} to {method} {path}"
            raise ClusterError(message)
        return status, answered


def _decoded(answer: httpx2.Response, method: str, path: str) -> dict[str, Any]:
    """Read the body of a success; that of a refusal — a page of a proxy, often — is not read."""
    if not answer.is_success or not answer.content:
        return {}
    said = f"the API of Kubernetes answered {answer.status_code} to {method} {path}"
    try:
        decoded = answer.json()
    except ValueError as error:
        message = f"{said}, not JSON"
        raise ClusterError(message) from error
    if not isinstance(decoded, dict):
        message = f"{said}, no object"
        raise ClusterError(message)
    return cast("dict[str, Any]", decoded)


def due(data: Mapping[str, str] | None, authority: Authority, now: datetime) -> str | None:
    """Tell why the certificate a Secret holds must be issued again, or ``None`` if it may stay.

    ``data`` is that of the Secret, in base 64, ``None`` when there is no Secret.
    """
    if data is None:
        return "missing"
    certificate = _certificate(data)
    if certificate is None:
        return "unreadable"
    try:
        certificate.verify_directly_issued_by(authority.issuer)
    except ValueError, TypeError, InvalidSignature:
        return "issued by another authority"
    try:
        root = base64.b64decode(data["ca.crt"])
    except KeyError, ValueError, TypeError, binascii.Error:
        root = None
    if root != authority.pem():
        return "another root"
    # A certificate never outlasts its authority (authority.issued): one that already ends with it
    # would be issued again for no more time, and its workload restarted at each upgrade.
    end = certificate.not_valid_after_utc
    if end - now < RENEW_BEFORE and end < authority.issuer.not_valid_after_utc:
        return "expiring"
    return None


def _certificate(data: Mapping[str, str]) -> x509.Certificate | None:
    """Read the certificate of a Secret, ``None`` unless it and its key can be read and match."""
    try:
        chain = x509.load_pem_x509_certificates(base64.b64decode(data["tls.crt"]))
        key = serialization.load_pem_private_key(base64.b64decode(data["tls.key"]), password=None)
    except KeyError, ValueError, TypeError, binascii.Error, UnsupportedAlgorithm:
        return None
    if not chain or chain[0].public_key() != key.public_key():
        return None
    return chain[0]


def _encoded(content: bytes) -> str:
    return base64.b64encode(content).decode("ascii")


def certify(
    cluster: Cluster, authority: Authority, workload: Workload, now: datetime
) -> str | None:
    """Issue the certificate of a workload if it is due; tell what was done, ``None`` if nothing.

    A Secret written again is written over the one read, by its version: a writer in between makes
    the API refuse it. The pods of the workload are then restarted, to read it; a restart owed by an
    earlier run is sent the same way.
    """
    secrets = f"/api/v1/namespaces/{cluster.namespace}/secrets"
    path = f"{secrets}/{workload.kept_in}"
    status, found = cluster.send("GET", path, None)
    if status not in {OK, MISSING}:
        message = f"the API of Kubernetes answered {status} to GET {path}"
        raise ClusterError(message)
    reason = due(found.get("data", {}) if status == OK else None, authority, now)
    if reason is None:
        owed = found.get("metadata", {}).get("annotations", {}).get(OWED)
        if owed is None:
            return None
        _restart(cluster, workload, found, owed)
        return f"restarted (owed since {owed})"
    key, chain = authorities.issued(authority, workload.name, now)
    root = authority.pem()
    data = {"tls.key": _encoded(key), "tls.crt": _encoded(chain), "ca.crt": _encoded(root)}
    if status == MISSING:
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": workload.kept_in, "labels": LABELS},
            "type": "kubernetes.io/tls",
            "data": data,
        }
        cluster.expect("POST", secrets, secret, CREATED)
        return f"issued ({reason})"
    metadata = found.get("metadata", {})
    annotations = {**metadata.get("annotations", {}), OWED: now.isoformat()}
    renewed = {**found, "metadata": {**metadata, "annotations": annotations}, "data": data}
    _, written = cluster.expect("PUT", path, renewed, OK)
    _restart(cluster, workload, written, now.isoformat())
    return f"issued ({reason})"


def _restart(cluster: Cluster, workload: Workload, secret: Mapping[str, Any], owed: str) -> None:
    """Restart the pods of a workload, then clear the restart its Secret owes, over its version."""
    restart = {"spec": {"template": {"metadata": {"annotations": {RESTARTED: owed}}}}}
    apps = f"/apis/apps/v1/namespaces/{cluster.namespace}/{workload.resource}/{workload.name}"
    cluster.expect("PATCH", apps, restart, OK, MISSING)
    metadata = secret.get("metadata", {})
    annotations = dict(metadata.get("annotations", {}))
    annotations.pop(OWED, None)
    paid = {**secret, "metadata": {**metadata, "annotations": annotations}}
    path = f"/api/v1/namespaces/{cluster.namespace}/secrets/{workload.kept_in}"
    cluster.expect("PUT", path, paid, OK)


def run(provided: Path, cluster: Cluster, workloads: Sequence[Workload]) -> list[str]:
    """Certify each workload under the authority provided; give what was done, one line each."""
    now = datetime.now(UTC)
    try:
        authority = authorities.loaded(
            provided / authorities.PROVIDED_CERTIFICATE, provided / authorities.PROVIDED_KEY, now
        )
    except OSError as error:
        message = f"the authority cannot be read in {provided}: {error.strerror}"
        raise AuthorityError(message) from error
    said: list[str] = []
    for workload in workloads:
        done = certify(cluster, authority, workload, now)
        said.append(f"{workload.kept_in}: {'kept' if done is None else done}")
    return said


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"{authorities.NAME} {COMMAND}",
        description="Issue the certificates of the data components in Secrets, when due.",
    )
    parser.add_argument("--provided", type=Path, required=True, help="its authority")
    parser.add_argument(
        "workloads", nargs="+", type=Workload.parse, help="statefulsets/<name>, deployments/<name>"
    )
    return parser


def main(
    argv: Sequence[str] | None = None, account: Path = SERVICE_ACCOUNT, address: str = API
) -> int:
    """Run ``waterfall-authority``: ``secrets …`` under Kubernetes, else the Compose's command.

    Status 1 when the authority cannot be read or the API refuses a step; 2 for a wrong command
    line.
    """
    given = list(sys.argv[1:] if argv is None else argv)
    if given[:1] != [COMMAND]:
        return authorities.main(given)
    arguments = _parser().parse_args(given[1:])
    try:
        said = run(arguments.provided, Cluster.in_cluster(account, address), arguments.workloads)
    except (AuthorityError, ClusterError, OSError, httpx2.HTTPError) as error:
        sys.stderr.write(f"{authorities.NAME} {COMMAND}: {error}\n")
        return 1
    sys.stdout.write("".join(f"{authorities.NAME} {COMMAND}: {line}\n" for line in said))
    return 0
