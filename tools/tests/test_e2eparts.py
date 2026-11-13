# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spread of the end-to-end paths over the parts of the chain, by measured duration."""

import io
import json
import os
import re
import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml

from wftools import REPOSITORY, e2eparts

if TYPE_CHECKING:
    from pathlib import Path

SEPARATOR = e2eparts.SEPARATOR
LISTING = """\
Listing tests:
  [chromium] \u203a admin.spec.ts:41:1 \u203a reaches a screen
  [chromium] \u203a grid.spec.ts:10:1 \u203a edits a cell
  [chromium] \u203a grid.spec.ts:30:1 \u203a pastes a column
  [chromium] \u203a map.spec.ts:5:1 \u203a zooms
  [chromium] \u203a wide.spec.ts:8:1 \u203a first \u203a one
  [chromium] \u203a wide.spec.ts:8:1 \u203a first \u203a two
  [chromium] \u203a wide.spec.ts:8:1 \u203a second
Total: 7 tests in 4 files
"""
LOG = """\
T \x1b[32m✓\x1b[39m    1 [chromium] \u203a e2e/admin.spec.ts:41:1 \u203a reaches a screen (8.3s)
T ✓    2 [chromium] \u203a e2e/grid.spec.ts:10:1 \u203a edits a cell (350ms)
T ✓    3 [chromium] \u203a e2e/grid.spec.ts:30:1 \u203a pastes a column (1.5s)
T ✘    4 [chromium] \u203a e2e/map.spec.ts:5:1 \u203a zooms (1.2m)
T -    5 [chromium] \u203a e2e/map.spec.ts:9:1 \u203a skipped one
T ✓    6 [chromium] \u203a e2e/wide.spec.ts:8:1 \u203a first \u203a one (2.0s)
T ✓    7 [chromium] \u203a e2e/wide.spec.ts:8:1 \u203a first \u203a two (3.0s)
T 87 passed (2.8m)
"""


def parallel(file: str) -> bool:
    return file == "wide.spec.ts"


def played(plans: list[list[str]], listing: str = LISTING) -> list[tuple[str, str]]:
    """Return the (file, title) pairs a test list plays: a file line plays all of its tests."""
    pairs: list[tuple[str, str]] = []
    for line in plans:
        for entry in line:
            file, _, title = entry.partition(SEPARATOR)
            pairs.extend(
                (test.file, test.title)
                for test in e2eparts.listed(listing)
                if test.file == file and (not title or test.title == title)
            )
    return pairs


def test_a_listing_gives_its_tests_and_a_log_their_seconds() -> None:
    assert e2eparts.listed(LISTING)[:2] == [
        ("chromium", "admin.spec.ts", "reaches a screen", 0.0),
        ("chromium", "grid.spec.ts", "edits a cell", 0.0),
    ]
    seconds = {test.title: test.seconds for test in e2eparts.listed(LOG, timed=True)}
    assert seconds["reaches a screen"] == pytest.approx(8.3)
    assert seconds["edits a cell"] == pytest.approx(0.35)
    assert seconds["zooms"] == pytest.approx(72.0)
    assert "skipped one" not in seconds


def test_the_seconds_of_a_file_are_summed_and_a_parallel_file_is_kept_test_by_test() -> None:
    measured = e2eparts.measure(LOG, parallel)
    assert measured == {
        "admin.spec.ts": 8.3,
        "grid.spec.ts": 1.9,
        "map.spec.ts": 72.0,
        f"wide.spec.ts{SEPARATOR}first{SEPARATOR}one": 2.0,
        f"wide.spec.ts{SEPARATOR}first{SEPARATOR}two": 3.0,
    }


def test_the_heavy_file_is_alone_in_its_part() -> None:
    durations = {"admin.spec.ts": 8.3, "grid.spec.ts": 1.9, "map.spec.ts": 72.0}
    plans = [e2eparts.plan(f"{i}/2", LISTING, durations, parallel) for i in (1, 2)]
    assert ["map.spec.ts"] in plans


def test_every_test_plays_once_whatever_the_durations_and_the_count() -> None:
    known = e2eparts.measure(LOG, parallel)
    for durations in ({}, known, {"gone.spec.ts": 99.0}):
        for count in (1, 2, 3, 5, 6):
            plans = [
                e2eparts.plan(f"{i}/{count}", LISTING, durations, parallel)
                for i in range(1, count + 1)
            ]
            everything = sorted((test.file, test.title) for test in e2eparts.listed(LISTING))
            assert sorted(played(plans)) == everything


