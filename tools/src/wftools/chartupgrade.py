# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Upgrade the chart from the version N to the branch under load, back, and again (US-2850).

Usage: ``python -m wftools.chartupgrade <base>``.

The version N is the last published version that carries the chart, a tag ``vX.Y.Z`` the base
reaches, its images tagged ``X.Y.Z``; as long as there is none, the base itself — the commit a pull
request targets, ``BASE`` of the chain —, or its nearest ancestor, by its first parents, whose three
images are published, tagged by its commit. Its chart is taken from the commit, its images from the
registry, unless the workstation holds them already. Without a base that carries the chart — the
pull request of an epic that brings the chart to ``main`` —, nothing is installed: the trial says
it is not executed, and why, and holds none of its requirements. The version N+1 is the branch: its
chart, and its images tagged ``WATERFALL_IMAGE_TAG``, the commit of the checkout unless it names
another, built here as for ``wftools.charttrial``.

On a cluster of kind made for it, as ``wftools.charttrial`` makes its own, N is installed, two
instances of the API and two of the front, and the first administrator signs in. Then, the session
of that administrator held through each passage by requests none of which may fail
(``wftools.chartload``), whose cookies are the same from the first to the last — no one is signed
out (WF-EXP-0030-A):

- the upgrade to N+1: its migrations first, by the hook of the chart, then the instances one by
  one — every pod of the platform's images is of N+1, and was made after the migrations ended;
- the rollback to N, on the schema of N+1: the pods are of N again, and the schema is the one N+1
  left, no migration undone nor run;
- the upgrade to N+1 again: its hook of migrations runs anew, and no migration already applied runs
  a second time (WF-DAT-0140-A) — what is seen, not supposed: a trigger of the trial on the table in
  which Alembic stamps each migration it applies records every write to it, and there is none.

