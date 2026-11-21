# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Every exchange inside the platform is encrypted, and each client checks the server (US-2840).

« Aucune connexion en clair n'est acceptée par un composant de la plateforme, hors le point de
métriques, qui n'est pas joignable hors du cluster. » The API serves in TLS alone, its metrics in
HTTP on a port of their own; the clients of Keycloak and of the storage check the certificate
against the root of the platform; and a process given that root refuses to start on an address in
the clear, as on a root or a certificate it cannot read (« Le démarrage d'un service sans les
secrets attendus échoue en le disant, plutôt que de démarrer sans. »).
"""

import contextlib
import json
import os
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, override

import httpx2
import pytest
from support import PLATFORM_ADDRESSES, PLATFORM_SECRETS, SECRETS

from waterfall.api import main as api_main
from waterfall.platform import authority
from waterfall.platform.errors import UnavailableError
from waterfall.platform.keycloak import Keycloak, trusted
from waterfall.platform.settings import (
    SettingsError,
    load_api_settings,
    load_service_settings,
    load_worker_settings,
)
from waterfall.platform.storage import Bucket

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from waterfall.platform.database import Database

START_SECONDS = 60.0
STOP_SECONDS = 30.0
VERIFIED = "sslmode=verify-full&sslrootcert=/trust/root.crt"
# What a process given the root says of an address of PostgreSQL or of Redis it refuses.
POSTGRESQL_WANTED = "ask sslmode=verify-full, and no other sslmode nor gssencmode"
REDIS_WANTED = (
    "be in rediss://, with no parameter ssl_ but ssl_ca_certs, ssl_cert_reqs=required "
    "and ssl_check_hostname=true"
)
# The addresses of a process given the root of the platform, each encrypted.
ENCRYPTED = {
    "WATERFALL_DATABASE_URL": f"{PLATFORM_SECRETS['WATERFALL_DATABASE_URL']}?{VERIFIED}",
    "WATERFALL_REDIS_URL": PLATFORM_SECRETS["WATERFALL_REDIS_URL"].replace("redis:", "rediss:", 1),
    "WATERFALL_BACKUP_DATABASE_URL": (
        f"{PLATFORM_SECRETS['WATERFALL_BACKUP_DATABASE_URL']}?{VERIFIED}"
    ),
    "WATERFALL_KEYCLOAK_DATABASE_URL": (
        f"{PLATFORM_SECRETS['WATERFALL_KEYCLOAK_DATABASE_URL']}?{VERIFIED}"
    ),
    "WATERFALL_KEYCLOAK_BACKCHANNEL": "https://keycloak:8443/auth",
    "WATERFALL_STORAGE_ADDRESS": "https://storage:3900",
}


class Certified:
    """The root of a platform, and the certificate and the key of a server it signs."""

    def __init__(self, folder: Path, name: str) -> None:
        provided = folder / "provided"
        provided.mkdir(parents=True)
        served = [authority.Served(name, os.getuid(), os.getgid())]
        authority.run(provided, folder / "kept", folder / "trust", folder / "certificates", served)
        self.root = folder / "trust" / "root.crt"
        self.certificate = folder / "certificates" / name / "tls.crt"
        self.key = folder / "certificates" / name / "tls.key"


@pytest.fixture
def certified(tmp_path: Path) -> Certified:
    """Give the root of a platform, and the certificate of its server ``keycloak``."""
    return Certified(tmp_path, "keycloak")


def free_port() -> int:
    """Give a port of the loopback that nothing listens on now."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


class Answering(BaseHTTPRequestHandler):
    """A server that answers 200 to anything: what matters is whether it is reached."""

    def do_GET(self) -> None:
        """Answer an empty object."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def do_HEAD(self) -> None:
        """Answer without a body."""
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    @override
    def log_message(self, format: str, *args: object) -> None:
        """Write nothing."""


@pytest.fixture
def server_in_tls(certified: Certified) -> Iterator[int]:
    """Serve in TLS on the loopback, with the certificate the root signs; give the port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Answering)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certified.certificate, certified.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()
    thread.join()


