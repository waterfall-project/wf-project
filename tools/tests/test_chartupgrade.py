# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The upgrade of the chart under load, its rollback and the second upgrade (US-2850).

The cluster is made, N installed, upgraded, rolled back and upgraded again by ``make
chart-upgrade``, run by hand, not yet in the chain (#5020); these tests hold what the trial decides
by itself — which version is N, what it is not executed for, what each passage must leave — on a
cluster played by a fake.

The tests citing WF-EXP-0030-A or WF-DAT-0140-A exercise the parts of the trial without closing
those criteria: the real trial, wired into the full tier by US-2850/L4 (#5029), will close them.
"""

import io
import json
import tarfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from wftools import chartload, charttrial, chartupgrade
from wftools.chartload import Tally
from wftools.charttrial import Tools, Trial
from wftools.chartupgrade import (
    CHART_FILE,
    Job,
    Upgrade,
    UpgradeError,
    Version,
)
from wftools.images import REGISTRY, Holding
from wftools.production import Answer, Browser, Platform, ProductionError

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Mapping


pytestmark = pytest.mark.story("US-2850")

BASE = "b" * 40
PARENT = "a" * 40
OLDER = "9" * 40
BRANCH = "c" * 40
PLATFORM = Platform("waterfall.localhost", 41443, 0)
OF_N = {"front": f"sha256:{'1' * 64}", "waterfall": f"sha256:{'2' * 64}"}
OF_BRANCH = {"front": f"sha256:{'3' * 64}", "waterfall": f"sha256:{'4' * 64}"}
"""The digests of the images of N and of the branch, as the cluster holds them."""


def git(
    tags: str = "", charts: frozenset[str] = frozenset(), first_parents: tuple[str, ...] = (BASE,)
) -> chartupgrade.Read:
    """Return a git that knows tags, the commits that carry the chart, and the first parents."""

    def read(command: list[str]) -> tuple[int, str]:
        match command:
            case ["git", "tag", "--list", "v*", "--merged", _]:
                return 0, tags
            case ["git", "rev-parse", name]:
                return 0, f"{name.removesuffix('^{commit}')}-commit\n"
            case ["git", "cat-file", "-e", where]:
                commit, _, path = where.partition(":")
                return (0, "") if path == CHART_FILE and commit in charts else (128, "")
            case ["git", "rev-list", "--first-parent", _, _]:
                return 0, "\n".join(first_parents)
            case _:
                raise AssertionError(command)

    return read


def held(published: set[str], unclear: frozenset[str] = frozenset()) -> Callable[[str], Holding]:
    def holding(tag: str) -> Holding:
        if tag in unclear:
            return Holding.UNCLEAR
        return Holding.HELD if tag in published else Holding.LACKING

    return holding


@pytest.mark.requirement("WF-EXP-0030-A")
def test_n_is_the_last_published_version_that_carries_the_chart() -> None:
    read = git(
        "v0.3.0\nv0.10.0\nv0.4.0\nv1.0.0-rc\n",
        frozenset({"v0.4.0-commit", "v0.10.0-commit"}),
    )
    found = chartupgrade.version_n(read, held(set()), BASE)
    assert found == Version("v0.10.0", "v0.10.0-commit", "0.10.0")


@pytest.mark.requirement("WF-EXP-0030-A")
def test_without_a_published_version_that_carries_the_chart_n_is_the_base() -> None:
    read = git("v0.3.0\n", frozenset({BASE, PARENT}), (BASE, PARENT))
    assert chartupgrade.version_n(read, held({BASE, PARENT}), BASE) == Version(
        f"the base {BASE[:12]}", BASE, BASE
    )


@pytest.mark.requirement("WF-EXP-0030-A")
def test_n_is_the_nearest_first_parent_whose_images_are_published() -> None:
    read = git("", frozenset({BASE, PARENT, OLDER}), (BASE, PARENT, OLDER))
    found = chartupgrade.version_n(read, held({PARENT, OLDER}), BASE)
    assert isinstance(found, Version)
    assert found.commit == PARENT
    assert found.tag == PARENT


def test_the_search_stops_at_the_first_parent_without_the_chart() -> None:
    read = git("", frozenset({BASE}), (BASE, PARENT, OLDER))
    with pytest.raises(UpgradeError, match="no image is published for the base"):
        chartupgrade.version_n(read, held({OLDER}), BASE)


def test_a_registry_that_does_not_say_fails_rather_than_passing_over_the_base() -> None:
    read = git("", frozenset({BASE, PARENT}), (BASE, PARENT))
    with pytest.raises(UpgradeError, match="does not say whether the images of"):
        chartupgrade.version_n(read, held({PARENT}, frozenset({BASE})), BASE)


def test_a_base_that_names_no_commit_fails() -> None:
    read = git("", frozenset(), ())
    with pytest.raises(UpgradeError, match="names no commit here"):
        chartupgrade.version_n(read, held(set()), "nowhere")


@pytest.mark.requirement("WF-EXP-0030-A")
@pytest.mark.parametrize(
    ("base", "said"),
    [("", "no base is given"), (BASE, f"the base {BASE} carries no chart")],
    ids=["no base", "a base without the chart"],
)
def test_without_a_base_that_carries_the_chart_the_trial_says_it_is_not_executed(
    base: str, said: str
) -> None:
    found = chartupgrade.version_n(git("v0.3.0\n"), held({BASE}), base)
    assert isinstance(found, str)
    assert said in found


@pytest.mark.requirement("WF-EXP-0030-A")
def test_a_trial_not_executed_says_so_and_what_it_does_not_hold_and_makes_no_cluster(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_tool(_name: str) -> None:
        raise AssertionError

    monkeypatch.setattr(chartupgrade, "_read", git())
    monkeypatch.setattr(charttrial, "tools_of", no_tool)
    assert chartupgrade.main([BASE], {"WATERFALL_IMAGE_TAG": BRANCH}) == 0
    said = capsys.readouterr().out
    assert "wftools.chartupgrade: not executed:" in said
    assert "carries no chart" in said
    assert "WF-EXP-0030-A, WF-DAT-0140-A are not held" in said


def test_images_the_workstation_holds_are_not_asked_of_the_registry() -> None:
    asked: list[list[str]] = []

    def read(command: list[str]) -> tuple[int, str]:
        asked.append(command)
        return (0, "sha256:x") if command[:3] == ["docker", "image", "inspect"] else (1, "")

    assert chartupgrade.images_held(read, BASE) is Holding.HELD
    assert all(command[:3] == ["docker", "image", "inspect"] for command in asked)


@pytest.mark.parametrize(
    ("answer", "holding"),
    [
        ((0, ""), Holding.HELD),
        ((1, "manifest unknown"), Holding.LACKING),
        ((1, "unauthorized"), Holding.UNCLEAR),
    ],
    ids=["published", "lacking", "unclear"],
)
def test_images_the_workstation_lacks_are_asked_of_the_registry(
    answer: tuple[int, str], holding: Holding
) -> None:
    def read(command: list[str]) -> tuple[int, str]:
        return (1, "no such image") if command[:2] == ["docker", "image"] else answer

    assert chartupgrade.images_held(read, BASE) is holding


def tree(*members: tuple[str, bytes | str]) -> bytes:
    """Return a tarball as git archive writes it: files, and links given as text."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as written:
        for name, content in members:
            info = tarfile.TarInfo(name)
            if isinstance(content, str):
                info.type, info.linkname = tarfile.SYMTYPE, content
                written.addfile(info)
            else:
                info.size = len(content)
                written.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def test_the_chart_of_n_is_taken_from_its_commit_with_the_files_it_links_to(tmp_path: Path) -> None:
    archive = tree(
        ("deploy/helm/waterfall/Chart.yaml", b"name: waterfall\n"),
        ("deploy/compose/pg_hba.conf", b"hostssl all\n"),
        ("deploy/helm/waterfall/files/pg_hba.conf", "../../../compose/pg_hba.conf"),
    )
    asked: list[str] = []

    def give(commit: str) -> bytes:
        asked.append(commit)
        return archive

    found = chartupgrade.extract_chart(give, BASE, tmp_path)
    assert asked == [BASE]
    assert found == tmp_path / "deploy" / "helm" / "waterfall"
    assert (found / "files" / "pg_hba.conf").read_text(encoding="utf-8") == "hostssl all\n"


def test_a_commit_without_the_chart_gives_none(tmp_path: Path) -> None:
    with pytest.raises(UpgradeError, match="gives no chart"):
        chartupgrade.extract_chart(lambda _: tree(("README.md", b"")), BASE, tmp_path)


def a_pod(name: str, digests: Mapping[str, str], made: str, **changes: Any) -> dict[str, Any]:
    """Return a pod as kubectl lists it, running the front of ``digests`` beside a third party."""
    item: dict[str, Any] = {
        "metadata": {
            "name": name,
            "uid": changes.get("uid", f"uid-{name}"),
            "creationTimestamp": made,
            "ownerReferences": [{"kind": changes.get("owner", "ReplicaSet")}],
        },
        "status": {
            "phase": changes.get("phase", "Running"),
            "containerStatuses": [{"restartCount": changes.get("restarts", 0)}],
        },
        "spec": {
            "containers": [
                {"image": f"{REGISTRY}/front@{digests['front']}"},
                {"image": "mirror/caddy@sha256:0"},
            ]
        },
    }
    if changes.get("ending"):
        item["metadata"]["deletionTimestamp"] = made
    return item


def front(digests: Mapping[str, str]) -> frozenset[str]:
    return frozenset({f"front@{digests['front']}"})


@pytest.mark.requirement("WF-EXP-0030-A")
def test_the_pods_that_serve_are_those_of_deployments_running_and_not_ending() -> None:
    listing = {
        "items": [
            a_pod("front-1", OF_BRANCH, "2026-11-25T10:02:00Z"),
            a_pod("front-0", OF_N, "2026-11-25T10:00:00Z", ending=True),
            a_pod("migrate-x", OF_BRANCH, "2026-11-25T10:01:00Z", owner="Job"),
            a_pod("front-2", OF_BRANCH, "2026-11-25T10:03:00Z", phase="Pending"),
        ]
    }
    assert chartupgrade.serving(listing) == {"front-1": ("2026-11-25T10:02:00Z", front(OF_BRANCH))}


def test_the_images_of_a_version_are_named_by_their_digests() -> None:
    assert chartupgrade.designations(OF_N) == {
        f"front@sha256:{'1' * 64}",
        f"waterfall@sha256:{'2' * 64}",
    }


@pytest.mark.requirement("WF-EXP-0030-A")
@pytest.mark.parametrize(
    ("pods", "said"),
    [
        ({}, "no pod of the platform's images runs"),
        (
            {"api-1": ("2026-11-25T10:02:00Z", front(OF_N))},
            f"runs front@{OF_N['front']}, not an image of the branch",
        ),
        (
            {"api-1": ("2026-11-25T10:00:59Z", front(OF_BRANCH))},
            "before the migrations ended",
        ),
    ],
    ids=["none", "an instance of N left", "made before the migrations"],
)
def test_an_upgrade_that_leaves_an_instance_or_ran_it_before_its_migrations_is_refused(
    pods: Mapping[str, tuple[str, frozenset[str]]], said: str
) -> None:
    with pytest.raises(UpgradeError, match=said):
        chartupgrade.check_serving(pods, OF_BRANCH, "the branch", "2026-11-25T10:01:00Z")


def test_the_pods_of_a_version_made_after_its_migrations_are_accepted() -> None:
    pods = {"front-1": ("2026-11-25T10:02:00Z", front(OF_BRANCH))}
    chartupgrade.check_serving(pods, OF_BRANCH, "the branch", "2026-11-25T10:01:00Z")
    chartupgrade.check_serving(pods, OF_BRANCH, "the branch")


@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_passage_that_wrote_the_stamp_of_the_migrations_applied_one() -> None:
    writes = chartupgrade.stamped("UPDATE 0055_x\n\n UPDATE 0056_y \n")
    assert writes == ["UPDATE 0055_x", "UPDATE 0056_y"]
    with pytest.raises(UpgradeError, match="the second upgrade wrote the stamp"):
        chartupgrade.check_none_stamped(writes, "the second upgrade")
    chartupgrade.check_none_stamped(chartupgrade.stamped("\n"), "the second upgrade")


@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_passage_that_did_not_run_its_own_job_of_migrations_is_refused() -> None:
    before = chartupgrade.job_of("u1|1|2026-11-25T10:00:00Z\n")
    assert before == Job("u1", succeeded=True, completed="2026-11-25T10:00:00Z")
    anew = Job("u2", succeeded=True, completed="2026-11-25T10:05:00Z")
    chartupgrade.check_migrated_anew(before, anew, "it")
    for after in (before, Job("u2", succeeded=False, completed=""), chartupgrade.job_of("u2||")):
        with pytest.raises(UpgradeError, match="did not run the migrations to their end"):
            chartupgrade.check_migrated_anew(before, after, "it")


def test_the_schema_a_passage_leaves_is_held() -> None:
    chartupgrade.check_schema(" 0055_x\n", "0055_x", "the rollback")
    with pytest.raises(UpgradeError, match=r"after the rollback, the schema is at '0054_w'"):
        chartupgrade.check_schema("0054_w", "0055_x", "the rollback")


def test_both_versions_are_installed_on_two_instances_of_the_api_and_of_the_front() -> None:
    given = {"images": {"digests": dict(OF_BRANCH), "mirror": "m/"}, "api": {"a": 1}}
    values = chartupgrade.values_of(given, OF_N)
    assert values["images"] == {"digests": OF_N, "mirror": "m/"}
    assert values["api"] == {"a": 1, "replicas": 2}
    assert values["front"] == {"replicas": 2}


def unsent(*_: object) -> Answer:
    pytest.fail("no request is sent but by the load")


def no_sender(_trial: Trial) -> None:
    return None


@dataclass
class Cluster:
    """A cluster played by a fake: what Helm made of the release, and what the database says."""

    replay: bool = False
    rollback_migrates: bool = False
    stale: bool = False
    restarts_data: str = ""
    """The passage that restarts PostgreSQL, ``upgrade`` or ``rollback``; none when empty."""
    digests: Mapping[str, str] = field(default_factory=dict[str, str])
    restarted: int = 0
    jobs: int = 0
    upgrades: int = 0
    schema: str = "0054_n"
    stamps: list[str] = field(default_factory=list[str])
    recorded: bool = False
    verbs: list[str] = field(default_factory=list[str])
    given: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    """The digests of the images each installation or upgrade was given."""

    def run(self, command: list[str]) -> int:
        if command[0] != "helm":
            return 0
        verb = command[1]
        self.verbs.append(verb)
        if "--values" in command:
            given = Path(command[command.index("--values") + 1]).read_text(encoding="utf-8")
            self.given.append(json.loads(given).get("images", {}).get("digests", {}))
        if verb == self.restarts_data:
            self.restarted += 1
        if verb == "rollback":
            assert command[2:4] == ["waterfall", "1"]
            self.digests = OF_N
            if self.rollback_migrates:
                self.stamps.append("UPDATE 0054_n")
            return 0
        self.jobs += 1
        if verb == "install":
            self.digests = OF_N
            return 0
        self.upgrades += 1
        if not self.stale:
            self.digests = OF_BRANCH
        if self.upgrades == 1 or self.replay:
            assert self.recorded
            self.stamps.append("UPDATE 0055_n1")
            self.schema = "0055_n1"
        return 0

    def read(self, command: list[str]) -> tuple[int, str]:
        if "psql" in command:
            return 0, self.sql(command[-1].removeprefix("--command="))
        if chartupgrade.MIGRATE in command:
            return 0, f"uid-{self.jobs}|1|2026-11-25T10:{self.jobs:02d}:00Z"
        if chartupgrade.DATA_PODS in command:
            postgres = a_pod(
                "waterfall-postgres-0",
                OF_N,
                "2026-11-25T09:00:00Z",
                owner="StatefulSet",
                restarts=self.restarted,
            )
            return 0, json.dumps({"items": [postgres]})
        if "pods" in command:
            made = f"2026-11-25T10:{self.jobs:02d}:30Z"
            return 0, json.dumps({"items": [a_pod("api-1", self.digests, made)]})
        raise AssertionError(command)

    def sql(self, query: str) -> str:
        if query == chartupgrade.RECORD:
            self.recorded = True
            return ""
        if query == chartupgrade.SCHEMA:
            return f"{self.schema}\n"
        if query == chartupgrade.STAMPS:
            return "\n".join(self.stamps)
        if query == chartupgrade.CLEAR:
            self.stamps.clear()
            return ""
        raise AssertionError(query)


@pytest.fixture
def loaded(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Hold every passage under a load the fake says was there, and sign in without a cluster."""
    passages: list[int] = []

    @contextmanager
    def requests_held(*_: object) -> Generator[Tally]:
        passages.append(1)
        yield Tally(sent=chartload.LEAST)

    def hold(_trial: Trial, _email: str) -> Browser:
        return Browser(unsent)

    monkeypatch.setattr(chartload, "requests_held", requests_held)
    monkeypatch.setattr(Trial, "hold", hold)
    monkeypatch.setattr(Trial, "sender", no_sender)
    return passages


def upgrade_on(cluster: Cluster, folder: Path) -> Upgrade:
    tools = Tools(["kind"], ["kubectl"], ["helm"])
    trial = Trial(tools, cluster.run, cluster.read, folder, PLATFORM)
    return Upgrade(trial, Version("the base", BASE, BASE), folder / "n", OF_N, OF_BRANCH)


@pytest.mark.requirement("WF-EXP-0030-A")
@pytest.mark.requirement("WF-DAT-0140-A")
def test_n_is_upgraded_under_load_rolled_back_on_the_schema_of_n1_and_upgraded_again(
    tmp_path: Path, loaded: list[int], capsys: pytest.CaptureFixture[str]
) -> None:
    cluster = Cluster()
    upgrade_on(cluster, tmp_path).hold({"images": {"digests": OF_BRANCH}})
    assert cluster.verbs == ["install", "upgrade", "rollback", "upgrade"]
    assert len(loaded) == 3
    assert cluster.given == [OF_N, OF_BRANCH, OF_BRANCH]
    said = capsys.readouterr().out
    assert "the migrations ran first, from 0054_n to 0055_n1 (1 applied)" in said
    assert "the rollback replaced and restarted no pod of postgres, redis, storage" in said
    assert "runs again on the schema of the branch, 0055_n1" in said
    assert "none already applied ran again" in said


@pytest.mark.requirement("WF-EXP-0030-A")
@pytest.mark.usefixtures("loaded")
@pytest.mark.parametrize("passage", ["upgrade", "rollback"])
def test_a_passage_that_restarts_a_data_component_fails(tmp_path: Path, passage: str) -> None:
    cluster = Cluster(restarts_data=passage)
    with pytest.raises(ProductionError, match="waterfall-postgres-0 was restarted by the passage"):
        upgrade_on(cluster, tmp_path).hold({})


@pytest.mark.usefixtures("loaded")
def test_without_a_data_component_running_the_trial_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def none(_upgrade: Upgrade) -> dict[str, tuple[str, int]]:
        return {}

    cluster = Cluster()
    monkeypatch.setattr(Upgrade, "data", none)
    with pytest.raises(UpgradeError, match="no pod of postgres, redis, storage runs"):
        upgrade_on(cluster, tmp_path).hold({})


@pytest.mark.requirement("WF-DAT-0140-A")
@pytest.mark.usefixtures("loaded")
def test_a_second_upgrade_that_applies_a_migration_again_fails(tmp_path: Path) -> None:
    with pytest.raises(UpgradeError, match="the second upgrade wrote the stamp"):
        upgrade_on(Cluster(replay=True), tmp_path).hold({})


@pytest.mark.requirement("WF-EXP-0030-A")
@pytest.mark.usefixtures("loaded")
def test_a_rollback_that_touches_the_schema_fails(tmp_path: Path) -> None:
    with pytest.raises(UpgradeError, match="the rollback wrote the stamp"):
        upgrade_on(Cluster(rollback_migrates=True), tmp_path).hold({})


@pytest.mark.requirement("WF-EXP-0030-A")
@pytest.mark.usefixtures("loaded")
def test_an_upgrade_that_leaves_the_instances_of_n_fails(tmp_path: Path) -> None:
    with pytest.raises(UpgradeError, match=f"runs front@{OF_N['front']}, not an image of the bra"):
        upgrade_on(Cluster(stale=True), tmp_path).hold({})


@pytest.mark.requirement("WF-EXP-0030-A")
def test_a_request_that_fails_during_a_passage_fails_the_trial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    @contextmanager
    def requests_held(*_: object) -> Generator[Tally]:
        yield Tally(sent=chartload.LEAST, failed=["the account answered 502"])

    monkeypatch.setattr(chartload, "requests_held", requests_held)
    monkeypatch.setattr(Trial, "sender", no_sender)
    upgrade = upgrade_on(Cluster(), tmp_path)
    browser = Browser(unsent)
    with pytest.raises(ProductionError, match="1 of 50 requests failed"):
        upgrade.under_load(browser, lambda: None, "the upgrade")
