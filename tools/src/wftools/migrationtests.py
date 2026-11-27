# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tests of the back of the last published version, on the schema of the branch (US-2850).

Usage: ``python -m wftools.migrationtests``, under the services of the tests of the back
(``make migrations-tests``).

WF-DAT-0140-A: the code of the version N runs on the schema the version N+1 migrated. N is the last
published version, the highest tag ``vX.Y.Z`` the checkout reaches (#4089): it moves to the next one
alone, at its publication, and nothing here names it. N+1 is the branch, which is all its
migrations are. The tree of N is extracted from its tag, the migrations of the branch laid over its
own (``backend/src/waterfall/migrations/versions``), and its own tests of its migrations left out
(``backend/tests/test_migration*.py``): they hold the history of N, that the branch has lengthened.
Then the tests of the back of N run, as its Makefile ran them, on databases its fixtures create and
migrate — to the head of the branch.

A test of N that fails says an incompatibility: the branch migrated the schema in a way the code
that still runs during an update does not take. It is not mended here; it is a finding, to settle
before the next version is published (US-2850). The outcome of each test is written
(``wftools.migrationreport``) and judged against the known failures of N
(``wftools.migrationknown``, ``tools/migrations-known.toml``): the tool fails on a new failure, and
on a known one that no longer fails. Without a published version, nothing is tried, and the tool
says it is not executed.
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from wftools import REPOSITORY
from wftools.migrationknown import judged
from wftools.migrationreport import REPORT

TOOL = "wftools.migrationtests"
REQUIREMENT = "WF-DAT-0140-A"
VERSION_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
VERSIONS = Path("backend/src/waterfall/migrations/versions")
"""Where the migrations are, in the tree of a version as in the branch."""
OWN_TESTS = "test_migration*.py"
"""The tests of the migrations of a version, which hold its own history."""
TOOLS = REPOSITORY / "tools" / "src"
"""Where the plugin that writes the outcomes is, put on the path of Python of the back of N."""
PLUGIN = "wftools.migrationreport"
OUTCOMES = "migrations-tests.jsonl"
"""The outcomes of the last run, under ``.waterfall/``: kept, to be read after a failure."""
MOST_PROCESSES = 8
"""As the Makefile of the back: each process of pytest takes a database of Redis of its own."""

Read = Callable[[list[str]], tuple[int, str]]


class MigrationTrialError(Exception):
    """What keeps the version N from being found or extracted."""


@dataclass(frozen=True, slots=True)
class Version:
    """A published version: its tag, and the tag of its images."""

    name: str

    @property
    def tag(self) -> str:
        """The tag of its images, the version without its ``v``."""
        return self.name.removeprefix("v")


def last_published(read: Read, base: str = "HEAD") -> Version | None:
    """Return the highest tag ``vX.Y.Z`` the base reaches, or None when it reaches none."""
    code, listed = read(["git", "tag", "--list", "v*", "--merged", base])
    if code != 0:
        message = f"the tags {base} reaches cannot be listed: {listed.strip()}"
        raise MigrationTrialError(message)
    versions = [
        (tuple(int(part) for part in found.groups()), name)
        for name in listed.split()
        if (found := VERSION_TAG.fullmatch(name))
    ]
    return Version(max(versions)[1]) if versions else None


def extract(archive: bytes, folder: Path) -> Path:
    """Write the tree of a version under ``folder``, and give the folder of its back."""
    with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
        tree.extractall(folder, filter="data")
    back = folder / "backend"
    if not (back / VERSIONS.relative_to("backend")).is_dir():
        message = f"the tree extracted under {folder} holds no {VERSIONS}"
        raise MigrationTrialError(message)
    return back


def lay_migrations(tree: Path, branch: Path) -> list[str]:
    """Replace the migrations of the tree by those of the branch; give the migrations laid."""
    target = tree / VERSIONS
    for each in target.glob("*.py"):
        each.unlink()
    laid = sorted(each.name for each in (branch / VERSIONS).glob("*.py"))
    for name in laid:
        shutil.copyfile(branch / VERSIONS / name, target / name)
    return [name for name in laid if name[:1].isdigit()]


def own_tests(back: Path) -> list[str]:
    """Return the tests of the migrations of the version, relative to its back."""
    return sorted(each.relative_to(back).as_posix() for each in back.glob(f"tests/{OWN_TESTS}"))


def pytest_command(environment: Mapping[str, str], left_out: list[str]) -> list[str]:
    """Return how the tests of the back of N run: on the share of the processors of the slot.

    The tests left out are not collected, but stay where they are: another test of the version may
    import them (``test_keycloak_bootstrap`` imports ``test_migrations``).
    """
    processes = environment.get("WATERFALL_PROCESSORS") or str(os.cpu_count() or 1)
    command = ["uv", "run", "--frozen", "--no-sync", "pytest", "-q", "-p", "no:cacheprovider"]
    command += ["-p", PLUGIN, "--tb=short"]
    command += ["-n", processes, "--maxprocesses", str(MOST_PROCESSES)]
    command += [f"--ignore={name}" for name in left_out]
    if shard := environment.get("SHARD"):
        command.append(f"--shard={shard}")
    return command


def child_environment(environment: Mapping[str, str], report: Path) -> dict[str, str]:
    """Return the environment of the back of N, its tests' outcomes written.

    The tools' own environment of Python is left out; the plugin of the outcomes is reachable, and
    told the file it writes them to.
    """
    child = {name: value for name, value in environment.items() if name != "VIRTUAL_ENV"}
    path = [str(TOOLS), *filter(None, [environment.get("PYTHONPATH")])]
    return {**child, "PYTHONPATH": os.pathsep.join(path), REPORT: str(report)}


def main(arguments: list[str] | None = None, environment: Mapping[str, str] | None = None) -> int:
    """Find N, extract it, lay the migrations of the branch over it, and run its tests."""
    del arguments
    given = dict(os.environ if environment is None else environment)
    try:
        version = last_published(_read)
    except MigrationTrialError as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 1
    if version is None:
        notice = "::notice::" if given.get("GITHUB_ACTIONS") == "true" else ""
        print(f"{notice}{TOOL}: not executed: no published version; {REQUIREMENT} is not held")
        return 0
    scratch = REPOSITORY / ".waterfall"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="migration-tests-", dir=scratch) as folder:
        tree = Path(folder)
        try:
            back = extract(_archive(version.name), tree)
        except (MigrationTrialError, subprocess.CalledProcessError, OSError) as error:
            print(f"{TOOL}: {error}", file=sys.stderr)
            return 1
        laid = lay_migrations(tree, REPOSITORY)
        taken = own_tests(back)
        print(
            f"  the tests of the back of {version.name}, on the {len(laid)} migrations of the "
            f"branch (up to {laid[-1] if laid else '-'}), without {', '.join(taken) or '-'}",
            flush=True,
        )
        report = scratch / OUTCOMES
        report.unlink(missing_ok=True)
        child = child_environment(given, report)
        synced = subprocess.run(["uv", "sync", "--frozen"], cwd=back, env=child, check=False)
        if synced.returncode:
            print(f"{TOOL}: the back of {version.name} does not install", file=sys.stderr)
            return 1
        ran = subprocess.run(pytest_command(given, taken), cwd=back, env=child, check=False)
        return 0 if judged(version.name, "tests", report, ran.returncode) else 1


def _archive(name: str) -> bytes:
    return subprocess.run(
        ["git", "archive", "--format=tar", name],
        cwd=REPOSITORY,
        capture_output=True,
        check=True,
    ).stdout


def _read(command: list[str]) -> tuple[int, str]:
    done = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout + done.stderr if done.returncode else done.stdout


if __name__ == "__main__":
    sys.exit(main())
