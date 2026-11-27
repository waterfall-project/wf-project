# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Put every container of the platform under one slice of the cgroups, bounded (US-2810).

« Le déploiement par Compose aboutit sur une machine conforme à ces caractéristiques. »
(WF-CMP-0020-A): four cores and eight gigabytes for the whole platform, its data components and its
supervision included. The chain holds it by running the Compose of production under a slice of
systemd it has bounded to those resources (``production.yml``): a container cannot be asked to share
a limit — ``mem_limit`` is each its own —, but it can be run under a parent whose limit they share.
This module writes the file of Compose that gives each service of a project that parent
(``cgroup_parent``), read from the services the files of the project declare, so that none is
forgotten when one is added.
"""

import re
from typing import TYPE_CHECKING, Any, cast

import yaml

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = (
    COMPOSE / "compose.prod.yaml",
    COMPOSE / "compose.prod.local.yaml",
    COMPOSE / "compose.isolated.yaml",
)
RESTORE_TEST = (COMPOSE / "compose.restore-test.yaml",)
RESTORE_TEST_OVERRIDE = "WATERFALL_RESTORE_TEST_OVERRIDE"
"""Where ``restore-test.sh`` reads the file that bounds its ephemeral platform, when it is given."""


TAGS = re.compile(r"(?<=\s)!(?:reset|override)\s+")
"""The tags of Compose that merge files (`!reset`, `!override`), which a plain reader refuses."""


def _load(text: str) -> dict[str, Any]:
    """Read a file of Compose, without the tags that say how another file merges with it."""
    document: Any = yaml.safe_load(TAGS.sub("", text))
    return cast("dict[str, Any]", document) if isinstance(document, dict) else {}


def services(files: Sequence[Path]) -> list[str]:
    """Return the names of the services the files of Compose declare, in every profile."""
    names: set[str] = set()
    for path in files:
        document = _load(path.read_text(encoding="utf-8"))
        names.update(document.get("services", {}))
    return sorted(names)


def override(files: Sequence[Path], parent: str) -> str:
    """Return a file of Compose that runs every service of ``files`` under ``parent``."""
    document = {"services": {name: {"cgroup_parent": parent} for name in services(files)}}
    return yaml.safe_dump(document)


def environment(parent: str | None, folder: Path) -> dict[str, str]:
    """Write the files that bound the production and the test of a restoration; say where they are.

    Nothing is written and nothing is said when ``parent`` is not given: nothing is bounded.
    """
    if not parent:
        return {}
    production = folder / "bounded.yaml"
    production.write_text(override(PRODUCTION, parent), encoding="utf-8")
    ephemeral = folder / "bounded-restore-test.yaml"
    ephemeral.write_text(override(RESTORE_TEST, parent), encoding="utf-8")
    return {"WATERFALL_PRODUCTION_OVERRIDE": str(production), RESTORE_TEST_OVERRIDE: str(ephemeral)}
