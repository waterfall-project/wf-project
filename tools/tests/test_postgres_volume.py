# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""PostgreSQL 18, and the control of its volume, on the production and the service platforms.

(US-1130.)

The script ``deploy/compose/postgres-volume.sh`` is run as the service ``postgres-volume`` runs it,
by ``sh``, on a temporary directory that stands for the volume: empty, of PostgreSQL 18, of an
image 17 or older — ``PG_VERSION`` at its root, a volume 16 —, and of an image since 18 of another
major — ``19/docker`` beside ``18/docker``. The files of Compose, of the chain and the Makefile are
read for what they say: the image, the mount, the health check, the control the server waits for,
and its log printed when ``make service-up`` fails.
"""

import re
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_worktree_slots import Workstation, docker_asked

from wftools import REPOSITORY

if TYPE_CHECKING:
    from pathlib import Path

COMPOSE = REPOSITORY / "deploy" / "compose"
SCRIPT = COMPOSE / "postgres-volume.sh"
PRODUCTION = COMPOSE / "compose.prod.yaml"
SERVICE = COMPOSE / "compose.service.yaml"
TEST = COMPOSE / "compose.test.yaml"
CHAIN = REPOSITORY / ".github" / "workflows" / "back.yml"
IMAGE = re.compile(r"\bpostgres:[\w.-]+@sha256:[0-9a-f]{64}")
REMEDY = "Drop the data: make service-down WATERFALL_RESET_DATA=yes."


def control(volume: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the control of the volume on a directory, with the remedy, as its service does."""
    return subprocess.run(
        ["sh", str(SCRIPT), *(arguments or (REMEDY,)), str(volume)],
        capture_output=True,
        text=True,
        check=False,
    )


def data(volume: Path, where: str, version: str) -> None:
    """Write the PG_VERSION of a cluster of a version in a directory of the volume."""
    cluster = volume / where
    cluster.mkdir(parents=True, exist_ok=True)
    (cluster / "PG_VERSION").write_text(f"{version}\n")
    (cluster / "base").mkdir()


