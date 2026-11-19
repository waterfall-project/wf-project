# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Lint the chart of Waterfall, and render it as the chain renders it (US-2800).

Usage: ``python -m wftools.chart``.

``deploy/helm/waterfall`` is linted by Helm, strictly, with the values of the chain: every value the
chart cannot do without, the secrets included, given values of the chain, visible and named as
such. The tests of the chart (``make test-chart``) render it by :func:`render` and hold what the
objects say; ``wftools.charttrial`` installs it on a cluster of its own.
"""

import json
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from wftools import REPOSITORY, kubetools

TOOL = "wftools.chart"
CHART = REPOSITORY / "deploy" / "helm" / "waterfall"
RELEASE = "waterfall"
SECRET_KEYS = (
    "WATERFALL_POSTGRES_ADMIN_PASSWORD",
    "WATERFALL_POSTGRES_PASSWORD",
    "WATERFALL_SERVICE_DATABASE_PASSWORD",
    "WATERFALL_BACKUP_DATABASE_PASSWORD",
    "WATERFALL_KEYCLOAK_DATABASE_PASSWORD",
    "WATERFALL_REDIS_PASSWORD",
    "WATERFALL_KEYCLOAK_ADMIN_PASSWORD",
    "WATERFALL_FRONT_CLIENT_SECRET",
    "WATERFALL_SERVICE_CLIENT_SECRET",
    "WATERFALL_INSTALLATION_CLIENT_SECRET",
    "WATERFALL_SERVER_ACTIONS_KEY",
    "WATERFALL_STORAGE_SECRET",
    "WATERFALL_STORAGE_RPC_SECRET",
)
"""The keys of the Secret of the platform: the names of production.env.example."""
# Helm says, on its standard error, that it follows each link of files/ to deploy/compose.
_LINK_NOTICE = "found symbolic link in path"


class ChartError(Exception):
    """What Helm refuses of the chart."""


def chain_values() -> dict[str, Any]:
    """Return the values the chain renders the chart with: every one it cannot do without."""
    return {
        "platform": {"domain": "waterfall.localhost"},
        "images": {"tag": "chain"},
        "bootstrap": {
            "adminEmail": "administrateur@waterfall.test",
            "currency": "EUR",
            "companyName": "Delmas Automatismes",
        },
        "secrets": {"values": {key: f"chainonly{index}" for index, key in enumerate(SECRET_KEYS)}},
    }


def merged(base: Mapping[str, Any], given: Mapping[str, Any]) -> dict[str, Any]:
    """Return the values of the base with those given over them, section by section."""
    result = dict(base)
    for key, value in given.items():
        below = result.get(key)
        if isinstance(value, Mapping) and isinstance(below, Mapping):
            result[key] = merged(cast("Mapping[str, Any]", below), cast("Mapping[str, Any]", value))
        else:
            result[key] = value
    return result


def helm(arguments: list[str], values: Mapping[str, Any]) -> str:
    """Run Helm on the chart with the values given; return its output, or fail with its error."""
    with tempfile.TemporaryDirectory(prefix="waterfall-chart-") as folder:
        given = Path(folder) / "values.json"
        given.write_text(json.dumps(values), encoding="utf-8")
        done = subprocess.run(
            [str(kubetools.installed("helm")), *arguments, str(CHART), "--values", str(given)],
            capture_output=True,
            text=True,
            check=False,
        )
    said = "\n".join(line for line in done.stderr.splitlines() if _LINK_NOTICE not in line)
    if done.returncode != 0:
        raise ChartError(f"{said}\n{done.stdout}".strip())
    return done.stdout


def render(values: Mapping[str, Any] | None = None) -> str:
    """Render the chart, its hooks included, with the values of the chain and those given."""
    return helm(["template", RELEASE], merged(chain_values(), values or {}))


def main() -> int:
    """Lint the chart strictly, with the values of the chain."""
    try:
        print(helm(["lint", "--strict"], chain_values()).strip())
    except (ChartError, kubetools.ToolError, OSError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
