# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scripts that run by the system's ``python3``, without uv, compile with it (US-1160).

The guard of the commands (``.claude/settings.json``) and the admission of the heavy runs
(``Makefile``) are started as ``python3 <script>``: no environment, no uv, the interpreter of the
workstation or of the runner. A syntax the target of ruff allows, and that interpreter does not,
would stop every command of an agent. No requirement is cited: it is a tool of the repository.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Sequence

SCRIPTS = ("guard.py", "slots.py")


def _outside_the_venv(entries: Sequence[str]) -> list[str]:
    """Keep the ``PATH`` entries that are neither under ``sys.prefix`` nor the ``VIRTUAL_ENV``."""
    roots = {Path(sys.prefix).resolve()}
    if os.environ.get("VIRTUAL_ENV"):
        roots.add(Path(os.environ["VIRTUAL_ENV"]).resolve())
    kept: list[str] = []
    for entry in entries:
        path = Path(entry).resolve()
        if not any(path == root or root in path.parents for root in roots):
            kept.append(entry)
    return kept


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_compiles_with_the_system_python(script: str, tmp_path: Path) -> None:
    """Compile the script with the system ``python3``, not the one of uv's venv.

    ``make test-tools`` runs under ``uv run``, which puts the venv first on the ``PATH``: the
    ``python3`` is looked up on a ``PATH`` without it, and runs without the environment it set.
    """
    path = os.pathsep.join(_outside_the_venv(os.environ.get("PATH", "").split(os.pathsep)))
    python = shutil.which("python3", path=path)
    assert python is not None
    # The venv's interpreter is a link to the system's: it is told by where it stands, not by
    # where it leads.
    assert Path(python).absolute() != Path(sys.executable).absolute()
    assert Path(sys.prefix).absolute() not in Path(python).absolute().parents
    environment = {
        name: value
        for name, value in os.environ.items()
        if name not in {"VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"}
    }
    environment["PATH"] = path
    source = REPOSITORY / "tools" / "src" / "wftools" / script
    program = (
        "import py_compile, sys\npy_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)\n"
    )
    result = subprocess.run(
        [python, "-I", "-c", program, str(source), str(tmp_path / "compiled.pyc")],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