The cluster is deleted at the end, whatever the outcome; what the pods said is printed first when
the trial fails.
"""

import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wftools import REPOSITORY, chart, chartload, charttrial, kubetools
from wftools.images import IMAGES, REGISTRY, Holding, reference, registry_answers
from wftools.production import Browser, Platform, ProductionError

TOOL = "wftools.chartupgrade"
REQUIREMENTS = ("WF-EXP-0030-A", "WF-DAT-0140-A")
"""What the trial holds, and what it holds nothing of when it is not executed."""
CLUSTER = "waterfall-upgrade"
CHART_FILE = "deploy/helm/waterfall/Chart.yaml"
EXTRACTED = ("deploy/helm", "deploy/compose")
"""What the chart of a commit is read from: its folder, and the files of the Compose it links to."""
VERSION_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
ANCESTORS = 20
"""How many first parents of the base are searched for published images: images.yml publishes those
of each merge, and the merge queue may start before the last one is published."""
INSTANCES = 2
"""The instances of the API and of the front: one serves while the other is replaced."""
INSTALLED = 1
"""The revision of the release the installation of N is, which the rollback goes back to."""

RECORD = (
    "CREATE SCHEMA IF NOT EXISTS upgrade_trial; "
    "CREATE TABLE IF NOT EXISTS upgrade_trial.stamp "
    "(seq bigserial PRIMARY KEY, operation text NOT NULL, version_num text); "
    "CREATE OR REPLACE FUNCTION upgrade_trial.record() RETURNS trigger "
    "LANGUAGE plpgsql SECURITY DEFINER AS $$BEGIN "
    "INSERT INTO upgrade_trial.stamp (operation, version_num) VALUES "
    "(TG_OP, CASE TG_OP WHEN 'DELETE' THEN OLD.version_num ELSE NEW.version_num END); "
    "RETURN NULL; END$$; "
    "CREATE OR REPLACE TRIGGER upgrade_trial_stamp "
    "AFTER INSERT OR UPDATE OR DELETE ON public.alembic_version "
    "FOR EACH ROW EXECUTE FUNCTION upgrade_trial.record()"
)
"""What records each write to the stamp of Alembic: a migration applied is one, and only that is.
The function runs as the administrator who made it, so that the owner of the tables, who migrates,
needs no right on the schema of the trial."""
STAMPS = (
    "SELECT operation || ' ' || coalesce(version_num, '') FROM upgrade_trial.stamp ORDER BY seq"
)
CLEAR = "TRUNCATE upgrade_trial.stamp"
SCHEMA = "SELECT version_num FROM public.alembic_version"
MIGRATE = f"job/{chart.RELEASE}-migrate"
JOB = "jsonpath={.metadata.uid}|{.status.succeeded}|{.status.completionTime}"

Read = Callable[[list[str]], tuple[int, str]]
Archive = Callable[[str], bytes]


class UpgradeError(Exception):
    """What the upgrade, the rollback or the second upgrade does not do as it must."""


@dataclass(frozen=True, slots=True)
class Version:
    """The version N: what it is called, its commit, and the tag of its images."""

    name: str
    commit: str
    tag: str


def _git(read: Read, *arguments: str) -> tuple[int, str]:
    return read(["git", *arguments])


def carries_chart(read: Read, commit: str) -> bool:
    """Tell whether the tree of a commit holds the chart."""
    code, _ = _git(read, "cat-file", "-e", f"{commit}:{CHART_FILE}")
    return code == 0


def published_version(read: Read, base: str) -> Version | None:
    """Return the last published version the base reaches whose tree holds the chart, or None."""
    code, listed = _git(read, "tag", "--list", "v*", "--merged", base)
    if code != 0:
        message = f"the tags the base {base} reaches cannot be listed"
        raise UpgradeError(message)
    versions = sorted(
        (
            (tuple(int(part) for part in found.groups()), name)
            for name in listed.split()
            if (found := VERSION_TAG.fullmatch(name))
        ),
        reverse=True,
    )
    for _, name in versions:
        code, commit = _git(read, "rev-parse", f"{name}^{{commit}}")
        if code == 0 and carries_chart(read, commit.strip()):
            return Version(name, commit.strip(), name.removeprefix("v"))
    return None


def images_held(read: Read, tag: str) -> Holding:
    """Tell whether the three images of a tag are here or published.

    The workstation first, which holds the images it built; then the registry, which says which it
    lacks. A registry that says neither — it refuses the credentials, it does not answer — is
    unclear, never taken for an absence.
    """
    if all(
        read(["docker", "image", "inspect", "--format", "{{.Id}}", reference(image, tag)])[0] == 0
        for image in IMAGES
    ):
        return Holding.HELD
    answers = set(registry_answers(tag, read).values())
    if Holding.UNCLEAR in answers:
        return Holding.UNCLEAR
    return Holding.HELD if answers == {Holding.HELD} else Holding.LACKING


def base_version(read: Read, held: Callable[[str], Holding], base: str) -> Version | None:
    """Return the base, or its nearest first parent whose images are published; None without chart.

    The search stops at the first commit that has no chart: none before it has one.
    """
    code, listed = _git(read, "rev-list", "--first-parent", f"--max-count={ANCESTORS}", base)
    if code != 0 or not listed.split():
        message = f"the base {base!r} names no commit here"
        raise UpgradeError(message)
    commits = listed.split()
    if not carries_chart(read, commits[0]):
        return None
    for commit in commits:
        if not carries_chart(read, commit):
            break
        holding = held(commit)
        if holding is Holding.UNCLEAR:
            message = f"the registry does not say whether the images of {commit} are published"
            raise UpgradeError(message)
        if holding is Holding.HELD:
            return Version(f"the base {commit[:12]}", commit, commit)
    message = (
        f"no image is published for the base {base} nor for any of its {ANCESTORS - 1} "
        "first parents that carry the chart"
    )
    raise UpgradeError(message)


def version_n(read: Read, held: Callable[[str], Holding], base: str) -> Version | str:
    """Return the version N to upgrade from, or why the trial is not executed."""
    if not base:
        return "no base is given: the trial upgrades from the base of a pull request"
    published = published_version(read, base)
    if published is not None:
        return published
    found = base_version(read, held, base)
    if found is None:
        return f"the base {base} carries no chart, and no published version does"
    return found


def extract_chart(archive: Archive, commit: str, folder: Path) -> Path:
    """Write the chart of a commit, and the files of the Compose it links to, under ``folder``."""
    with tarfile.open(fileobj=io.BytesIO(archive(commit))) as tree:
        tree.extractall(folder, filter="data")
    found = folder / "deploy" / "helm" / "waterfall"
    if not (found / "Chart.yaml").is_file():
        message = f"the commit {commit} gives no chart"
        raise UpgradeError(message)
    return found


def serving(listing: Mapping[str, Any]) -> dict[str, tuple[str, frozenset[str]]]:
    """Return the pods that serve the images of the platform: when each was made, and their tags.

    Those of a Deployment alone, which runs and is not ending: a Job comes and goes, and a pod being
    removed after its replacement is ready is no longer served.
    """
    found: dict[str, tuple[str, frozenset[str]]] = {}
    for item in listing["items"]:
        metadata = item["metadata"]
        owners = {owner["kind"] for owner in metadata.get("ownerReferences", [])}
        ending = metadata.get("deletionTimestamp") is not None
        if "ReplicaSet" not in owners or ending or item["status"].get("phase") != "Running":
            continue
        tags = frozenset(
            image.rpartition(":")[2]
            for container in item["spec"]["containers"]
            if (image := container["image"]).startswith(f"{REGISTRY}/")
        )
        if tags:
            found[metadata["name"]] = (metadata["creationTimestamp"], tags)
    return found


def check_serving(
    pods: Mapping[str, tuple[str, frozenset[str]]], tag: str, migrated: str | None = None
) -> None:
    """Hold that every pod of the platform runs the images of ``tag``, made after ``migrated``.

    Times are those of kubectl, in UTC, in ISO form, which compare as text.
    """
    if not pods:
        message = "no pod of the platform's images runs"
        raise UpgradeError(message)
    for name, (made, tags) in sorted(pods.items()):
        if tags != frozenset({tag}):
            message = f"the pod {name} runs the images {', '.join(sorted(tags))}, not {tag}"
            raise UpgradeError(message)
        if migrated is not None and made < migrated:
            message = f"the pod {name} was made at {made}, before the migrations ended, {migrated}"
            raise UpgradeError(message)


def stamped(lines: str) -> list[str]:
    """Return the writes recorded to the stamp of Alembic, one ``OPERATION version`` a line."""
    return [line.strip() for line in lines.splitlines() if line.strip()]


def check_none_stamped(writes: list[str], passage: str) -> None:
    """Hold that no migration was applied during a passage: nothing wrote the stamp of Alembic."""
    if writes:
        message = f"{passage} wrote the stamp of the migrations: {'; '.join(writes)}"
        raise UpgradeError(message)


def check_schema(found: str, expected: str, passage: str) -> None:
    """Hold that the schema is at the revision a passage must leave it at."""
    if found.strip() != expected:
        message = f"after {passage}, the schema is at {found.strip()!r}, not {expected!r}"
        raise UpgradeError(message)


@dataclass(frozen=True, slots=True)
class Job:
    """The Job of the migrations of the last passage that ran it: which it is, and how it ended."""

    uid: str
    succeeded: bool
    completed: str


def job_of(said: str) -> Job:
    """Read the Job of the migrations as ``JOB`` writes it."""
    uid, _, rest = said.strip().partition("|")
    succeeded, _, completed = rest.partition("|")
    return Job(uid, succeeded == "1", completed)


def check_migrated_anew(before: Job, after: Job, passage: str) -> None:
    """Hold that a passage ran its own Job of the migrations to its end."""
    if after.uid == before.uid or not after.succeeded or not after.completed:
        message = f"{passage} did not run the migrations to their end, by a Job of its own"
        raise UpgradeError(message)


@dataclass(frozen=True, slots=True)
class Upgrade:
    """The cluster of the trial, and what it upgrades: the chart of N and that of N+1."""

    trial: charttrial.Trial
    version: Version
    chart_n: Path
    tag: str

    def output(self, command: list[str], what: str) -> str:
        """Run a command that must succeed and return what it wrote; fail naming what it was for."""
        code, output = self.trial.read(command)
        if code != 0:
            message = f"{what} failed ({code})"
            raise UpgradeError(message)
        return output

    def helm(self, arguments: list[str], values: Mapping[str, Any] | None, what: str) -> None:
        """Run Helm on the release of the platform, with the values given, and wait for it.

        Helm waits for what it deploys, but at the installation: its migrations are a hook after
        it, which the services wait for, and which Helm would hold until they are ready.
        """
        given: list[str] = []
        if values is not None:
            path = self.trial.folder / "values.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            given = ["--values", str(path)]
        wait = [] if arguments[0] == "install" else ["--wait"]
        command = [
            *self.trial.tools.helm,
            *arguments,
            "--namespace",
            charttrial.NAMESPACE,
            *given,
            *wait,
            "--timeout",
            charttrial.INSTALLATION,
        ]
        if code := self.trial.run(command):
            message = f"{what} failed ({code})"
            raise UpgradeError(message)
        self.trial.rolled_out()

    def sql(self, query: str, what: str) -> str:
        """Run a query on the database of the platform, as the administrator of the server."""
        psql = [
            *self.trial.kubectl,
            "exec",
            f"statefulset/{chart.RELEASE}-postgres",
            "--",
            "psql",
            "--username=postgres",
            "--dbname=waterfall",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--set=ON_ERROR_STOP=1",
            f"--command={query}",
        ]
        return self.output(psql, what).strip()

    def job(self) -> Job:
        """Return the Job of the migrations the last passage that ran them left."""
        said = self.output(
            [*self.trial.kubectl, "get", MIGRATE, "--output", JOB], "read the Job of the migrations"
        )
        return job_of(said)

    def pods(self) -> dict[str, tuple[str, frozenset[str]]]:
        """Return the pods that serve the platform's images."""
        listing = self.output(
            [*self.trial.kubectl, "get", "pods", "--selector", charttrial.INSTANCE, "-o", "json"],
            "list the pods of the platform",
        )
        return serving(json.loads(listing))

    def stamps(self) -> list[str]:
        """Return the writes to the stamp of Alembic since the last read, and clear them."""
        writes = stamped(self.sql(STAMPS, "read the writes to the stamp of the migrations"))
        self.sql(CLEAR, "clear the writes to the stamp of the migrations")
        return writes

    def under_load(self, browser: Browser, passage: Callable[[], None], what: str) -> None:
        """Run a passage under requests of the signed-in administrator, none of which may fail."""
        trial = self.trial
        with chartload.requests_held(trial.sender(), browser, trial.platform, ADMIN) as held:
            passage()
        chartload.check_uninterrupted(held)
        print(f"  {held.sent} requests were held through {what}, none failed", flush=True)

    def hold(self, values: Mapping[str, Any]) -> None:
        """Install N, upgrade to N+1, roll back to N, upgrade again, holding what each must do."""
        n_values = values_of(values, self.version.tag)
        self.helm(["install", chart.RELEASE, str(self.chart_n)], n_values, "install the version N")
        print(f"  {self.version.name} is installed, its hooks done", flush=True)
        browser = self.trial.hold(ADMIN)
        check_serving(self.pods(), self.version.tag)
        self.sql(RECORD, "record the writes to the stamp of the migrations")
        installed = self.job()
        before = self.sql(SCHEMA, "read the schema of N")

        def upgrade() -> None:
            self.helm(
                ["upgrade", chart.RELEASE, str(chart.CHART)],
                values_of(values, self.tag),
                "upgrade to the branch",
            )

        self.under_load(browser, upgrade, "the upgrade to the branch")
        upgraded = self.job()
        check_migrated_anew(installed, upgraded, "the upgrade")
        check_serving(self.pods(), self.tag, upgraded.completed)
        applied = self.stamps()
        head = self.sql(SCHEMA, "read the schema of N+1")
        print(
            f"  the migrations ran first, from {before} to {head} "
            f"({len(applied)} applied), then every instance was replaced by one of the branch",
            flush=True,
        )

        def rollback() -> None:
            self.helm(["rollback", chart.RELEASE, str(INSTALLED)], None, "roll back to N")

        self.under_load(browser, rollback, f"the rollback to {self.version.name}")
        check_serving(self.pods(), self.version.tag)
        check_none_stamped(self.stamps(), "the rollback")
        check_schema(self.sql(SCHEMA, "read the schema"), head, "the rollback")
        print(f"  {self.version.name} runs again on the schema of the branch, {head}", flush=True)
        self.under_load(browser, upgrade, "the second upgrade to the branch")
        again = self.job()
        check_migrated_anew(upgraded, again, "the second upgrade")
        check_serving(self.pods(), self.tag, again.completed)
        check_none_stamped(self.stamps(), "the second upgrade")
        check_schema(self.sql(SCHEMA, "read the schema"), head, "the second upgrade")
        print(
            "  the second upgrade ran its migrations anew, and none already applied ran again",
            flush=True,
        )


