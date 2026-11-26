# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What tries to leave the network of an isolated platform: the sink of its names, and its door.

Usage, in a container of ``deploy/compose/compose.isolated.yaml``: ``python egress.py sink``,
``python egress.py door <port>:<host>:<port>…``, ``python egress.py probe <port>``.

The production platform runs isolated in the chain (US-3010, WF-CMP-0030): every network of it is
internal, which Docker gives no route out, so that a connection to an address outside fails at
once. That alone sees nothing: a component that tries to go out fails silently, or waits, and the
trial would pass. So every service of the platform resolves through Docker's resolver, which
answers the names of the platform itself and forwards every other one to the sink, the server a
service names in ``dns``: the sink answers that the name does not exist — at once, nothing waits on
it — and writes it, with the address of the container that asked, on its standard output, one line
``query <address> <type> <name>``. Every connection out begins by such a name: the trial reads the
lines at its end (``attempts``) and fails on each name outside the platform, naming the service.

What the sink does not see: a connection to an address written without a name asks no resolver.
It fails all the same, the network having no route out, but nothing says it was tried.

The door is the only container on a network with a way out, the one Docker publishes the ports of
the platform on: it relays each port it is given to its server inside — Caddy —, byte for byte, the
TLS included, so that Caddy, the door of the installation, stays on the internal network with the
rest. It stands for the firewall that lets the users in: no component of Waterfall runs on it.

Run by the image of Python of Docker Hub, mounted as a file: the standard library alone.
"""

import asyncio
import contextlib
import ipaddress
import socket
import socketserver
import struct
import sys
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from collections.abc import Sequence

PORT = 53
HEADER = 12
"""The bytes of the header of a message of DNS, before its question."""
NAME_ERROR = 3
"""The code of an answer that says the name does not exist (NXDOMAIN)."""
LABEL = 63
"""The longest label of a name: a byte above says a pointer, which a question does not carry."""
LENGTH = struct.Struct("!H")
TIMEOUT = 5.0
CHUNK = 65536
REVERSE = {".in-addr.arpa": 4, ".ip6.arpa": 32}
"""The suffixes of the reverse lookups, and the labels of the address each carries."""
FIELDS = 4
"""The words of a line of the sink: ``query``, the address, the type, the name."""


class MessageError(ValueError):
    """A message the sink cannot read as a question of DNS."""


@dataclass(frozen=True)
class Question:
    """The question of a message: the name asked, the type of the record, where it ends."""

    name: str
    kind: int
    end: int


def _presented(label: str) -> str:
    r"""Write a label as a zone file does: a space or a control character as ``\ddd``.

    A name written on one line of the sink is one word, whatever its bytes.
    """
    return "".join(
        character
        if character.isprintable() and not character.isspace()
        else f"\\{ord(character):03d}"
        for character in label
    )


def question(message: bytes) -> Question:
    """Read the first question of a message of DNS."""
    offset = HEADER
    labels: list[str] = []
    try:
        while length := message[offset]:
            if length > LABEL:
                said = "a pointer in a question"
                raise MessageError(said)
            labels.append(_presented(message[offset + 1 : offset + 1 + length].decode("ascii")))
            offset += 1 + length
        (kind,) = LENGTH.unpack_from(message, offset + 1)
    except (IndexError, UnicodeDecodeError, struct.error) as error:
        raise MessageError(str(error)) from error
    # The null label, the type and the class.
    return Question(".".join(labels), kind, offset + 5)


def refusal(message: bytes) -> bytes:
    """Answer a question that its name does not exist: the identifier and the question kept."""
    asked = question(message)
    flags = 0x8000 | (message[2] & 0x79) << 8 | 0x0080 | NAME_ERROR
    header = message[:2] + struct.pack("!HHHHH", flags, 1, 0, 0, 0)
    return header + message[HEADER : asked.end]


def line(client: str, message: bytes) -> str:
    """Say a question asked, as the sink writes it."""
    asked = question(message)
    return f"query {client} {asked.kind} {asked.name}"


@dataclass(frozen=True)
class Attempt:
    """A name asked from inside the platform that only a server outside it would answer."""

    client: str
    name: str


def _private_reverse(name: str) -> bool:
    """Tell whether a name asks the name of a private address, the platform's own."""
    for suffix, count in REVERSE.items():
        if name.endswith(suffix):
            labels = name.removesuffix(suffix).split(".")
            if len(labels) != count:
                return False
            reverse = labels[::-1]
            text = (
                ".".join(reverse)
                if count == REVERSE[".in-addr.arpa"]
                else ":".join("".join(reverse[i : i + 4]) for i in range(0, count, 4))
            )
            try:
                return ipaddress.ip_address(text).is_private
            except ValueError:
                return False
    return False


