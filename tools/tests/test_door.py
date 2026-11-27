# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Under Compose, the door serves the certificate the operator's authority issues (US-3010).

« Une plateforme dont les certificats sont émis par une autorité interne fonctionne. »
(WF-CMP-0030-A), under Compose: the operator gives the certificate of the domain, its key and its
root in the folder ``WATERFALL_DOOR_DIRECTORY`` names; Caddy serves it and asks no one for a
certificate, and the front trusts that root besides the platform's. The trial of the production
gives the door one, issued by an authority made for it, under a name neither ``*.localhost`` nor
``*.internal``, on networks without a way out (``wftools.production``). Here, where a docker daemon
answers, Caddy started as the production starts it, under such a name, on an internal network whose
sink writes every name asked: with the certificate given, it presents it and asks for nothing;
without, it asks Let's Encrypt, as it always did.
"""

import hashlib
import json
import shutil
import socket
import ssl
import subprocess
import threading
import time
from typing import TYPE_CHECKING, Any

import pytest
from dockerdaemon import mirrored
from test_egress import NO_DAEMON, STARTED_WITHIN, Network, docker
from test_grafanalive import trust
from test_isolated import ISOLATED, PRODUCTION, compose
from test_supervision import services

from wftools import REPOSITORY, production
from wftools.production import Platform, ProductionError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-CMP-0030-A"), pytest.mark.story("US-3010")]

DOMAIN = production.DOMAIN
CADDYFILE = PRODUCTION.parent / "Caddyfile.prod"
DOCUMENTATION = REPOSITORY / "docs" / "exploitation" / "reseau-isole.md"
GIVEN = {"WATERFALL_DOOR_DIRECTORY": "/srv/waterfall/door"}
NO_OPENSSL = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl is not installed")
NO_DOCKER = pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")
UNEXECUTED = pytest.mark.unexecuted("skipped where docker, its daemon or openssl is missing")
# Caddy asks for the certificate of a public name as it starts: what it would ask, within this time.
WATCHED = 15.0
ASKED_OF_ACME = ("letsencrypt.org", "zerossl.com")


def handshake(door: Path, name: str) -> bytes:
    """Serve the certificate of the door, reach it as the front does, and give what it presented.

    The client trusts the root given with it alone, and checks the name.
    """
    served = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    served.load_cert_chain(door / "tls.crt", door / "tls.key")
    client = ssl.create_default_context(cafile=door / production.DOOR_ROOT)
    inside, outside = socket.socketpair()
    server = threading.Thread(target=_accept, args=(served, inside), daemon=True)
    server.start()
    try:
        with client.wrap_socket(outside, server_hostname=name) as reached:
            return reached.getpeercert(binary_form=True) or b""
    finally:
        outside.close()
        server.join(timeout=5)
        inside.close()


def _accept(served: ssl.SSLContext, inside: socket.socket) -> None:
    try:
        with served.wrap_socket(inside, server_side=True):
            pass
    except OSError:
        return


def first_certificate(path: Path) -> bytes:
    """Give the first certificate of a PEM file, in DER."""
    end = "-----END CERTIFICATE-----"
    return ssl.PEM_cert_to_DER_cert(path.read_text(encoding="utf-8").split(end, 1)[0] + end + "\n")


def test_the_trial_runs_a_public_name_without_the_file_of_a_local_name() -> None:
    platform = production.platform_of({})
    assert platform.domain == DOMAIN
    assert not platform.local
    for local in ("localhost", "waterfall.localhost", "waterfall.internal"):
        assert Platform(local, 443, 80).local, local
    public = production.compose_command("trial", local=False)
    assert str(production.LOCAL) not in public
    assert public[-2:] == ["--file", str(ISOLATED)]
    assert str(production.LOCAL) in production.compose_command("trial")


@NO_OPENSSL
@pytest.mark.unexecuted("skipped where openssl is not installed")
def test_the_trial_gives_the_door_a_certificate_of_an_authority_of_test_and_its_root(
    tmp_path: Path,
) -> None:
    platform, setting = production.given_door(production.platform_of({}), tmp_path)
    door = platform.door
    assert door is not None
    assert setting == {"WATERFALL_DOOR_DIRECTORY": str(door)}
    assert sorted(path.name for path in door.iterdir()) == ["ca.crt", "tls.crt", "tls.key"]
    # The key of the authority is no more: nothing else can be signed for the door to present.
    assert not [path for path in tmp_path.iterdir() if path.name.endswith(".key")]
    assert handshake(door, DOMAIN) == first_certificate(door / "tls.crt")
    with pytest.raises(ssl.SSLCertVerificationError):
        handshake(door, "elsewhere.example.org")


def test_a_local_name_gives_the_door_nothing(tmp_path: Path) -> None:
    platform = Platform("waterfall.localhost", 443, 80)
    assert production.given_door(platform, tmp_path) == (platform, {})
    assert list(tmp_path.iterdir()) == []


def test_an_address_is_a_local_name_as_the_caddyfile_ranges_it(tmp_path: Path) -> None:
    for address in ("127.0.0.1", "10.1.2.3", "::1"):
        platform = Platform(address, 443, 80)
        assert platform.local, address
        assert production.given_door(platform, tmp_path) == (platform, {})
    assert not Platform("waterfall.example.org", 443, 80).local
    with pytest.raises(ProductionError, match="is no name a certificate is issued for"):
        production.door_certificate(tmp_path, "127.0.0.1")
    assert list(tmp_path.iterdir()) == []


def test_a_domain_that_is_no_name_is_refused_before_openssl(tmp_path: Path) -> None:
    with pytest.raises(ProductionError, match="is no name a certificate is issued for"):
        production.door_certificate(tmp_path, "waterfall.example.org\nsubjectAltName = DNS:x")
    assert list(tmp_path.iterdir()) == []


@NO_DOCKER
@UNEXECUTED
def test_the_setting_gives_caddy_the_certificate_and_the_front_its_root() -> None:
    found = compose(PRODUCTION, ISOLATED, given=GIVEN)["services"]
    caddy, roots, front = found["caddy"], found["door-authority"], found["front"]
    assert caddy["environment"]["WATERFALL_DOOR_CERTIFICATE"] == "given"
    for service in (caddy, roots):
        mounts = service["volumes"]
        mounted = {(each["source"], each["target"], each.get("read_only")) for each in mounts}
        assert (GIVEN["WATERFALL_DOOR_DIRECTORY"], "/door", True) in mounted
    command = " ".join(roots["command"])
    assert "cat /trust/root.crt /door/ca.crt > /roots/" in command
    # The root given must hold a certificate: else the front would start trusting nothing more.
    assert command.index("grep -q 'BEGIN CERTIFICATE' /door/ca.crt") < command.index("cat /trust")
    assert front["environment"]["NODE_EXTRA_CA_CERTS"] == "/roots/roots.crt"
    assert front["depends_on"]["door-authority"]["condition"] == "service_completed_successfully"


@NO_DOCKER
@UNEXECUTED
def test_without_the_setting_caddy_obtains_the_certificate_and_the_front_trusts_the_platform() -> (
    None
):
    found = compose(PRODUCTION)["services"]
    assert found["caddy"]["environment"]["WATERFALL_DOOR_CERTIFICATE"] == ""
    command = " ".join(found["door-authority"]["command"])
    assert "cat /trust/root.crt  > /roots/" in command
    assert "grep" not in command


def test_the_documentation_says_how_to_give_the_certificate_of_the_door() -> None:
    # Proper to US-3010: « la documentation d'exploitation dit comment y charger … l'autorité ».
    operation = DOCUMENTATION.read_text(encoding="utf-8")
    compose_readme = (PRODUCTION.parent / "README.md").read_text(encoding="utf-8")
    settings = (PRODUCTION.parent / "production.env.example").read_text(encoding="utf-8")
    for text in (operation, compose_readme, settings):
        for named in ("WATERFALL_DOOR_DIRECTORY", "tls.crt", "tls.key", "ca.crt"):
            assert named in text, named
    assert "# WATERFALL_DOOR_DIRECTORY=./door\n" in settings
    assert "### Le certificat de la porte" in compose_readme
    assert "#5055" not in operation
    # The root given is an anchor of the front for every name it reaches: the text says so, and
    # advises an authority, or an intermediate one, made for the door.
    for named in ("NODE_EXTRA_CA_CERTS", "api:8443", "dédiée à la porte"):
        assert named in operation, named
    for text in (compose_readme, settings):
        assert "dedicated" in text or "dédiée" in text
    assert "OCSP" in operation


def adapted(certificate: str) -> dict[str, Any]:
    """Adapt the Caddyfile of production, the setting of the door given as the Compose gives it."""
    done = subprocess.run(
        [
            *("docker", "run", "--rm"),
            *("--env", f"WATERFALL_DOMAIN={DOMAIN}"),
            *("--env", f"WATERFALL_ADDRESS=https://{DOMAIN}"),
            *("--env", "WATERFALL_ACME_EMAIL=operator@waterfall.test"),
            *("--env", f"WATERFALL_DOOR_CERTIFICATE={certificate}"),
            *("--volume", f"{CADDYFILE.resolve()}:/etc/caddy/Caddyfile.prod:ro"),
            mirrored(str(services(PRODUCTION)["caddy"]["image"])),
            *("caddy", "adapt", "--config", "/etc/caddy/Caddyfile.prod"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return dict(json.loads(done.stdout))


@NO_DAEMON
@UNEXECUTED
def test_caddy_loads_the_certificate_given_and_nothing_without_it() -> None:
    given = adapted("given")
    assert given["apps"]["tls"]["certificates"]["load_files"] == [
        {"certificate": "/door/tls.crt", "key": "/door/tls.key", "tags": ["cert0"]}
    ]
    policy = given["apps"]["http"]["servers"]["srv0"]["tls_connection_policies"][0]
    assert policy == {"match": {"sni": [DOMAIN]}, "certificate_selection": {"any_tag": ["cert0"]}}
    # Without it, the configuration of before: no certificate loaded, no policy of connection, and
    # the domain obtained by ACME. With it, Caddy does not obtain a name it holds a certificate for.
    obtained = adapted("")
    assert "certificates" not in obtained["apps"]["tls"]
    assert "tls_connection_policies" not in obtained["apps"]["http"]["servers"]["srv0"]
    assert obtained["apps"]["tls"]["automation"]["policies"][0]["subjects"] == [DOMAIN]
    # A certificate given may name an OCSP responder the network does not reach: no stapling then.
    assert given["apps"]["tls"]["disable_ocsp_stapling"] is True
    assert "disable_ocsp_stapling" not in obtained["apps"]["tls"]


@NO_DOCKER
@UNEXECUTED
def test_the_service_of_the_roots_stops_on_a_root_that_is_no_certificate(tmp_path: Path) -> None:
    found = compose(PRODUCTION, ISOLATED, given=GIVEN)["services"]["door-authority"]
    trusted, door, roots = tmp_path / "trust", tmp_path / "door", tmp_path / "roots"
    for folder in (trusted, door, roots):
        folder.mkdir()
    (trusted / "root.crt").write_text("-----BEGIN CERTIFICATE-----\nplatform\n", encoding="utf-8")
    command = found["command"]
    volumes = {trusted: "/trust", door: "/door", roots: "/roots"}
    outcomes = {}
    for content in ("", "not a certificate\n", "-----BEGIN CERTIFICATE-----\nroot\n"):
        (door / "ca.crt").write_text(content, encoding="utf-8")
        done = docker(
            *("run", "--rm", "--network", "none"),
            *(word for path, to in volumes.items() for word in ("--volume", f"{path}:{to}")),
            mirrored(str(found["image"])),
            *command,
        )
        outcomes[content] = done.returncode
    assert outcomes == {"": 1, "not a certificate\n": 1, "-----BEGIN CERTIFICATE-----\nroot\n": 0}
    assert (roots / "roots.crt").read_text(encoding="utf-8").endswith("root\n")


@pytest.fixture
def network() -> Iterator[Network]:
    made = Network()
    try:
        made.start()
        yield made
    finally:
        made.remove()


def start_caddy(network: Network, folder: Path, door: Path | None) -> str:
    """Start Caddy as the production does, under the public name, the certificate given or not."""
    caddy = services(PRODUCTION)["caddy"]
    variables = {
        "WATERFALL_DOMAIN": DOMAIN,
        "WATERFALL_ADDRESS": f"https://{DOMAIN}",
        "WATERFALL_ACME_EMAIL": "operator@waterfall.test",
        "WATERFALL_DOOR_CERTIFICATE": "given" if door else "",
    }
    assert set(variables) == set(caddy["environment"])
    if door is None:
        door = folder / "door"
        door.mkdir(mode=0o755)
    roots = folder / "trust"
    roots.mkdir()
    mounts = {CADDYFILE.resolve(): "/etc/caddy/Caddyfile.prod", trust(roots): "/trust"}
    mounts[door] = "/door"
    name = network.run(
        "caddy",
        *(argument for key, value in variables.items() for argument in ("--env", f"{key}={value}")),
        *(word for path, to in mounts.items() for word in ("--volume", f"{path}:{to}:ro")),
        mirrored(str(caddy["image"])),
        *caddy["command"],
    )
    deadline = time.monotonic() + STARTED_WITHIN
    while "serving initial configuration" not in docker("logs", name).stderr:
        assert time.monotonic() < deadline, docker("logs", name).stderr
        time.sleep(0.5)
    return name


def presented(network: Network, caddy: str, door: Path) -> str:
    """Reach Caddy as the front does, trusting the root given alone; give its certificate's hash."""
    reach = (
        "import hashlib, socket, ssl; "
        f"tls = ssl.create_default_context(cafile='/door/{production.DOOR_ROOT}'); "
        f"plain = socket.create_connection(('{caddy}', 443), 10); "
        f"door = tls.wrap_socket(plain, server_hostname='{DOMAIN}'); "
        "print('presented', hashlib.sha256(door.getpeercert(True)).hexdigest())"
    )
    client = network.run(
        "client",
        *("--volume", f"{door}:/door:ro"),
        mirrored(str(services(ISOLATED)["egress-sink"]["image"])),
        *("python", "-c", reach),
    )
    deadline = time.monotonic() + STARTED_WITHIN
    while "presented" not in (said := docker("logs", client)).stdout:
        assert time.monotonic() < deadline, said.stderr
        time.sleep(0.5)
    return said.stdout.split()[-1]