def faults(capsys: pytest.CaptureFixture[str]) -> str:
    """Give what the API said when it refused to start, after checking it named no secret."""
    said = capsys.readouterr().err
    assert not [secret for secret in SECRETS if secret in said]
    return said


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("platform_environment")
def test_a_process_given_the_root_refuses_every_address_in_the_clear_naming_it(
    certified: Certified, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(certified.root))
    assert api_main.main([]) == 2
    said = faults(capsys)
    for name, wanted in (
        ("WATERFALL_DATABASE_URL", POSTGRESQL_WANTED),
        ("WATERFALL_REDIS_URL", REDIS_WANTED),
        ("WATERFALL_KEYCLOAK_ADDRESS", "be in https://"),
        ("WATERFALL_STORAGE_ADDRESS", "be in https://"),
    ):
        assert f"{name} must {wanted} when WATERFALL_TLS_AUTHORITY is given" in said


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("platform_environment")
def test_the_api_given_the_root_reads_prometheus_in_https_alone(
    certified: Certified, monkeypatch: pytest.MonkeyPatch
) -> None:
    # TFX-14: the API reads the metrics and the alerts of Prometheus in HTTPS, its certificate
    # checked against the root; an address in the clear stops it, naming the variable.
    for name, value in ENCRYPTED.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(certified.root))
    monkeypatch.setenv("WATERFALL_PROMETHEUS_ADDRESS", "http://prometheus:9090")
    with pytest.raises(SettingsError) as refused:
        load_api_settings()
    wanted = "must be in https:// when WATERFALL_TLS_AUTHORITY is given"
    assert f"WATERFALL_PROMETHEUS_ADDRESS {wanted}" in str(refused.value)
    monkeypatch.setenv("WATERFALL_PROMETHEUS_ADDRESS", "https://prometheus:9090")
    assert load_api_settings().prometheus_address == "https://prometheus:9090"
    monkeypatch.setenv("WATERFALL_PROMETHEUS_ADDRESS", "")
    assert load_api_settings().prometheus_address is None


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("platform_environment")
@pytest.mark.parametrize(
    ("name", "query", "verdict"),
    [
        ("WATERFALL_REDIS_URL", "", "kept"),
        ("WATERFALL_REDIS_URL", "?ssl_ca_certs=/trust/root.crt&ssl_cert_reqs=required", "kept"),
        ("WATERFALL_REDIS_URL", "?ssl_check_hostname=true", "kept"),
        ("WATERFALL_REDIS_URL", "?ssl_cert_reqs=none", "refused"),
        ("WATERFALL_REDIS_URL", "?ssl_cert_reqs=optional", "refused"),
        ("WATERFALL_REDIS_URL", "?ssl_cert_reqs=required&ssl_cert_reqs=none", "refused"),
        ("WATERFALL_REDIS_URL", "?ssl_check_hostname=false", "refused"),
        ("WATERFALL_REDIS_URL", "?SSL_CHECK_HOSTNAME=no", "refused"),
        ("WATERFALL_REDIS_URL", "?ssl_exclude_verify_flags=VERIFY_X509_STRICT", "refused"),
        ("WATERFALL_REDIS_URL", "?ssl_min_version=TLSv1", "refused"),
        ("WATERFALL_REDIS_URL", "?ssl_ciphers=NULL", "refused"),
        ("WATERFALL_DATABASE_URL", "?sslmode=verify-full", "kept"),
        ("WATERFALL_DATABASE_URL", "?sslmode=verify-full&gssencmode=disable", "kept"),
        ("WATERFALL_DATABASE_URL", "?sslmode=verify-ca", "refused"),
        ("WATERFALL_DATABASE_URL", "?sslmode=require", "refused"),
        ("WATERFALL_DATABASE_URL", "?sslmode=prefer", "refused"),
        ("WATERFALL_DATABASE_URL", "?sslmode=verify-full&sslmode=disable", "refused"),
        ("WATERFALL_DATABASE_URL", "?SSLMODE=allow&sslmode=verify-full", "refused"),
        ("WATERFALL_DATABASE_URL", "?sslmode=verify-full&gssencmode=prefer", "refused"),
        ("WATERFALL_DATABASE_URL", "", "refused"),
    ],
)
def test_a_process_given_the_root_refuses_an_address_that_loosens_the_check_of_the_certificate(
    name: str,
    query: str,
    verdict: str,
    certified: Certified,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Encrypted, but with the check of the certificate or of its name turned off or loosened.
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(certified.root))
    for each, value in ENCRYPTED.items():
        monkeypatch.setenv(each, value)
    plain = {
        "WATERFALL_REDIS_URL": ENCRYPTED["WATERFALL_REDIS_URL"],
        "WATERFALL_DATABASE_URL": PLATFORM_SECRETS["WATERFALL_DATABASE_URL"],
    }
    monkeypatch.setenv(name, plain[name] + query)
    wanted = REDIS_WANTED if name == "WATERFALL_REDIS_URL" else POSTGRESQL_WANTED
    if verdict == "kept":
        assert load_service_settings().tls_authority == str(certified.root)
        return
    with pytest.raises(SettingsError) as found:
        load_service_settings()
    assert f"{name} must {wanted} when WATERFALL_TLS_AUTHORITY is given" in str(found.value)


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("platform_environment")
def test_the_worker_given_the_root_refuses_a_database_of_the_backup_in_the_clear(
    certified: Certified, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(certified.root))
    for name, value in ENCRYPTED.items():
        monkeypatch.setenv(name, value)
    assert load_worker_settings().tls_authority == str(certified.root)
    monkeypatch.setenv("WATERFALL_BACKUP_DATABASE_URL", PLATFORM_SECRETS["WATERFALL_DATABASE_URL"])
    with pytest.raises(SettingsError) as refused:
        load_worker_settings()
    assert "WATERFALL_BACKUP_DATABASE_URL must ask sslmode=verify-full" in str(refused.value)
    assert "WATERFALL_KEYCLOAK_DATABASE_URL" not in str(refused.value)


