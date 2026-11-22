# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A component of the platform that stops and comes back: what the tests of the degraded mode share.

The services of the tests (PostgreSQL, Redis, the object storage) are shared by every process of
the run: none may be stopped for one test. Each component is reached through a ``Gate`` instead, a
relay on the loopback that the test closes and opens again: closed, the address refuses the
connections it had and the ones to come, as a server that is stopped does; open again, it is the
same server, its data as it was. What the services do when a component stops is what the sockets
make them do: nothing is replaced in them (WF-EXP-0040-A, §4.5.4 table 12).
"""

import contextlib
import socket
import threading
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from types import TracebackType

# How much a relay reads at a time.
BLOCK = 65536
# How often the relay looks whether it is asked to close, in seconds.
POLL = 0.05


class Gate:
    """A relay to a server, which is closed and opened again at the same address."""

    def __init__(self, host: str, port: int) -> None:
        """Open the relay on a free port of the loopback, to the server at ``host`` and ``port``."""
        self.target = (host, port)
        self._lock = threading.Lock()
        self._connections: list[socket.socket] = []
        self._listener: socket.socket | None = None
        self._acceptor: threading.Thread | None = None
        self._closing = threading.Event()
        self.port = 0
        self.open()

    @property
    def host(self) -> str:
        """Where the relay is reached: the loopback."""
        return "127.0.0.1"

    @property
    def address(self) -> str:
        """Where the relay is reached, as ``host:port``."""
        return f"{self.host}:{self.port}"

    def open(self) -> None:
        """Serve the server again, at the same port once it has one."""
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen()
        listener.settimeout(POLL)
        self.port = listener.getsockname()[1]
        self._closing.clear()
        self._listener = listener
        self._acceptor = threading.Thread(target=self._accept, args=(listener,), daemon=True)
        self._acceptor.start()

    def close(self) -> None:
        """Stop serving: the connections made are cut, those to come refused."""
        self._closing.set()
        listener, self._listener = self._listener, None
        acceptor, self._acceptor = self._acceptor, None
        if listener is not None:
            listener.close()
        if acceptor is not None:
            # The address is free once the call that waits on the listener has returned.
            acceptor.join()
        with self._lock:
            held, self._connections = self._connections, []
        for each in held:
            with contextlib.suppress(OSError):
                each.shutdown(socket.SHUT_RDWR)
            each.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()

    def _accept(self, listener: socket.socket) -> None:
        while not self._closing.is_set():
            try:
                client, _ = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            try:
                server = socket.create_connection(self.target, timeout=5)
            except OSError:
                client.close()
                continue
            server.settimeout(None)
            client.settimeout(None)
            with self._lock:
                self._connections.extend([client, server])
            for source, sink in ((client, server), (server, client)):
                threading.Thread(target=self._relay, args=(source, sink), daemon=True).start()

    @staticmethod
    def _relay(source: socket.socket, sink: socket.socket) -> None:
        try:
            while data := source.recv(BLOCK):
                sink.sendall(data)
        except OSError:
            return
        finally:
            for each in (source, sink):
                with contextlib.suppress(OSError):
                    each.shutdown(socket.SHUT_RDWR)
                each.close()
