# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The sink of the names and the door of the isolated platform (US-3010, WF-CMP-0030).

The sink answers every name it is asked that it does not exist, at once, and writes it down with who
asked; the trial reads its lines and keeps the names outside the platform. The door relays a port
byte for byte. Both are held here in process; then, where a docker daemon answers, on an internal
network as the trial makes it: a client that asks for a server outside fails at once and the sink
names it, and Grafana started as the production starts it asks for nothing — when a Grafana with its
defaults, the same image, is caught asking for grafana.com. The images are pulled behind
``WATERFALL_MIRROR``, as the Compose pulls them (#4321).
"""

import asyncio
import shutil
import socket
import struct
import subprocess
import time
import uuid
from typing import TYPE_CHECKING, cast

import pytest
from dockerdaemon import answers, mirrored
from test_grafanalive import certificates, production, substituted, trust
from test_grafanalive import image as grafana_image
from test_supervision import services

from wftools import REPOSITORY, egress

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

pytestmark = pytest.mark.story("US-3010")

ISOLATED = REPOSITORY / "deploy" / "compose" / "compose.isolated.yaml"
PRODUCTION = ISOLATED.parent / "compose.prod.yaml"
EGRESS = REPOSITORY / "tools" / "src" / "wftools" / "egress.py"
DOMAIN = "waterfall.localhost"
A = 1
AAAA = 28
IDENTIFIER = b"\x12\x34"


def asked(name: str, kind: int = A, flags: int = 0x0100) -> bytes:
    """Make a question of DNS for a name, recursion desired, as a resolver forwards it."""
    labels = b"".join(bytes([len(part)]) + part.encode() for part in name.split("."))
    return (
        IDENTIFIER
        + struct.pack("!HHHHH", flags, 1, 0, 0, 0)
        + labels
        + b"\0"
        + struct.pack("!HH", kind, 1)
    )


def test_the_sink_answers_at_once_that_the_name_does_not_exist_keeping_the_question() -> None:
    question = asked("grafana.com")
    answer = egress.refusal(question)
    flags, questions, answers_, authorities, additional = struct.unpack_from("!HHHHH", answer, 2)
    assert answer[:2] == IDENTIFIER
    # An answer (QR), recursion desired kept and available, the name does not exist (NXDOMAIN).
    assert flags & 0x8000
    assert flags & 0x0100
    assert flags & 0x0080
    assert flags & 0x000F == egress.NAME_ERROR
    assert (questions, answers_, authorities, additional) == (1, 0, 0, 0)
    assert answer[egress.HEADER :] == question[egress.HEADER :]


def test_the_sink_says_who_asked_which_type_of_which_name() -> None:
    assert (
        egress.line("10.213.0.7", asked("Grafana.com", AAAA)) == "query 10.213.0.7 28 Grafana.com"
    )
    # A name is one word on its line, whatever its bytes: the trial reads it whole.
    assert egress.line("10.213.0.7", asked("a b\t.com")) == r"query 10.213.0.7 1 a\032b\009.com"


@pytest.mark.parametrize(
    "message",
    [b"\x12\x34", asked("grafana.com")[:-3], asked("a.b").replace(b"\x01a", b"\xc0a")],
    ids=["no question", "cut short", "a pointer"],
)
def test_a_message_that_is_no_question_is_refused_without_an_answer(message: bytes) -> None:
    with pytest.raises(egress.MessageError):
        egress.refusal(message)


@pytest.mark.parametrize(
    ("name", "out"),
    [
        ("grafana.com", True),
        ("pool.ntp.org.", True),
        ("fonts.googleapis.com", True),
        ("keycloak", False),
        ("waterfall.localhost", False),
        ("WATERFALL.localhost.", False),
        ("auth.waterfall.localhost", False),
        ("7.0.213.10.in-addr.arpa", False),
        ("8.8.8.8.in-addr.arpa", True),
        ("1.2.in-addr.arpa", True),
        ("x.0.213.10.in-addr.arpa", True),
        (".".join(["1", *"0" * 29, "d", "f"]) + ".ip6.arpa", False),
        (".".join(["1", *"0" * 30, "2"]) + ".ip6.arpa", True),
    ],
)
def test_a_name_leaves_the_platform_unless_it_is_a_service_its_domain_or_a_private_address(
    name: str, *, out: bool
) -> None:
    assert egress.leaves(name, DOMAIN) is out


def test_the_trial_reads_each_name_out_of_the_platform_once_in_order() -> None:
    log = (
        "the sink answers on 53\n"
        "query 10.213.0.9 1 keycloak\n"
        "query 10.213.0.7 1 grafana.com\n"
        "query 10.213.0.7 28 grafana.com.\n"
        "unread 10.213.0.8 a pointer in a question\n"
        "query 10.213.0.8 1 waterfall.localhost\n"
        "query 10.213.0.8 1 Pool.NTP.org\n"
    )
    assert egress.attempts(log, DOMAIN) == [
        egress.Attempt("10.213.0.7", "grafana.com"),
        egress.Attempt("10.213.0.8", "pool.ntp.org"),
    ]
    assert egress.attempts("", DOMAIN) == []


@pytest.fixture
def served() -> Iterator[tuple[int, int]]:
    """Serve the sink on the loopback; give its ports in UDP and in TCP."""
    servers = egress.sink(0, "127.0.0.1")
    try:
        udp, tcp = (cast("tuple[str, int]", server.server_address) for server in servers)
        yield udp[1], tcp[1]
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


def test_the_sink_answers_in_udp_and_tcp_and_writes_each_question(
    served: tuple[int, int], capsys: pytest.CaptureFixture[str]
) -> None:
    udp, tcp = served
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(5)
        client.sendto(asked("grafana.com"), ("127.0.0.1", udp))
        answer, _ = client.recvfrom(512)
    assert answer == egress.refusal(asked("grafana.com"))
    with socket.create_connection(("127.0.0.1", tcp), 5) as client:
        question = asked("pool.ntp.org")
        client.sendall(struct.pack("!H", len(question)) + question)
        (length,) = struct.unpack("!H", client.recv(2))
        answer = client.recv(length)
    assert answer == egress.refusal(question)
    deadline = time.monotonic() + 5
    said = ""
    while time.monotonic() < deadline and "pool.ntp.org" not in said:
        said += capsys.readouterr().out
        time.sleep(0.05)
    assert "query 127.0.0.1 1 grafana.com" in said
    assert "query 127.0.0.1 1 pool.ntp.org" in said


def test_the_door_relays_each_port_byte_for_byte_both_ways() -> None:
    async def trial() -> bytes:
        async def echo(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            writer.write(b"inside:" + await reader.read(100))
            await writer.drain()
            writer.close()

        inside = await asyncio.start_server(echo, "127.0.0.1", 0)
        port = inside.sockets[0].getsockname()[1]
        doors = await egress.door([egress.Route(0, "127.0.0.1", port)], "127.0.0.1")
        entry = doors[0].sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", entry)
        writer.write(b"\x16\x03\x01hello")
        writer.write_eof()
        said = await asyncio.wait_for(reader.read(), 5)
        writer.close()
        for server in (*doors, inside):
            server.close()
        return said

    assert asyncio.run(trial()) == b"inside:\x16\x03\x01hello"


def test_a_route_of_the_door_names_its_port_and_the_server_inside() -> None:
    assert egress.route("8443:caddy:443") == egress.Route(8443, "caddy", 443)


def test_the_probe_says_whether_a_port_listens() -> None:
    with socket.create_server(("127.0.0.1", 0)) as listening:
        port = listening.getsockname()[1]
        assert egress.probe(port) == 0
    assert egress.probe(port) == 1
    assert egress.main(["nothing"]) == 2


# --- On an internal network, as the trial makes it. ---------------------------------------------

NO_DAEMON = pytest.mark.skipif(
    not answers() or shutil.which("openssl") is None,
    reason="no docker daemon answers, or openssl is not installed",
)
UNEXECUTED = pytest.mark.unexecuted(
    "skipped where no docker daemon answers or openssl is not installed"
)
STARTED_WITHIN = 120.0
# Grafana checks its updates as it starts: what it would ask, it asks within this time.
WATCHED = 30.0


def docker(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *arguments], capture_output=True, text=True, check=False)


def image_of(path: Path, service: str) -> str:
    """Give the image of a service of a Compose file, as Compose pulls it."""
    return mirrored(str(services(path)[service]["image"]))


class Network:
    """An internal network, its sink, and the containers a test starts on it."""

    def __init__(self) -> None:
        self.name = f"waterfall-egress-us3010-{uuid.uuid4().hex[:8]}"
        self.started: list[str] = []
        self.address = ""

    def start(self) -> None:
        created = docker("network", "create", "--internal", self.name)
        assert created.returncode == 0, created.stderr
        sink = self.run(
            "sink",
            *("--user", "65534:65534", "--volume", f"{EGRESS}:/opt/egress.py:ro"),
            image_of(ISOLATED, "egress-sink"),
            *("python", "/opt/egress.py", "sink"),
            resolved=False,
        )
        inspected = docker(
            "inspect", "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", sink
        )
        self.address = inspected.stdout.strip()
        deadline = time.monotonic() + STARTED_WITHIN
        while "the sink answers" not in docker("logs", sink).stdout:
            assert time.monotonic() < deadline, docker("logs", sink).stderr
            time.sleep(0.5)

    def run(self, role: str, *arguments: str, resolved: bool = True) -> str:
        """Start a container on the network, resolving through the sink; give its name.

        No search domain, as the isolated Compose: else the container inherits the host's — a
        runner's — and asks each name it does not find again with that domain after it.
        """
        name = f"{self.name}-{role}"
        dns = ("--dns", self.address, "--dns-search", ".") if resolved else ()
        started = docker(
            "run", "--detach", "--name", name, "--network", self.name, *dns, *arguments
        )
        assert started.returncode == 0, started.stderr
        self.started.append(name)
        return name

    def asked(self) -> list[egress.Attempt]:
        """Read what the sink wrote: the names asked out of the platform."""
        return egress.attempts(docker("logs", f"{self.name}-sink").stdout, DOMAIN)

    def address_of(self, name: str) -> str:
        return docker(
            "inspect", "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name
        ).stdout.strip()

    def remove(self) -> None:
        for name in self.started:
            docker("rm", "--force", "--volumes", name)
        docker("network", "rm", self.name)


@pytest.fixture
def network() -> Iterator[Network]:
    made = Network()
    try:
        made.start()
        yield made
    finally:
        made.remove()


@NO_DAEMON
@UNEXECUTED
def test_a_client_that_asks_for_a_server_outside_fails_at_once_and_the_sink_names_it(
    network: Network,
) -> None:
    # The client stays once curl has ended, so that its address is still the network's.
    client = network.run(
        "client",
        *("--entrypoint", "sh", image_of(PRODUCTION, "storage-buckets")),
        "-c",
        "took=$(curl --silent --max-time 60 --write-out '%{time_total}' https://grafana.com/);"
        ' echo "curl $? $took"; sleep 300',
    )
    deadline = time.monotonic() + STARTED_WITHIN
    while "curl " not in (said := docker("logs", client).stdout):
        assert time.monotonic() < deadline, "curl did not end"
        time.sleep(0.2)
    # curl could not resolve the host (6), at once: nothing waited on the sink.
    _, code, took = said.split()
    assert code == "6"
    assert float(took) < 1
    assert network.asked() == [egress.Attempt(network.address_of(client), "grafana.com")]


def grafana_variables(*, production_settings: bool) -> dict[str, str]:
    """Give the variables of Grafana in the production Compose, or without those that keep it in."""
    given = {"WATERFALL_GRAFANA_ADMIN_PASSWORD": "egress-test-only", "WATERFALL_DOMAIN": DOMAIN}
    variables = {
        name: substituted(str(value), given) for name, value in production()["environment"].items()
    }
    if production_settings:
        return variables
    return {
        name: value
        for name, value in variables.items()
        if not name.startswith(("GF_ANALYTICS_", "GF_NEWS_", "GF_PLUGINS_"))
    }


def start_grafana(network: Network, folder: Path, *, production_settings: bool) -> str:
    """Start Grafana on the network, with the mounts of the production Compose."""
    volumes = {
        "trust": trust(folder / "trust"),
        "certificates-grafana": certificates(folder / "certificates"),
    }
    mounts: list[str] = []
    for volume in production()["volumes"]:
        source, target, mode = str(volume).split(":")
        path = volumes.get(source) or (ISOLATED.parent / source).resolve()
        mounts += ["--volume", f"{path}:{target}:{mode}"]
    variables = grafana_variables(production_settings=production_settings)
    name = network.run(
        "grafana",
        *(argument for key, value in variables.items() for argument in ("--env", f"{key}={value}")),
        *mounts,
        grafana_image(),
    )
    deadline = time.monotonic() + STARTED_WITHIN
    while "HTTP Server Listen" not in docker("logs", name).stdout + docker("logs", name).stderr:
        assert time.monotonic() < deadline, "Grafana did not start"
        time.sleep(1)
    return name


@NO_DAEMON
@UNEXECUTED
def test_grafana_as_the_production_starts_it_asks_for_no_server_outside(
    network: Network, tmp_path: Path
) -> None:
    for each in ("trust", "certificates"):
        (tmp_path / each).mkdir()
    start_grafana(network, tmp_path, production_settings=True)
    time.sleep(WATCHED)
    assert network.asked() == []


@NO_DAEMON
@UNEXECUTED
def test_grafana_left_to_its_defaults_is_caught_asking_for_grafana_com(
    network: Network, tmp_path: Path
) -> None:
    # What makes the test above worth something: the same image, without the variables of the
    # production that keep it inside, asks for its updates as it starts, and the sink sees it.
    for each in ("trust", "certificates"):
        (tmp_path / each).mkdir()
    grafana = start_grafana(network, tmp_path, production_settings=False)
    deadline = time.monotonic() + WATCHED
    while not network.asked() and time.monotonic() < deadline:
        time.sleep(1)
    found = network.asked()
    assert found
    assert {attempt.client for attempt in found} == {network.address_of(grafana)}
    names = [attempt.name for attempt in found]
    assert all(name == "grafana.com" or name.endswith(".grafana.com") for name in names), names