ADMIN = charttrial.ADMIN


def values_of(values: Mapping[str, Any], tag: str) -> dict[str, Any]:
    """Return the values of the trial for the images of a tag, on two instances of API and front."""
    return chart.merged(
        values,
        {
            "images": {"tag": tag},
            "api": {"replicas": INSTANCES},
            "front": {"replicas": INSTANCES},
        },
    )


def pull(run: Callable[[list[str]], int], tag: str) -> None:
    """Pull the images of a tag the workstation does not hold."""
    for image in IMAGES:
        tagged = reference(image, tag)
        if run(["docker", "image", "inspect", "--format", "{{.Id}}", tagged]) == 0:
            continue
        if code := run(["docker", "pull", "--quiet", tagged]):
            message = f"pull {tagged} failed ({code})"
            raise UpgradeError(message)


def main(arguments: list[str] | None = None, environment: Mapping[str, str] | None = None) -> int:
    """Find N, then install it on a cluster, upgrade, roll back and upgrade again; delete it."""
    given = dict(os.environ if environment is None else environment)
    words = sys.argv[1:] if arguments is None else arguments
    base = words[0] if words else ""
    try:
        found = version_n(_read, lambda tag: images_held(_read, tag), base)
        tag = given.get("WATERFALL_IMAGE_TAG") or _head()
    except (UpgradeError, OSError, subprocess.CalledProcessError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 1
    if isinstance(found, str) or found.commit == tag:
        why = found if isinstance(found, str) else f"{found.name} is the branch itself"
        print(f"{TOOL}: not executed: {why}; {', '.join(REQUIREMENTS)} are not held", flush=True)
        return 0
    name = given.get("WATERFALL_CHART_CLUSTER") or CLUSTER
    platform = Platform(charttrial.DOMAIN, charttrial.free_port(), 0)
    print(f"  from {found.name} to the images {tag}, on the cluster {name}", flush=True)
    with tempfile.TemporaryDirectory(prefix="waterfall-chart-upgrade-") as folder:
        try:
            tools = charttrial.tools_of(Path(folder) / "kubeconfig")
            trial = charttrial.Trial(tools, _run, _read, Path(folder), platform)
        except (kubetools.ToolError, OSError) as error:
            print(f"{TOOL}: {error}", file=sys.stderr)
            return 1
        failed = True
        try:
            chart_n = extract_chart(_archive, found.commit, Path(folder) / "version-n")
            pull(_run, found.tag)
            charttrial.make_authority(_read, Path(folder), charttrial.DOMAIN)
            trial.create(name, charttrial.docker_config_of(given))
            trial.load(name, found.tag)
            trial.load(name, tag)
            address = trial.ingress()
            values = charttrial.chart_values(
                tag, platform, address, given, charttrial.drawn_secrets()
            )
            trial.prepare()
            Upgrade(trial, found, chart_n, tag).hold(values)
            failed = False
        except (
            UpgradeError,
            charttrial.TrialError,
            ProductionError,
            OSError,
            subprocess.CalledProcessError,
        ) as error:
            print(f"{TOOL}: {error}", file=sys.stderr)
            return 1
        finally:
            if failed:
                trial.report()
            _run([*trial.tools.kind, "delete", "cluster", "--name", name])
    return 0


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, capture_output=True, text=True, check=True
    ).stdout.strip()


def _archive(commit: str) -> bytes:
    return subprocess.run(
        ["git", "archive", "--format=tar", commit, *EXTRACTED],
        cwd=REPOSITORY,
        capture_output=True,
        check=True,
    ).stdout


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPOSITORY, check=False).returncode


def _read(command: list[str]) -> tuple[int, str]:
    done = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout + done.stderr if done.returncode else done.stdout


if __name__ == "__main__":
    sys.exit(main())