@pytest.mark.usefixtures("platform_environment")
def test_without_the_root_the_addresses_are_taken_as_they_are() -> None:
    # The workstation and the tests reach their components on the loopback, in the clear.
    settings = load_service_settings()
    assert settings.tls_authority is None
    assert settings.transport_faults() != []


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("platform_environment")
@pytest.mark.parametrize("given", ["missing", "not-pem"])
def test_a_root_that_cannot_be_read_stops_the_process_naming_it(
    given: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "root.crt"
    if given == "not-pem":
        path.write_text("no certificate\n", encoding="utf-8")
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(path))
    with pytest.raises(SettingsError) as refused:
        load_service_settings()
    said = str(refused.value)
    assert said.startswith("settings are not valid: WATERFALL_TLS_AUTHORITY: ")
    expected = f"no file at {path}" if given == "missing" else "not a file of certificates in PEM"
    assert expected in said


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("platform_environment")
def test_the_api_given_half_of_its_certificate_or_one_it_cannot_read_refuses_to_start(
    certified: Certified, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WATERFALL_TLS_CERTIFICATE", str(certified.certificate))
    with pytest.raises(SettingsError, match="WATERFALL_TLS_CERTIFICATE and WATERFALL_TLS_KEY go"):
        load_api_settings()
    monkeypatch.setenv("WATERFALL_TLS_KEY", str(tmp_path / "none.key"))
    with pytest.raises(SettingsError, match=r"WATERFALL_TLS_KEY: no file at .*none\.key"):
        load_api_settings()
    other = Certified(tmp_path / "other", "api")
    monkeypatch.setenv("WATERFALL_TLS_KEY", str(other.key))
    with pytest.raises(SettingsError, match="are not a certificate in PEM and its key"):
        load_api_settings()
    monkeypatch.setenv("WATERFALL_TLS_KEY", str(certified.key))
    assert load_api_settings().tls_key == str(certified.key)


@pytest.mark.usefixtures("platform_environment")
def test_the_metrics_have_a_port_of_their_own_never_that_of_the_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_METRICS_PORT", "")
    assert load_api_settings().metrics_port is None
    monkeypatch.setenv("WATERFALL_METRICS_PORT", "8000")
    with pytest.raises(SettingsError, match="WATERFALL_METRICS_PORT must not be WATERFALL_PORT"):
        load_api_settings()


@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_api_given_its_certificate_asks_uvicorn_to_serve_in_tls(
    certified: Certified, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WATERFALL_TLS_CERTIFICATE", str(certified.certificate))
    monkeypatch.setenv("WATERFALL_TLS_KEY", str(certified.key))
    served: dict[str, object] = {}

    def serve(_: str, **options: object) -> None:
        served.update(options)

    monkeypatch.setattr(api_main.uvicorn, "run", serve)
    assert api_main.main([]) == 0
    assert (served["ssl_certfile"], served["ssl_keyfile"]) == (
        str(certified.certificate),
        str(certified.key),
    )


@pytest.mark.requirement("WF-SEC-0010-A")
def test_keycloak_is_reached_in_tls_its_certificate_checked_against_the_root(
    certified: Certified, server_in_tls: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in {**PLATFORM_SECRETS, **PLATFORM_ADDRESSES}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_BACKCHANNEL", f"https://localhost:{server_in_tls}/auth")
    assert trusted(None) is True
    usual = Keycloak(load_service_settings())
    try:
        # The usual roots do not vouch for the platform's server.
        with pytest.raises(UnavailableError):
            usual.send("GET", "/realms/waterfall")
    finally:
        usual.close()
    for name, value in ENCRYPTED.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_BACKCHANNEL", f"https://localhost:{server_in_tls}/auth")
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(certified.root))
    platform = Keycloak(load_service_settings())
    try:
        assert platform.send("GET", "/realms/waterfall").status_code == 200
    finally:
        platform.close()


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_storage_is_reached_in_tls_its_certificate_checked_against_the_root(
    certified: Certified, server_in_tls: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in {**PLATFORM_SECRETS, **PLATFORM_ADDRESSES, **ENCRYPTED}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("WATERFALL_STORAGE_ADDRESS", f"https://localhost:{server_in_tls}")
    usual = Bucket.of_backups(load_service_settings())
    with pytest.raises(UnavailableError):
        usual.reach()
    monkeypatch.setenv("WATERFALL_TLS_AUTHORITY", str(certified.root))
    Bucket.of_backups(load_service_settings()).reach()


def plain_answer(port: int) -> bytes | None:
    """Give what a server answers to a request in HTTP, in the clear; None if refused at once."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
            connection.sendall(b"GET /api/v1/health HTTP/1.1\r\nHost: localhost\r\n\r\n")
            try:
                return connection.recv(512)
            except OSError:
                return b""
    except OSError:
        return None


def stop(process: subprocess.Popen[bytes]) -> None:
    """Stop the API and every worker of its group, killing them if they do not stop in time."""
    try:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(STOP_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_api_serves_in_tls_alone_and_its_metrics_in_http_on_a_port_of_their_own(
    database: Database, service_environment: dict[str, str], tmp_path: Path
) -> None:
    # The API on two processes, as the platform serves it: both serve the port of the metrics.
    del database
    api = Certified(tmp_path, "api")
    port, metrics = free_port(), free_port()
    environment = {
        **PLATFORM_SECRETS,
        **PLATFORM_ADDRESSES,
        **service_environment,
        "WATERFALL_PORT": str(port),
        "WATERFALL_METRICS_PORT": str(metrics),
        "WATERFALL_API_PROCESSES": "2",
        "WATERFALL_TLS_CERTIFICATE": str(api.certificate),
        "WATERFALL_TLS_KEY": str(api.key),
    }
    logs = tmp_path / "api.log"
    with logs.open("wb") as written:
        process = subprocess.Popen(
            [sys.executable, "-m", "waterfall.api.main"],
            env=environment,
            stderr=written,
            start_new_session=True,
        )
    root = ssl.create_default_context(cafile=api.root)
    secure = f"https://localhost:{port}/api/v1/health"
    try:
        deadline = time.monotonic() + START_SECONDS
        while True:
            assert process.poll() is None, logs.read_text(encoding="utf-8")
            with contextlib.suppress(httpx2.TransportError):
                if httpx2.get(secure, verify=root, timeout=5).status_code == 200:
                    break
            assert time.monotonic() < deadline, logs.read_text(encoding="utf-8")
            time.sleep(0.1)
        assert httpx2.get(secure, verify=root, timeout=5).json() == {"status": "ok"}
        # In the clear, the API gives no answer: the request never reaches it.
        answered = plain_answer(port)
        assert answered is not None
        assert not answered.startswith(b"HTTP/")
        # Its metrics, in HTTP, at the path of getMetrics, and nothing else on their port.
        exposed = httpx2.get(f"http://127.0.0.1:{metrics}/api/v1/metrics", timeout=10)
        assert exposed.status_code == 200
        assert "waterfall_component_up" in exposed.text
        other = httpx2.get(f"http://127.0.0.1:{metrics}/api/v1/health", timeout=10)
        assert other.status_code == 404
    finally:
        stop(process)
    events = [
        json.loads(line).get("event")
        for line in logs.read_text(encoding="utf-8").splitlines()
        if line.startswith("{")
    ]
    assert "service.starting" in events
