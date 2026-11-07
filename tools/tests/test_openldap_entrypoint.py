# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The seeding of the directory of test, on volumes that stand for those of the platform (#1994).

``deploy/openldap/entrypoint.sh`` runs in the image the repository builds, on two throwaway named
volumes, data and configuration, of a name of its own to each test and removed after it. Without
configuration, it empties and seeds again the volume of the data only if the marker it lays before
loading the seed is there — a seeding interrupted — or if the volume is empty; data without marker
are a directory that has served, and it refuses. Volumes laid without the entrypoint, as the image
of osixia left them, and a marker left beside the configuration by a stop between its copy and the
removal, are served as they are. Docker is needed: a test skips without it.
"""

import shutil
import subprocess
import uuid
from typing import TYPE_CHECKING

import pytest

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Iterator

OPENLDAP = REPOSITORY / "deploy" / "openldap"
SEED = REPOSITORY / "deploy" / "keycloak" / "development" / "directory.ldif"
REMEDY = "make service-down WATERFALL_RESET_DATA=yes"
MARKER = ".seeding"

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")


class Volumes:
    """The image and the two throwaway volumes of one test."""

    def __init__(self, image: str, name: str) -> None:
        self.image = image
        self.data = f"{name}-data"
        self.config = f"{name}-config"

    def run(self, script: str) -> subprocess.CompletedProcess[str]:
        """Run a shell script in the image, on the two volumes and the seed."""
        return subprocess.run(
            [
                *("docker", "run", "--rm", "--entrypoint", "sh"),
                *("--env", "WATERFALL_DIRECTORY_ADMIN_PASSWORD=development-only"),
                *("--volume", f"{SEED}:/seed/directory.ldif:ro"),
                *("--volume", f"{self.data}:/var/lib/ldap"),
                *("--volume", f"{self.config}:/etc/ldap/slapd.d"),
                self.image,
                *("-c", script),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def start(self) -> subprocess.CompletedProcess[str]:
        """Run the entrypoint for a few seconds: slapd serves until it is stopped (code 124)."""
        return self.run("timeout 8 /usr/local/bin/entrypoint.sh")

    def listing(self) -> str:
        """Return the files of the two volumes, the data first."""
        return self.run("ls -A /var/lib/ldap; echo ---; ls -A /etc/ldap/slapd.d").stdout


@pytest.fixture(scope="module")
def image() -> Iterator[str]:
    name = f"waterfall-openldap-us1270-l1-{uuid.uuid4().hex[:8]}"
    subprocess.run(["docker", "build", "--quiet", "--tag", name, str(OPENLDAP)], check=True)
    yield name
    subprocess.run(["docker", "rmi", name], check=False, capture_output=True)


@pytest.fixture
def volumes(image: str) -> Iterator[Volumes]:
    found = Volumes(image, f"waterfall-us1270-l1-{uuid.uuid4().hex[:8]}")
    for volume in (found.data, found.config):
        subprocess.run(["docker", "volume", "create", volume], check=True, capture_output=True)
    yield found
    for volume in (found.data, found.config):
        subprocess.run(["docker", "volume", "rm", volume], check=False, capture_output=True)


def test_two_empty_volumes_are_seeded_and_the_marker_is_gone(volumes: Volumes) -> None:
    assert volumes.start().returncode == 124
    data, config = volumes.listing().split("---")
    assert "data.mdb" in data
    assert MARKER not in data
    assert "cn=config.ldif" in config


def test_an_interrupted_seeding_is_emptied_and_seeded_again(volumes: Volumes) -> None:
    left = f"/var/lib/ldap/{MARKER} /var/lib/ldap/stale /var/lib/ldap/data.mdb"
    prepared = volumes.run(f"touch {left}")
    assert prepared.returncode == 0
    assert volumes.start().returncode == 124
    data, config = volumes.listing().split("---")
    assert "stale" not in data
    assert MARKER not in data
    assert "cn=config.ldif" in config


def test_data_that_served_without_configuration_are_refused_with_the_remedy(
    volumes: Volumes,
) -> None:
    assert volumes.start().returncode == 124
    gone = volumes.run("rm -rf /etc/ldap/slapd.d/* && touch /var/lib/ldap/served")
    assert gone.returncode == 0
    before = volumes.listing()
    refused = volumes.start()
    assert refused.returncode == 1
    assert REMEDY in refused.stderr
    assert volumes.listing() == before
    assert "served" in before.split("---")[0]


def test_a_later_start_loads_nothing(volumes: Volumes) -> None:
    assert volumes.start().returncode == 124
    kept = volumes.run("touch /var/lib/ldap/kept")
    assert kept.returncode == 0
    assert volumes.start().returncode == 124
    assert "kept" in volumes.listing().split("---")[0]


def test_volumes_laid_without_the_entrypoint_are_not_emptied_or_refused(volumes: Volumes) -> None:
    """Data and configuration without marker, as osixia's image left them: nothing is touched."""
    laid = volumes.run("touch /etc/ldap/slapd.d/cn=config.ldif /var/lib/ldap/osixia")
    assert laid.returncode == 0
    started = volumes.start()
    assert REMEDY not in started.stderr
    assert "interrupted" not in started.stderr
    data, config = volumes.listing().split("---")
    assert "osixia" in data
    assert "cn=config.ldif" in config
    assert MARKER not in data


def test_a_marker_left_beside_the_configuration_is_removed_and_nothing_emptied(
    volumes: Volumes,
) -> None:
    """A stop between the copy of the configuration and the removal of the marker leaves both."""
    assert volumes.start().returncode == 124
    left = volumes.run(f"touch /var/lib/ldap/{MARKER} /var/lib/ldap/kept")
    assert left.returncode == 0
    assert volumes.start().returncode == 124
    data, config = volumes.listing().split("---")
    assert MARKER not in data
    assert "kept" in data
    assert "cn=config.ldif" in config
