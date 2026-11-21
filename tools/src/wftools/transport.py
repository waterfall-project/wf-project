# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The trial of the transport of the production platform: nothing accepted in the clear (US-2840).

« Aucune connexion en clair n'est acceptée par un composant de la plateforme, hors le point de
métriques, qui n'est pas joignable hors du cluster. » (WF-SEC-0010-A). Inside the container of the
API, on the network of the platform, ``PROBE`` speaks in the clear to each server — PostgreSQL,
Redis, the API, Keycloak, the object storage — and says how it answered; it also reaches each in
TLS, its certificate checked against the root of the platform, so that a server out of reach is not
taken for one that refuses. The listeners that must not be reached at all — Keycloak in HTTP, its
management, Garage behind its proxy — are tried too, and the port of the metrics of the API, which
serves them in HTTP, must answer nothing else. ``wftools.production`` runs it on the started
platform and holds that every server refuses, and serves in TLS.

A verdict is ``refused`` — the server was reached and gave no answer of its own to what came in the
clear —, ``accepted``, ``unreached`` — nothing listens, or the name is unknown —, ``no tls`` for
a server that does not answer in TLS with a certificate the root vouches for, or ``metrics alone``
for the port of the metrics that answers another path 404.
"""

import json
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

SERVED = ("postgres", "redis", "api", "keycloak", "storage")
"""The servers that must refuse the clear and serve in TLS (TFX-02 to TFX-05, TFX-08, TFX-12)."""

CLOSED = ("keycloak-http", "keycloak-management", "garage")
"""What must not be reached at all from the network of the platform."""

METRICS = "api-metrics"
"""The port of the metrics of the API, in HTTP: it must answer nothing but the metrics."""

PROBE = r"""
import json, socket, ssl
import psycopg

ROOT = "/trust/root.crt"
TIMEOUT = 5
REQUEST = b"GET / HTTP/1.1\r\nHost: %b\r\nConnection: close\r\n\r\n"
# What Go, Caddy's language, answers in HTTP to a request in the clear on a port in TLS: no answer
# of the server behind it.
SAYS_TLS = b"HTTP request to an HTTPS server"
WRONG_PASSWORD = "password authentication failed"
said = {}


def clear(host, port, sent):
    # What a server answers to bytes in the clear; None if nothing could be reached.
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT) as connection:
            connection.sendall(sent)
            try:
                return connection.recv(512)
            except OSError:
                return b""
    except OSError:
        return None


def in_tls(host, port):
    trusted = ssl.create_default_context(cafile=ROOT)
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT) as connection:
            with trusted.wrap_socket(connection, server_hostname=host):
                return True
    except OSError:
        return False


def http(host, port):
    answer = clear(host, port, REQUEST % host.encode())
    if answer is None:
        return "unreached"
    if answer.startswith(b"HTTP/") and SAYS_TLS not in answer:
        return "accepted"
    return "refused" if in_tls(host, port) else "no tls"


def postgresql(sslmode):
    try:
        psycopg.connect(
            host="postgres",
            port=5432,
            dbname="waterfall",
            user="waterfall_service",
            password="not-the-password",
            sslmode=sslmode,
            sslrootcert=ROOT,
            connect_timeout=TIMEOUT,
        ).close()
    except psycopg.OperationalError as error:
        return str(error)
    return "connected"


# PostgreSQL refuses by pg_hba.conf before it asks a password; in TLS, it asks it.
plain = postgresql("disable")
if "no encryption" in plain:
    tls = WRONG_PASSWORD in postgresql("verify-full")
    said["postgres"] = "refused" if tls else "no tls"
elif WRONG_PASSWORD in plain or plain == "connected":
    said["postgres"] = "accepted"
else:
    said["postgres"] = "unreached"

# Redis answers any command, even one it refuses, by a line that starts with + or -.
answer = clear("redis", 6379, b"PING\r\n")
if answer is None:
    said["redis"] = "unreached"
elif answer[:1] in (b"+", b"-"):
    said["redis"] = "accepted"
else:
    said["redis"] = "refused" if in_tls("redis", 6379) else "no tls"

said["api"] = http("api", 8443)
said["keycloak"] = http("keycloak", 8443)
said["storage"] = http("storage", 3900)
# The port of the metrics of the API, in HTTP, serves the metrics and nothing else (TFX-09).
answer = clear("api", 8000, b"GET /api/v1/health HTTP/1.0\r\nHost: api\r\n\r\n")
if answer is None:
    said["api-metrics"] = "unreached"
else:
    alone = answer.startswith(b"HTTP/") and answer.split(b" ")[1:2] == [b"404"]
    said["api-metrics"] = "metrics alone" if alone else "accepted"
for name, host, port in (
    ("keycloak-http", "keycloak", 8080),
    ("keycloak-management", "keycloak", 9000),
    ("garage", "garage", 3900),
):
    reached = clear(host, port, b"GET / HTTP/1.0\r\n\r\n") is not None
    said[name] = "accepted" if reached else "unreached"
print(json.dumps(said))
"""
"""What the container of the API runs: one verdict for each listener, in JSON."""


class TransportError(Exception):
    """The output of the probe does not read, or a listener does not refuse the clear."""


def verdicts(output: str) -> Mapping[str, str]:
    """Read the verdicts the probe printed."""
    try:
        read: Any = json.loads(output)
    except ValueError:
        read = None
    if not isinstance(read, dict):
        message = f"the probe of the transport does not read: {output.strip()!r}"
        raise TransportError(message)
    return {str(name): str(verdict) for name, verdict in cast("dict[Any, Any]", read).items()}


def check_clear_refused(output: str) -> None:
    """Hold that every server refuses the clear and serves in TLS, and that nothing else answers."""
    said = verdicts(output)
    expected = {
        **dict.fromkeys(SERVED, "refused"),
        **dict.fromkeys(CLOSED, "unreached"),
        METRICS: "metrics alone",
    }
    faults = [
        f"{name} {said.get(name, 'not tried')}"
        for name, verdict in expected.items()
        if said.get(name) != verdict
    ]
    if faults:
        message = "a connection in the clear is not refused as it must be: " + ", ".join(faults)
        raise TransportError(message)
