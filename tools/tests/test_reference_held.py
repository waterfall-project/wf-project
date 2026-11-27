# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the check that make e2e-reference makes of the platform before the paths (US-2950).

The macro ``reference-held`` is run with a ``docker`` that answers as the platform would: the
count of its projects, or a failure; its threshold is ``REFERENCE_PROJECTS``.
"""

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
MAKEFILE = (REPOSITORY / "Makefile").read_text(encoding="utf-8")


def recipe() -> str:
    """Return the shell of the macro ``reference-held``, variables left as written."""
    macro = re.search(r"^reference-held = (.*?)(?=^\S)", MAKEFILE, re.MULTILINE | re.DOTALL)
    assert macro
    return macro[1].replace("\\\n", " ").replace("$$", "$")


def played(tmp_path: Path, answer: str, threshold: int = 300) -> subprocess.CompletedProcess[str]:
    """Run the recipe with a ``docker`` that prints ``answer``, or fails when it is empty."""
    fake = tmp_path / "docker"
    body = f"echo {answer}" if answer else "exit 1"
    fake.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    shell = recipe().replace("$(COMPOSE_SERVICE)", str(fake))
    shell = shell.replace("$(REFERENCE_PROJECTS)", str(threshold))
    return subprocess.run(
        ["/bin/sh", "-c", shell],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": os.environ["PATH"]},
    )


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_threshold_is_the_size_of_the_reference_set() -> None:
    assert re.search(r"^REFERENCE_PROJECTS \?= 300$", MAKEFILE, re.MULTILINE)


@pytest.mark.requirement("WF-QUA-0040-A")
def test_a_platform_that_holds_less_than_the_set_is_refused_and_told_what_to_run(
    tmp_path: Path,
) -> None:
    refused = played(tmp_path, "299")
    assert refused.returncode == 1
    assert "holds 299 projects, the reference set 300" in refused.stderr
    assert "make service-reference-restore" in refused.stderr
    assert played(tmp_path, "300").returncode == 0


@pytest.mark.requirement("WF-QUA-0040-A")
def test_a_platform_whose_projects_cannot_be_counted_is_refused_and_told_what_to_run(
    tmp_path: Path,
) -> None:
    refused = played(tmp_path, "")
    assert refused.returncode == 1
    assert "cannot be counted" in refused.stderr
    assert "make service-up" in refused.stderr
    assert "make service-reference-restore" in refused.stderr
