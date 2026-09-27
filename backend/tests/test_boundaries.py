# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contracts of the core reject what WF-ARC-0010 forbids.

The core has no module yet, so the contracts of ``pyproject.toml`` are applied, unchanged
but for the name of the root package, to a sample package built for each test.
"""

import os
import subprocess
import tomllib
from pathlib import Path
from typing import cast

import pytest

PROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

LAYOUT = {
    "api/__init__.py": "",
    "worker/__init__.py": "",
    "core/__init__.py": "",
    "core/accounts/__init__.py": "",
    "core/accounts/interface.py": "from sample.core.accounts import tables\n",
    "core/accounts/tables.py": "",
    "core/projects/__init__.py": "",
    "core/projects/interface.py": "",
    "core/projects/tables.py": "",
}


def contracts_for(package: str) -> str:
    """Write the import contracts of the project for another root package."""
    settings = tomllib.loads(PROJECT.read_text(encoding="utf-8"))["tool"]["importlinter"]
    lines = [f'[tool.importlinter]\nroot_package = "{package}"\n']
    for contract in settings["contracts"]:
        lines.append("[[tool.importlinter.contracts]]")
        for key, value in contract.items():
            lines.append(f"{key} = {_toml(value, package)}")
        lines.append("")
    return "\n".join(lines)


def _toml(value: object, package: str) -> str:
    if isinstance(value, list):
        items = cast("list[object]", value)
        return "[" + ", ".join(_toml(item, package) for item in items) + "]"
    text = str(value).replace("waterfall", package)
    return f'"{text}"'


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    """Build a package named ``sample`` laid out like ``waterfall``, and its contracts."""
    for name, content in LAYOUT.items():
        path = tmp_path / "sample" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (tmp_path / "sample" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "contracts.toml").write_text(contracts_for("sample"), encoding="utf-8")
    return tmp_path


def lint(sample: Path, module: str, code: str) -> subprocess.CompletedProcess[str]:
    """Add an import to a module of the sample, and run the contracts on it."""
    path = sample / "sample" / f"{module.replace('.', '/')}.py"
    path.write_text(code, encoding="utf-8")
    environment = {**os.environ, "PYTHONPATH": str(sample)}
    return subprocess.run(
        ["lint-imports", "--config", str(sample / "contracts.toml"), "--no-cache"],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def test_a_module_may_use_the_interface_of_another(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample.core.accounts import interface\n")
    assert result.returncode == 0, result.stdout


def test_a_module_that_reads_the_tables_of_another_is_rejected(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample.core.accounts import tables\n")
    assert result.returncode == 1
    assert "sample.core.projects.tables -> sample.core.accounts.tables" in result.stdout


def test_the_core_may_not_import_the_api(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "import sample.api\n")
    assert result.returncode == 1


def test_the_api_may_not_import_the_worker(sample: Path) -> None:
    result = lint(sample, "api.__init__", "import sample.worker\n")
    assert result.returncode == 1


def test_the_package_itself_keeps_its_contracts() -> None:
    result = subprocess.run(
        ["lint-imports", "--no-cache"],
        cwd=PROJECT.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
