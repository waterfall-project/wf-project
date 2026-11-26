# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The platform of the chain runs under a slice of four cores and eight gigabytes (US-2810).

« Le déploiement par Compose aboutit sur une machine conforme à ces caractéristiques. »
(WF-CMP-0020-A): ``production.yml`` bounds a slice of the cgroups of the runner; ``wftools.bounded``
puts every container of the platform, and of the test of a restoration, under it.
"""

import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml
from test_restoretest import SCRIPT, environment, fake_docker

from wftools import REPOSITORY, bounded, production

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-CMP-0020-A"), pytest.mark.story("US-2810")]

OVERRIDE = bounded.RESTORE_TEST_OVERRIDE
PARENT = "waterfall-bounded.slice"
WORKFLOWS = REPOSITORY / ".github" / "workflows"


def test_every_service_of_the_production_runs_under_the_slice_even_those_of_a_profile() -> None:
    written = yaml.safe_load(bounded.override(bounded.PRODUCTION, PARENT))["services"]
    declared = yaml.safe_load(bounded.PRODUCTION[0].read_text(encoding="utf-8"))["services"]
    assert set(written) >= set(declared)
    # The install service, which only a profile starts, and the services of the local file.
    assert {"install", "caddy", "prometheus", "alertmanager", "grafana", "postgres"} <= set(written)
    assert "door-authority" in written
    assert all(service == {"cgroup_parent": PARENT} for service in written.values())


def test_the_ephemeral_platform_of_the_test_of_a_restoration_runs_under_it_too() -> None:
    written = yaml.safe_load(bounded.override(bounded.RESTORE_TEST, PARENT))["services"]
    assert {"restore-test", "restore-test-postgres"} <= set(written)
    assert all(service == {"cgroup_parent": PARENT} for service in written.values())


def test_nothing_is_bounded_nor_written_unless_a_slice_is_named(tmp_path: Path) -> None:
    assert bounded.environment(None, tmp_path) == {}
    assert bounded.environment("", tmp_path) == {}
    assert list(tmp_path.iterdir()) == []


def test_the_files_are_written_and_named_for_the_trial_and_the_script_of_the_test(
    tmp_path: Path,
) -> None:
    given = bounded.environment(PARENT, tmp_path)
    assert given == {
        production.OVERRIDE: str(tmp_path / "bounded.yaml"),
        bounded.RESTORE_TEST_OVERRIDE: str(tmp_path / "bounded-restore-test.yaml"),
    }
    assert PARENT in (tmp_path / "bounded.yaml").read_text(encoding="utf-8")
    assert PARENT in (tmp_path / "bounded-restore-test.yaml").read_text(encoding="utf-8")


def test_compose_reads_the_bound_after_the_files_of_the_platform(tmp_path: Path) -> None:
    command = production.compose_command("p", tmp_path / "bounded.yaml")
    assert command[-2:] == ["--file", str(tmp_path / "bounded.yaml")]
    assert command[-3] == str(production.FILES[-1])
    assert production.compose_command("p")[-1] == str(production.FILES[-1])


def run_script(folder: Path, override: str | None) -> list[str]:
    """Run ``restore-test.sh`` against a ``docker`` that writes down what it is asked."""
    log = fake_docker(folder, hold=False)
    given = {key: value for key, value in environment(folder).items() if key != OVERRIDE}
    if override is not None:
        given[OVERRIDE] = override
    done = subprocess.run(
        ["sh", str(SCRIPT)], env=given, capture_output=True, check=False, timeout=60
    )
    assert done.returncode == 0
    return log.read_text(encoding="utf-8").splitlines()


def test_the_script_of_the_test_reads_the_bound_after_its_own_file_when_it_is_given(
    tmp_path: Path,
) -> None:
    bound = tmp_path / "bounded-restore-test.yaml"
    calls = run_script(tmp_path, str(bound))
    assert calls
    for call in calls:
        assert call.startswith(f"compose --file compose.restore-test.yaml --file {bound} ")


def test_the_script_of_the_test_reads_only_its_own_file_when_nothing_is_bounded(
    tmp_path: Path,
) -> None:
    for call in run_script(tmp_path, None) + run_script(tmp_path, ""):
        assert call.startswith("compose --file compose.restore-test.yaml --profile restore-test ")


def test_the_trial_fails_when_a_container_of_the_platform_is_outside_the_slice() -> None:
    def read(command: list[str]) -> tuple[int, str]:
        if "ps" in command:
            return 0, "a1\nb2\n"
        return 0, f"/caddy {PARENT}\n/grafana \n"

    with pytest.raises(production.ProductionError, match=r"outside the slice .*: grafana"):
        production.check_bounded(["docker", "compose"], read, PARENT)


def test_the_trial_fails_when_the_platform_has_no_container_to_inspect() -> None:
    with pytest.raises(production.ProductionError, match="no container of the platform"):
        production.check_bounded(["docker", "compose"], lambda _command: (0, ""), PARENT)


def test_the_trial_passes_when_every_container_runs_under_the_slice() -> None:
    def read(command: list[str]) -> tuple[int, str]:
        return (0, "a1\nb2\n") if "ps" in command else (0, f"/caddy {PARENT}\n/grafana {PARENT}\n")

    production.check_bounded(["docker", "compose"], read, PARENT)


ACTION = "./.github/actions/bound-platform"


@pytest.mark.parametrize("name", ["production.yml", "images.yml"])
def test_the_chain_bounds_the_slice_before_every_trial_of_the_production(name: str) -> None:
    job = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))["jobs"]["trial"]
    steps = job["steps"]
    bound = next(index for index, step in enumerate(steps) if step.get("uses") == ACTION)
    trial = next(index for index, step in enumerate(steps) if "production" in step.get("run", ""))
    assert bound < trial
    assert job["env"][production.PARENT] == PARENT


def test_the_slice_is_bounded_to_four_cores_and_eight_gigabytes_without_swap_and_read_back() -> (
    None
):
    action = yaml.safe_load((REPOSITORY / ACTION / "action.yml").read_text(encoding="utf-8"))
    (step,) = action["runs"]["steps"]
    for setting in ("MemoryMax=8G", "MemorySwapMax=0", "CPUQuota=400%"):
        assert setting in step["run"]
    assert "waterfall-bounded.slice" in step["run"]
    assert PARENT == "waterfall-bounded.slice"
    assert "8589934592" in step["run"]
    # Four cores are the whole of a runner of four: a cpuset would bound nothing, and fail on two.
    assert "AllowedCPUs" not in step["run"]
    assert "CPUQuotaPerSecUSec" in step["run"]
