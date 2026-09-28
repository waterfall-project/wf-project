# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The Python rule set rejects what WF-QUA-0030 says it must.

Each test writes a deliberate fault in a scratch file and runs the tool of the chain on it,
with the repository's own configuration: a type error, a rule violation, a format drift, a
complexity of 15. The same file without the fault passes, so that the failure is the
fault's and not the scratch file's.
"""

import json
import subprocess
from pathlib import Path

import pytest

from wftools import REPOSITORY

pytestmark = pytest.mark.requirement("WF-QUA-0030-A")

RUFF_CONFIG = str(REPOSITORY / "ruff.toml")
# Written in pieces, so that REUSE does not read this file's licence in the scratch header.
SPDX = "SPDX-"
HEADER = (
    f"# {SPDX}FileCopyrightText: 2026 waterfall-project\n"
    f"# {SPDX}License-Identifier: AGPL-3.0-only\n"
    '"""Scratch module."""\n'
)


def run(*command: str, cwd: Path) -> int:
    """Run a tool of the chain, and return its exit status."""
    return subprocess.run(command, cwd=cwd, capture_output=True, check=False).returncode


def ruff_check(tmp_path: Path, body: str, *select: str) -> int:
    """Lint a scratch module with the rule set of the repository, or some of its rules."""
    (tmp_path / "scratch.py").write_text(HEADER + body, encoding="utf-8")
    only = ["--select", ",".join(select)] if select else []
    return run("ruff", "check", "--config", RUFF_CONFIG, *only, "scratch.py", cwd=tmp_path)


def branches(count: int) -> str:
    """Return a function whose cyclomatic complexity is ``count + 1``."""
    tests = "".join(f"    if x == {n}:\n        y = {n}\n" for n in range(count))
    return f'\n\ndef f(x: int) -> int:\n    """Branch."""\n    y = 0\n{tests}    return y\n'


def test_a_clean_module_passes(tmp_path: Path) -> None:
    assert ruff_check(tmp_path, "\nX = 1\n") == 0


def test_a_rule_violation_fails(tmp_path: Path) -> None:
    assert ruff_check(tmp_path, "\nimport os\n") == 1


def test_a_complexity_of_fifteen_fails_and_fourteen_passes(tmp_path: Path) -> None:
    # The two rules that measure it, at the thresholds the repository sets for them.
    assert ruff_check(tmp_path, branches(13), "C901", "PLR0912") == 0
    assert ruff_check(tmp_path, branches(14), "C901", "PLR0912") == 1


def test_a_format_drift_fails(tmp_path: Path) -> None:
    (tmp_path / "scratch.py").write_text(HEADER + "\nX  =  1\n", encoding="utf-8")
    assert (
        run("ruff", "format", "--check", "--config", RUFF_CONFIG, "scratch.py", cwd=tmp_path) == 1
    )


@pytest.fixture
def strict(tmp_path: Path) -> Path:
    """Make a scratch project with the Pyright settings of the repository's projects."""
    settings = {"typeCheckingMode": "strict", "enableTypeIgnoreComments": False}
    (tmp_path / "pyrightconfig.json").write_text(json.dumps(settings), encoding="utf-8")
    return tmp_path


def test_a_type_error_fails(strict: Path) -> None:
    (strict / "scratch.py").write_text('X: int = "a"\n', encoding="utf-8")
    assert run("pyright", cwd=strict) == 1


def test_a_silenced_type_error_still_fails(strict: Path) -> None:
    silenced = 'X: int = "a"  # type' + ": ignore\n"
    (strict / "scratch.py").write_text(silenced, encoding="utf-8")
    assert run("pyright", cwd=strict) == 1


def test_a_well_typed_module_passes(strict: Path) -> None:
    (strict / "scratch.py").write_text("X: int = 1\n", encoding="utf-8")
    assert run("pyright", cwd=strict) == 0