def services(path: Path) -> dict[str, Any]:
    """Read the services of a Compose file."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))["services"]


def test_an_empty_volume_passes_silently(tmp_path: Path) -> None:
    """US-1130: a new volume, or one the image made 18/docker in and nothing more, passes."""
    empty = control(tmp_path)
    assert (empty.returncode, empty.stdout, empty.stderr) == (0, "", "")
    (tmp_path / "18" / "docker").mkdir(parents=True)
    made = control(tmp_path)
    assert (made.returncode, made.stdout, made.stderr) == (0, "", "")


def test_a_volume_of_postgresql_18_passes_silently(tmp_path: Path) -> None:
    """US-1130: the data of the version the platform runs, in 18/docker, are taken."""
    data(tmp_path, "18/docker", "18")
    done = control(tmp_path)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_a_volume_16_is_refused_naming_the_versions_and_the_remedy(tmp_path: Path) -> None:
    """US-1130: PG_VERSION at the root of the volume, the layout of the images up to 17, refused.

    « la plateforme de production et la plateforme de service refusent de démarrer sur un volume
    PostgreSQL d'une autre majeure ; le refus nomme la version trouvée et celle attendue, et dit
    quoi faire […] ; un test le prouve sur un volume 16 ».
    """
    data(tmp_path, ".", "16")
    done = control(tmp_path)
    assert done.returncode == 1
    assert done.stdout == ""
    assert "PostgreSQL 16," in done.stderr
    assert "runs PostgreSQL 18" in done.stderr
    assert done.stderr.rstrip().endswith(REMEDY)


def test_a_root_and_an_18_docker_together_are_refused(tmp_path: Path) -> None:
    """US-1130: a PG_VERSION at the root is refused though 18/docker/PG_VERSION is there too."""
    data(tmp_path, ".", "16")
    data(tmp_path, "18/docker", "18")
    done = control(tmp_path)
    assert done.returncode == 1
    assert f"PostgreSQL 16, at {tmp_path}/PG_VERSION" in done.stderr
    assert done.stderr.rstrip().endswith(REMEDY)


def test_a_version_empty_or_unreadable_is_refused_all_the_same(tmp_path: Path) -> None:
    """US-1130: an empty PG_VERSION, or a directory, still names the versions and the remedy.

    The refusal is owed whatever the file says: `set -eu` must not end the script on `cat` alone.
    """
    (tmp_path / "PG_VERSION").write_text("")
    empty = control(tmp_path)
    (tmp_path / "PG_VERSION").unlink()
    (tmp_path / "PG_VERSION").mkdir()
    directory = control(tmp_path)
    for done in (empty, directory):
        assert done.returncode == 1
        assert done.stdout == ""
        assert "PostgreSQL unknown (PG_VERSION is empty or unreadable), at " in done.stderr
        assert "runs PostgreSQL 18" in done.stderr
        assert done.stderr.rstrip().endswith(REMEDY)


@pytest.mark.parametrize("major", ["17", "19"])
def test_the_data_of_another_major_beside_those_of_18_are_refused(
    tmp_path: Path, major: str
) -> None:
    """US-1130: a <n>/docker/PG_VERSION whose n is not 18 is refused, though 18/docker is there.

    An image 19 would find 18/docker and make an empty 19/docker beside it: a volume where it did
    so, or that another image filled, says it.
    """
    data(tmp_path, "18/docker", "18")
    data(tmp_path, f"{major}/docker", major)
    done = control(tmp_path)
    assert done.returncode == 1
    assert f"PostgreSQL {major}, at {tmp_path}/{major}/docker/PG_VERSION" in done.stderr
    assert "runs PostgreSQL 18" in done.stderr
    assert REMEDY in done.stderr


def test_the_control_without_its_remedy_is_refused(tmp_path: Path) -> None:
    """US-1130: the remedy comes from Compose; a control called without it says how to call it."""
    done = subprocess.run(
        ["sh", str(SCRIPT)], capture_output=True, text=True, check=False, cwd=tmp_path
    )
    assert done.returncode == 2
    assert "usage: postgres-volume.sh <remedy>" in done.stderr


def test_postgresql_18_pinned_by_its_digest_serves_every_platform_and_the_chain() -> None:
    """US-1130: one image of PostgreSQL 18, by its digest, in production, service, tests, chain.

    « PostgreSQL 18, à l'image épinglée par empreinte, sert la plateforme de production, la
    plateforme de service, les services de test et la chaîne ».
    """
    found = {
        path.name: IMAGE.findall(path.read_text(encoding="utf-8"))
        for path in (PRODUCTION, SERVICE, TEST, CHAIN)
    }
    pinned = {image for images in found.values() for image in images}
    assert all(found.values()), found
    assert len(pinned) == 1, pinned
    assert next(iter(pinned)).startswith("postgres:18-trixie@sha256:")


def test_the_chain_installs_the_client_18_before_the_tests_of_the_back() -> None:
    """US-1130: the job of the back has the pg_dump and pg_restore 18 its tests run.

    The runner brings a client 16 beside its client 18, and 16 refuses a server 18: /usr/bin/pg_dump
    and pg_restore are pointed at the 18 the runner image carries and checked to be of that major,
    before ``make check-back-tests``, in each part of the tests. Nothing is installed (US-1900/L4).
    """
    steps = yaml.safe_load(CHAIN.read_text(encoding="utf-8"))["jobs"]["tests"]["steps"]
    runs = [step.get("run", "") for step in steps]
    install = next(i for i, run in enumerate(runs) if "postgresql-client-18" in run)
    tests = next(i for i, run in enumerate(runs) if run.startswith("make check-back-tests"))
    assert install < tests
    assert "for tool in pg_dump pg_restore; do" in runs[install]
    assert "apt" not in runs[install].replace("(PostgreSQL)", "")
    assert '"/usr/lib/postgresql/18/bin/$tool" "/usr/bin/$tool"' in runs[install]
    assert '"/usr/bin/$tool" --version' in runs[install]
    assert "(PostgreSQL) 18." in runs[install]


@pytest.mark.parametrize(
    ("path", "remedy"),
    [
        (PRODUCTION, "deploy/compose/README.md, « Mettre à jour »"),
        (SERVICE, "make service-down WATERFALL_RESET_DATA=yes"),
    ],
)
def test_the_server_starts_once_the_control_of_its_volume_has_passed(
    path: Path, remedy: str
) -> None:
    """US-1130: postgres waits for postgres-volume, which reads its volume read-only.

    The control runs the image of the server, is given its remedy by Compose, and is done once.
    """
    found = services(path)
    server, volume = found["postgres"], found["postgres-volume"]
    assert server["volumes"] == ["postgres-data:/var/lib/postgresql"]
    assert server["depends_on"] == {
        "postgres-volume": {"condition": "service_completed_successfully"}
    }
    assert volume["image"] == server["image"]
    assert volume["entrypoint"] == ["/bin/sh", "/postgres-volume.sh"]
    assert len(volume["command"]) == 1
    assert remedy in volume["command"][0]
    assert volume["volumes"] == [
        "postgres-data:/var/lib/postgresql:ro",
        "./postgres-volume.sh:/postgres-volume.sh:ro",
    ]
    assert volume["restart"] == "no"


def test_the_health_check_of_postgresql_asks_by_tcp_everywhere() -> None:
    """US-1130: pg_isready --host 127.0.0.1, which the server of the first initialisation misses.

    « leur contrôle de santé ne dit PostgreSQL prêt qu'une fois son initialisation finie » : that
    server listens on the socket alone, then stops before the real one starts.
    """
    for path in (PRODUCTION, SERVICE, TEST):
        test = services(path)["postgres"]["healthcheck"]["test"]
        assert test[0] == "CMD-SHELL", path.name
        assert test[1].startswith("pg_isready --host 127.0.0.1 "), path.name
    chain = CHAIN.read_text(encoding="utf-8")
    assert chain.count("pg_isready") == chain.count("pg_isready --host 127.0.0.1 ") == 1
    assert services(TEST)["postgres"]["tmpfs"] == ["/var/lib/postgresql"]


def test_service_up_prints_the_log_of_the_control_when_the_platform_does_not_start(
    tmp_path: Path,
) -> None:
    """US-1130: `up --detach` shows no log; a start that fails prints the refusal, if any."""
    workstation = Workstation(tmp_path)
    done = workstation.make(workstation.main, "service-up", extra={"FAIL_CODE": "1"})
    assert done.returncode != 0
    asked = docker_asked(workstation.logged())
    assert len(asked) == 2, asked
    assert " up --build --detach --wait postgres " in asked[0]
    assert asked[1].endswith(" logs --no-color --no-log-prefix postgres-volume")
    recipe = (REPOSITORY / "Makefile").read_text(encoding="utf-8")
    assert "|| { rc=$$?; " in recipe.split("\nservice-up:")[1].split("\n\n")[0]
    assert "; exit $$rc; }" in recipe.split("\nservice-up:")[1].split("\n\n")[0]


def test_check_tools_warns_of_a_pg_restore_that_is_not_18() -> None:
    """US-1130: `make check-tools` warns when /usr/bin/pg_restore is not the server's major, 18."""
    recipe = (REPOSITORY / "Makefile").read_text(encoding="utf-8")
    tools = recipe.split("\ncheck-tools:")[1].split("\n\n")[0]
    assert '/usr/bin/pg_restore --version 2>/dev/null | grep -q " 18\\."' in tools
    assert "warning  /usr/bin/pg_restore is not PostgreSQL 18" in tools


def test_the_note_of_the_update_says_the_break_and_the_refusal_sends_to_it() -> None:
    """US-1130: « Mettre à jour » says that the data of a platform 16 are not taken over.

    « la version qui passe à PostgreSQL 18 ne reprend pas les données d'une plateforme 16, qu'on
    retire (`down --volumes`) avant de réinstaller ».
    """
    readme = (COMPOSE / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## Mettre à jour\n")[1].split("\n## ")[0]
    update = " ".join(section.split())
    assert "PostgreSQL 16 à PostgreSQL 18" in update
    assert "ne reprend pas les données d'une plateforme 16" in update
    assert "docker compose -f compose.prod.yaml down --volumes" in update
    assert "`postgres-volume`" in update
