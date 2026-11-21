# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A Prometheus of the tests: its query API, answering what a test says the metrics hold.

It answers the three paths the status screen reads (``waterfall.platform.prometheus``) as the query
API of Prometheus answers them — an instant vector for each expression, the alerts, the build — on
a port of its own, in HTTP. An expression a test has not given is an empty vector; a moment asked
(``time``) is answered from what the test gave at that moment, else from what it gave now.
"""

import json
import threading
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, override
from urllib.parse import parse_qs, urlsplit

if TYPE_CHECKING:
    import ssl
    from collections.abc import Mapping

# How often the loop of the server looks at whether it must stop.
POLL_INTERVAL = 0.05

type Vector = list[tuple[dict[str, str], float]]


def at(moment: datetime) -> str:
    """Give a moment as the query API reads it, in Unix seconds."""
    return f"{moment.timestamp():.3f}"


class TestPrometheus:
    """A query API of Prometheus, on a port of its own, until it is stopped."""

    __test__ = False

    def __init__(self, context: ssl.SSLContext | None = None) -> None:
        """Serve in HTTP, or in TLS when given the context of a server."""
        # The vector of each expression, by the moment asked: "" for now.
        self.vectors: dict[tuple[str, str], Vector] = {}
        # The alerts, as ``/api/v1/alerts`` lists them.
        self.alerts: list[dict[str, Any]] = []
        self.version = "3.16.0"
        # A status other than 200 makes every answer fail; a body that is not JSON, likewise.
        self.status: int = HTTPStatus.OK
        self.garbled = False
        # A success whose vector has not the shape of one.
        self.shapeless = False
        self.asked: list[str] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            @override
            def log_message(self, format: str, *args: Any) -> None:
                """Write nothing."""

            def do_GET(self) -> None:
                parsed = urlsplit(self.path)
                asked = {name: values[0] for name, values in parse_qs(parsed.query).items()}
                server.asked.append(asked.get("query", parsed.path))
                data = server.data(parsed.path, asked)
                if data is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                body = b"not json" if server.garbled else json.dumps(data).encode()
                self.send_response(server.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        if context is not None:
            self._server.socket = context.wrap_socket(self._server.socket, server_side=True)
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": POLL_INTERVAL}, daemon=True
        )
        self._thread.start()

    @property
    def address(self) -> str:
        """Where the query API is reached, as ``WATERFALL_PROMETHEUS_ADDRESS`` says it."""
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def holds(self, expression: str, vector: Vector, moment: datetime | None = None) -> None:
        """Make an expression evaluate to ``vector``, now or at a moment."""
        self.vectors[expression, "" if moment is None else at(moment)] = vector

    def fires(self, name: str, since: datetime, **labels: str) -> None:
        """Make an alert in progress, since a moment."""
        self.alerts.append(
            {
                "labels": {"alertname": name, **labels},
                "annotations": {},
                "state": "firing",
                "activeAt": since.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "value": "1e+00",
            }
        )

    def data(self, path: str, asked: Mapping[str, str]) -> object:
        """Give the document of the answer to a path; ``None`` for a path the API does not have."""
        if path == "/api/v1/query" and self.shapeless:
            shapeless: dict[str, object] = {"result": [{}]}
            return {"status": "success", "data": shapeless}
        if path == "/api/v1/query":
            vector = self.vectors.get(
                (asked["query"], asked.get("time", "")), self.vectors.get((asked["query"], ""), [])
            )
            now = datetime.now(UTC).timestamp()
            result = [{"metric": labels, "value": [now, repr(value)]} for labels, value in vector]
            return {"status": "success", "data": {"resultType": "vector", "result": result}}
        if path == "/api/v1/alerts":
            return {"status": "success", "data": {"alerts": self.alerts}}
        if path == "/api/v1/status/buildinfo":
            return {"status": "success", "data": {"version": self.version}}
        return None

    def stop(self) -> None:
        """Stop answering, as a Prometheus that is down."""
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()
