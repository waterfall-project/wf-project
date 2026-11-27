# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The oldest version of Kubernetes the chart declares is tried, and is maintained (US-2810).

« Le chart s'installe sur deux distributions de Kubernetes différentes sans modification. »
(WF-CMP-0020-A, #5069): the node of kind the trial makes is that of the ``kubeVersion`` of
``Chart.yaml``, and a ``kubeVersion`` older than the oldest version maintained is refused.
"""

import re
from typing import TYPE_CHECKING

import pytest

from wftools import kubeversions
from wftools.charttrial import Tools, Trial
from wftools.kubeversions import VersionError
from wftools.production import Platform

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-CMP-0020-A"), pytest.mark.story("US-2810")]

PLATFORM = Platform("waterfall.localhost", 41443, 0)


def chart_of(folder: Path, constraint: str) -> Path:
    """Write a ``Chart.yaml`` that declares a ``kubeVersion`` and return its path."""
    written = folder / "Chart.yaml"
    written.write_text(f'name: x\nkubeVersion: "{constraint}"\n', encoding="utf-8")
    return written


def list_of(folder: Path, versions: str) -> Path:
    """Write a list of maintained versions, each ending long after the date of the list."""
    entries = "".join(
        f'[[maintained]]\nversion = "{version}"\nend_of_life = 2030-01-01\n\n'
        for version in versions.split()
    )
    written = folder / "maintained.toml"
    written.write_text(f"as_of = 2026-11-27\n\n{entries}", encoding="utf-8")
    return written


@pytest.mark.parametrize(
    ("constraint", "node"),
    [(">=1.35.0-0", "v1.35."), (">=1.36.0-0", "v1.36."), (">=1.34.2", "v1.34.")],
)
def test_the_node_tried_is_that_of_the_kube_version_of_the_chart(
    tmp_path: Path, constraint: str, node: str
) -> None:
    assert kubeversions.node(chart_of(tmp_path, constraint)).startswith(f"kindest/node:{node}")


def test_the_node_tried_follows_the_chart_of_the_repository() -> None:
    minimum = kubeversions.minimum()
    assert minimum == (1, 35)
    assert kubeversions.node().startswith(f"kindest/node:v{kubeversions.text(minimum)}.")


def test_the_nodes_are_pinned_by_digest_like_every_image_of_the_repository() -> None:
    for (major, minor), node in kubeversions.NODES.items():
        assert re.fullmatch(rf"kindest/node:v{major}\.{minor}\.\d+@sha256:[0-9a-f]{{64}}", node)


def test_a_version_without_a_pinned_node_is_refused_not_guessed(tmp_path: Path) -> None:
    with pytest.raises(VersionError, match=r"no node of kind is pinned for Kubernetes 1\.99"):
        kubeversions.node(chart_of(tmp_path, ">=1.99.0-0"))


@pytest.mark.parametrize("constraint", ["1.35.0", ">=1.35", ">=1.35.0 <1.38.0", "~1.35.0"])
def test_a_kube_version_in_another_form_is_refused(tmp_path: Path, constraint: str) -> None:
    with pytest.raises(VersionError, match="kubeVersion"):
        kubeversions.minimum(chart_of(tmp_path, constraint))


def test_the_trial_of_kind_makes_the_cluster_of_the_node_of_the_chart(tmp_path: Path) -> None:
    ran: list[list[str]] = []

    def run(command: list[str]) -> int:
        ran.append(command)
        return 0

    def read(command: list[str]) -> tuple[int, str]:
        ran.append(command)
        return 0, ""

    trial = Trial(Tools(["kind"], ["kubectl"], ["helm"]), run, read, tmp_path, PLATFORM)
    trial.create("c", None)
    command = ran[0]
    assert command[:3] == ["kind", "create", "cluster"]
    assert command[command.index("--image") + 1] == kubeversions.node()


def test_a_kube_version_older_than_the_oldest_maintained_is_refused(tmp_path: Path) -> None:
    maintained = list_of(tmp_path, "1.35 1.36")
    with pytest.raises(VersionError, match=r"is 1\.34, older than 1\.35"):
        kubeversions.check(chart_of(tmp_path, ">=1.34.0-0"), maintained)


@pytest.mark.parametrize("constraint", [">=1.35.0-0", ">=1.36.0-0"])
def test_a_kube_version_as_old_as_the_oldest_maintained_or_newer_is_accepted(
    tmp_path: Path, constraint: str
) -> None:
    kubeversions.check(chart_of(tmp_path, constraint), list_of(tmp_path, "1.35 1.36"))


def test_the_chart_of_the_repository_is_not_older_than_the_list_of_the_repository() -> None:
    kubeversions.check()
    listed = kubeversions.maintained()
    assert listed.versions[0] == (1, 35)
    assert str(listed.as_of) == "2026-11-27"


def test_a_list_with_a_version_already_ended_is_refused_as_stale(tmp_path: Path) -> None:
    stale = tmp_path / "stale.toml"
    stale.write_text(
        'as_of = 2026-11-27\n\n[[maintained]]\nversion = "1.34"\nend_of_life = 2026-10-27\n',
        encoding="utf-8",
    )
    with pytest.raises(VersionError, match="ends on 2026-10-27"):
        kubeversions.maintained(stale)


def test_a_list_without_a_version_is_refused(tmp_path: Path) -> None:
    empty = tmp_path / "empty.toml"
    empty.write_text("as_of = 2026-11-27\nmaintained = []\n", encoding="utf-8")
    with pytest.raises(VersionError, match="lists no version"):
        kubeversions.maintained(empty)


def test_the_check_fails_and_says_why_on_a_kube_version_no_longer_maintained(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert kubeversions.main(chart_of(tmp_path, ">=1.34.0-0"), list_of(tmp_path, "1.35")) == 1
    assert "older than 1.35" in capsys.readouterr().err


def test_the_check_passes_on_the_chart_and_the_list_of_the_repository() -> None:
    assert kubeversions.main() == 0