def leaves(name: str, domain: str) -> bool:
    """Tell whether a name asked is outside the platform.

    A name of one label is a service of the platform, asked while it restarts, which no server
    outside could answer; the domain of the platform and its subdomains are Caddy's, inside; so is
    the name of a private address. Every other name is a server outside.
    """
    name = name.lower().rstrip(".")
    domain = domain.lower().rstrip(".")
    if "." not in name or name == domain or name.endswith(f".{domain}"):
        return False
    return not _private_reverse(name)


def attempts(log: str, domain: str) -> list[Attempt]:
    """Read the lines of the sink: each name asked that leaves the platform, once, in order."""
    found: dict[Attempt, None] = {}
    for written in log.splitlines():
        words = written.split()
        if len(words) == FIELDS and words[0] == "query" and leaves(words[3], domain):
            found[Attempt(words[1], words[3].lower().rstrip("."))] = None
    return list(found)


def _answer(client: str, message: bytes) -> bytes | None:
    try:
        said = line(client, message)
        answered = refusal(message)
    except MessageError as error:
        print(f"unread {client} {error}", flush=True)
        return None
    print(said, flush=True)
    return answered


class _Datagram(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        message, sock = self.request
        answered = _answer(self.client_address[0], message)
        if answered is not None:
            sock.sendto(answered, self.client_address)


class _Stream(socketserver.StreamRequestHandler):
    @override
    def handle(self) -> None:
        self.connection.settimeout(TIMEOUT)
        with contextlib.suppress(OSError, struct.error):
            while size := self.rfile.read(LENGTH.size):
                (length,) = LENGTH.unpack(size)
                answered = _answer(self.client_address[0], self.rfile.read(length))
                if answered is None:
                    return
                self.wfile.write(LENGTH.pack(len(answered)) + answered)


class _Udp(socketserver.ThreadingUDPServer):
    daemon_threads = True
    allow_reuse_address = True


class _Tcp(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def sink(port: int = PORT, host: str = "") -> tuple[socketserver.BaseServer, ...]:
    """Serve the sink on a port, in UDP and TCP, in threads; give the servers, to shut them.

    Every interface by default: the services reach it at its address in each network.
    """
    servers = (_Udp((host, port), _Datagram), _Tcp((host, port), _Stream))
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    return servers


@dataclass(frozen=True)
class Route:
    """A port the door listens on, and the server inside it relays to."""

    port: int
    host: str
    target: int


def route(given: str) -> Route:
    """Read a route of the door, ``<port>:<host>:<port>``."""
    port, host, target = given.split(":")
    return Route(int(port), host, int(target))


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    with contextlib.suppress(OSError):
        while data := await reader.read(CHUNK):
            writer.write(data)
            await writer.drain()
        if writer.can_write_eof():
            writer.write_eof()


async def _relay(target: Route, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        inner_reader, inner_writer = await asyncio.open_connection(target.host, target.target)
    except OSError:
        writer.close()
        return
    await asyncio.gather(_pipe(reader, inner_writer), _pipe(inner_reader, writer))
    for each in (writer, inner_writer):
        each.close()


async def door(routes: Sequence[Route], host: str | None = None) -> list[asyncio.Server]:
    """Listen on the port of each route, and relay each connection to its server inside."""
    servers: list[asyncio.Server] = []
    for each in routes:

        async def relay(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter, target: Route = each
        ) -> None:
            await _relay(target, reader, writer)

        servers.append(await asyncio.start_server(relay, host, each.port))
    return servers


async def _serve_door(routes: Sequence[Route]) -> None:
    servers = await door(routes)
    print(" ".join(f"{r.port}->{r.host}:{r.target}" for r in routes), flush=True)
    await asyncio.gather(*(server.serve_forever() for server in servers))


def probe(port: int) -> int:
    """Tell whether something listens on a port of the loopback, in TCP: the health check."""
    try:
        socket.create_connection(("127.0.0.1", port), TIMEOUT).close()
    except OSError:
        return 1
    return 0


def main(arguments: Sequence[str]) -> int:
    """Run the sink, the door, or the probe."""
    match list(arguments):
        case ["sink"]:
            sink()
            print(f"the sink answers on {PORT}", flush=True)
            threading.Event().wait()
            return 0
        case ["door", *given] if given:
            asyncio.run(_serve_door([route(each) for each in given]))
            return 0
        case ["probe", port]:
            return probe(int(port))
        case _:
            print(__doc__, file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
