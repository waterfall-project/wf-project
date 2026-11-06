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
import re
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
# The modules of the projects and of the revisions (EP-04), one file per subject.
PROJECT_INTERFACES: dict[str, set[str]] = {
    "projects": {"projects", "contributors", "subprojects", "work_breakdown", "lifecycle"},
    "revisions": {"revisions", "structures", "marking", "reference"},
}
# What the design names of each (EP-04, "Modules"), declared from US-0910/L1 on, which the other
# stories call before theirs fill them.
DESIGNED: dict[str, set[str]] = {
    "projects": {
        "read_project",
        "list_projects",
        "create_project",
        "update_project",
        "contributor_kind",
        "next_state",
        "advance",
        "exit_project",
        "list_state_transitions",
        "no_background_task_running",
        "project_label",
        "project_code",
        "load_project",
    },
    "revisions": {
        "list_revisions",
        "read_revision",
        "create_revision",
        "copy_revision",
        "abandon_revision",
        "mark_revision",
        "designate_reference",
        "revision_has_tasks_and_lines",
        "compute_indicators",
        "current_revision",
        "revision_draft",
        "create_project_partitions",
        "load_revision",
    },
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


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(("module", "files"), PROJECT_INTERFACES.items())
def test_the_projects_and_the_revisions_offer_their_interface_as_a_package_by_subject(
    module: str, files: set[str]
) -> None:
    interface = importlib.import_module(f"waterfall.core.{module}.interface")
    held = {info.name for info in pkgutil.iter_modules(interface.__path__)}
    assert held == files
    offered = set(interface.__all__)
    assert DESIGNED[module] <= offered
    # Each name is the one its file declares, re-exported: a function of a file alone, or of the
    # package alone, would be another.
    for name in offered:
        declared = getattr(interface, name)
        source = getattr(declared, "__module__", f"{interface.__name__}.?")
        assert source.rsplit(".", 1)[0] == interface.__name__, name


STUB_STATEMENTS = 2


def is_stub(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Tell whether a body is a stub: a docstring at most, ``msg = "..."``, then the raise."""
    body = list(function.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body.pop(0)
    if len(body) != STUB_STATEMENTS:
        return False
    assign, raised = body
    return (
        isinstance(assign, ast.Assign)
        and len(assign.targets) == 1
        and isinstance(assign.targets[0], ast.Name)
        and assign.targets[0].id == "msg"
        and isinstance(assign.value, ast.Constant)
        and isinstance(assign.value.value, str)
        and isinstance(raised, ast.Raise)
        and isinstance(raised.exc, ast.Call)
        and isinstance(raised.exc.func, ast.Name)
        and raised.exc.func.id == "NotImplementedError"
        and [a.id for a in raised.exc.args if isinstance(a, ast.Name)] == ["msg"]
        and len(raised.exc.args) == 1
    )


def functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """List every function of a tree, nested ones and ``async`` ones included."""
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]


def refuses(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Tell whether a function's own body (not a nested one's) raises NotImplementedError."""
    pending: list[ast.AST] = list(function.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        if isinstance(node, ast.Raise):
            target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if isinstance(target, ast.Name) and target.id == "NotImplementedError":
                return True
        pending.extend(ast.iter_child_nodes(node))
    return False


def malformed_stubs(source: str) -> list[str]:
    """Name the functions of a source that raise NotImplementedError without being a stub."""
    return [f.name for f in functions(ast.parse(source)) if refuses(f) and not is_stub(f)]


def interface_sources() -> list[tuple[str, str]]:
    """List (file, source) of each file of the two interfaces, subpackages included."""
    found: list[tuple[str, str]] = []
    for module in PROJECT_INTERFACES:
        interface = importlib.import_module(f"waterfall.core.{module}.interface")
        for directory in interface.__path__:
            found.extend(
                (f"{module}/{path.name}", path.read_text(encoding="utf-8"))
                for path in sorted(Path(directory).rglob("*.py"))
            )
    return found


def stubs() -> list[tuple[str, str, str]]:
    """List (file, function, message) of each stub the files of the two interfaces declare.

    Read from the code, not from a list: a function a story fills leaves it alone. The silent ones
    (the design gives them a documented result without effect) are not stubs, and need no list.
    """
    found: list[tuple[str, str, str]] = []
    for file, source in interface_sources():
        for node in functions(ast.parse(source)):
            if is_stub(node):
                assign = node.body[-2]
                assert isinstance(assign, ast.Assign)
                assert isinstance(assign.value, ast.Constant)
                found.append((file, node.name, str(assign.value.value)))
    return found


@pytest.mark.requirement("WF-ARC-0010-A")
def test_no_function_of_the_interfaces_raises_not_implemented_without_being_a_stub() -> None:
    # True whatever the number of stubs left, none included: the sweep and `is_stub` agree.
    assert [(f, m) for f, s in interface_sources() for m in malformed_stubs(s)] == []


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    "source",
    [
        "def f():\n    raise NotImplementedError('f is filled by US-0001')\n",
        "async def f():\n    msg = 1\n    raise NotImplementedError(msg)\n",
        "async def f():\n    raise NotImplementedError\n",
        "def g():\n    def f():\n        raise NotImplementedError('x')\n    return f\n",
        (
            "class C:\n    def f(self):\n        msg = 'x'\n        print(msg)\n"
            "        raise NotImplementedError(msg)\n"
        ),
    ],
)
def test_the_sweep_of_the_stubs_rejects_a_malformed_or_async_or_nested_stub(source: str) -> None:
    assert malformed_stubs(source) == ["f"]


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    "source",
    [
        "async def f():\n    msg = 'f is filled by US-0001'\n    raise NotImplementedError(msg)\n",
        (
            "def g():\n    def f():\n        msg = 'f is filled by US-0001'\n"
            "        raise NotImplementedError(msg)\n"
        ),
    ],
)
def test_the_sweep_of_the_stubs_accepts_a_well_formed_stub_async_or_nested(source: str) -> None:
    assert malformed_stubs(source) == []


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(("file", "name", "message"), stubs())
def test_a_stub_of_the_projects_and_the_revisions_refuses_naming_the_story_that_fills_it(
    file: str, name: str, message: str
) -> None:
    # A caller that reaches a function before its story fills it must fail, not read or write
    # nothing: a green test would hide a refusal (`revision_draft`) that does not exist yet.
    assert re.fullmatch(rf"{name} is filled by US-\d{{4}}(/L\d+)?", message), (file, message)


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
    assert imported(statement) == "['waterfall.core.users.tables']"
    # The package of the core, alone, holds the tables of none.
    statement = "import sys, waterfall.core; print(any(m.endswith('.tables') for m in sys.modules))"
    assert imported(statement) == "False"


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
