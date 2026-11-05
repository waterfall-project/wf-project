# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scripts that run by the system's ``python3``, without uv, compile with it (US-1160).

The guard of the commands (``.claude/settings.json``) and the admission of the heavy runs
(``Makefile``) are started as ``python3 <script>``: no environment, no uv, the interpreter of the
workstation or of the runner. A syntax the target of ruff allows, and that interpreter does not,
would stop every command of an agent. No requirement is cited: it is a tool of the repository.
"""

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from wftools import REPOSITORY

if TYPE_CHECKING:
    from pathlib import Path

SCRIPTS = ("guard.py", "slots.py")


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_compiles_with_the_system_python(script: str, tmp_path: Path) -> None:
    """Compile the script with the ``python3`` the shell finds, as the hook and the Makefile do."""
    python = shutil.which("python3")
    assert python is not None
    source = REPOSITORY / "tools" / "src" / "wftools" / script
    program = (
        "import py_compile, sys\npy_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)\n"
    )
    result = subprocess.run(
        [python, "-I", "-c", program, str(source), str(tmp_path / "compiled.pyc")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