def test_a_file_the_durations_do_not_know_plays_for_the_mean_of_the_known_ones() -> None:
    durations = {"admin.spec.ts": 10.0, "grid.spec.ts": 30.0}
    first, second = (e2eparts.plan(f"{i}/2", LISTING, durations, parallel) for i in (1, 2))
    assert "map.spec.ts" in first + second
    # the unknown file weighs 20 s: it goes with admin.spec.ts (10 s), not grid.spec.ts (30 s)
    with_map = next(part for part in (first, second) if "map.spec.ts" in part)
    assert "grid.spec.ts" not in with_map


def test_without_any_duration_the_units_are_still_spread() -> None:
    plans = [e2eparts.plan(f"{i}/2", LISTING, {}, parallel) for i in (1, 2)]
    assert all(plans)


@pytest.mark.parametrize("shard", ["", "1", "0/5", "6/5", "a/b", "1/5/5"])
def test_a_part_is_i_over_n(shard: str) -> None:
    with pytest.raises(ValueError, match="i/N"):
        e2eparts.parse_shard(shard)


def test_a_listing_without_a_test_is_refused() -> None:
    for listing in ("", "Listing tests:\nTotal: 0 tests in 0 files\n", "Error: no format\n"):
        with pytest.raises(ValueError, match="no test recognised"):
            e2eparts.plan("1/2", listing, {}, parallel)


def test_a_listing_with_a_line_lost_or_without_its_total_is_refused() -> None:
    lost = LISTING.replace("admin.spec.ts:41:1", "admin.spec:41")
    with pytest.raises(ValueError, match="6 tests recognised"):
        e2eparts.plan("1/2", lost, {}, parallel)
    with pytest.raises(ValueError, match="no Total line"):
        e2eparts.plan("1/2", LISTING.replace("Total: 7", "Sum: 7"), {}, parallel)
    # #3026: a Total said twice is not one, and a Total in colours is still read
    with pytest.raises(ValueError, match=r"7\+7 counted"):
        e2eparts.plan("1/2", LISTING + "Total: 7 tests in 4 files\n", {}, parallel)
    coloured = LISTING.replace("Total: 7", "\x1b[1mTotal: 7").replace("files\n", "files\x1b[22m\n")
    whole = e2eparts.plan("1/1", LISTING, {}, parallel)
    assert e2eparts.plan("1/1", coloured, {}, parallel) == whole


def test_a_listing_of_one_test_is_read_by_its_total_in_the_singular() -> None:
    # #3026: Playwright says « 1 test in 1 file »
    listing = (
        "Listing tests:\n  [chromium] \u203a a.spec.ts:1:1 \u203a alone\nTotal: 1 test in 1 file\n"
    )
    assert e2eparts.plan("1/1", listing, {}, parallel) == ["a.spec.ts"]


def test_a_part_that_would_be_empty_is_refused() -> None:
    with pytest.raises(ValueError, match="empty"):
        e2eparts.plan("1/9", LISTING, {}, parallel)


def test_a_title_ending_like_a_duration_is_kept_whole_in_a_listing() -> None:
    line = "[chromium] \u203a a.spec.ts:1:1 \u203a waits (12s)"
    assert e2eparts.listed(line)[0].title == "waits (12s)"
    (timed,) = e2eparts.listed(f"T ✓ 1 {line} (3.0s)", timed=True)
    assert (timed.title, timed.seconds) == ("waits (12s)", 3.0)


def test_a_refresh_that_loses_known_units_is_refused_unless_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "durations.json"
    e2eparts.write({"gone.spec.ts": 4.0, "admin.spec.ts": 1.0}, target)
    monkeypatch.setattr(e2eparts, "DURATIONS", target)
    monkeypatch.setattr(e2eparts, "SERVICE_DURATIONS", tmp_path / "service.json")
    monkeypatch.setattr(e2eparts, "is_parallel", parallel)
    log = tmp_path / "log"
    log.write_text(LOG, encoding="utf-8")
    assert e2eparts.main(["refresh", str(log)]) == 1
    assert e2eparts.read(target) == {"gone.spec.ts": 4.0, "admin.spec.ts": 1.0}
    assert e2eparts.main(["refresh", "--drop", str(log)]) == 0
    assert "gone.spec.ts" not in e2eparts.read(target)
    assert not (tmp_path / "service.json").exists()


