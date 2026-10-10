# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API and the worker start, and carry the same version (WF-ARC-0010)."""

import subprocess
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

import pytest

import waterfall
import waterfall.worker.main

PROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def run(script: str) -> str:
    """Run an installed entry point asked for its version and return what it prints."""
    result = subprocess.run([script, "--version"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def test_the_api_the_worker_and_the_migration_command_are_the_entry_points() -> None:
    scripts = {
        entry.name
        for entry in entry_points(group="console_scripts")
        if entry.value.startswith("waterfall.")
    }
    assert scripts == {"waterfall-api", "waterfall-worker", "waterfall-migrate"}


@pytest.mark.parametrize("script", ["waterfall-api", "waterfall-worker", "waterfall-migrate"])
def test_each_command_states_the_version_of_the_package(script: str) -> None:
    assert run(script) == f"{script} {waterfall.__version__}"


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_api_and_the_worker_carry_the_same_version() -> None:
    api = run("waterfall-api").split()[-1]
    worker = run("waterfall-worker").split()[-1]
    declared = tomllib.loads(PROJECT.read_text(encoding="utf-8"))["project"]["version"]
    assert api == worker == declared


def test_the_worker_entry_point_returns_success(capsys: pytest.CaptureFixture[str]) -> None:
    assert waterfall.worker.main.main() == 0
    assert capsys.readouterr().out == f"waterfall-worker {waterfall.__version__}\n"