@NO_DAEMON
@NO_OPENSSL
@UNEXECUTED
def test_caddy_presents_the_certificate_given_under_a_public_name_and_asks_for_nothing(
    network: Network, tmp_path: Path
) -> None:
    door = production.door_certificate(tmp_path, DOMAIN)
    # As an operator's chain is: the issuer follows the certificate, so that Caddy could staple
    # OCSP, and ask the responder the certificate names, outside the network.
    with (door / "tls.crt").open("a", encoding="utf-8") as chain:
        chain.write((door / production.DOOR_ROOT).read_text(encoding="utf-8"))
    caddy = start_caddy(network, tmp_path, door)
    expected = hashlib.sha256(first_certificate(door / "tls.crt")).hexdigest()
    assert presented(network, caddy, door) == expected
    time.sleep(WATCHED)
    assert network.asked() == []


@NO_DAEMON
@UNEXECUTED
def test_caddy_without_a_certificate_given_is_caught_asking_let_s_encrypt(
    network: Network, tmp_path: Path
) -> None:
    # What makes the test above worth something, and the behaviour without the setting, unchanged:
    # the same Caddy, under the same name, asks for its certificate as it starts; the sink sees it.
    caddy = start_caddy(network, tmp_path, None)
    deadline = time.monotonic() + WATCHED
    while not network.asked() and time.monotonic() < deadline:
        time.sleep(1)
    found = network.asked()
    assert found
    assert {attempt.client for attempt in found} == {network.address_of(caddy)}
    names = {attempt.name for attempt in found}
    assert all(name.endswith(ASKED_OF_ACME) for name in names), names
    assert any(name.endswith("letsencrypt.org") for name in names), names