def test_the_durations_are_written_one_unit_a_line_and_read_back(tmp_path: Path) -> None:
    target = tmp_path / "durations.json"
    e2eparts.write({"a.spec.ts": 1.5, f"b.spec.ts{SEPARATOR}t": 2.0}, target)
    assert target.read_text(encoding="utf-8").count("\n") == 4
    assert e2eparts.read(target) == {"a.spec.ts": 1.5, f"b.spec.ts{SEPARATOR}t": 2.0}


def test_the_files_played_test_by_test_are_the_ones_that_say_so(tmp_path: Path) -> None:
    (tmp_path / "e2e").mkdir()
    (tmp_path / "e2e" / "a.spec.ts").write_text('test.describe.configure({ mode: "parallel" });')
    (tmp_path / "e2e" / "b.spec.ts").write_text('test.describe.configure({ mode: "serial" });')
    (tmp_path / "e2e" / "d.spec.ts").write_text("test.describe.configure({ mode: 'parallel' });")
    assert e2eparts.is_parallel("a.spec.ts", tmp_path)
    assert not e2eparts.is_parallel("b.spec.ts", tmp_path)
    assert e2eparts.is_parallel("d.spec.ts", tmp_path)
    (tmp_path / "e2e" / "c.spec.ts").write_text(
        '// test.describe.configure({ mode: "parallel" });\n'
        'test.describe("x", () => {\n  test.describe.configure({ mode: "parallel" });\n});\n'
    )
    assert not e2eparts.is_parallel("c.spec.ts", tmp_path)


def test_the_versioned_durations_are_those_of_the_paths_of_the_repository() -> None:
    durations = json.loads(e2eparts.DURATIONS.read_text(encoding="utf-8"))
    assert durations
    assert all(seconds >= 0 for seconds in durations.values())
    assert not [unit for unit in durations if unit.startswith(("e2e/", "service/"))]


def test_units_measured_at_zero_still_fill_every_part() -> None:
    names = ["a", "b", "c"]
    for durations in ({"a": 0.0, "b": 0.0, "c": 0.0}, {"a": 5.0, "b": 0.0, "c": 0.0}):
        parts = e2eparts.spread(names, durations, 3)
        assert all(parts)
        assert sorted(unit for part in parts for unit in part) == names
    zero: dict[str, float] = dict.fromkeys(["admin.spec.ts", "grid.spec.ts", "map.spec.ts"], 0.0)
    assert all(e2eparts.plan(f"{i}/3", LISTING, zero, parallel) for i in (1, 2, 3))


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "-1.5"])
def test_a_duration_that_is_not_one_is_refused(tmp_path: Path, value: str) -> None:
    # #3026: json reads NaN, which the floor of the weights let through and left a part empty
    target = tmp_path / "durations.json"
    target.write_text(f'{{"a.spec.ts": {value}}}', encoding="utf-8")
    with pytest.raises(ValueError, match=r"a\.spec\.ts are not a duration"):
        e2eparts.read(target)


def test_the_files_of_the_repository_played_test_by_test_are_all_recognised() -> None:
    # #3026: a configuration written otherwise — indented, between apostrophes — would leave a file
    # of independent tests one unit; any file that names the parallel mode must be recognised.
    named = re.compile(r"""mode:\s*["']parallel["']""")
    files = sorted((e2eparts.FRONT / "e2e").rglob("*.spec.ts"))
    assert files
    mentioning: set[str] = set()
    recognised: set[str] = set()
    for path in files:
        file = path.relative_to(e2eparts.FRONT / "e2e").as_posix()
        if named.search(path.read_text(encoding="utf-8")):
            mentioning.add(file)
        if e2eparts.is_parallel(file):
            recognised.add(file)
    assert recognised
    assert mentioning == recognised


# The paths against the service, in N parts (US-1910/L3)

