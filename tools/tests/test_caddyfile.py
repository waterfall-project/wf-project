# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The Caddyfile of production is adapted by the Caddy of the Compose and routes Grafana.

A directive that Caddy rejects only shows when Caddy starts: the production trial caught
``handle /grafana /grafana/*``, which takes one matcher. The image pinned by compose.prod.yaml
adapts the file, and the configuration it gives sends /grafana and /grafana/... to grafana:3000,
by a route Caddy tries before that of Keycloak, /auth/*, and before the one without matcher, the
front's: a route tried after either would never be reached (#4332). A docker daemon is needed: a
test skips without one, and says so.
"""

import json
import subprocess
from typing import TYPE_CHECKING, Any, cast

import pytest
import yaml
from dockerdaemon import answers, mirrored

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = [
    pytest.mark.skipif(not answers(), reason="no docker daemon answers"),
    pytest.mark.unexecuted("skipped where no docker daemon answers"),
]

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = COMPOSE / "compose.prod.yaml"
CADDYFILE = COMPOSE / "Caddyfile.prod"
GRAFANA = '"dial": "grafana:3000"'


def adapted() -> dict[str, Any]:
    """Adapt the Caddyfile of production with the image of the Compose."""
    services = yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]
    image = mirrored(str(services["caddy"]["image"]))
    done = subprocess.run(
        [
            *("docker", "run", "--rm"),
            *("--env", "WATERFALL_DOMAIN=waterfall.test"),
            *("--env", "WATERFALL_ADDRESS=https://waterfall.test"),
            *("--env", "WATERFALL_ACME_EMAIL=operator@waterfall.test"),
            *("--volume", f"{CADDYFILE.resolve()}:/etc/caddy/Caddyfile.prod:ro"),
            image,
            *("caddy", "adapt", "--config", "/etc/caddy/Caddyfile.prod"),
            *("--adapter", "caddyfile"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return dict(json.loads(done.stdout))


def routes(node: object) -> Iterator[dict[str, Any]]:
    """Every route of the configuration that matches a path, at any depth."""
    if isinstance(node, dict):
        found = cast("dict[str, Any]", node)
        if "match" in found and "handle" in found:
            yield found
        for value in found.values():
            yield from routes(value)
    elif isinstance(node, list):
        for item in cast("list[Any]", node):
            yield from routes(item)


def lists(node: object) -> Iterator[list[dict[str, Any]]]:
    """Every list of routes of the configuration, at any depth, in the order Caddy tries them."""
    if isinstance(node, dict):
        found = cast("dict[str, Any]", node)
        for key, value in found.items():
            if key == "routes" and isinstance(value, list):
                yield cast("list[dict[str, Any]]", value)
            yield from lists(cast("object", value))
    elif isinstance(node, list):
        for item in cast("list[Any]", node):
            yield from lists(item)


def paths(route: dict[str, Any]) -> set[str]:
    return {path for match in route.get("match", []) for path in match.get("path", [])}


def sends_to_grafana(route: dict[str, Any]) -> bool:
    """Tell a route that matches a path and reaches grafana:3000; not the site that holds it."""
    return bool(paths(route)) and GRAFANA in json.dumps(route.get("handle"), sort_keys=True)


@pytest.mark.story("US-2880")
def test_the_caddyfile_of_production_is_adapted_and_sends_grafana_to_its_service() -> None:
    """Proper to US-2880: /grafana and /grafana/... reach grafana:3000 in the adapted file."""
    sent = {path for route in routes(adapted()) if sends_to_grafana(route) for path in paths(route)}
    assert {"/grafana", "/grafana/*"} <= sent


@pytest.mark.story("US-2880")
def test_the_route_of_grafana_is_tried_before_that_of_keycloak_and_that_of_the_front() -> None:
    """Proper to US-2880: Caddy tries Grafana before /auth/* and before the route without matcher.

    The last route without matcher is the front's, which takes every path left: the first route
    without matcher only sets the headers of every answer, and lets the others be tried.
    """
    (siblings,) = [found for found in lists(adapted()) if any(map(sends_to_grafana, found))]
    rank = {
        "grafana": next(i for i, route in enumerate(siblings) if sends_to_grafana(route)),
        "keycloak": next(i for i, route in enumerate(siblings) if "/auth/*" in paths(route)),
        "front": max(i for i, route in enumerate(siblings) if "match" not in route),
    }
    assert rank["grafana"] < rank["keycloak"] < rank["front"], rank
