# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The platform of the chain runs under a slice of four cores and eight gigabytes (US-2810).

« Le déploiement par Compose aboutit sur une machine conforme à ces caractéristiques. »
(WF-CMP-0020-A): ``production.yml`` bounds a slice of the cgroups of the runner; ``wftools.bounded``
puts every container of the platform, and of the test of a restoration, under it.
"""

from typing import TYPE_CHECKING

import pytest
import yaml

from wftools import REPOSITORY, bounded, production

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-CMP-0020-A"), pytest.mark.story("US-2810")]

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


def test_the_script_of_the_test_reads_the_bound_when_it_is_given() -> None:
    script = (REPOSITORY / "deploy" / "compose" / "restore-test.sh").read_text(encoding="utf-8")
    assert bounded.RESTORE_TEST_OVERRIDE in script


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
    for setting in ("MemoryMax=8G", "MemorySwapMax=0", "CPUQuota=400%", "AllowedCPUs=0-3"):
        assert setting in step["run"]
    assert "waterfall-bounded.slice" in step["run"]
    assert PARENT == "waterfall-bounded.slice"
    assert "8589934592" in step["run"]