SERVICE_LISTING = """\
Listing tests:
  [installation] \u203a service/installation.setup.ts:42:1 \u203a sets its password
  [service] \u203a service/account.spec.ts:10:1 \u203a reads its account
  [service] \u203a service/account.spec.ts:20:1 \u203a changes its name
  [service] \u203a service/roles.spec.ts:5:1 \u203a gives a role
  [shared] \u203a grid.spec.ts:10:1 \u203a edits a cell
  [shared] \u203a wide.spec.ts:8:1 \u203a first \u203a one
  [shared] \u203a wide.spec.ts:8:1 \u203a second
  [shared-serial] \u203a grid.spec.ts:40:1 \u203a changes the units @serial
  [realm] \u203a service/account.spec.ts:30:1 \u203a idles out @realm-wide
  [restoration] \u203a service/backups.spec.ts:9:1 \u203a restores @platform-wide
  [contract] \u203a service/contract.teardown.ts:11:1 \u203a refused nothing
Total: 11 tests in 7 files
"""
SERVICE_LOG = """\
T ✓    1 [installation] \u203a e2e/service/installation.setup.ts:42:1 \u203a sets it (5.0s)
T ✓    2 [service] \u203a e2e/service/account.spec.ts:10:1 \u203a reads its account (2.0s)
T ✓    3 [service] \u203a e2e/service/account.spec.ts:20:1 \u203a changes its name (3.0s)
T ✓    4 [shared] \u203a e2e/grid.spec.ts:10:1 \u203a edits a cell (1.2m)
T ✓    5 [shared] \u203a e2e/wide.spec.ts:8:1 \u203a first \u203a one (4.0s)
T ✓    6 [realm] \u203a e2e/service/account.spec.ts:30:1 \u203a idles out @realm-wide (9.0s)
"""
FOUR_PARTS = 4
"""Three parts of `service` and `shared`, and the projects in series (US-1910/L3)."""
SERIAL_PROJECTS = {"installation", "shared-serial", "realm", "restoration", "contract"}


def test_the_last_part_of_the_paths_against_the_service_plays_them_in_series() -> None:
    assert [e2eparts.service_part(f"{i}/4") for i in (1, 2, 3, 4)] == [
        (1, 3),
        (2, 3),
        (3, 3),
        None,
    ]
    assert e2eparts.service_part("1/2") == (1, 1)
    with pytest.raises(ValueError, match="two parts at least"):
        e2eparts.service_part("1/1")
    with pytest.raises(ValueError, match="i/N"):
        e2eparts.service_part("5/4")
    with pytest.raises(ValueError, match="no test list"):
        e2eparts.service_plan("4/4", SERVICE_LISTING, {}, parallel)


def test_the_parts_but_the_last_share_service_and_shared_each_line_naming_its_project() -> None:
    for count in (2, 3, 4):
        plans = [
            e2eparts.service_plan(f"{i}/{count}", SERVICE_LISTING, {}, parallel)
            for i in range(1, count)
        ]
        lines = [line for plan in plans for line in plan]
        assert sorted(lines) == [
            f"[service]{SEPARATOR}service/account.spec.ts",
            f"[service]{SEPARATOR}service/roles.spec.ts",
            f"[shared]{SEPARATOR}grid.spec.ts",
            f"[shared]{SEPARATOR}wide.spec.ts{SEPARATOR}first{SEPARATOR}one",
            f"[shared]{SEPARATOR}wide.spec.ts{SEPARATOR}second",
        ]
        # the projects in series, and those every part plays, are in no test list
        assert not [line for line in lines if line.split("]")[0][1:] in SERIAL_PROJECTS]


def test_the_service_and_the_shared_paths_are_spread_by_their_own_durations() -> None:
    durations = e2eparts.measure(SERVICE_LOG, parallel, e2eparts.SERVICE)
    assert durations == {
        f"[service]{SEPARATOR}service/account.spec.ts": 5.0,
        f"[shared]{SEPARATOR}grid.spec.ts": 72.0,
        f"[shared]{SEPARATOR}wide.spec.ts{SEPARATOR}first{SEPARATOR}one": 4.0,
    }
    first, second = (
        e2eparts.service_plan(f"{i}/3", SERVICE_LISTING, durations, parallel) for i in (1, 2)
    )
    assert [f"[shared]{SEPARATOR}grid.spec.ts"] in (first, second)
    # an unknown unit weighs the mean of its kind, a file or a test, the project it names aside
    assert e2eparts.is_per_test(f"[shared]{SEPARATOR}wide.spec.ts{SEPARATOR}second")
    assert e2eparts.is_per_test(f"wide.spec.ts{SEPARATOR}second")
    assert not e2eparts.is_per_test(f"[service]{SEPARATOR}service/account.spec.ts")
    assert not e2eparts.is_per_test("grid.spec.ts")


