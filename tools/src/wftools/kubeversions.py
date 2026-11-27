# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The oldest version of Kubernetes the chart declares: tried, and kept maintained (US-2810).

« Le chart s'installe sur deux distributions de Kubernetes différentes sans modification. »
(WF-CMP-0020-A, and #5069 for its wording: the chain deploys the chart on the minimal version it
declares.)

``kubeVersion`` of ``Chart.yaml`` is the one place the oldest version is written. :func:`minimum`
reads it; the node of kind the trial makes is that of this minor version (:func:`node`), so that
changing ``kubeVersion`` changes the version tried, and a minor version without a pinned node is
refused rather than guessed. :func:`check` refuses a ``kubeVersion`` older than the oldest version
of ``tools/kubernetes-maintained.toml``, a dated list that the publication will update (US-3000,
not yet delivered): ``make lint-chart`` runs it.
"""

import re
import sys
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from wftools import REPOSITORY

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

TOOL = "wftools.kubeversions"
CHART = REPOSITORY / "deploy" / "helm" / "waterfall" / "Chart.yaml"
MAINTAINED = REPOSITORY / "tools" / "kubernetes-maintained.toml"
CONSTRAINT = re.compile(r"^>=\s*v?(\d+)\.(\d+)\.\d+(?:-0)?$")
"""The only form the chart declares: ``>=1.35.0-0``, an oldest version and no other bound."""
Version = tuple[int, int]
NODES: dict[Version, str] = {
    (1, 34): (
        "kindest/node:v1.34.11"
        "@sha256:44e222ee2132dab25ff87301682f89eb82c7880ea3a1bf543bfe9708fd08d67d"
    ),
    (1, 35): (
        "kindest/node:v1.35.8"
        "@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0"
    ),
    (1, 36): (
        "kindest/node:v1.36.4"
        "@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed"
    ),
    (1, 37): (
        "kindest/node:v1.37.0"
        "@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5"
    ),
}
"""The nodes of kind 0.33.0 by minor version, by the digests its release names: raise them with
the version of kind (``wftools.kubetools``)."""


class VersionError(Exception):
    """What keeps the oldest version of Kubernetes from being read, tried or accepted."""


@dataclass(frozen=True, slots=True)
class Maintained:
    """The list of the versions Kubernetes maintains, and the day it was drawn up."""

    as_of: date
    versions: tuple[Version, ...]


def text(version: Version) -> str:
    """Return a minor version as written: ``1.35``."""
    return f"{version[0]}.{version[1]}"


def minimum(chart: Path = CHART) -> Version:
    """Return the oldest minor version ``kubeVersion`` of the chart allows."""
    declared = yaml.safe_load(chart.read_text(encoding="utf-8")).get("kubeVersion")
    found = CONSTRAINT.match(str(declared).strip())
    if found is None:
        message = f"kubeVersion {declared!r} of {chart} is not of the form >=1.35.0-0"
        raise VersionError(message)
    return int(found[1]), int(found[2])


def node(chart: Path = CHART) -> str:
    """Return the node of kind, by its digest, for the oldest version the chart declares."""
    version = minimum(chart)
    if version not in NODES:
        message = (
            f"no node of kind is pinned for Kubernetes {text(version)}, the kubeVersion of the "
            f"chart: pin one in {TOOL}.NODES, from the notes of the release of kind"
        )
        raise VersionError(message)
    return NODES[version]


def maintained(source: Path = MAINTAINED) -> Maintained:
    """Read the list of the versions Kubernetes maintains."""
    document = tomllib.loads(source.read_text(encoding="utf-8"))
    as_of: date = document["as_of"]
    versions: list[Version] = []
    for entry in document["maintained"]:
        major, minor = entry["version"].split(".")
        if entry["end_of_life"] < as_of:
            message = f"{source}: {entry['version']} ends on {entry['end_of_life']}, before {as_of}"
            raise VersionError(message)
        versions.append((int(major), int(minor)))
    if not versions:
        message = f"{source} lists no version"
        raise VersionError(message)
    return Maintained(as_of, tuple(sorted(versions)))


def check(chart: Path = CHART, source: Path = MAINTAINED) -> None:
    """Refuse a ``kubeVersion`` older than the oldest version of Kubernetes still maintained."""
    declared = minimum(chart)
    listed = maintained(source)
    if declared < listed.versions[0]:
        message = (
            f"kubeVersion of {chart} is {text(declared)}, older than {text(listed.versions[0])}, "
            f"the oldest version of Kubernetes maintained on {listed.as_of} ({source})"
        )
        raise VersionError(message)


def main(chart: Path = CHART, source: Path = MAINTAINED) -> int:
    """Check the ``kubeVersion`` of the chart against the list of the maintained versions."""
    try:
        check(chart, source)
    except (VersionError, OSError, KeyError, ValueError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
