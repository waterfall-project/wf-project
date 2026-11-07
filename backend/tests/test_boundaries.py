# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contracts of the core reject what WF-ARC-0010 forbids.

The core has no module yet, so the contracts of ``pyproject.toml`` are applied, unchanged
but for the name of the root package, to a sample package built for each test.
"""

import ast
import importlib
import os
import pkgutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import cast

import pytest

PROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

LAYOUT = {
    "witness/__init__.py": "",
    "bootstrap.py": "",
    "restore/__init__.py": "",
    "api/__init__.py": "",
    "worker/__init__.py": "",
    "migrations/__init__.py": "",
    "schema.py": "",
    "core/__init__.py": "",
    "platform/__init__.py": "",
    "core/accounts/__init__.py": "",
    "core/accounts/interface.py": "from sample.core.accounts import tables\n",
    "core/accounts/tables.py": "",
    "core/projects/__init__.py": "",
    "core/projects/interface.py": "",
    "core/projects/tables.py": "",
    # An interface in a package: one file per object, re-exported by the package.
    "core/settings/__init__.py": "",
    "core/settings/interface/__init__.py": (
        "from sample.core.settings.interface.rates import RATE\n"
    ),
    "core/settings/interface/rates.py": "from sample.core.settings import tables\nRATE = 1\n",
    "core/settings/tables.py": "",
}
# The modules of the reference (EP-05), and the files of the interface of each, one per object.
REFERENCE_INTERFACES: dict[str, set[str]] = {
    "cost_settings": {
        "reference_settings",
        "readiness",
        "cost_types",
        "cost_categories",
        "hourly_rates",
        "actual_cost_mapping",
    },
    "resource_settings": {
        "readiness",
        "org_nodes",
        "resource_roles",
        "calendars",
        "duration_units",
    },
    "risk_settings": set(),
    "indicator_settings": set(),
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


@pytest.mark.requirement("WF-ARC-0010-A")
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


def test_the_platform_may_be_imported_by_the_core_the_api_and_the_worker(sample: Path) -> None:
    for module in ("core.projects.tables", "api.__init__", "worker.__init__"):
        result = lint(sample, module, "import sample.platform\n")
        assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("imported", ["core.projects.interface", "api", "worker"])
def test_the_platform_may_not_import_the_core_the_api_or_the_worker(
    sample: Path, imported: str
) -> None:
    result = lint(sample, "platform.__init__", f"import sample.{imported}\n")
    assert result.returncode == 1
    assert f"sample.platform -> sample.{imported}" in result.stdout


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_core_may_not_import_the_schema(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample import schema\n")
    assert result.returncode == 1
    assert "sample.core.projects.tables -> sample.schema" in result.stdout


def test_the_entry_points_may_import_the_schema_which_may_import_the_core(sample: Path) -> None:
    (sample / "sample" / "schema.py").write_text("from sample.core.projects import tables\n")
    result = lint(sample, "api.__init__", "from sample import schema\n")
    assert result.returncode == 0, result.stdout


def test_the_core_may_not_import_the_migrations(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample import migrations\n")
    assert result.returncode == 1


def test_the_bootstrap_may_apply_the_migrations(sample: Path) -> None:
    # The bootstrap applies the migrations, which the API may not import (US-0420).
    imports = "import sample.migrations\nimport sample.api\nimport sample.core.accounts.interface\n"
    result = lint(sample, "bootstrap", imports)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("module", ["api.__init__", "migrations.__init__", "core.projects.tables"])
def test_nothing_imports_the_bootstrap(sample: Path, module: str) -> None:
    result = lint(sample, module, "import sample.bootstrap\n")
    assert result.returncode == 1
    assert f"sample.{module.removesuffix('.__init__')} -> sample.bootstrap" in result.stdout


def test_the_service_of_the_restoration_may_apply_the_migrations_and_run_as_the_worker(
    sample: Path,
) -> None:
    # The restoration applies the migrations and runs as the worker does (#953).
    imports = (
        "import sample.migrations\nimport sample.worker\nimport sample.core.accounts.interface\n"
    )
    result = lint(sample, "restore.__init__", imports)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("module", ["worker.__init__", "api.__init__", "core.projects.tables"])
def test_nothing_imports_the_service_of_the_restoration(sample: Path, module: str) -> None:
    result = lint(sample, module, "import sample.restore\n")
    assert result.returncode == 1
    assert f"sample.{module.removesuffix('.__init__')} -> sample.restore" in result.stdout


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_module_may_use_an_interface_in_a_package_but_none_of_its_files(sample: Path) -> None:
    through = lint(
        sample, "core.projects.tables", "from sample.core.settings.interface import RATE\n"
    )
    assert through.returncode == 0, through.stdout
    beside = "from sample.core.settings.interface.rates import RATE\n"
    result = lint(sample, "core.projects.tables", beside)
    assert result.returncode == 1
    assert "sample.core.projects.tables -> sample.core.settings.interface.rates" in result.stdout


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.parametrize("module", ["bootstrap", "api.__init__", "core.projects.tables"])
def test_nothing_imports_the_loader_of_the_witness(sample: Path, module: str) -> None:
    result = lint(sample, module, "import sample.witness\n")
    assert result.returncode == 1
    assert f"sample.{module.removesuffix('.__init__')} -> sample.witness" in result.stdout


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_loader_of_the_witness_may_run_the_bootstrap_and_write_through_the_interfaces(
    sample: Path,
) -> None:
    # It passes on what is not its own to the bootstrap, and reads the models of the contract.
    imports = "import sample.bootstrap\nimport sample.api\nimport sample.core.accounts.interface\n"
    result = lint(sample, "witness.__init__", imports)
    assert result.returncode == 0, result.stdout


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(("module", "files"), REFERENCE_INTERFACES.items())
def test_each_module_of_the_reference_offers_its_interface_as_a_package_of_one_file_per_object(
    module: str, files: set[str]
) -> None:
    interface = importlib.import_module(f"waterfall.core.{module}.interface")
    held = {info.name for info in pkgutil.iter_modules(interface.__path__)}
    assert held == files


def imported(statement: str) -> str:
    """Run a statement in a fresh interpreter, and give what it prints."""
    done = subprocess.run(
        [sys.executable, "-c", statement], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


@pytest.mark.requirement("WF-ARC-0010-A")
def test_importing_a_module_of_the_core_declares_the_tables_of_no_other() -> None:
    # The tables of every module are declared together by ``waterfall.schema``, which the entry
    # points import: the core itself imports no module's tables by way of another.
    statement = (
        "import sys, waterfall.core.users.interface;"
        "print(sorted(m for m in sys.modules if m.endswith('.tables')))"
    )
    # An account is attached to a node of the resource settings: it asks that module, by its
    # interface, which brings its own tables — and theirs alone, the resource settings reading no
    # other module (#2109, #2114). Exactly the tables of the two modules, no fewer, no more.
    users, resources = "waterfall.core.users.tables", "waterfall.core.resource_settings.tables"
    assert set(ast.literal_eval(imported(statement))) == {users, resources}
    # The package of the core, alone, holds the tables of none.
    statement = "import sys, waterfall.core; print(any(m.endswith('.tables') for m in sys.modules))"
    assert imported(statement) == "False"


def interfaces() -> list[str]:
    """Name the interface of every module of the core, as a package or as a file."""
    core = Path(importlib.import_module("waterfall.core").__file__ or "").parent
    return sorted(
        f"waterfall.core.{module.name}.interface"
        for module in pkgutil.iter_modules([str(core)])
        if (core / module.name / "interface.py").exists()
        or (core / module.name / "interface" / "__init__.py").exists()
    )


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_resource_settings_import_nothing_of_the_cost_settings_which_read_them() -> None:
    # The cost settings ask the resource settings what binds a category (``category_has_roles``);
    # the roles are told of their category by their caller: no cycle between the two.
    statement = (
        "import sys, waterfall.core.resource_settings.interface;"
        "print(sorted(m for m in sys.modules if m.startswith('waterfall.core.cost_settings')))"
    )
    assert ast.literal_eval(imported(statement)) == []


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize("interface", interfaces())
def test_the_interface_of_each_module_of_the_core_is_imported_alone(interface: str) -> None:
    # In a fresh interpreter, first: a cycle between two interfaces fails the import of one.
    assert imported(f"import {interface}; print('imported')") == "imported"


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_schema_declares_the_tables_of_every_module_and_the_entry_points_import_it() -> None:
    statement = (
        "import waterfall.schema; from waterfall.platform.database import Base;"
        "print(len(Base.metadata.tables))"
    )
    # An entry point alone declares what a foreign key of the reference names (``user_account``).
    entry = (
        "import waterfall.{}, waterfall.platform.database as d;"
        "print('user_account' in d.Base.metadata.tables and 'cost_type' in d.Base.metadata.tables)"
    )
    assert int(imported(statement)) >= 10
    for module in ("api.app", "worker.main", "bootstrap", "witness.main"):
        assert imported(entry.format(module)) == "True", module
    # The environment of the migrations runs on import, against a database: its source is read.
    env = Path(__file__).resolve().parents[1] / "src/waterfall/migrations/env.py"
    calls = [
        node
        for node in ast.walk(ast.parse(env.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "declared"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "schema"
    ]
    assert calls


def test_the_package_itself_keeps_its_contracts() -> None:
    result = subprocess.run(
        ["lint-imports", "--no-cache"],
        cwd=PROJECT.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