def test_a_refresh_writes_the_durations_of_the_service_apart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(e2eparts, "DURATIONS", tmp_path / "paths.json")
    monkeypatch.setattr(e2eparts, "SERVICE_DURATIONS", tmp_path / "service.json")
    monkeypatch.setattr(e2eparts, "is_parallel", parallel)
    log = tmp_path / "log"
    log.write_text(SERVICE_LOG, encoding="utf-8")
    assert e2eparts.main(["refresh", str(log)]) == 0
    assert not (tmp_path / "paths.json").exists()
    assert e2eparts.read(tmp_path / "service.json") == e2eparts.measure(
        SERVICE_LOG, parallel, e2eparts.SERVICE
    )
    log.write_text("T 0 passed\n", encoding="utf-8")
    assert e2eparts.main(["refresh", str(log)]) == 1


def test_the_command_says_the_part_and_prints_its_test_list(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert e2eparts.main(["service-part", "4/4"]) == 0
    assert e2eparts.main(["service-part", "1/4"]) == 0
    assert capsys.readouterr().out == "serial\nspread\n"
    assert e2eparts.main(["service-part", "1/1"]) == 1
    assert "two parts at least" in capsys.readouterr().err
    target = tmp_path / "service.json"
    e2eparts.write({}, target)
    monkeypatch.setattr(e2eparts, "SERVICE_DURATIONS", target)
    monkeypatch.setattr(e2eparts, "is_parallel", parallel)
    monkeypatch.setattr("sys.stdin", io.StringIO(SERVICE_LISTING))
    assert e2eparts.main(["plan", "--service", "1/2"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == f"[service]{SEPARATOR}service/account.spec.ts"


def test_the_versioned_durations_of_the_service_name_the_paths_of_the_repository() -> None:
    durations = e2eparts.read(e2eparts.SERVICE_DURATIONS)
    assert durations
    for name in durations:
        project, _, unit = name.partition(f"]{SEPARATOR}")
        file = unit.split(SEPARATOR)[0]
        assert project in {"[service", "[shared"}, name
        assert file.startswith("service/") is (project == "[service"), name
        assert (e2eparts.FRONT / "e2e" / file).is_file(), name


def test_the_chain_plays_the_paths_against_the_service_in_four_parts() -> None:
    workflow = yaml.safe_load(
        (REPOSITORY / ".github" / "workflows" / "service.yml").read_text(encoding="utf-8")
    )
    (job,) = workflow["jobs"].values()
    assert job["name"] == "paths (${{ matrix.part }})"
    assert job["strategy"]["fail-fast"] is False
    parts = job["strategy"]["matrix"]["part"]
    assert parts == [f"{i}/{len(parts)}" for i in range(1, len(parts) + 1)]
    assert len(parts) == FOUR_PARTS
    (played,) = [step for step in job["steps"] if step.get("run") == "make check-service"]
    assert played["env"]["SHARD"] == "${{ matrix.part }}"


def make_dry(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run make without running its recipes, as the chain or a developer would call it."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"MAKEFLAGS", "MAKELEVEL", "SHARD", "TESTS"}
    }
    return subprocess.run(
        ["make", "--no-print-directory", "-n", "-C", str(REPOSITORY), *arguments],
        capture_output=True,
        text=True,
        check=False,
        env={
            **environment,
            "E2E_API_PORT": "4110",
            "E2E_FRONT_PORT": "3100",
            "WATERFALL_PROCESSORS": "4",
        },
    )


@pytest.mark.parametrize("target", ["e2e", "e2e-service", "check-service"])
def test_a_part_with_a_file_is_refused_before_anything_is_built(target: str) -> None:
    # #3026: the refusal waited for the installation and the build of the front
    done = make_dry(target, "SHARD=1/2", "TESTS=e2e/a.spec.ts")
    assert done.returncode != 0
    assert "SHARD and TESTS do not combine" in done.stderr
    assert done.stdout == ""


def test_a_part_of_the_paths_against_the_service_is_checked_then_planned() -> None:
    done = make_dry("e2e-service", "SHARD=2/4", "E2E_BUILT=1")
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    checked = next(i for i, line in enumerate(lines) if "e2eparts service-part 2/4 >" in line)
    started = next(i for i, line in enumerate(lines) if "mock-spec" in line)
    assert checked < started
    played = next(line for line in lines if "playwright test $part" in line)
    planned = next(line for line in lines if "e2eparts plan --service 2/4" in line)
    assert "export E2E_SERVICE_SERIAL=1" in planned
    assert lines.index(planned) < lines.index(played)
