# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The Caddyfile of production is adapted by the Caddy of the Compose and routes Grafana.

A directive that Caddy rejects only shows when Caddy starts: the production trial caught
``handle /grafana /grafana/*``, which takes one matcher. The image pinned by compose.prod.yaml
adapts the file, and the configuration it gives sends /grafana and /grafana/... to grafana:3000.
Docker is needed: a test skips without it, and says so.
"""

import json
import shutil
import subprocess
from typing import TYPE_CHECKING, Any, cast

import pytest
import yaml
from test_notification import CADDYFILE, PRODUCTION

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = [
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed"),
    pytest.mark.unexecuted("skipped where docker is not installed"),
]


def adapted() -> dict[str, Any]:
    """Adapt the Caddyfile of production with the image of the Compose."""
    services = yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]
    image = str(services["caddy"]["image"]).removeprefix("${WATERFALL_MIRROR:-}")
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


def test_the_caddyfile_of_production_is_adapted_and_sends_grafana_to_its_service() -> None:
    """Proper to US-2880: /grafana and /grafana/... reach grafana:3000 in the adapted file."""
    paths = {
        path
        for route in routes(adapted())
        if '"dial": "grafana:3000"' in json.dumps(route["handle"], sort_keys=True)
        for match in route["match"]
        for path in match.get("path", [])
    }
    assert {"/grafana", "/grafana/*"} <= paths
